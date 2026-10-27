"""
IMUCA: Intelligent Measurement, Uncertainty, Calibration and Analysis.

A modular, scientifically defensible measurement analysis foundation for low-cost
measurement systems covering DC voltage, DC current, and temperature.
"""

__version__ = "1.0.0"
__author__ = "IMUCA Engineering Team"

from src.imuca.schema import (
    MeasurementRecord,
    validate_schema,
    convert_voltage,
    convert_current,
    convert_temperature,
    SchemaValidationResult,
    CANONICAL_COLUMNS
)

from src.imuca.data_ingestion import (
    DataIngestionPipeline,
    MeasurementStreamBuffer,
    IngestionDiagnostics
)

from src.imuca.synthetic_data import (
    SyntheticDataGenerator,
    SyntheticScenarioConfig
)

from src.imuca.data_quality import (
    DataQualityAssessor,
    QualityAssessmentReport,
    FaultDetectionMetrics,
    SamplingIntervalDiagnostics
)

from src.imuca.measurement_metrics import (
    compute_descriptive_statistics,
    compute_error_metrics,
    compute_pooled_repeatability,
    compute_residual_diagnostics,
    DescriptiveStatistics,
    ErrorMetrics,
    RepeatabilityMetrics
)

from src.imuca.uncertainty import (
    evaluate_type_a,
    evaluate_type_b,
    evaluate_shunt_current_uncertainty,
    build_uncertainty_budget,
    round_uncertainty_metrology,
    UncertaintyBudget,
    UncertaintyComponent
)

from src.imuca.calibration import (
    CalibrationEngine,
    CalibrationModel,
    CalibrationValidationComparison
)

from src.imuca.validation import (
    evaluate_guard_banded_conformity,
    analyze_temporal_drift,
    ConformityAssessmentResult,
    DriftAnalysisResult
)

from src.imuca.reporting import (
    MetrologyReportGenerator
)

__all__ = [
    "MeasurementRecord",
    "validate_schema",
    "convert_voltage",
    "convert_current",
    "convert_temperature",
    "SchemaValidationResult",
    "CANONICAL_COLUMNS",
    "DataIngestionPipeline",
    "MeasurementStreamBuffer",
    "IngestionDiagnostics",
    "SyntheticDataGenerator",
    "SyntheticScenarioConfig",
    "DataQualityAssessor",
    "QualityAssessmentReport",
    "FaultDetectionMetrics",
    "SamplingIntervalDiagnostics",
    "compute_descriptive_statistics",
    "compute_error_metrics",
    "compute_pooled_repeatability",
    "compute_residual_diagnostics",
    "DescriptiveStatistics",
    "ErrorMetrics",
    "RepeatabilityMetrics",
    "evaluate_type_a",
    "evaluate_type_b",
    "evaluate_shunt_current_uncertainty",
    "build_uncertainty_budget",
    "round_uncertainty_metrology",
    "UncertaintyBudget",
    "UncertaintyComponent",
    "CalibrationEngine",
    "CalibrationModel",
    "CalibrationValidationComparison",
    "evaluate_guard_banded_conformity",
    "analyze_temporal_drift",
    "ConformityAssessmentResult",
    "DriftAnalysisResult",
    "MetrologyReportGenerator"
]
