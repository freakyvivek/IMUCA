# IMUCA — Synthetic Data Specification (Suite v2)

> **SYNTHETIC SIMULATED DATA.** Every parameter in this document is a simulation assumption chosen for benchmark coverage. None of them is a verified specification of the INA219, DS18B20 or any other physical device, and no result obtained on these data is evidence of physical instrument performance.

| Item | Location |
|---|---|
| Generator | `src/imuca/synthetic_suite.py` (v2.0.0) |
| Configuration (all parameters) | `config/synthetic_suite_config.json` |
| Generation / verification script | `scripts/generate_synthetic_suite.py` (`--verify`, `--force`) |
| Datasets | `data/synthetic/{voltage,current,temperature,fault_detection}/` |
| Metadata, manifest, fault-event table | `data/synthetic/metadata/` |
| Malformed ingestion fixtures | `data/synthetic/malformed/` |
| File-level catalog (auto-generated) | `docs/DATASET_CATALOG.md` |
| Validation tests | `tests/test_synthetic_suite.py` |
| Conventional baseline | `scripts/run_synthetic_benchmark.py` |

The Milestone-1 generator (`src/imuca/synthetic_data.py`, v1.0.0) and its four datasets directly under `data/synthetic/` are unchanged and remain the inputs of `scripts/run_baseline_experiment.py`. A test (`test_historical_milestone1_datasets_preserved`) checks that they still match the v1 generator.

---

## 1. Why a v2 generator

Inspecting the v1 generator showed these limits for benchmark and ML use. All are kept as they are in v1 for reproducibility.

| v1 behaviour | Consequence | v2 approach |
|---|---|---|
| Reference noise is 0.1 × DUT noise; no reference systematic error | Reference error model is tied to the DUT, not documented as an instrument | Independent reference model per measurand with its own realised offset/gain, noise, resolution, lag and stated U |
| One boolean `is_injected_fault` | Fault classes cannot be separated | Per-record `label_fault_type`, `label_fault_event_id` + event table |
| Gaps shift `sequence_number` but not `elapsed_ms` / timestamps | Time and sequence disagree | Gaps drop whole records; time and sequence stay consistent |
| "Duplicate" overwrites a record's sequence number | Not a duplicated record | An exact copy of the record is inserted |
| `dwell_per_step` unused; description of `temperature_drift_scenario` says 0.02 °C/s while code uses 0.015 °C/s | Documentation drift | Explicit, tested profiles |
| Single run per scenario, no partitions | Calibration/validation can only split correlated samples (baseline script uses a random split of dwell data) | Several independent runs per scenario, partitioned by run |
| No shunt, lag or self-heating physics | Current and temperature behaviour not exercised | Measurand-specific forward models (§3) |

---

## 2. Record model and column roles

For every record the generator separates, in distinct columns:

| Role | Columns | Meaning |
|---|---|---|
| `observation` | `voltage_V` / `current_mA` / `temperature_C`, `shunt_voltage_mV` (current), `status`, `environmental_temperature_C` | What the simulated DUT and ambient sensor report |
| `reference_observation` | `reference_<measurand>`, `reference_expanded_uncertainty_k2` | Reading of a **simulated** reference instrument and its stated U (k = 2) |
| `ground_truth` | `true_<measurand>`, `true_environmental_temperature_C`, `true_drift_component`, `true_injected_error_component`, `true_sensor_element_temperature_C` (temperature), `true_shunt_temperature_C`, `true_shunt_resistance_ohm`, `true_shunt_voltage_mV` (current) | Values imposed by the simulation; never a measurement |
| `derived_error` | `error_vs_true` = obs − true, `error_vs_reference` = obs − reference | Error relative to ground truth and to the reference |
| `label` | `is_injected_fault`, `label_fault_type`, `label_fault_event_id`, `label_process_event` | Injected-fault labels; genuine (non-fault) process events |
| `quality_flag` | `dq_flags` | Flags derivable from observable fields only (`MISSING_VALUE`, `NON_FINITE`, `STATUS_<code>`, `DUPLICATE_SEQ`, `SEQ_GAP_<n>`, `NONE`) |
| `identifier` / `partition` / `provenance` | `scenario_id`, `experiment_id`, `run_id`, `device_id`, `partition`, `generation_seed`, `data_source` | Identification and split assignment |
| `protocol` | `operating_condition_id`, `setpoint_index`, `protocol_phase` | Planned experimental protocol known to the operator. Never encodes fault presence |
| `time` | `timestamp_utc` (ISO 8601, UTC), `sequence_number`, `elapsed_ms` | Acquisition timing |

Field names reuse the canonical schema (`src/imuca/schema.py`): `experiment_id`, `device_id`, `timestamp_utc`, `sequence_number`, `elapsed_ms`, `<measurand>`, `status`, `data_source`, `reference_<measurand>`, `environmental_temperature_C`. `is_injected_fault` keeps the name used by `DataQualityAssessor`. Each metadata file contains the full column dictionary (name, unit, dtype, role, description).

**Units.** Voltage V, current mA, temperature °C, time ms (`elapsed_ms`) and s (rates), resistance Ω. Drift magnitudes are in measurand units per second; gain changes are dimensionless.

**Serialisation.** CSV, UTF-8, `\n` line endings, floats written with `%.10g`. Integer-valued floats (e.g. `elapsed_ms`) are therefore written without a decimal point. Missing values are empty fields; non-finite values are `inf` / `-inf`.

---

## 3. Forward models

`Q(v; q)` denotes round-to-nearest quantisation with step `q`. `N(0, σ)` denotes independent zero-mean Gaussian noise. Δt = 1 s throughout (`sampling_period_s`).

### 3.1 DC voltage (`model: direct_adc`)

$$ V_{obs} = Q\Big(b + (1+g)\,V + a_{INL}\,4\tfrac{V}{FS}\big(1-\tfrac{V}{FS}\big) + \alpha_T (T_{amb}-T_0) + f(t) + N(0,\sigma);\ q\Big),\quad FS = 26\ \text{V} $$

| Device | b (V) | g | a_INL (V) | σ (V) | q (V) | α_T |
|---|---|---|---|---|---|---|
| `DUT_V01` (linear) | +0.008 | +0.25 % | 0 | 0.0015 | 0.001 | 0 |
| `DUT_V02` (nonlinear) | −0.012 | −0.40 % | 0.015 | 0.0015 | 0.001 | 0 |

**Nonlinearity justification.** `DUT_V02` carries a parabolic "bow" INL that is zero at 0 V and full scale and largest (15 mV) at mid-scale. This is the simplest endpoint-referenced INL shape and exists to test whether F-test/BIC model selection adopts a quadratic calibration only when one is needed. `DUT_V01` has no INL, so a linear model should be selected there. Both outcomes are confirmed by the benchmark.

### 3.2 DC current (`model: shunt`)

The instrument measures a shunt voltage and divides by the **nominal** resistance:

$$ R(t) = R_{nom}(1+\delta_R)\,[1+\alpha_R (T_{sh}(t)-T_0)] $$
$$ T_{sh}[k] = T_{sh}[k-1] + (1-e^{-\Delta t/\tau_{th}})\,\big(T_{amb}[k] + R_{th}\,I[k]^2 R[k-1] - T_{sh}[k-1]\big),\quad T_{sh}[0]=T_{amb}[0] $$
$$ V_{sh} = I \cdot R \quad(\text{mA}\cdot\Omega = \text{mV}),\qquad V_{obs} = Q\big(b_V + (1+g_V)V_{sh} + R_{nom} f(t) + N(0,\sigma_V);\ q_V\big),\qquad I_{obs} = V_{obs}/R_{nom} $$

| Device | R_nom (Ω) | δ_R | α_R (1/°C) | R_th (°C/W) | τ_th (s) | b_V (mV) | g_V | σ_V (mV) | q_V (mV) |
|---|---|---|---|---|---|---|---|---|---|
| `DUT_I01` | 0.100 | +0.30 % | 1.0e-4 | **0 (self-heating not modelled)** | 45 | +0.05 | +0.20 % | 0.02 | 0.01 |
| `DUT_I02` | 0.100 | −0.40 % | 1.0e-4 | **40 (self-heating modelled)** | 45 | −0.03 | +0.10 % | 0.02 | 0.01 |

R_nom = 0.100 Ω and the ±0.5 % tolerance band (δ_R lies inside it) come from `config/default_config.json`; q_V = 0.01 mV is that file's `v_shunt_resolution_mv`. The TCR, R_th and τ_th are **assumed scenario parameters**: no verified value is available, and `docs/HARDWARE_READINESS.md` lists the physical TCR as unknown. Self-heating appears only in `DUT_I02` scenarios. At 2.8 A it raises the shunt by about 30 °C, an error of about +0.3 % that depends on load history. Even without self-heating (`DUT_I01`) the shunt follows ambient through τ_th. A test checks the identity `current_mA = shunt_voltage_mV / 0.1` on every finite record, along with `true_shunt_voltage_mV = true_current_mA × true_shunt_resistance_ohm` and the R(T) relation.

### 3.3 Temperature (`model: first_order_lag`)

$$ T_{elem}[k] = T_{elem}[k-1] + (1-e^{-\Delta t/\tau})(T[k]-T_{elem}[k-1]),\quad T_{elem}[0]=T[0] $$
$$ T_{obs} = Q\big(b + (1+g)\,T_{elem} + f(t) + N(0,\sigma);\ q\big) $$

`DUT_T01`: b = +0.25 °C, g = +0.3 %, σ = 0.03 °C, q = 0.0625 °C (the `nominal_resolution` in `config/default_config.json`), τ = 20 s.

The lag is a **simulated** probe time constant, not a sensor specification. The discretisation is exact for zero-order-hold input. True trajectories are continuous ramps (≤ 0.1 °C/s) or plateaus, except the explicitly labelled bath-transfer steps in `TEMP_INTEGRITY` (`label_process_event = true_step`). Those steps are genuine process events, not faults; the sensing element follows them through its lag.

### 3.4 Simulated reference instruments

$$ X_{ref} = o_{ref} + (1+g_{ref})\,\mathrm{lag}(X, \tau_{ref}) + N(0,\sigma_{ref}),\ \text{quantised to resolution} $$

The systematic terms o_ref ~ N(0, offset_std) and g_ref ~ N(0, gain_std) are drawn **once** per instrument from `reference_realization_seed = 31415` and shared by all runs, like a single laboratory reference. Their realised values are ground truth *about the reference*: they are stored in each metadata file and would be unknown in a real laboratory. The reference is therefore not perfect, and calibrating against it leaves a residual error with respect to truth.

| Measurand | Instrument id | offset_std | gain_std | σ | resolution | τ (s) | realised offset | realised gain |
|---|---|---|---|---|---|---|---|---|
| Voltage | `SIM_REF_VOLTMETER_01` | 0.2 mV | 50 ppm | 0.1 mV | 10 µV | 0 | −0.194 mV | +7.7 ppm |
| Current | `SIM_REF_AMMETER_01` | 0.1 mA | 50 ppm | 0.05 mA | 0.01 mA | 0 | −0.084 mA | −68 ppm |
| Temperature | `SIM_REF_THERMOMETER_01` | 0.01 °C | 0 | 0.005 °C | 0.001 °C | 2 | +0.022 °C | 0 |

Stated uncertainty per reading: `reference_expanded_uncertainty_k2 = 2·sqrt(offset_std² + (gain_std·|X_ref|)² + σ² + res²/12)`. It covers steady-state errors only and **excludes the reference's own dynamic lag**. The stated values stay below the `reference_uncertainty` values in `config/default_config.json`.

### 3.5 Ambient

T_amb,true = mean + 0.2·sin(2πt / 3600 s), with mean 23 °C unless a run overrides it (30 °C in one current test run). The ambient sensor adds N(0, 0.05 °C) and has 0.01 °C resolution.

---

## 4. Fault injection

Faults act **only on the DUT**. Reference and ground truth are never altered. Onsets are drawn from each run's fault stream so that they avoid the first and last 10 % of the run (`fault_margin_fraction`) and never overlap another transient event (3-sample guard). Persistent faults start between 25 % and 75 % of the run. Explicit onsets (drift scenarios) override this.

| Class | Stage | Effect | Labelled rows |
|---|---|---|---|
| `isolated_spike` | pre-quantisation | +m on one sample | that sample |
| `offset_shift` | pre-quantisation | +m from onset to end | onset → end |
| `gain_change` | pre-quantisation | +m·(sensed input) from onset | onset → end |
| `gradual_drift` | pre-quantisation | +m·(t − t_onset) from onset; also in `true_drift_component` | onset → end |
| `abrupt_change` | pre-quantisation | +m for `duration` samples (transient level shift) | event window |
| `stuck_signal` | post-quantisation | reading frozen at the last pre-onset value | event window |
| `missing_samples` | post-quantisation | value empty (NaN), status OK | event window |
| `non_finite` | post-quantisation | value ±inf | that sample |
| `invalid_status` | post-quantisation | status ∈ {`ERR_SENSOR_INVALID`, `ERR_OVERRANGE`, `ERR_CRC`} (generic codes, not device codes) | event window |
| `duplicate_sequence` | record | exact copy of a record inserted after it | the copy only |
| `communication_gap` | record | `duration` records dropped (sequence and time jump) | first record after the gap |

The fault-event table (`fault_events` in metadata and `data/synthetic/metadata/fault_events.csv`) gives, per event: id, run, class, onset index / sequence number / elapsed ms, duration (null = persistent), signed magnitude and unit, status code or non-finite sign, labelled-row count and an observability note.

**Ambiguity (documented, not hidden).** Not every fault can be identified from the measurement signal alone:

- `offset_shift`, `abrupt_change`: indistinguishable from a genuine process step without a reference or redundant sensor.
- `gain_change`: at a single operating point, indistinguishable from an offset shift.
- `gradual_drift`: inseparable from a slow true process change without a reference; invisible to pointwise checks.
- `stuck_signal`: with 0.0625 °C quantisation and σ = 0.03 °C, runs of identical readings are normal on a plateau, so stuck temperature signals are partly unobservable.
- `communication_gap`: the lost records do not exist; the label is attached to the next record.
- Genuine process events (`setpoint_change`, `load_step`, `true_step`, `ramp_start`) are labelled in `label_process_event` so that false alarms caused by them can be counted separately.

Fault-free scenarios contain no labels, no non-OK status, no non-finite values, consecutive sequence numbers and no excursion beyond 6σ + q/2 from the nominal model. All of this is tested.

---

## 5. Scenarios

Each scenario contains several independently generated runs; `docs/DATASET_CATALOG.md` lists exact record counts, seeds and checksums.

| Group | Scenario | Coverage |
|---|---|---|
| Voltage | `VOLT_SWEEP_LINEAR` | 11-point sweep 0.5–20 V (20 samples/point): offset, gain, repeatability noise, quantisation; test adds held-out interleaved points and 22/24 V extrapolation |
| | `VOLT_SWEEP_NONLINEAR` | Same protocol with INL bow (nonlinearity) |
| | `VOLT_REPEATABILITY` | 300 repeats at 5 V |
| | `VOLT_DRIFT` | 12 V, 1200 s; gradual drift +5 µV/s (validation) / −8 µV/s (test) with onset; drift-free controls |
| | `VOLT_INTEGRITY` | 4/8/12 V steps (abrupt process changes) with spikes, transient level shift, missing samples, invalid status |
| Current | `CURR_SWEEP_AMBIENT` | 10-point sweep 0.1–2.8 A, shunt tolerance + TCR, no self-heating; test adds held-out points, 3.1 A extrapolation and a 30 °C ambient run |
| | `CURR_SWEEP_SELFHEAT` | Same sweep with modelled self-heating (load-dependent change), 60 s dwell; test adds held-out points and a descending sweep |
| | `CURR_LOAD_STEPS` | Random load steps 0.2–2.5 A with thermal transients |
| | `CURR_DRIFT` | 1.5 A, drift +3 µA/s / −4 µA/s with controls |
| | `CURR_INTEGRITY` | Level steps with spikes, transient shift, missing, invalid status, communication gaps |
| Temperature | `TEMP_PLATEAUS` | Stable plateaus 10–70 °C with 0.1 °C/s ramps; test adds held-out plateaus and 80 °C extrapolation |
| | `TEMP_RAMPS` | 25 → 75 → 30 °C heating/cooling ramps at 0.05 °C/s; test at 0.08 °C/s (sensor lag) |
| | `TEMP_DRIFT` | 45 °C plateau, slow drift +0.5 °C/h (validation) / −0.8 °C/h (test) with controls |
| | `TEMP_INTEGRITY` | Abrupt true steps (bath transfers) with spikes, missing, invalid status, communication gaps |
| Fault detection | `FD_{VOLT,CURR,TEMP}_<CLASS>` | 12 classes (11 fault classes + fault-free `NONE`) × 3 measurands, 4 runs × 600 samples each, one class per scenario |

---

## 6. Seeds, partitions and leakage control

- **Seed roots** per partition: calibration `20261101`, validation `20261102`, test `77031119`. The final test set is drawn from an independent stream.
- **Run seed:** `SeedSequence(entropy=seed_roots[partition], spawn_key=(crc32(scenario_id), run_number)).generate_state(1)[0]`, stored per record (`generation_seed`) and in the metadata. Each run seed is spawned into five independent streams: profile, ambient, DUT noise, reference noise and fault placement.
- **Unit of partitioning:** the run (`experiment_id`). Every run belongs to exactly one partition, and within-run splitting is not used. Run start times are ordered calibration → validation → test, one simulated day apart.
- **Held-out conditions** (interleaved set-points, extrapolation, a different ambient, sweep direction, ramp rate) appear only in the test partition, labelled by `operating_condition_id`.
- **Tested safeguards:** seeds are unique across all 214 runs, no two runs share an identical observation vector, noise realisations of same-profile runs are uncorrelated (|r| < 5/√n), each `experiment_id` belongs to one partition, and seeds re-derive from the documented formula.

## 7. Determinism and immutability

With the same generator version, configuration (SHA-256 recorded in the manifest) and seeds, every CSV is regenerated byte-for-byte. `python scripts/generate_synthetic_suite.py --verify` and `test_on_disk_files_match_fresh_regeneration` check this against the manifest checksums. Export never overwrites a raw file whose content differs unless `--force` is given. Unchanged files keep their original metadata and generation timestamp. Derived outputs go to `data/processed/synthetic_suite_<timestamp>/` and `results/synthetic_benchmark_<timestamp>/`. The numpy/pandas versions used are recorded in metadata, since other versions could in principle change floating-point output.

## 8. Using the data with the existing pipeline

A scenario CSV holds several acquisition sessions, each with its own sequence numbering and elapsed time. `DataIngestionPipeline.load_csv` validates one session per file. Whole-file ingestion therefore reports duplicate and out-of-order sequence errors, and a test asserts this. Use `src.imuca.synthetic_suite.iter_run_csv_buffers(path)` to ingest run by run; all fault-free runs then validate with zero errors.

## 9. Known limitations

White Gaussian noise only; no clock jitter; an ideal calibrator (true value = planned set-point); single-parameter INL; lumped first-order thermal models; assumed TCR / thermal parameters; reference stated U covers steady state only; fault magnitudes and frequencies come from documented ranges, not field statistics. Every metadata file lists its scenario-specific limitations.
