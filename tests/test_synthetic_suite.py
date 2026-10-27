"""
Validation tests for the IMUCA v2 synthetic benchmark suite (data/synthetic/<group>/).

Statistical checks use tolerances derived from the sampling distribution of the
estimator (k = 5 standard errors) plus, where stated, a small explicit model allowance
(e.g. Sheppard's quantisation approximation). Random samples are never required to
equal their theoretical values exactly.
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.imuca.synthetic_suite import (
    SyntheticSuiteGenerator,
    MEASURAND_UNITS,
    NO_LABEL,
    PARTITIONS,
    derive_run_seed,
    dataframe_to_csv_bytes,
    iter_run_csv_buffers,
)
from src.imuca.synthetic_data import SyntheticDataGenerator
from src.imuca.data_ingestion import DataIngestionPipeline
from src.imuca.data_quality import DataQualityAssessor
from src.imuca.calibration import CalibrationEngine
from src.imuca.validation import analyze_temporal_drift

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config", "synthetic_suite_config.json")
DATA_ROOT = os.path.join(ROOT, "data", "synthetic")
META_DIR = os.path.join(DATA_ROOT, "metadata")
K_SE = 5.0


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture(scope="module")
def gen():
    return SyntheticSuiteGenerator.from_file(CONFIG_PATH)


@pytest.fixture(scope="module")
def suite(gen):
    return gen.generate_all()


@pytest.fixture(scope="module")
def manifest():
    path = os.path.join(META_DIR, "suite_manifest.json")
    assert os.path.exists(path), "Suite not generated: run `python scripts/generate_synthetic_suite.py`."
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def disk(manifest):
    out = {}
    for entry in manifest["files"]:
        df = pd.read_csv(os.path.join(DATA_ROOT, entry["csv_file"]))
        with open(os.path.join(DATA_ROOT, entry["metadata_file"]), "r", encoding="utf-8") as f:
            meta = json.load(f)
        out[entry["scenario_id"]] = (df, meta)
    return out


def _lag(x, tau, dt=1.0):
    """Independent re-implementation of the first-order ZOH lag (test oracle)."""
    if tau <= 0:
        return np.asarray(x, dtype=float).copy()
    a = 1.0 - np.exp(-dt / tau)
    y = np.empty(len(x))
    y[0] = x[0]
    for k in range(1, len(x)):
        y[k] = y[k - 1] + a * (x[k] - y[k - 1])
    return y


def _nominal_dut(df, dev, measurand, gen_cfg):
    """Noise-free DUT response recomputed from exported columns + configuration."""
    if dev["model"] == "direct_adc":
        x = df[f"true_{measurand}"].to_numpy()
        r = x / gen_cfg["measurands"][measurand]["full_scale"]
        return dev["offset"] + (1 + dev["gain_error"]) * x + dev["inl_bow_amplitude"] * 4 * r * (1 - r)
    if dev["model"] == "shunt":
        v = df["true_shunt_voltage_mV"].to_numpy()
        return (dev["adc_offset_mV"] + (1 + dev["adc_gain_error"]) * v) / dev["r_shunt_nominal_ohm"]
    return dev["offset"] + (1 + dev["gain_error"]) * df["true_sensor_element_temperature_C"].to_numpy()


def _noise_and_step(dev):
    if dev["model"] == "shunt":
        r = dev["r_shunt_nominal_ohm"]
        return dev["adc_noise_std_mV"] / r, dev["adc_quantization_mV"] / r
    return dev["noise_std"], dev["quantization_step"]


def _fault_free_ids(gen):
    out = []
    for sc in gen.scenarios:
        if not sc.get("faults") and all(not r.get("faults") for r in sc["runs"]):
            out.append(sc["scenario_id"])
    return out


# ==============================================================================
# 1-2. Columns, dtypes, units
# ==============================================================================

def test_required_columns_exist(disk):
    for sid, (df, meta) in disk.items():
        m = meta["measurand"]
        expected = [c["name"] for c in meta["columns"]]
        assert list(df.columns) == expected, sid
        for c in ["experiment_id", "device_id", "timestamp_utc", "sequence_number", "elapsed_ms", m, "status",
                  "data_source", f"reference_{m}", f"true_{m}", "environmental_temperature_C", "partition",
                  "scenario_id", "run_id", "generation_seed", "operating_condition_id", "error_vs_true",
                  "error_vs_reference", "is_injected_fault", "label_fault_type", "label_fault_event_id", "dq_flags"]:
            assert c in df.columns, f"{sid}: missing {c}"


def test_dtypes_and_units_consistent(disk):
    for sid, (df, meta) in disk.items():
        m = meta["measurand"]
        assert meta["measurand_unit"] == MEASURAND_UNITS[m]
        units = {c["name"]: c["unit"] for c in meta["columns"]}
        assert units[m] == units[f"reference_{m}"] == units[f"true_{m}"] == units["error_vs_true"] == MEASURAND_UNITS[m]
        assert units["elapsed_ms"] == "ms"
        for c in meta["columns"]:
            s = df[c["name"]]
            if c["dtype"] == "float":
                # Integer-valued floats (e.g. elapsed_ms) are written without a decimal point by %.10g
                assert pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s), f"{sid}.{c['name']} is {s.dtype}"
            elif c["dtype"] == "int":
                assert pd.api.types.is_integer_dtype(s), f"{sid}.{c['name']} is {s.dtype}"
            elif c["dtype"] == "bool":
                assert pd.api.types.is_bool_dtype(s), f"{sid}.{c['name']} is {s.dtype}"
            assert c["role"] and c["description"]


# ==============================================================================
# 3. Ground truth vs reference separation
# ==============================================================================

def test_ground_truth_and_reference_not_confused(gen, suite):
    for sid, (df, meta) in suite.items():
        m = meta["measurand"]
        roles = {c["name"]: c["role"] for c in meta["columns"]}
        for name, role in roles.items():
            if name.startswith("true_"):
                assert role == "ground_truth", name
            if name.startswith("reference_"):
                assert role == "reference_observation", name
        ref = df[f"reference_{m}"].to_numpy()
        true = df[f"true_{m}"].to_numpy()
        assert not np.array_equal(ref, true), f"{sid}: reference identical to ground truth"
        # Reference error must be statistically independent of the DUT error
        obs = df[m].to_numpy(dtype=float)
        ok = np.isfinite(obs) & (df["true_injected_error_component"].to_numpy() == 0)
        if ok.sum() > 100:
            dut_err = obs[ok] - true[ok]
            ref_err = ref[ok] - true[ok]
            # remove per-setpoint means so the shared systematic structure does not dominate
            g = df[ok].groupby(["experiment_id", "setpoint_index"])
            de = dut_err - g[m].transform("mean").to_numpy() + g[f"true_{m}"].transform("mean").to_numpy()
            re = ref_err - g[f"reference_{m}"].transform("mean").to_numpy() + g[f"true_{m}"].transform("mean").to_numpy()
            if np.std(de) > 0 and np.std(re) > 0 and sid.startswith(("VOLT_SWEEP", "CURR_SWEEP_AMBIENT", "FD_VOLT_NONE")):
                assert abs(np.corrcoef(de, re)[0, 1]) < K_SE / np.sqrt(ok.sum()), sid

    # Reference residual matches its own documented error model (not the DUT model)
    for m, sid in [("voltage_V", "VOLT_SWEEP_LINEAR"), ("current_mA", "CURR_SWEEP_AMBIENT"), ("temperature_C", "TEMP_PLATEAUS")]:
        df, meta = suite[sid]
        rc = gen.config["reference_instruments"][m]
        real = meta["reference_error_model"]
        resid = []
        for _, run in df.groupby("experiment_id"):
            sensed = _lag(run[f"true_{m}"].to_numpy(), rc["time_constant_s"])
            resid.append(run[f"reference_{m}"].to_numpy() - (real["realized_offset"] + (1 + real["realized_gain_error"]) * sensed))
        resid = np.concatenate(resid)
        expected_sd = np.sqrt(rc["noise_std"] ** 2 + rc["resolution"] ** 2 / 12)
        n = len(resid)
        assert abs(resid.mean()) < K_SE * expected_sd / np.sqrt(n), sid
        assert abs(resid.std(ddof=1) / expected_sd - 1) < K_SE / np.sqrt(2 * (n - 1)) + 0.02, sid


# ==============================================================================
# 4. Missing values remain missing
# ==============================================================================

def test_missing_and_non_finite_values_preserved(disk):
    for sid, (df, meta) in disk.items():
        m = meta["measurand"]
        v = df[m].to_numpy(dtype=float)
        nan_rows = np.isnan(v)
        inf_rows = np.isinf(v)
        assert nan_rows.sum() == meta["missing_data"]["nan_observation_rows"], sid
        assert inf_rows.sum() == meta["missing_data"]["non_finite_observation_rows"], sid
        types = df["label_fault_type"].astype(str)
        assert np.array_equal(nan_rows, types.str.contains("missing_samples").to_numpy()), sid
        assert np.array_equal(inf_rows, types.str.contains("non_finite").to_numpy()), sid
        assert df.loc[nan_rows, "error_vs_true"].isna().all(), sid
        assert (df.loc[nan_rows, "dq_flags"].str.contains("MISSING_VALUE")).all(), sid
        # Reference and truth are not erased by DUT faults
        assert df[f"true_{m}"].notna().all() and np.isfinite(df[f"true_{m}"]).all(), sid
        assert np.isfinite(df[f"reference_{m}"]).all(), sid


# ==============================================================================
# 5. Injected faults match their metadata labels
# ==============================================================================

def test_injected_faults_match_metadata(gen, suite):
    for sid, (df, meta) in suite.items():
        m = meta["measurand"]
        dev = gen.config["devices"][gen.get_scenario(sid)["device_id"]]
        assert np.array_equal(df["is_injected_fault"].to_numpy(), (df["label_fault_type"] != NO_LABEL).to_numpy()), sid
        ids = df["label_fault_event_id"].str.split(";")
        n_single = len([1 for s in df["label_fault_type"] if s != NO_LABEL and ";" not in s])
        assert n_single <= df["is_injected_fault"].sum()
        for ev in meta["fault_events"]:
            run = df[df["experiment_id"] == ev["run_id"]].reset_index(drop=True)
            rows = run.index[run["label_fault_event_id"].str.split(";").apply(lambda l: ev["event_id"] in l)].to_numpy()
            assert len(rows) == ev["labelled_row_count"] > 0, ev["event_id"]
            assert run.loc[rows, "label_fault_type"].str.contains(ev["fault_type"]).all()
            ft, k, mag = ev["fault_type"], ev["onset_index"], ev["magnitude"]
            seq = run["sequence_number"].to_numpy()
            t_s = run["elapsed_ms"].to_numpy() / 1000.0
            if ft in ("isolated_spike", "offset_shift", "abrupt_change"):
                assert np.allclose(run.loc[rows, "true_injected_error_component"], mag, rtol=1e-12, atol=1e-12), ev["event_id"]
                if ft == "isolated_spike":
                    assert len(rows) == 1 and seq[rows[0]] == k + 1
                if ft == "abrupt_change":
                    assert len(rows) == ev["duration_samples"]
            elif ft == "gain_change":
                sensed = run["true_sensor_element_temperature_C"] if dev["model"] == "first_order_lag" else run[f"true_{m}"]
                assert np.allclose(run.loc[rows, "true_injected_error_component"], mag * sensed[rows], rtol=1e-9)
            elif ft == "gradual_drift":
                expected = mag * (t_s[rows] - ev["onset_elapsed_ms"] / 1000.0)
                assert np.allclose(run.loc[rows, "true_drift_component"], expected, rtol=1e-9, atol=1e-12)
                assert (run.loc[run.index < rows.min(), "true_drift_component"] == 0).all()
            elif ft == "stuck_signal":
                vals = run.loc[rows, m].to_numpy()
                assert np.all(vals == run.loc[rows.min() - 1, m]), ev["event_id"]
                assert len(rows) == ev["duration_samples"]
            elif ft == "missing_samples":
                assert run.loc[rows, m].isna().all() and len(rows) == ev["duration_samples"]
            elif ft == "non_finite":
                v = run.loc[rows[0], m]
                assert np.isinf(v) and np.sign(v) == (1 if ev["non_finite_value"] == "+inf" else -1)
            elif ft == "invalid_status":
                assert (run.loc[rows, "status"] == ev["status_code"]).all() and len(rows) == ev["duration_samples"]
            elif ft == "duplicate_sequence":
                r = rows[0]
                assert len(rows) == 1 and seq[r] == seq[r - 1] == k + 1
                assert run.loc[r, "elapsed_ms"] == run.loc[r - 1, "elapsed_ms"]
                assert run.loc[r, m] == run.loc[r - 1, m] or (np.isnan(run.loc[r, m]) and np.isnan(run.loc[r - 1, m]))
            elif ft == "communication_gap":
                r = rows[0]
                assert len(rows) == 1 and seq[r] - seq[r - 1] - 1 == ev["duration_samples"]
                assert seq[r] == k + ev["duration_samples"] + 1


def test_fault_benchmark_classes_are_individually_labelled(suite, gen):
    classes = gen.config["fault_benchmark"]["classes"]
    for mcfg in gen.config["fault_benchmark"]["measurands"].values():
        for cls in classes:
            df, meta = suite[f"{mcfg['prefix']}_{cls.upper()}"]
            present = set()
            for s in df["label_fault_type"]:
                present.update(s.split(";"))
            present.discard(NO_LABEL)
            assert present == (set() if cls == NO_LABEL else {cls})
            if cls != NO_LABEL:
                assert {e["fault_type"] for e in meta["fault_events"]} == {cls}
                assert all(e["observability"] for e in meta["fault_events"])


# ==============================================================================
# 6. Fault-free scenarios contain no unintended faults
# ==============================================================================

def test_fault_free_scenarios_are_clean(gen, suite):
    ids = _fault_free_ids(gen)
    assert len(ids) >= 10
    for sid in ids:
        df, meta = suite[sid]
        m = meta["measurand"]
        dev = gen.config["devices"][gen.get_scenario(sid)["device_id"]]
        assert not df["is_injected_fault"].any(), sid
        assert (df["label_fault_type"] == NO_LABEL).all() and (df["dq_flags"] == "NONE").all(), sid
        assert (df["status"] == "OK").all() and np.isfinite(df[m]).all(), sid
        assert (df["true_injected_error_component"] == 0).all() and (df["true_drift_component"] == 0).all()
        for _, run in df.groupby("experiment_id"):
            assert np.array_equal(run["sequence_number"].to_numpy(), np.arange(1, len(run) + 1))
        sigma, q = _noise_and_step(dev)
        resid = df[m].to_numpy() - _nominal_dut(df, dev, m, gen.config)
        assert np.max(np.abs(resid)) < 6.0 * sigma + q / 2.0, f"{sid}: unexpected excursion"


# ==============================================================================
# 7. Reproducibility
# ==============================================================================

def test_seed_reproducibility_in_memory():
    a, _ = SyntheticSuiteGenerator.from_file(CONFIG_PATH).generate_scenario("FD_CURR_COMMUNICATION_GAP")
    b, _ = SyntheticSuiteGenerator.from_file(CONFIG_PATH).generate_scenario("FD_CURR_COMMUNICATION_GAP")
    pd.testing.assert_frame_equal(a, b)


def test_different_seed_root_changes_data():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    a, _ = SyntheticSuiteGenerator(cfg).generate_scenario("VOLT_REPEATABILITY")
    cfg["seed_roots"]["test"] += 1
    b, _ = SyntheticSuiteGenerator(cfg).generate_scenario("VOLT_REPEATABILITY")
    ta, tb = a[a.partition == "test"], b[b.partition == "test"]
    ca, cb = a[a.partition == "calibration"], b[b.partition == "calibration"]
    assert not np.array_equal(ta["voltage_V"].to_numpy(), tb["voltage_V"].to_numpy())
    assert np.array_equal(ca["voltage_V"].to_numpy(), cb["voltage_V"].to_numpy())


def test_on_disk_files_match_fresh_regeneration(gen, manifest):
    assert gen.verify_against_manifest(DATA_ROOT) == []
    assert manifest["config_sha256"] == gen.config_sha256


def test_export_refuses_to_overwrite_changed_raw_data(tmp_path):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["scenarios"] = [s for s in cfg["scenarios"] if s["scenario_id"] == "VOLT_REPEATABILITY"]
    cfg.pop("fault_benchmark")
    g = SyntheticSuiteGenerator(cfg)
    g.export(str(tmp_path))
    assert g.export(str(tmp_path))["file_status"]["VOLT_REPEATABILITY"] == "unchanged"
    csv = tmp_path / "voltage" / "VOLT_REPEATABILITY.csv"
    csv.write_text(csv.read_text() + "\n")
    with pytest.raises(FileExistsError):
        g.export(str(tmp_path))


# ==============================================================================
# 8. Statistical consistency with the configured generator
# ==============================================================================

def test_offset_and_gain_recovered(gen, suite):
    df, _ = suite["VOLT_SWEEP_LINEAR"]
    dev = gen.config["devices"]["DUT_V01"]
    res = stats.linregress(df["true_voltage_V"], df["voltage_V"])
    assert abs(res.slope - (1 + dev["gain_error"])) < K_SE * res.stderr
    assert abs(res.intercept - dev["offset"]) < K_SE * res.intercept_stderr


def test_noise_level_matches_configuration(gen, suite):
    for sid in ["VOLT_SWEEP_LINEAR", "VOLT_SWEEP_NONLINEAR", "CURR_SWEEP_AMBIENT", "CURR_SWEEP_SELFHEAT", "TEMP_PLATEAUS", "TEMP_RAMPS"]:
        df, meta = suite[sid]
        m = meta["measurand"]
        dev = gen.config["devices"][gen.get_scenario(sid)["device_id"]]
        sigma, q = _noise_and_step(dev)
        resid = df[m].to_numpy() - _nominal_dut(df, dev, m, gen.config)
        n = len(resid)
        expected = np.sqrt(sigma ** 2 + q ** 2 / 12.0)  # Sheppard approximation
        assert abs(resid.mean()) < K_SE * expected / np.sqrt(n) + 0.01 * q, sid
        assert abs(resid.std(ddof=1) / expected - 1) < K_SE / np.sqrt(2 * (n - 1)) + 0.03, sid


def test_drift_rate_recovered(gen, suite):
    for sid in ["VOLT_DRIFT", "CURR_DRIFT", "TEMP_DRIFT"]:
        df, meta = suite[sid]
        m = meta["measurand"]
        dev = gen.config["devices"][gen.get_scenario(sid)["device_id"]]
        drift_events = [e for e in meta["fault_events"] if e["fault_type"] == "gradual_drift"]
        assert len(drift_events) == 2
        for ev in drift_events:
            run = df[df["experiment_id"] == ev["run_id"]]
            post = run[run["sequence_number"] > ev["onset_index"]]
            resid = post[m].to_numpy() - _nominal_dut(post, dev, m, gen.config)
            res = stats.linregress(post["elapsed_ms"].to_numpy() / 1000.0, resid)
            assert abs(res.slope - ev["magnitude"]) < K_SE * res.stderr, (sid, res.slope, ev["magnitude"])
        # Control runs: no drift component
        for exp_id in meta["partitions"]["test"]["experiment_ids"]:
            if exp_id not in {e["run_id"] for e in drift_events}:
                assert (df.loc[df.experiment_id == exp_id, "true_drift_component"] == 0).all()


def test_shunt_model_internally_consistent(gen, disk, suite):
    for sid in ["CURR_SWEEP_AMBIENT", "CURR_SWEEP_SELFHEAT", "CURR_LOAD_STEPS", "CURR_INTEGRITY", "FD_CURR_NONE"]:
        df, meta = disk[sid]
        dev = gen.config["devices"][meta["sensor_error_model"]["device_id"]]
        fin = np.isfinite(df["current_mA"])
        assert np.allclose(df.loc[fin, "current_mA"], df.loc[fin, "shunt_voltage_mV"] / dev["r_shunt_nominal_ohm"], rtol=1e-8, atol=1e-9)
        assert np.allclose(df["true_shunt_voltage_mV"], df["true_current_mA"] * df["true_shunt_resistance_ohm"], rtol=1e-8)
        r_ref = dev["r_shunt_nominal_ohm"] * (1 + dev["r_shunt_actual_deviation"])
        expected_r = r_ref * (1 + dev["r_shunt_tcr_per_C"] * (df["true_shunt_temperature_C"] - dev["r_shunt_reference_temp_C"]))
        assert np.allclose(df["true_shunt_resistance_ohm"], expected_r, rtol=1e-8)
    # Self-heating only where explicitly modelled
    df, _ = suite["CURR_SWEEP_AMBIENT"]
    tau_th = gen.config["devices"]["DUT_I01"]["thermal_time_constant_s"]
    for _, run in df.groupby("experiment_id"):
        # No self-heating: shunt follows ambient through its thermal lag only
        assert np.allclose(run["true_shunt_temperature_C"], _lag(run["true_environmental_temperature_C"].to_numpy(), tau_th), atol=1e-9)
    df, _ = suite["CURR_SWEEP_SELFHEAT"]
    run = df[df.run_id == "CAL01"]
    end_low = run[run.setpoint_index == 0]["true_shunt_temperature_C"].iloc[-1]
    end_high = run[run.setpoint_index == run.setpoint_index.max()]["true_shunt_temperature_C"].iloc[-1]
    assert end_high - end_low > 20.0


def test_temperature_lag_follows_first_order_response(gen, suite):
    tau = gen.config["devices"]["DUT_T01"]["time_constant_s"]
    df, _ = suite["TEMP_INTEGRITY"]
    run = df[df.run_id == "CAL01"].set_index("sequence_number")
    step_seq = run.index[run["label_process_event"] == "true_step"][0]
    before = run.loc[step_seq - 1, "true_temperature_C"]
    after = run.loc[step_seq, "true_temperature_C"]
    k = int(tau)
    if step_seq - 1 + k in run.index:
        elem = run.loc[step_seq - 1 + k, "true_sensor_element_temperature_C"]
        frac = (elem - before) / (after - before)
        assert abs(frac - (1 - np.exp(-k / tau))) < 1e-6


def test_temperature_trajectories_physically_coherent(gen, suite):
    max_rate = 2.0  # degC/s, config/default_config.json max_rate_of_change_per_sec
    for sid in ["TEMP_PLATEAUS", "TEMP_RAMPS", "TEMP_DRIFT", "FD_TEMP_NONE"]:
        df, _ = suite[sid]
        for _, run in df.groupby("experiment_id"):
            rate = np.abs(np.diff(run["true_temperature_C"].to_numpy())) / gen.period_s
            assert rate.max() <= 0.1 + 1e-9, sid
            elem_rate = np.abs(np.diff(run["true_sensor_element_temperature_C"].to_numpy()))
            assert elem_rate.max() < max_rate
            assert run["true_temperature_C"].between(-55, 125).all()


# ==============================================================================
# 9. Timestamps and sequences
# ==============================================================================

def test_timestamp_and_sequence_behaviour(gen, suite):
    for sid, (df, meta) in suite.items():
        starts = {}
        for exp_id, run in df.groupby("experiment_id", sort=False):
            seq = run["sequence_number"].to_numpy()
            el = run["elapsed_ms"].to_numpy()
            assert np.allclose(el, (seq - 1) * gen.period_s * 1000.0), exp_id
            ts = pd.to_datetime(run["timestamp_utc"], format="ISO8601")
            assert np.allclose((ts - ts.iloc[0]).dt.total_seconds().to_numpy() * 1000.0, el - el[0]), exp_id
            d = np.diff(seq)
            dup = run["label_fault_type"].str.contains("duplicate_sequence").to_numpy()[1:]
            gap = run["label_fault_type"].str.contains("communication_gap").to_numpy()[1:]
            assert np.all(d[dup] == 0) and np.all(d[~dup] >= 1), exp_id
            assert np.all(d[~dup & ~gap] == 1), exp_id
            starts[exp_id] = (meta_part(meta, exp_id), ts.iloc[0])
        order = sorted(starts.values(), key=lambda t: t[1])
        assert [PARTITIONS.index(p) for p, _ in order] == sorted(PARTITIONS.index(p) for p, _ in order), sid


def meta_part(meta, exp_id):
    return next(r["partition"] for r in meta["runs"] if r["experiment_id"] == exp_id)


# ==============================================================================
# 10. Partition leakage
# ==============================================================================

def test_partitions_do_not_leak(gen, suite):
    all_seeds, all_hashes = [], set()
    for sid, (df, meta) in suite.items():
        per_run = df.groupby("experiment_id")["partition"].nunique()
        assert (per_run == 1).all(), sid
        ids = {p: set(v["experiment_ids"]) for p, v in meta["partitions"].items()}
        assert not (ids["calibration"] & ids["validation"]) and not (ids["calibration"] & ids["test"]) and not (ids["validation"] & ids["test"])
        assert ids["calibration"] and ids["validation"] and ids["test"], sid
        for r in meta["runs"]:
            assert r["generation_seed"] == derive_run_seed(gen.seed_roots[r["partition"]], sid, int(r["run_id"][3:]))
            all_seeds.append(r["generation_seed"])
            h = hash(df.loc[df.experiment_id == r["experiment_id"], meta["measurand"]].to_numpy().tobytes())
            assert h not in all_hashes, f"{r['experiment_id']} duplicates another run's observations"
            all_hashes.add(h)
    assert len(all_seeds) == len(set(all_seeds)), "generation seeds must be unique across the suite"
    assert len(set(gen.seed_roots.values())) == 3


def test_noise_realisations_independent_across_partitions(gen, suite):
    df, _ = suite["VOLT_SWEEP_LINEAR"]
    dev = gen.config["devices"]["DUT_V01"]
    cal = df[df.run_id == "CAL01"]
    tst = df[df.run_id == "TST01"]  # same grid_A profile, independent seed root
    rc = cal["voltage_V"].to_numpy() - _nominal_dut(cal, dev, "voltage_V", gen.config)
    rt = tst["voltage_V"].to_numpy() - _nominal_dut(tst, dev, "voltage_V", gen.config)
    r = np.corrcoef(rc, rt)[0, 1]
    assert abs(r) < K_SE / np.sqrt(len(rc))


def test_heldout_conditions_only_in_test(suite):
    for sid in ["VOLT_SWEEP_LINEAR", "VOLT_SWEEP_NONLINEAR", "CURR_SWEEP_AMBIENT", "CURR_SWEEP_SELFHEAT", "TEMP_PLATEAUS"]:
        df, _ = suite[sid]
        trainval = df[df.partition != "test"]
        test = df[df.partition == "test"]
        held = set(test["operating_condition_id"]) - set(trainval["operating_condition_id"])
        assert held, sid
        assert test.loc[test.operating_condition_id.str.startswith("extrapolation"), "true_" + df.columns[13]].min() > trainval["true_" + df.columns[13]].max()


# ==============================================================================
# 11-12. Existing IMUCA pipeline on generated and malformed datasets
# ==============================================================================

def test_existing_pipeline_processes_valid_datasets(manifest):
    pipe = DataIngestionPipeline()
    engine = CalibrationEngine()
    files = {f["scenario_id"]: f for f in manifest["files"]}
    for sid in ["VOLT_SWEEP_LINEAR", "CURR_SWEEP_AMBIENT", "TEMP_PLATEAUS", "FD_VOLT_NONE", "FD_CURR_NONE", "FD_TEMP_NONE"]:
        m = files[sid]["measurand"]
        cal_x, cal_y = [], []
        for exp_id, buf in iter_run_csv_buffers(os.path.join(DATA_ROOT, files[sid]["csv_file"])):
            df, diag = pipe.load_csv(buf, source_id=exp_id)
            assert diag.schema_validation.is_valid, exp_id
            assert diag.schema_validation.error_record_count == 0
            assert m in diag.mapped_columns and f"reference_{m}" in diag.mapped_columns
            rep = DataQualityAssessor().assess(df, measurand_col=m, range_limits=(-60.0, 4000.0), ground_truth_fault_col=None)
            assert rep.error_records_count == 0, exp_id
            if "CAL" in exp_id:
                # Temperature: protocol-stable plateau samples only (unmapped columns carry a raw_ prefix)
                keep = (df["raw_protocol_phase"] == "plateau_stable").to_numpy() if m == "temperature_C" else np.ones(len(df), bool)
                cal_x.append(df[m].to_numpy()[keep])
                cal_y.append(df[f"reference_{m}"].to_numpy()[keep])
        model = engine.select_best_model(np.concatenate(cal_x), np.concatenate(cal_y))
        assert model.r_squared > 0.999, sid
    df = pd.read_csv(os.path.join(DATA_ROOT, files["VOLT_DRIFT"]["csv_file"]))
    run = df[df.run_id == "VAL01"]
    res = analyze_temporal_drift(run.elapsed_ms / 1000.0, run.voltage_V - run.reference_voltage_V, nominal_target=0.0)
    assert res.is_drift_significant


def test_malformed_datasets_rejected_or_flagged():
    with open(os.path.join(META_DIR, "malformed_manifest.json"), "r", encoding="utf-8") as f:
        mal = json.load(f)
    assert len(mal) >= 10
    pipe = DataIngestionPipeline()
    for name, exp in mal.items():
        _, diag = pipe.load_csv(os.path.join(DATA_ROOT, "malformed", name))
        sv = diag.schema_validation
        assert sv.is_valid == exp["expect_valid"], name
        if exp.get("expect_read_error"):
            assert "read_error" in diag.file_metadata, name
        codes = {d.issue_code for d in sv.diagnostics}
        for c in exp.get("expect_issue_codes", []):
            assert c in codes, f"{name}: expected {c}, got {codes}"
        if exp.get("expect_auto_sequence"):
            assert diag.mapped_columns["sequence_number"] == "[auto-generated sequence]"
        if not exp["expect_valid"] and sv.total_records > 0:
            assert sv.error_record_count > 0


def test_whole_file_ingestion_of_multi_run_csv_is_flagged(manifest):
    """Documents a known constraint: ingesting a multi-run file as one session yields sequence errors."""
    f = next(x for x in manifest["files"] if x["scenario_id"] == "VOLT_REPEATABILITY")
    _, diag = DataIngestionPipeline().load_csv(os.path.join(DATA_ROOT, f["csv_file"]))
    assert not diag.schema_validation.is_valid


# ==============================================================================
# ML benchmark specification and historical data
# ==============================================================================

def test_ml_spec_features_respect_role_policy(suite):
    with open(os.path.join(ROOT, "config", "ml_benchmark_spec.json"), "r", encoding="utf-8") as f:
        spec = json.load(f)
    policy = spec["column_role_policy"]
    roles = {}
    for _, (_, meta) in suite.items():
        for c in meta["columns"]:
            roles.setdefault(c["name"], set()).add(c["role"])
    for task in spec["tasks"]:
        for feat in task["features"]:
            assert feat in roles, f"{task['task_id']}: unknown feature column {feat}"
            assert roles[feat] <= set(policy["allowed_feature_roles"]), f"{task['task_id']}: {feat} has role {roles[feat]}"
        for d in task["derived_features"]:
            for src in d["source_columns"]:
                r = roles[src]
                assert not (r & set(policy["forbidden_feature_roles"])), f"{task['task_id']}/{d['name']} uses {src}"
                if "reference_observation" in r:
                    assert task["reference_access"] not in ("none", "target_only"), f"{task['task_id']} uses reference without access"
        assert task["target"]["name"] not in task["features"]
        assert not set(task["target"]["source_columns"]) & {fd for fd in task["features"] if "reference_observation" in roles[fd] or "label" in roles[fd]}


def test_historical_milestone1_datasets_preserved():
    gen1 = SyntheticDataGenerator(seed=42)
    for name, cfg in gen1.create_standard_scenarios().items():
        path = os.path.join(DATA_ROOT, f"{name}.csv")
        assert os.path.exists(path), name
        disk_df = pd.read_csv(path)
        df, _ = gen1.generate_scenario(cfg)
        m = cfg.measurand
        assert np.allclose(disk_df[m].to_numpy(), df[m].to_numpy(), equal_nan=True), name
        assert np.allclose(disk_df[f"true_{m}"].to_numpy(), df[f"true_{m}"].to_numpy()), name
