"""
IMUCA Synthetic Data Generator.

Section 6 Specification:
- Generates reproducible multi-measurand datasets (Voltage, Current, Temperature).
- Rigorously separates ground-truth values from observed simulated readings.
- Simulates documented error components: offset, gain error, noise, quantization,
  linear drift, isolated outliers, missing samples, sequence gaps, and status faults.
- Includes metadata export and deterministic random seeds.
"""

from __future__ import annotations
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import numpy as np
import pandas as pd


@dataclass
class SyntheticScenarioConfig:
    """Configuration parameters for a simulated measurement scenario."""
    scenario_name: str
    description: str
    measurand: str                   # 'voltage_V', 'current_mA', 'temperature_C'
    num_samples: int = 100
    sampling_period_s: float = 1.0
    random_seed: int = 42

    # Reference profile: 'stepped', 'constant', 'ramp', 'sinusoidal'
    profile_type: str = "stepped"
    nominal_min: float = 0.5
    nominal_max: float = 5.0
    num_steps: int = 10
    dwell_per_step: int = 10         # Repeated measurements per step

    # Systematic errors
    offset: float = 0.0              # Additive offset b
    gain_error: float = 0.0          # Relative gain error g (meas = (1+g)*true + offset)
    quantization_step: Optional[float] = None # ADC quantization step

    # Random errors
    noise_std: float = 0.001         # Random Gaussian noise standard deviation

    # Drift and environmental effects
    drift_rate_per_s: float = 0.0    # Linear temporal drift rate
    temp_coefficient: float = 0.0    # Error per degC of environmental variation
    nominal_env_temp_c: float = 23.0 # Baseline ambient temperature

    # Fault and integrity injection
    outlier_indices: List[int] = field(default_factory=list)
    outlier_magnitudes: List[float] = field(default_factory=list)
    missing_sample_indices: List[int] = field(default_factory=list)
    duplicate_seq_indices: List[int] = field(default_factory=list)
    gap_after_indices: List[int] = field(default_factory=list)
    gap_sizes: List[int] = field(default_factory=list)
    sensor_fault_indices: List[int] = field(default_factory=list)
    fault_status_value: str = "ERROR_COMM_TIMEOUT"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SyntheticDataGenerator:
    """
    Generator for metrology-grade synthetic datasets.
    Stores ground truth distinctly from sensor observations.
    """

    def __init__(self, seed: Optional[int] = None):
        self.default_seed = seed or 42

    def generate_scenario(self, config: SyntheticScenarioConfig) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate a synthetic dataset from a scenario configuration.
        Returns:
            (dataset_df, metadata_dict)
        """
        rng = np.random.default_rng(config.random_seed)
        n = config.num_samples

        # 1. Generate nominal reference trajectory (ground truth)
        if config.profile_type == "stepped":
            step_values = np.linspace(config.nominal_min, config.nominal_max, config.num_steps)
            repeats = int(np.ceil(n / config.num_steps))
            true_vals = np.repeat(step_values, repeats)[:n]
        elif config.profile_type == "ramp":
            true_vals = np.linspace(config.nominal_min, config.nominal_max, n)
        elif config.profile_type == "constant":
            true_vals = np.full(n, config.nominal_min)
        elif config.profile_type == "sinusoidal":
            t = np.linspace(0, 2 * np.pi, n)
            mid = 0.5 * (config.nominal_min + config.nominal_max)
            amp = 0.5 * (config.nominal_max - config.nominal_min)
            true_vals = mid + amp * np.sin(t)
        else:
            true_vals = np.linspace(config.nominal_min, config.nominal_max, n)

        # 2. Time series indices
        elapsed_s = np.arange(n) * config.sampling_period_s
        elapsed_ms = elapsed_s * 1000.0

        # Ambient temperature profile (nominal plus slight sinusoidal fluctuation)
        env_temp = config.nominal_env_temp_c + 0.5 * np.sin(2 * np.pi * elapsed_s / (n * config.sampling_period_s + 1e-6))

        # 3. Reference instrument reading (has slight independent reference uncertainty)
        # Reference instrument is calibrated and very accurate, but NOT identical to mathematical truth
        ref_noise = rng.normal(0.0, config.noise_std * 0.1, size=n)
        ref_vals = true_vals + ref_noise

        # 4. Device Under Test (DUT) observed reading model
        # DUT = (1 + gain_error) * GroundTruth + offset + drift(t) + temp_effect + noise
        drift_component = config.drift_rate_per_s * elapsed_s
        temp_component = config.temp_coefficient * (env_temp - config.nominal_env_temp_c)
        dut_noise = rng.normal(0.0, config.noise_std, size=n)

        observed = (1.0 + config.gain_error) * true_vals + config.offset + drift_component + temp_component + dut_noise

        # 5. Quantization (if configured)
        if config.quantization_step is not None and config.quantization_step > 0:
            q = config.quantization_step
            observed = np.round(observed / q) * q

        # 6. Fault and Anomaly Injections
        fault_labels = np.zeros(n, dtype=bool)
        statuses = ["OK"] * n
        seq_numbers = list(np.arange(1, n + 1))

        # Outliers
        for idx, mag in zip(config.outlier_indices, config.outlier_magnitudes):
            if 0 <= idx < n:
                observed[idx] += mag
                fault_labels[idx] = True

        # Missing values
        for idx in config.missing_sample_indices:
            if 0 <= idx < n:
                observed[idx] = np.nan
                fault_labels[idx] = True

        # Sensor status faults
        for idx in config.sensor_fault_indices:
            if 0 <= idx < n:
                statuses[idx] = config.fault_status_value
                fault_labels[idx] = True

        # Sequence duplicates
        for idx in config.duplicate_seq_indices:
            if 1 <= idx < n:
                seq_numbers[idx] = seq_numbers[idx - 1]
                fault_labels[idx] = True

        # Gaps
        for idx, gap in zip(config.gap_after_indices, config.gap_sizes):
            if 0 <= idx < n - 1:
                for k in range(idx + 1, n):
                    seq_numbers[k] += gap
                fault_labels[idx + 1] = True

        # 7. Construct canonical DataFrame with strict separation
        # Ground truth is explicitly prefixed with true_ and not confused with reference_*
        base_time = datetime(2026, 10, 25, 0, 0, 0, tzinfo=timezone.utc).timestamp()
        utc_strings = [
            datetime.fromtimestamp(base_time + t_s, tz=timezone.utc).isoformat()
            for t_s in elapsed_s
        ]

        df_data = {
            "experiment_id": [config.scenario_name] * n,
            "device_id": ["SIMULATED_DUT_01"] * n,
            "timestamp_utc": utc_strings,
            "sequence_number": seq_numbers,
            "elapsed_ms": elapsed_ms,
            "status": statuses,
            "data_source": "synthetic_generator",
            "environmental_temperature_C": env_temp,
            "is_injected_fault": fault_labels,  # Ground truth fault indicator for verification
            "notes": [f"Simulated {config.scenario_name}"] * n
        }

        # Place measurand, reference, and ground truth in respective slots
        m = config.measurand
        df_data[m] = observed
        df_data[f"reference_{m}"] = ref_vals
        df_data[f"true_{m}"] = true_vals

        df = pd.DataFrame(df_data)

        # 8. Metadata documentation
        metadata = {
            "generator": "IMUCA Synthetic Data Generator",
            "version": "1.0.0",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scenario": config.to_dict(),
            "summary_statistics": {
                "sample_count": n,
                "injected_fault_count": int(np.sum(fault_labels)),
                "true_mean": float(np.mean(true_vals)),
                "observed_mean": float(np.nanmean(observed)),
                "reference_mean": float(np.mean(ref_vals))
            },
            "disclaimer": "SYNTHETIC SIMULATED DATASET. Not physical hardware readings."
        }

        return df, metadata

    @classmethod
    def create_standard_scenarios(cls) -> Dict[str, SyntheticScenarioConfig]:
        """Factory for four standard benchmark scenarios across Voltage, Current, Temperature."""
        scenarios = {
            # 1. Clean nominal baseline (Voltage sweep: 0.5V to 5.0V, 10 steps, 10 repeats each)
            "nominal_voltage_baseline": SyntheticScenarioConfig(
                scenario_name="nominal_voltage_baseline",
                description="Nominal clean 10-point voltage calibration sweep (0.5V - 5.0V) with 1mV repeatability noise.",
                measurand="voltage_V",
                num_samples=100,
                nominal_min=0.5,
                nominal_max=5.0,
                num_steps=10,
                dwell_per_step=10,
                offset=0.005,           # 5 mV small nominal offset
                gain_error=0.002,       # +0.2% gain error
                noise_std=0.001,        # 1 mV repeatability
                quantization_step=0.001,# 1 mV resolution
                random_seed=101
            ),
            # 2. Pronounced offset and gain error (Current sweep: 100mA to 2000mA, ideal for calibration fitting)
            "current_calibration_sweep": SyntheticScenarioConfig(
                scenario_name="current_calibration_sweep",
                description="DC Current calibration sweep with pronounced +15mA offset and +1.5% gain error.",
                measurand="current_mA",
                num_samples=120,
                nominal_min=100.0,
                nominal_max=2000.0,
                num_steps=12,
                dwell_per_step=10,
                offset=15.0,            # +15 mA offset
                gain_error=0.015,       # +1.5% gain error
                noise_std=0.5,          # 0.5 mA repeatability
                quantization_step=0.1,  # 0.1 mA resolution
                random_seed=102
            ),
            # 3. Drift and environmental sensitivity (Temperature monitoring over 200 seconds)
            "temperature_drift_scenario": SyntheticScenarioConfig(
                scenario_name="temperature_drift_scenario",
                description="Temperature measurement with gradual linear sensor aging drift (+0.02 degC/s) and ambient variation.",
                measurand="temperature_C",
                num_samples=200,
                profile_type="constant",
                nominal_min=45.0,
                nominal_max=45.0,
                drift_rate_per_s=0.015, # 15 mK/s drift
                temp_coefficient=0.05,  # 50 mK per degC
                noise_std=0.0625,       # DS18B20 quantization noise
                quantization_step=0.0625,
                random_seed=103
            ),
            # 4. Fault, outlier, missing sample, and sequence gap stress test
            "fault_stress_scenario": SyntheticScenarioConfig(
                scenario_name="fault_stress_scenario",
                description="Voltage measurement containing injected anomalies: extreme outliers, NaN gaps, duplicates, and timeouts.",
                measurand="voltage_V",
                num_samples=150,
                profile_type="ramp",
                nominal_min=1.0,
                nominal_max=10.0,
                noise_std=0.002,
                outlier_indices=[25, 80, 120],
                outlier_magnitudes=[3.5, -4.0, 8.0],
                missing_sample_indices=[40, 41, 95],
                duplicate_seq_indices=[60],
                gap_after_indices=[110],
                gap_sizes=[5],
                sensor_fault_indices=[135, 136],
                random_seed=104
            )
        }
        return scenarios

    def save_dataset(self, df: pd.DataFrame, metadata: Dict[str, Any], output_dir: str) -> Tuple[str, str]:
        """Save dataset to CSV and metadata to JSON."""
        os.makedirs(output_dir, exist_ok=True)
        name = metadata["scenario"]["scenario_name"]
        csv_path = os.path.join(output_dir, f"{name}.csv")
        json_path = os.path.join(output_dir, f"{name}_metadata.json")

        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return csv_path, json_path
