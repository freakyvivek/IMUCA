"""
IMUCA Synthetic Benchmark Suite Generator (v2).

Builds on the Milestone-1 single-scenario generator (``synthetic_data.py``), which is
kept frozen at v1.0.0 so that historical datasets and results stay reproducible.

This module adds:
- Measurand-specific forward models:
    * DC voltage: direct ADC channel with offset, gain, parabolic INL bow, noise, quantisation.
    * DC current: shunt model I_obs = V_shunt,obs / R_nominal with resistor tolerance,
      temperature coefficient (TCR) and optional first-order self-heating.
    * Temperature: first-order thermal-lag probe with offset, gain, noise, quantisation.
- An independent simulated reference instrument with its own (non-perfect) error model
  and a stated expanded uncertainty per reading.
- Per-sample fault-type labels plus an event table (onset, duration, magnitude).
- Run-level calibration / validation / test partitions with independent seed roots.
- Deterministic CSV export with SHA-256 manifest and per-scenario metadata JSON.

Column-role convention (also exported in every metadata file):
    <measurand>                 DUT observation (what the instrument reports)
    reference_*                 simulated reference-instrument observation
    true_*                      simulation ground truth (never a measurement)
    error_vs_true / error_vs_reference   derived errors
    is_injected_fault, label_*  ground-truth labels
    dq_flags                    flags derivable from observable fields only

All numeric parameters are simulation assumptions documented in
``config/synthetic_suite_config.json``. They are not specifications of any physical sensor.
"""

from __future__ import annotations
import copy
import hashlib
import io
import json
import os
import zlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.signal import lfilter


GENERATOR_NAME = "IMUCA Synthetic Benchmark Suite Generator"
GENERATOR_VERSION = "2.0.0"
DATA_SOURCE_TAG = "synthetic_suite_v2"

PARTITIONS = ("calibration", "validation", "test")
PARTITION_ABBR = {"calibration": "CAL", "validation": "VAL", "test": "TST"}
MEASURAND_UNITS = {"voltage_V": "V", "current_mA": "mA", "temperature_C": "degC"}
STATUS_OK = "OK"
NO_LABEL = "none"
CSV_FLOAT_FORMAT = "%.10g"

FAULT_TYPES = (
    "isolated_spike", "offset_shift", "gain_change", "gradual_drift", "abrupt_change",
    "stuck_signal", "missing_samples", "duplicate_sequence", "communication_gap",
    "invalid_status", "non_finite",
)
# Faults added to the analogue signal before quantisation
VALUE_FAULTS = {"isolated_spike", "offset_shift", "gain_change", "gradual_drift", "abrupt_change"}
# Faults that persist from onset to the end of the run
PERSISTENT_FAULTS = {"offset_shift", "gain_change", "gradual_drift"}
# Faults that replace the digitised reading or its status
POST_QUANT_FAULTS = {"stuck_signal", "missing_samples", "non_finite", "invalid_status"}
# Faults that add or remove whole records
RECORD_FAULTS = {"duplicate_sequence", "communication_gap"}
SINGLE_SAMPLE_FAULTS = {"isolated_spike", "non_finite", "duplicate_sequence"}

FAULT_OBSERVABILITY = {
    "isolated_spike": "Usually observable from the DUT signal alone when the magnitude is large relative to noise; spikes near the noise floor are not reliably separable.",
    "offset_shift": "AMBIGUOUS from the DUT signal alone: indistinguishable from a genuine process step unless a reference or redundant sensor is available.",
    "gain_change": "AMBIGUOUS from the DUT signal alone: at a single operating point it is indistinguishable from an offset shift or a process change; needs a reference at several operating points.",
    "gradual_drift": "AMBIGUOUS from the DUT signal alone: a slow sensor drift cannot be separated from a slow true process change without a reference; not detectable pointwise.",
    "abrupt_change": "AMBIGUOUS from the DUT signal alone: a transient sensor level shift resembles a short genuine process step.",
    "stuck_signal": "Observable only when the expected noise exceeds the quantisation step; for coarse quantisation on a stable input, repeated identical readings are normal behaviour.",
    "missing_samples": "Observable from the record (empty value field).",
    "duplicate_sequence": "Observable from record metadata (repeated sequence number), not from the signal.",
    "communication_gap": "Observable from record metadata (sequence and time jump). The dropped records do not exist, so the label is attached to the first record after the gap.",
    "invalid_status": "Observable from the status field; the accompanying value may look plausible.",
    "non_finite": "Observable from the record (non-finite value).",
}

FAULT_MAGNITUDE_SEMANTICS = {
    "isolated_spike": "additive value in measurand units, applied to one sample",
    "offset_shift": "additive value in measurand units, persistent from onset",
    "gain_change": "relative gain change (dimensionless), persistent from onset",
    "gradual_drift": "drift rate in measurand units per second, persistent from onset",
    "abrupt_change": "additive value in measurand units, applied for 'duration' samples",
    "stuck_signal": "no magnitude; the digitised reading is frozen at the last value before onset",
    "missing_samples": "no magnitude; value field is empty (NaN)",
    "duplicate_sequence": "no magnitude; an exact copy of the record is inserted after it",
    "communication_gap": "no magnitude; 'duration' records are dropped",
    "invalid_status": "no magnitude; status field set to a non-OK code",
    "non_finite": "value replaced by +inf or -inf",
}


# ==============================================================================
# Data containers
# ==============================================================================

@dataclass
class FaultEvent:
    """One injected fault event. Indices refer to the original sample index (sequence_number - 1)."""
    event_id: str
    run_id: str
    fault_type: str
    onset_index: int
    duration_samples: Optional[int]           # None = persists to end of run
    magnitude: Optional[float] = None
    magnitude_unit: str = ""
    status_code: Optional[str] = None
    non_finite_value: Optional[str] = None
    onset_sequence_number: int = 0
    onset_elapsed_ms: float = 0.0
    labelled_row_count: int = 0
    observability: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Profile:
    """True (ground-truth) trajectory of the measurand plus protocol annotations."""
    true_values: np.ndarray
    condition: np.ndarray
    setpoint_index: np.ndarray
    protocol_phase: np.ndarray
    process_event: np.ndarray


# ==============================================================================
# Helpers
# ==============================================================================

def derive_run_seed(seed_root: int, scenario_id: str, run_number: int) -> int:
    """
    Deterministic per-run seed. Each partition has its own seed root, so final-test
    runs are drawn from a stream that is independent of calibration/validation runs.
    """
    ss = np.random.SeedSequence(entropy=int(seed_root), spawn_key=(zlib.crc32(scenario_id.encode("utf-8")), int(run_number)))
    return int(ss.generate_state(1, dtype=np.uint32)[0])


def first_order_lag(x: np.ndarray, tau_s: float, dt_s: float) -> np.ndarray:
    """
    Exact zero-order-hold discretisation of dy/dt = (x - y) / tau:
        y[k] = y[k-1] + a * (x[k] - y[k-1]),  a = 1 - exp(-dt / tau)
    The sensor starts in equilibrium with the first input sample (y[0] = x[0]).
    """
    x = np.asarray(x, dtype=float)
    if tau_s <= 0 or len(x) == 0:
        return x.copy()
    a = 1.0 - np.exp(-dt_s / tau_s)
    y, _ = lfilter([a], [1.0, -(1.0 - a)], x, zi=[(1.0 - a) * x[0]])
    return y


def quantize(x: np.ndarray, step: Optional[float]) -> np.ndarray:
    if step is None or step <= 0:
        return np.asarray(x, dtype=float)
    return np.round(np.asarray(x, dtype=float) / step) * step


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _draw(rng: np.random.Generator, spec_value: Any, integer: bool = False):
    """Draw from [lo, hi] when a range is given, else return the scalar."""
    if isinstance(spec_value, (list, tuple)):
        lo, hi = spec_value
        if integer:
            return int(rng.integers(int(lo), int(hi) + 1))
        return float(rng.uniform(float(lo), float(hi)))
    return int(spec_value) if integer else float(spec_value)


# ==============================================================================
# Profiles (ground-truth trajectories)
# ==============================================================================

def build_profile(p: Dict[str, Any], period_s: float, rng: np.random.Generator) -> Profile:
    ptype = p["type"]
    vals: List[float] = []
    cond: List[str] = []
    sp_idx: List[int] = []
    phase: List[str] = []
    event: List[str] = []

    def add(n: int, v, c: str, s: int, ph: str, first_event: str = NO_LABEL):
        v_arr = np.broadcast_to(np.asarray(v, dtype=float), (n,))
        vals.extend(v_arr.tolist())
        cond.extend([c] * n)
        sp_idx.extend([s] * n)
        phase.extend([ph] * n)
        event.extend([first_event] + [NO_LABEL] * (n - 1))

    if ptype == "sweep":
        pts = [(float(v), g["condition"]) for g in p["setpoint_groups"] for v in g["values"]]
        pts.sort(key=lambda t: t[0], reverse=(p.get("order", "ascending") == "descending"))
        for i, (v, c) in enumerate(pts):
            add(int(p["dwell_samples"]), v, c, i, "dwell", "setpoint_change" if i > 0 else NO_LABEL)

    elif ptype == "constant":
        add(int(p["num_samples"]), float(p["value"]), p["condition"], 0, "steady")

    elif ptype == "levels":
        label = p.get("event_label", "setpoint_change")
        for i, lv in enumerate(p["levels"]):
            add(int(lv["samples"]), float(lv["value"]), p["condition"], i, "steady", label if i > 0 else NO_LABEL)

    elif ptype == "random_levels":
        levels = [float(v) for v in p["levels"]]
        n_total = int(p["num_samples"])
        lo, hi = p["dwell_range"]
        prev = None
        i = 0
        while len(vals) < n_total:
            choices = [v for v in levels if v != prev]
            v = float(choices[int(rng.integers(0, len(choices)))])
            d = min(int(rng.integers(int(lo), int(hi) + 1)), n_total - len(vals))
            add(d, v, p["condition"], i, "steady", "load_step" if i > 0 else NO_LABEL)
            prev = v
            i += 1

    elif ptype == "plateaus":
        pts = [(float(v), g["condition"]) for g in p["plateau_groups"] for v in g["values"]]
        pts.sort(key=lambda t: t[0])
        rate = float(p["ramp_rate_per_s"])
        dwell = int(p["dwell_samples"])
        settle = int(p["settle_samples"])
        for i, (v, c) in enumerate(pts):
            if i > 0:
                prev_v = pts[i - 1][0]
                n_ramp = int(np.ceil(abs(v - prev_v) / (rate * period_s)))
                # Linear ramp that reaches the next plateau value on the first plateau sample
                ramp = prev_v + (v - prev_v) * np.arange(1, n_ramp + 1) / (n_ramp + 1)
                add(n_ramp, ramp, "transition", -1, "ramp", "ramp_start")
            add(settle, v, c, i, "plateau_settling")
            add(dwell - settle, v, c, i, "plateau_stable")

    elif ptype == "ramp_cycle":
        start, peak, end = float(p["start"]), float(p["peak"]), float(p["end"])
        c = p["condition"]
        add(int(p["pre_hold_samples"]), start, c, 0, "hold_start")
        n_up = int(np.ceil((peak - start) / (float(p["heat_rate_per_s"]) * period_s)))
        add(n_up, start + (peak - start) * np.arange(1, n_up + 1) / n_up, c, -1, "heating_ramp", "ramp_start")
        add(int(p["hold_samples"]), peak, c, 1, "hold_peak")
        n_dn = int(np.ceil((peak - end) / (float(p["cool_rate_per_s"]) * period_s)))
        add(n_dn, peak + (end - peak) * np.arange(1, n_dn + 1) / n_dn, c, -1, "cooling_ramp", "ramp_start")
        add(int(p["post_hold_samples"]), end, c, 2, "hold_end")

    else:
        raise ValueError(f"Unknown profile type '{ptype}'.")

    return Profile(
        true_values=np.asarray(vals, dtype=float),
        condition=np.asarray(cond, dtype=object),
        setpoint_index=np.asarray(sp_idx, dtype=int),
        protocol_phase=np.asarray(phase, dtype=object),
        process_event=np.asarray(event, dtype=object),
    )


# ==============================================================================
# Fault planning
# ==============================================================================

def plan_fault_events(
    specs: List[Dict[str, Any]],
    n: int,
    rng: np.random.Generator,
    unit: str,
    run_id: str,
    margin_fraction: float,
    status_codes: List[str],
) -> List[FaultEvent]:
    """
    Turn fault specifications into concrete events. Random onsets avoid the first and last
    `margin_fraction` of the run (fault-free baseline window) and never overlap other
    transient events. Persistent faults start between 25 % and 75 % of the run.
    """
    events: List[FaultEvent] = []
    occupied: List[Tuple[int, int]] = []
    margin = max(int(n * margin_fraction), 2)
    guard = 3

    def free(a: int, b: int) -> bool:
        return all(b + guard <= s or a >= e + guard for s, e in occupied)

    counter = 0
    for spec in specs:
        ftype = spec["type"]
        if ftype not in FAULT_TYPES:
            raise ValueError(f"Unknown fault type '{ftype}'.")
        count = 1 if "onset_index" in spec else int(spec.get("count", 1))
        for _ in range(count):
            counter += 1
            # Duration
            if ftype in PERSISTENT_FAULTS:
                duration = None
            elif ftype in SINGLE_SAMPLE_FAULTS:
                duration = 1
            else:
                duration = _draw(rng, spec.get("duration", 1), integer=True)

            # Onset
            if "onset_index" in spec:
                onset = int(spec["onset_index"])
            elif ftype in PERSISTENT_FAULTS:
                onset = int(rng.integers(int(0.25 * n), int(0.75 * n) + 1))
            else:
                span = duration + (1 if ftype == "communication_gap" else 0)
                onset = None
                for _attempt in range(1000):
                    cand = int(rng.integers(margin, n - margin - span + 1))
                    if free(cand, cand + span):
                        onset = cand
                        break
                if onset is None:
                    raise RuntimeError(f"Could not place fault '{ftype}' in run {run_id} without overlap.")
            if duration is not None:
                occupied.append((onset, onset + duration + (1 if ftype == "communication_gap" else 0)))

            # Magnitude
            magnitude = None
            mag_unit = ""
            status_code = None
            nf_value = None
            if ftype in VALUE_FAULTS:
                magnitude = _draw(rng, spec["magnitude"])
                if isinstance(spec["magnitude"], (list, tuple)):
                    sign = spec.get("sign")
                    sign = float(sign) if sign is not None else float(rng.choice([-1.0, 1.0]))
                    magnitude *= sign
                mag_unit = {"gain_change": "relative", "gradual_drift": f"{unit}/s"}.get(ftype, unit)
            elif ftype == "invalid_status":
                status_code = str(status_codes[int(rng.integers(0, len(status_codes)))])
            elif ftype == "non_finite":
                nf_value = "+inf" if rng.random() < 0.5 else "-inf"

            events.append(FaultEvent(
                event_id=f"{run_id}-F{counter:02d}",
                run_id=run_id,
                fault_type=ftype,
                onset_index=onset,
                duration_samples=duration,
                magnitude=magnitude,
                magnitude_unit=mag_unit,
                status_code=status_code,
                non_finite_value=nf_value,
                observability=FAULT_OBSERVABILITY[ftype],
            ))
    return events


# ==============================================================================
# Suite generator
# ==============================================================================

class SyntheticSuiteGenerator:
    """
    Generates the configurable multi-measurand synthetic benchmark suite.

    Determinism: for a given generator version, configuration and seed roots, every
    scenario is bit-for-bit reproducible (verified via the SHA-256 manifest).
    """

    def __init__(self, config: Dict[str, Any], config_path: Optional[str] = None):
        self.config = config
        self.config_path = config_path
        self.config_sha256 = _sha256_bytes(json.dumps(config, sort_keys=True).encode("utf-8"))
        self.period_s = float(config["sampling_period_s"])
        self.epoch = pd.Timestamp(config["epoch_utc"])
        self.seed_roots = {k: int(v) for k, v in config["seed_roots"].items()}
        self.reference_realizations = self._realize_reference_instruments()
        self.scenarios = self._expand_scenarios()

    # ------------------------------------------------------------------ config
    @classmethod
    def from_file(cls, path: str) -> "SyntheticSuiteGenerator":
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f), config_path=path)

    def _realize_reference_instruments(self) -> Dict[str, Dict[str, float]]:
        """
        Draw the (unknown to the user) systematic offset and gain error of each simulated
        reference instrument once, from N(0, offset_std) and N(0, gain_std).
        """
        out = {}
        for i, (m, ref) in enumerate(sorted(self.config["reference_instruments"].items())):
            rng = np.random.default_rng([int(self.config["reference_realization_seed"]), i])
            out[m] = {
                "realized_offset": float(rng.normal(0.0, ref["offset_std"])) if ref["offset_std"] > 0 else 0.0,
                "realized_gain_error": float(rng.normal(0.0, ref["gain_std"])) if ref["gain_std"] > 0 else 0.0,
            }
        return out

    def _expand_scenarios(self) -> List[Dict[str, Any]]:
        """Explicit scenarios plus one fault-benchmark scenario per (measurand, fault class)."""
        scenarios = [copy.deepcopy(s) for s in self.config["scenarios"]]
        fb = self.config.get("fault_benchmark")
        if fb:
            for m, mcfg in fb["measurands"].items():
                # A measurand block is either one variant (v2 layout) or holds a list of "variants"
                for var in mcfg.get("variants", [mcfg]):
                    for cls_name in fb["classes"]:
                        faults = []
                        if cls_name != NO_LABEL:
                            entry = var["fault_specs"][cls_name]
                            if isinstance(entry, list):  # multi-fault class: each spec names its own type
                                faults = [dict(s) for s in entry]
                            else:
                                spec = dict(entry)
                                spec["type"] = cls_name
                                faults = [spec]
                        if cls_name == NO_LABEL:
                            desc = f"Fault-detection benchmark, {m}: fault-free control runs."
                        elif isinstance(var["fault_specs"][cls_name], list):
                            desc = f"Fault-detection benchmark, {m}: '{cls_name}' runs with faults of types {sorted({f['type'] for f in faults})}."
                        else:
                            desc = f"Fault-detection benchmark, {m}: individually labelled '{cls_name}' faults."
                        scenarios.append({
                            "scenario_id": f"{var['prefix']}_{cls_name.upper()}",
                            "group": fb["group"],
                            "measurand": m,
                            "device_id": var["device_id"],
                            "description": desc,
                            "analysis": {"type": "fault_detection", "fault_class": cls_name},
                            "profile": copy.deepcopy(var["profile"]),
                            "faults": faults,
                            "runs": copy.deepcopy(var.get("runs", fb["runs"])),
                        })
        ids = [s["scenario_id"] for s in scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate scenario_id in suite configuration.")
        return scenarios

    def get_scenario(self, scenario_id: str) -> Dict[str, Any]:
        for s in self.scenarios:
            if s["scenario_id"] == scenario_id:
                return s
        raise KeyError(scenario_id)

    def iter_runs(self, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Resolve run entries into concrete run specifications (calibration -> validation -> test order)."""
        runs = []
        counters = {p: 0 for p in PARTITIONS}
        entries = sorted(scenario["runs"], key=lambda r: PARTITIONS.index(r["partition"]))
        for entry in entries:
            part = entry["partition"]
            for _ in range(int(entry.get("count", 1))):
                counters[part] += 1
                run_number = counters[part]
                run_id = f"{PARTITION_ABBR[part]}{run_number:02d}"
                runs.append({
                    "partition": part,
                    "run_number": run_number,
                    "run_id": run_id,
                    "experiment_id": f"SYN2-{scenario['scenario_id']}-{run_id}",
                    "seed": derive_run_seed(self.seed_roots[part], scenario["scenario_id"], run_number),
                    "profile": copy.deepcopy(entry.get("profile", scenario["profile"])),
                    "faults": copy.deepcopy(entry.get("faults", scenario.get("faults", []))),
                    "ambient": copy.deepcopy(entry.get("ambient", scenario.get("ambient", {}))),
                    "condition_suffix": entry.get("condition_suffix", ""),
                })
        return runs

    # ------------------------------------------------------------------ models
    def _ambient(self, n: int, mean_c: float, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
        am = self.config["ambient_model"]
        t = np.arange(n) * self.period_s
        true_amb = mean_c + am["sinusoid_amplitude_C"] * np.sin(2.0 * np.pi * t / am["sinusoid_period_s"])
        obs_amb = quantize(true_amb + rng.normal(0.0, am["sensor_noise_std_C"], n), am["sensor_resolution_C"])
        return true_amb, obs_amb

    def _reference(self, measurand: str, true_vals: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
        ref = self.config["reference_instruments"][measurand]
        n = len(true_vals)
        if not ref.get("enabled", True):
            return np.full(n, np.nan), np.full(n, np.nan)
        real = self.reference_realizations[measurand]
        sensed = first_order_lag(true_vals, float(ref.get("time_constant_s", 0.0)), self.period_s)
        reading = real["realized_offset"] + (1.0 + real["realized_gain_error"]) * sensed + rng.normal(0.0, ref["noise_std"], n)
        reading = quantize(reading, ref["resolution"])
        # Stated (steady-state) expanded uncertainty of each reference reading
        u = np.sqrt(ref["offset_std"] ** 2 + (ref["gain_std"] * np.abs(reading)) ** 2
                    + ref["noise_std"] ** 2 + ref["resolution"] ** 2 / 12.0)
        return reading, ref["coverage_k"] * u

    def _dut_nominal(self, dev: Dict[str, Any], measurand: str, true_vals: np.ndarray,
                     true_amb: np.ndarray, rng: np.random.Generator) -> Dict[str, np.ndarray]:
        """
        Noise-free nominal DUT response, the 'sensed' input used by gain faults, latent
        ground-truth variables and the DUT noise realisation (in measurand units).
        """
        n = len(true_vals)
        out: Dict[str, np.ndarray] = {}
        model = dev["model"]
        if model == "direct_adc":
            fs = float(self.config["measurands"][measurand]["full_scale"])
            r = true_vals / fs
            inl = dev["inl_bow_amplitude"] * 4.0 * r * (1.0 - r)
            tc = dev["temp_coefficient_per_C"] * (true_amb - dev["temp_coefficient_reference_C"])
            out["nominal"] = dev["offset"] + (1.0 + dev["gain_error"]) * true_vals + inl + tc
            out["sensed"] = true_vals
            out["noise"] = rng.normal(0.0, dev["noise_std"], n)
            out["quant_step"] = np.full(n, dev["quantization_step"])
        elif model == "shunt":
            r_nom = dev["r_shunt_nominal_ohm"]
            r_ref = r_nom * (1.0 + dev["r_shunt_actual_deviation"])
            tcr = dev["r_shunt_tcr_per_C"]
            t0 = dev["r_shunt_reference_temp_C"]
            rth = dev["thermal_resistance_C_per_W"]
            i_a = true_vals / 1000.0
            t_sh = np.empty(n)
            r_sh = np.empty(n)
            a = 1.0 - np.exp(-self.period_s / dev["thermal_time_constant_s"])
            t_sh[0] = true_amb[0]  # cold start: shunt at ambient
            r_sh[0] = r_ref * (1.0 + tcr * (t_sh[0] - t0))
            for k in range(1, n):
                p_w = i_a[k] ** 2 * r_sh[k - 1]
                t_sh[k] = t_sh[k - 1] + a * (true_amb[k] + rth * p_w - t_sh[k - 1])
                r_sh[k] = r_ref * (1.0 + tcr * (t_sh[k] - t0))
            v_true_mv = true_vals * r_sh                       # mA * Ohm = mV
            v_nom_mv = dev["adc_offset_mV"] + (1.0 + dev["adc_gain_error"]) * v_true_mv
            out["nominal"] = v_nom_mv / r_nom                  # mV / Ohm = mA
            out["sensed"] = true_vals
            out["noise"] = rng.normal(0.0, dev["adc_noise_std_mV"], n) / r_nom
            out["quant_step"] = np.full(n, dev["adc_quantization_mV"] / r_nom)
            out["true_shunt_temperature_C"] = t_sh
            out["true_shunt_resistance_ohm"] = r_sh
            out["true_shunt_voltage_mV"] = v_true_mv
        elif model == "first_order_lag":
            elem = first_order_lag(true_vals, dev["time_constant_s"], self.period_s)
            out["nominal"] = dev["offset"] + (1.0 + dev["gain_error"]) * elem
            out["sensed"] = elem
            out["noise"] = rng.normal(0.0, dev["noise_std"], n)
            out["quant_step"] = np.full(n, dev["quantization_step"])
            out["true_sensor_element_temperature_C"] = elem
        else:
            raise ValueError(f"Unknown device model '{model}'.")
        return out

    # ------------------------------------------------------------------ run
    def generate_run(self, scenario: Dict[str, Any], run: Dict[str, Any], run_order: int) -> Tuple[pd.DataFrame, List[FaultEvent]]:
        measurand = scenario["measurand"]
        unit = MEASURAND_UNITS[measurand]
        dev = self.config["devices"][scenario["device_id"]]
        if dev["measurand"] != measurand:
            raise ValueError(f"Device {scenario['device_id']} does not measure {measurand}.")

        rng_profile, rng_ambient, rng_dut, rng_ref, rng_fault = [
            np.random.default_rng(s) for s in np.random.SeedSequence(run["seed"]).spawn(5)
        ]

        prof = build_profile(run["profile"], self.period_s, rng_profile)
        n = len(prof.true_values)
        x_true = prof.true_values
        t_s = np.arange(n) * self.period_s
        amb_mean = float(run["ambient"].get("mean_C", self.config["ambient_model"]["default_mean_C"]))
        true_amb, obs_amb = self._ambient(n, amb_mean, rng_ambient)
        dut = self._dut_nominal(dev, measurand, x_true, true_amb, rng_dut)
        ref_vals, ref_u = self._reference(measurand, x_true, rng_ref)

        events = plan_fault_events(
            run["faults"], n, rng_fault, unit, run["experiment_id"],
            float(self.config["fault_margin_fraction"]), self.config["invalid_status_codes"],
        )

        # ---- value-domain faults (pre-quantisation)
        fault_add = np.zeros(n)
        drift = np.zeros(n)
        label_types: List[List[str]] = [[] for _ in range(n)]
        label_ids: List[List[str]] = [[] for _ in range(n)]

        def mark(rows, ev: FaultEvent):
            for r in rows:
                label_types[r].append(ev.fault_type)
                label_ids[r].append(ev.event_id)

        for ev in events:
            k = ev.onset_index
            end = n if ev.duration_samples is None else min(n, k + ev.duration_samples)
            if ev.fault_type == "isolated_spike":
                fault_add[k] += ev.magnitude
            elif ev.fault_type == "offset_shift":
                fault_add[k:] += ev.magnitude
            elif ev.fault_type == "gain_change":
                fault_add[k:] += ev.magnitude * dut["sensed"][k:]
            elif ev.fault_type == "gradual_drift":
                d = ev.magnitude * (t_s[k:] - t_s[k])
                drift[k:] += d
                fault_add[k:] += d
            elif ev.fault_type == "abrupt_change":
                fault_add[k:end] += ev.magnitude
            if ev.fault_type in VALUE_FAULTS or ev.fault_type in POST_QUANT_FAULTS:
                mark(range(k, end), ev)

        obs = quantize(dut["nominal"] + fault_add + dut["noise"], float(dut["quant_step"][0]))
        status = np.array([STATUS_OK] * n, dtype=object)

        # ---- post-quantisation faults
        for ev in events:
            k = ev.onset_index
            end = n if ev.duration_samples is None else min(n, k + ev.duration_samples)
            if ev.fault_type == "stuck_signal":
                obs[k:end] = obs[k - 1]
            elif ev.fault_type == "missing_samples":
                obs[k:end] = np.nan
            elif ev.fault_type == "non_finite":
                obs[k] = np.inf if ev.non_finite_value == "+inf" else -np.inf
            elif ev.fault_type == "invalid_status":
                status[k:end] = ev.status_code

        # ---- assemble pre-record-fault frame
        cond = prof.condition.astype(str)
        if run["condition_suffix"]:
            cond = np.char.add(cond, run["condition_suffix"])
        start = self.epoch + pd.Timedelta(days=run_order)
        elapsed_ms = t_s * 1000.0
        stamps = (start + pd.to_timedelta(elapsed_ms, unit="ms")).strftime("%Y-%m-%dT%H:%M:%S.%f")
        ts = [s[:-3] + "+00:00" for s in stamps]

        cols: Dict[str, Any] = {
            "scenario_id": scenario["scenario_id"],
            "experiment_id": run["experiment_id"],
            "run_id": run["run_id"],
            "partition": run["partition"],
            "generation_seed": run["seed"],
            "device_id": scenario["device_id"],
            "data_source": DATA_SOURCE_TAG,
            "operating_condition_id": cond,
            "setpoint_index": prof.setpoint_index,
            "protocol_phase": prof.protocol_phase,
            "timestamp_utc": ts,
            "sequence_number": np.arange(1, n + 1),
            "elapsed_ms": elapsed_ms,
            measurand: obs,
        }
        if measurand == "current_mA":
            cols["shunt_voltage_mV"] = obs * dev["r_shunt_nominal_ohm"]
        cols["status"] = status
        cols["environmental_temperature_C"] = obs_amb
        cols[f"reference_{measurand}"] = ref_vals
        cols["reference_expanded_uncertainty_k2"] = ref_u
        cols[f"true_{measurand}"] = x_true
        cols["true_environmental_temperature_C"] = true_amb
        for latent in ("true_sensor_element_temperature_C", "true_shunt_temperature_C",
                       "true_shunt_resistance_ohm", "true_shunt_voltage_mV"):
            if latent in dut:
                cols[latent] = dut[latent]
        cols["true_drift_component"] = drift
        cols["true_injected_error_component"] = fault_add
        df = pd.DataFrame(cols)

        # ---- record-level faults: communication gaps (drop) and duplicates (insert)
        keep = np.ones(n, dtype=bool)
        dup_after = set()
        for ev in events:
            k = ev.onset_index
            if ev.fault_type == "communication_gap":
                keep[k:k + ev.duration_samples] = False
                mark([k + ev.duration_samples], ev)
            elif ev.fault_type == "duplicate_sequence":
                dup_after.add(k)

        order: List[int] = []
        is_dup_copy: List[bool] = []
        for i in range(n):
            if keep[i]:
                order.append(i)
                is_dup_copy.append(False)
                if i in dup_after:
                    order.append(i)
                    is_dup_copy.append(True)

        dup_event = {ev.onset_index: ev for ev in events if ev.fault_type == "duplicate_sequence"}
        types_out, ids_out = [], []
        for i, dup in zip(order, is_dup_copy):
            t_list = list(label_types[i])
            id_list = list(label_ids[i])
            if dup:
                t_list.append("duplicate_sequence")
                id_list.append(dup_event[i].event_id)
            types_out.append(";".join(t_list) if t_list else NO_LABEL)
            ids_out.append(";".join(id_list) if id_list else NO_LABEL)

        df = df.iloc[order].reset_index(drop=True)
        df["error_vs_true"] = df[measurand] - df[f"true_{measurand}"]
        df["error_vs_reference"] = df[measurand] - df[f"reference_{measurand}"]
        df["is_injected_fault"] = np.array([t != NO_LABEL for t in types_out], dtype=bool)
        df["label_fault_type"] = types_out
        df["label_fault_event_id"] = ids_out
        df["label_process_event"] = prof.process_event[order]
        # A duplicated record is not a second process event
        df.loc[np.asarray(is_dup_copy), "label_process_event"] = NO_LABEL
        df["dq_flags"] = compute_observable_flags(df, measurand)

        # ---- finalise event bookkeeping
        for ev in events:
            ev.onset_sequence_number = ev.onset_index + 1
            ev.onset_elapsed_ms = float(elapsed_ms[ev.onset_index])
            ev.labelled_row_count = int(sum(ev.event_id in s.split(";") for s in ids_out))
        return df, events

    # ------------------------------------------------------------------ scenario
    def generate_scenario(self, scenario_id: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        scenario = self.get_scenario(scenario_id)
        runs = self.iter_runs(scenario)
        frames, all_events, run_meta = [], [], []
        for order, run in enumerate(runs):
            df_run, events = self.generate_run(scenario, run, order)
            frames.append(df_run)
            all_events.extend(events)
            run_meta.append({
                "experiment_id": run["experiment_id"],
                "run_id": run["run_id"],
                "partition": run["partition"],
                "generation_seed": run["seed"],
                "seed_root": self.seed_roots[run["partition"]],
                "record_count": int(len(df_run)),
                "operating_conditions": sorted(set(df_run["operating_condition_id"])),
                "ambient_mean_C": float(run["ambient"].get("mean_C", self.config["ambient_model"]["default_mean_C"])),
                "profile": run["profile"],
                "fault_specifications": run["faults"],
                "fault_event_ids": [e.event_id for e in events],
            })
        df = pd.concat(frames, ignore_index=True)
        meta = self._scenario_metadata(scenario, df, run_meta, all_events)
        return df, meta

    def generate_all(self) -> Dict[str, Tuple[pd.DataFrame, Dict[str, Any]]]:
        return {s["scenario_id"]: self.generate_scenario(s["scenario_id"]) for s in self.scenarios}

    # ------------------------------------------------------------------ metadata
    def _scenario_metadata(self, scenario, df, run_meta, events) -> Dict[str, Any]:
        measurand = scenario["measurand"]
        dev = self.config["devices"][scenario["device_id"]]
        n = len(df)
        obs = df[measurand].to_numpy(dtype=float)
        by_type: Dict[str, int] = {}
        for s in df["label_fault_type"]:
            if s != NO_LABEL:
                for t in s.split(";"):
                    by_type[t] = by_type.get(t, 0) + 1
        dropped = sum(e.duration_samples for e in events if e.fault_type == "communication_gap")
        ref_cfg = self.config["reference_instruments"][measurand]
        partitions = {}
        for p in PARTITIONS:
            rm = [r for r in run_meta if r["partition"] == p]
            partitions[p] = {"experiment_ids": [r["experiment_id"] for r in rm],
                             "record_count": int(sum(r["record_count"] for r in rm))}
        return {
            "dataset_id": scenario["scenario_id"],
            "suite_id": self.config["suite_id"],
            "group": scenario["group"],
            "measurand": measurand,
            "measurand_unit": MEASURAND_UNITS[measurand],
            "description": scenario["description"],
            "analysis": scenario.get("analysis", {}),
            "disclaimer": self.config["disclaimer"],
            "generator": {
                "name": GENERATOR_NAME,
                "module": "src/imuca/synthetic_suite.py",
                "version": GENERATOR_VERSION,
                "config_file": self.config.get("config_file", "config/synthetic_suite_config.json"),
                "config_sha256": self.config_sha256,
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
            },
            "generation_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "random_seeds": {
                "seed_roots": self.seed_roots,
                "derivation": "run_seed = SeedSequence(entropy=seed_roots[partition], spawn_key=(crc32(scenario_id), run_number)).generate_state(1)[0]; the run seed is spawned into 5 independent streams: profile, ambient, DUT noise, reference noise, fault placement.",
                "reference_realization_seed": int(self.config["reference_realization_seed"]),
                "runs": {r["experiment_id"]: r["generation_seed"] for r in run_meta},
            },
            "record_count": int(n),
            "run_count": len(run_meta),
            "runs": run_meta,
            "partitions": partitions,
            "columns": column_dictionary(measurand, dev["model"]),
            "ground_truth_definitions": ground_truth_definitions(measurand, dev["model"]),
            "sensor_error_model": sensor_model_description(scenario["device_id"], dev, measurand),
            "reference_error_model": {
                **ref_cfg,
                **self.reference_realizations[measurand],
                "unit": MEASURAND_UNITS[measurand],
                "equation": "reference = realized_offset + (1 + realized_gain_error) * lag(true, time_constant_s) + N(0, noise_std), quantised to resolution",
                "stated_uncertainty": "reference_expanded_uncertainty_k2 = coverage_k * sqrt(offset_std^2 + (gain_std*|reading|)^2 + noise_std^2 + resolution^2/12); steady-state only, excludes dynamic (lag) error",
                "note": "The reference is a simulated instrument with its own errors; it is NOT ground truth. realized_* values are simulation ground truth about the reference and would be unknown in a real laboratory.",
            },
            "ambient_model": self.config["ambient_model"],
            "fault_events": [e.to_dict() for e in events],
            "fault_prevalence": {
                "fault_row_count": int(df["is_injected_fault"].sum()),
                "fault_row_fraction": float(df["is_injected_fault"].mean()) if n else 0.0,
                "rows_by_fault_type": by_type,
                "events_by_fault_type": {t: sum(e.fault_type == t for e in events) for t in sorted({e.fault_type for e in events})},
            },
            "missing_data": {
                "nan_observation_rows": int(np.isnan(obs).sum()),
                "non_finite_observation_rows": int(np.isinf(obs).sum()),
                "missing_rate": float(np.isnan(obs).mean()) if n else 0.0,
                "dropped_records_communication_gap": int(dropped),
                "dropped_rate": float(dropped / (n + dropped)) if n + dropped else 0.0,
            },
            "process_events": {k: int(v) for k, v in df["label_process_event"].value_counts().items() if k != NO_LABEL},
            "split_strategy": {
                "unit_of_partitioning": "experiment run (experiment_id); every run belongs to exactly one partition",
                "calibration": "fit calibration / tune detector thresholds / train ML models",
                "validation": "model selection and hyper-parameter choice",
                "test": "final evaluation only; generated from an independent seed root and, where configured, held-out operating conditions",
                "chronology": "run start times are ordered calibration -> validation -> test (one simulated day apart)",
                "within_run_split": "not permitted: adjacent samples are correlated (dwell, lag, thermal state)",
            },
            "known_limitations": known_limitations(measurand, dev["model"]),
        }

    # ------------------------------------------------------------------ export
    def export(self, output_root: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Write every scenario to <output_root>/<group>/<scenario_id>.csv and its metadata to
        <output_root>/metadata/<scenario_id>.metadata.json. Raw files are immutable: an
        existing file with identical content is left untouched (original metadata kept);
        a differing file raises unless overwrite=True.
        """
        meta_dir = os.path.join(output_root, "metadata")
        os.makedirs(meta_dir, exist_ok=True)
        files, event_rows, statuses = [], [], {}
        for sc in self.scenarios:
            sid = sc["scenario_id"]
            df, meta = self.generate_scenario(sid)
            data = dataframe_to_csv_bytes(df)
            sha = _sha256_bytes(data)
            group_dir = os.path.join(output_root, sc["group"])
            os.makedirs(group_dir, exist_ok=True)
            csv_path = os.path.join(group_dir, f"{sid}.csv")
            meta_path = os.path.join(meta_dir, f"{sid}.metadata.json")
            status = "written"
            if os.path.exists(csv_path):
                with open(csv_path, "rb") as f:
                    old_sha = _sha256_bytes(f.read())
                if old_sha == sha:
                    status = "unchanged"
                elif not overwrite:
                    raise FileExistsError(f"{csv_path} exists with different content; refusing to overwrite immutable raw data.")
                else:
                    status = "overwritten"
            meta["csv_file"] = f"{sc['group']}/{sid}.csv"
            meta["csv_sha256"] = sha
            if status != "unchanged":
                with open(csv_path, "wb") as f:
                    f.write(data)
            elif os.path.exists(meta_path):
                # Unchanged data: keep the original generation timestamp (provenance)
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta["generation_timestamp_utc"] = json.load(f).get("generation_timestamp_utc")
            write_json_if_changed(meta_path, meta)
            statuses[sid] = status
            for e in meta["fault_events"]:
                event_rows.append({"scenario_id": sid, **e})
            files.append({
                "scenario_id": sid, "group": sc["group"], "measurand": sc["measurand"],
                "device_id": sc["device_id"], "csv_file": meta["csv_file"],
                "metadata_file": f"metadata/{sid}.metadata.json", "csv_sha256": sha,
                "record_count": meta["record_count"], "run_count": meta["run_count"],
                "partition_records": {p: v["record_count"] for p, v in meta["partitions"].items()},
                "run_seeds": meta["random_seeds"]["runs"],
                "fault_row_fraction": meta["fault_prevalence"]["fault_row_fraction"],
                "fault_events": len(meta["fault_events"]),
                "missing_rate": meta["missing_data"]["missing_rate"],
                "description": sc["description"],
                "generation_timestamp_utc": meta["generation_timestamp_utc"],
            })

        buf = io.StringIO()
        pd.DataFrame(event_rows).to_csv(buf, index=False, lineterminator="\n")
        aux = {"fault_events.csv": write_if_changed(os.path.join(meta_dir, "fault_events.csv"), buf.getvalue().encode("utf-8"))}

        malformed = write_malformed_fixtures(os.path.join(output_root, "malformed"))
        aux["malformed_manifest.json"] = write_json_if_changed(os.path.join(meta_dir, "malformed_manifest.json"), malformed)

        manifest = {
            "suite_id": self.config["suite_id"],
            "generator": GENERATOR_NAME,
            "generator_version": GENERATOR_VERSION,
            "config_file": self.config.get("config_file", "config/synthetic_suite_config.json"),
            "config_sha256": self.config_sha256,
            "seed_roots": self.seed_roots,
            "reference_realization_seed": int(self.config["reference_realization_seed"]),
            "manifest_written_utc": datetime.now(timezone.utc).isoformat(),
            "total_records": int(sum(f["record_count"] for f in files)),
            "scenario_count": len(files),
            "files": files,
            "disclaimer": self.config["disclaimer"],
        }
        manifest_path = os.path.join(meta_dir, "suite_manifest.json")
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                old_manifest = json.load(f)
            if _manifest_substance(old_manifest) == _manifest_substance(manifest):
                # Same substantive content: keep the original write time (no rewrite)
                manifest["manifest_written_utc"] = old_manifest.get("manifest_written_utc")
        stored = {k: v for k, v in manifest.items()}
        if os.path.exists(manifest_path) and "file_status" in old_manifest and _manifest_substance(old_manifest) == _manifest_substance(manifest):
            stored["file_status"] = old_manifest["file_status"]   # legacy field kept so the historical file is not rewritten
        aux["suite_manifest.json"] = write_json_if_changed(manifest_path, stored)
        manifest["file_status"] = statuses          # returned to the caller, not stored
        manifest["auxiliary_file_status"] = aux
        return manifest

    def verify_against_manifest(self, output_root: str) -> List[str]:
        """Regenerate every scenario in memory and compare SHA-256 with the stored manifest."""
        with open(os.path.join(output_root, "metadata", "suite_manifest.json"), "r", encoding="utf-8") as f:
            manifest = json.load(f)
        mismatches = []
        for entry in manifest["files"]:
            df, _ = self.generate_scenario(entry["scenario_id"])
            if _sha256_bytes(dataframe_to_csv_bytes(df)) != entry["csv_sha256"]:
                mismatches.append(entry["scenario_id"])
            path = os.path.join(output_root, entry["csv_file"])
            with open(path, "rb") as f:
                if _sha256_bytes(f.read()) != entry["csv_sha256"]:
                    mismatches.append(f"{entry['scenario_id']} (file on disk)")
        return mismatches


# ==============================================================================
# Observable flags, CSV serialisation, documentation helpers
# ==============================================================================

def compute_observable_flags(df: pd.DataFrame, measurand: str) -> List[str]:
    """Flags derivable from observable fields only (no ground truth, no labels)."""
    vals = df[measurand].to_numpy(dtype=float)
    seq = df["sequence_number"].to_numpy()
    status = df["status"].astype(str).to_numpy()
    flags = []
    prev = None
    for i in range(len(df)):
        f = []
        if np.isnan(vals[i]):
            f.append("MISSING_VALUE")
        elif np.isinf(vals[i]):
            f.append("NON_FINITE")
        if status[i] != STATUS_OK:
            f.append(f"STATUS_{status[i]}")
        if prev is not None:
            if seq[i] <= prev:
                f.append("DUPLICATE_SEQ")
            elif seq[i] > prev + 1:
                f.append(f"SEQ_GAP_{int(seq[i] - prev - 1)}")
        prev = seq[i] if prev is None else max(prev, seq[i])
        flags.append(";".join(f) if f else "NONE")
    return flags


MANIFEST_VOLATILE_KEYS = ("manifest_written_utc", "file_status", "auxiliary_file_status")


def _manifest_substance(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Manifest content without bookkeeping fields that change on every export."""
    return {k: v for k, v in manifest.items() if k not in MANIFEST_VOLATILE_KEYS}


def write_if_changed(path: str, data: bytes) -> str:
    """Write bytes only when the file is missing or differs; returns 'written', 'updated' or 'unchanged'."""
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return "unchanged"
        status = "updated"
    else:
        status = "written"
    with open(path, "wb") as f:
        f.write(data)
    return status


def write_text_if_changed(path: str, text: str) -> str:
    """Write text (platform newline convention) only when content differs, ignoring line-ending style."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            if f.read() == text:            # universal-newline read normalises CRLF/LF
                return "unchanged"
        status = "updated"
    else:
        status = "written"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return status


def write_json_if_changed(path: str, obj: Any) -> str:
    """
    Write JSON (text mode, as historically) only when the file is missing or its parsed content
    differs. Comparing parsed content makes the check independent of platform line endings.
    """
    normalized = json.loads(json.dumps(obj, default=_json_default))
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                if json.load(f) == normalized:
                    return "unchanged"
        except (ValueError, OSError):
            pass
        status = "updated"
    else:
        status = "written"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_json_default)
    return status


def iter_run_csv_buffers(csv_path: str):
    """
    Scenario CSVs contain several acquisition sessions (runs), each with its own
    sequence_number and elapsed_ms starting from 1 / 0. The existing ingestion pipeline
    validates one session per file, so a scenario file must be ingested run by run.
    Yields (experiment_id, StringIO) with the run's rows in the original CSV text form.
    """
    df = pd.read_csv(csv_path)
    for exp_id, run_df in df.groupby("experiment_id", sort=False):
        buf = io.StringIO()
        run_df.to_csv(buf, index=False, float_format=CSV_FLOAT_FORMAT, lineterminator="\n")
        buf.seek(0)
        yield exp_id, buf


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, float_format=CSV_FLOAT_FORMAT, lineterminator="\n")
    return buf.getvalue().encode("utf-8")


def _json_default(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def column_dictionary(measurand: str, model: str) -> List[Dict[str, str]]:
    u = MEASURAND_UNITS[measurand]
    cols = [
        ("scenario_id", "", "string", "identifier", "Scenario (dataset) identifier; spans partitions."),
        ("experiment_id", "", "string", "identifier", "Unique acquisition session (run); the unit of partitioning."),
        ("run_id", "", "string", "identifier", "Run label within the scenario (CALnn / VALnn / TSTnn)."),
        ("partition", "", "string", "partition", "calibration | validation | test (assigned per run)."),
        ("generation_seed", "", "int", "provenance", "Integer seed of the run's random streams."),
        ("device_id", "", "string", "identifier", "Simulated device-under-test instance."),
        ("data_source", "", "string", "provenance", "Provenance tag (synthetic_suite_v2)."),
        ("operating_condition_id", "", "string", "protocol", "Planned operating-condition group (e.g. grid_A, grid_B_interleaved, extrapolation_above_cal_range). Never encodes fault presence."),
        ("setpoint_index", "", "int", "protocol", "Index of the planned set-point/plateau in run order (-1 during ramps)."),
        ("protocol_phase", "", "string", "protocol", "Planned protocol phase (dwell, steady, ramp, plateau_settling, plateau_stable, ...)."),
        ("timestamp_utc", "ISO 8601", "string", "time", "Simulated acquisition timestamp (UTC)."),
        ("sequence_number", "count", "int", "time", "Record counter as transmitted (duplicates/gaps reflect injected record faults)."),
        ("elapsed_ms", "ms", "float", "time", "Milliseconds since run start."),
        (measurand, u, "float", "observation", "DUT observed (digitised) reading. May be NaN (missing) or +/-inf (non-finite fault)."),
    ]
    if model == "shunt":
        cols.append(("shunt_voltage_mV", "mV", "float", "observation", "DUT digitised shunt voltage; current_mA = shunt_voltage_mV / r_shunt_nominal_ohm."))
    cols += [
        ("status", "", "string", "observation", "Sensor status code (OK or injected invalid-status code)."),
        ("environmental_temperature_C", "degC", "float", "observation", "Simulated ambient-temperature sensor reading."),
        (f"reference_{measurand}", u, "float", "reference_observation", "Simulated independent reference-instrument reading (has its own error model)."),
        ("reference_expanded_uncertainty_k2", u, "float", "reference_observation", "Stated expanded uncertainty (k=2) of the reference reading."),
        (f"true_{measurand}", u, "float", "ground_truth", "True simulated measurand value (not a measurement)."),
        ("true_environmental_temperature_C", "degC", "float", "ground_truth", "True simulated ambient temperature."),
    ]
    if model == "first_order_lag":
        cols.append(("true_sensor_element_temperature_C", "degC", "float", "ground_truth", "Latent lagged temperature of the sensing element."))
    if model == "shunt":
        cols += [
            ("true_shunt_temperature_C", "degC", "float", "ground_truth", "Latent shunt-resistor temperature."),
            ("true_shunt_resistance_ohm", "Ohm", "float", "ground_truth", "Latent actual shunt resistance."),
            ("true_shunt_voltage_mV", "mV", "float", "ground_truth", "Latent true shunt voltage = true_current_mA * true_shunt_resistance_ohm."),
        ]
    cols += [
        ("true_drift_component", u, "float", "ground_truth", "Injected gradual-drift contribution to the DUT reading (pre-quantisation)."),
        ("true_injected_error_component", u, "float", "ground_truth", "Sum of all injected value-domain fault contributions (spike, offset, gain, drift, abrupt)."),
        ("error_vs_true", u, "float", "derived_error", "DUT reading minus ground truth."),
        ("error_vs_reference", u, "float", "derived_error", "DUT reading minus reference reading."),
        ("is_injected_fault", "", "bool", "label", "True when any injected fault affects this record (compatible with DataQualityAssessor ground_truth_fault_col)."),
        ("label_fault_type", "", "string", "label", "';'-joined injected fault types active on this record, or 'none'."),
        ("label_fault_event_id", "", "string", "label", "';'-joined fault event ids (see metadata fault_events), or 'none'."),
        ("label_process_event", "", "string", "label", "Genuine (non-fault) process events: setpoint_change, load_step, true_step, ramp_start, or 'none'."),
        ("dq_flags", "", "string", "quality_flag", "Flags derivable from observable fields only: MISSING_VALUE, NON_FINITE, STATUS_<code>, DUPLICATE_SEQ, SEQ_GAP_<n>, or NONE."),
    ]
    return [{"name": c[0], "unit": c[1], "dtype": c[2], "role": c[3], "description": c[4]} for c in cols]


def ground_truth_definitions(measurand: str, model: str) -> Dict[str, str]:
    d = {
        f"true_{measurand}": "Value of the measurand imposed by the simulation (e.g. calibrator set-point or bath temperature). It is a simulation construct and is never presented as an instrument reading.",
        f"reference_{measurand}": "Reading of a simulated reference instrument with its own offset, gain, noise, resolution and (temperature only) lag. Use it as a laboratory reference, not as truth.",
        "error_vs_true": "Total DUT error including all modelled effects and injected faults.",
        "error_vs_reference": "Observable calibration error; differs from error_vs_true by the reference error.",
    }
    if model == "first_order_lag":
        d["true_sensor_element_temperature_C"] = "Temperature of the simulated sensing element after first-order lag; the difference to true_temperature_C is the dynamic (lag) error."
    if model == "shunt":
        d["true_shunt_resistance_ohm"] = "Actual shunt resistance including tolerance, TCR and (if modelled) self-heating; the instrument always divides by the nominal value."
    return d


def sensor_model_description(device_id: str, dev: Dict[str, Any], measurand: str) -> Dict[str, Any]:
    eq = {
        "direct_adc": "obs = Q( offset + (1+gain_error)*x + inl_bow_amplitude*4*(x/FS)*(1-x/FS) + temp_coefficient_per_C*(T_amb - T_ref) + faults + N(0, noise_std) ; quantization_step )",
        "shunt": ("R(t) = R_nom*(1+r_shunt_actual_deviation)*(1 + tcr*(T_sh(t) - T_ref)); "
                  "T_sh[k] = T_sh[k-1] + (1-exp(-dt/tau_th))*(T_amb[k] + R_th*I[k]^2*R[k-1] - T_sh[k-1]), T_sh[0]=T_amb[0] (cold start); "
                  "V_true = I*R; V_obs = Q( adc_offset_mV + (1+adc_gain_error)*V_true + R_nom*faults + N(0, adc_noise_std_mV) ; adc_quantization_mV ); "
                  "I_obs = V_obs / R_nom  (mV / Ohm = mA)"),
        "first_order_lag": "T_elem = first-order lag of T_true with time_constant_s (ZOH discretisation, starts in equilibrium); obs = Q( offset + (1+gain_error)*T_elem + faults + N(0, noise_std) ; quantization_step )",
    }[dev["model"]]
    return {
        "device_id": device_id,
        "measurand": measurand,
        "parameters": dev,
        "equation": eq,
        "noise_distribution": "independent Gaussian, zero mean",
        "quantisation": "round-to-nearest",
        "fault_magnitude_semantics": FAULT_MAGNITUDE_SEMANTICS,
        "parameter_status": "Simulation assumptions chosen for benchmark coverage. Not verified specifications of any physical sensor.",
    }


def known_limitations(measurand: str, model: str) -> List[str]:
    lim = [
        "Synthetic data only; no physical sensor behaviour is claimed.",
        "Noise is white Gaussian; no 1/f noise, interference, or correlated noise between DUT and reference.",
        "Sampling is perfectly periodic (no clock jitter); only injected record faults perturb timing.",
        "The calibrator/source is ideal: the true value equals the planned set-point exactly.",
        "Reference stated uncertainty covers steady-state errors only.",
        "Fault magnitudes and placements are drawn from documented ranges and may not reflect real fault statistics.",
    ]
    if model == "shunt":
        lim.append("Shunt TCR and thermal resistance/time constant are assumed scenario parameters, not measured values.")
        lim.append("Self-heating model is first-order and lumped; no PCB heat spreading or airflow effects.")
    if model == "first_order_lag":
        lim.append("Sensor lag is a single first-order time constant (simulation assumption, not a probe specification).")
    if model == "direct_adc":
        lim.append("INL is a single parabolic bow; real ADC INL can be irregular.")
    return lim


# ==============================================================================
# Malformed ingestion fixtures
# ==============================================================================

def write_malformed_fixtures(out_dir: str) -> Dict[str, Any]:
    """Small hand-specified malformed CSV files used to test ingestion rejection/flagging."""
    os.makedirs(out_dir, exist_ok=True)
    hdr = "experiment_id,timestamp_utc,sequence_number,elapsed_ms,voltage_V,status,reference_voltage_V\n"

    def row(seq, el, v, st="OK", ref="5.0", ts=None):
        ts = ts or f"2026-11-02T08:00:{int(el // 1000):02d}.000+00:00"
        return f"MAL,{ts},{seq},{el},{v},{st},{ref}\n"

    fixtures = {
        "MAL_zero_byte.csv": ("", "Zero-byte file.", {"expect_read_error": True, "expect_valid": False}),
        "MAL_header_only.csv": (hdr, "Header without records.", {"expect_valid": False, "expect_issue_codes": ["EMPTY_DATASET"]}),
        "MAL_non_numeric_value.csv": (hdr + "".join(row(i, i * 1000.0, "5.001" if i != 3 else "abc") for i in range(1, 7)),
                                      "Non-numeric measurand string.", {"expect_valid": False, "expect_issue_codes": ["NON_NUMERIC"]}),
        "MAL_non_finite.csv": (hdr + "".join(row(i, i * 1000.0, {2: "inf", 4: "-inf"}.get(i, "5.001")) for i in range(1, 7)),
                               "Infinite measurand values.", {"expect_valid": False, "expect_issue_codes": ["NON_FINITE"]}),
        "MAL_backwards_time.csv": (hdr + "".join(row(i, {4: 1500.0}.get(i, i * 1000.0), "5.001") for i in range(1, 7)),
                                   "elapsed_ms decreases.", {"expect_valid": False, "expect_issue_codes": ["MONOTONICITY_VIOLATION"]}),
        "MAL_duplicate_sequence.csv": (hdr + "".join(row({4: 3}.get(i, i), i * 1000.0, "5.001") for i in range(1, 7)),
                                       "Repeated sequence number.", {"expect_valid": False, "expect_issue_codes": ["DUPLICATE"]}),
        "MAL_bad_timestamp.csv": (hdr + "".join(row(i, i * 1000.0, "5.001", ts=("not-a-time" if i == 2 else None)) for i in range(1, 7)),
                                  "Unparseable timestamp.", {"expect_valid": False, "expect_issue_codes": ["INVALID_TIMESTAMP"]}),
        "MAL_out_of_range.csv": (hdr + "".join(row(i, i * 1000.0, {5: "1000.0"}.get(i, "5.001")) for i in range(1, 7)),
                                 "Physically implausible value.", {"expect_valid": False, "expect_issue_codes": ["OUT_OF_RANGE"]}),
        "MAL_sequence_gap.csv": (hdr + "".join(row(s, s * 1000.0, "5.001") for s in [1, 2, 3, 9, 10, 11]),
                                 "Sequence jump (warning, not rejection).", {"expect_valid": True, "expect_issue_codes": ["SEQUENCE_GAP"]}),
        "MAL_invalid_status.csv": (hdr + "".join(row(i, i * 1000.0, "5.001", st=("ERR_SENSOR_INVALID" if i == 3 else "OK")) for i in range(1, 7)),
                                   "Non-OK status (warning at schema level).", {"expect_valid": True, "expect_issue_codes": ["SENSOR_STATUS_WARNING"]}),
        "MAL_missing_sequence_column.csv": ("experiment_id,elapsed_ms,voltage_V,status\n" + "".join(f"MAL,{i*1000.0},5.001,OK\n" for i in range(6)),
                                            "No sequence column (ingestion auto-generates and records it).", {"expect_valid": True, "expect_auto_sequence": True}),
    }
    manifest = {}
    for name, (content, desc, expect) in fixtures.items():
        write_if_changed(os.path.join(out_dir, name), content.encode("utf-8"))
        manifest[name] = {"description": desc, **expect}
    return manifest
