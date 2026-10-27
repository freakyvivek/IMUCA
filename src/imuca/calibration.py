"""
IMUCA Calibration Module.

Section 10 Specification:
- Implements conventional calibration baseline: uncalibrated, linear, and polynomial models.
- Guarantees data-leakage prevention by strictly separating calibration (training)
  and validation (test) observations.
- Conducts statistical model selection (F-test and AIC/BIC) to ensure higher-order
  polynomials are justified before adoption.
- Evaluates pre-calibration vs post-calibration performance on held-out validation data.
- Includes domain verification and extrapolation warnings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
import numpy as np
import scipy.stats as stats
import math

from src.imuca.measurement_metrics import compute_error_metrics, ErrorMetrics


@dataclass
class CalibrationModel:
    """Documented calibration model parameters and diagnostics."""
    model_type: str               # 'uncalibrated', 'linear', 'polynomial'
    degree: int                   # 0 for uncalibrated, 1 for linear, 2+ for polynomial
    coefficients: List[float]     # [a0, a1, ...] where y_corr = a0 + a1*x + a2*x^2 + ...
    coefficient_std_errors: List[float]
    covariance_matrix: List[List[float]]
    r_squared: float
    adjusted_r_squared: float
    residual_std_dev: float       # s_res
    domain_min: float             # Training range min
    domain_max: float             # Training range max
    aic: float
    bic: float
    f_statistic: Optional[float] = None
    f_p_value: Optional[float] = None
    is_polynomial_justified: bool = False
    formula_string: str = ""

    def predict(self, x: Union[float, np.ndarray]) -> np.ndarray:
        """Apply calibration correction to observed readings."""
        arr = np.asarray(x, dtype=float)
        if self.model_type == "uncalibrated":
            return arr

        # Polynomial evaluation: sum(c_i * x^i)
        y_pred = np.zeros_like(arr, dtype=float)
        for p, c in enumerate(self.coefficients):
            y_pred += c * (arr ** p)
        return y_pred

    def check_extrapolation(self, x: Union[float, np.ndarray]) -> Tuple[np.ndarray, List[str]]:
        """Identify observations falling outside the calibration domain [domain_min, domain_max]."""
        arr = np.asarray(x, dtype=float)
        warnings = []
        is_extrapolated = (arr < self.domain_min) | (arr > self.domain_max)
        extrap_count = int(np.sum(is_extrapolated))
        if extrap_count > 0:
            warnings.append(f"{extrap_count} observations fall outside calibration domain [{self.domain_min:.4g}, {self.domain_max:.4g}].")
        return is_extrapolated, warnings


@dataclass
class CalibrationValidationComparison:
    """Rigorous comparison of pre-calibration and post-calibration metrics on held-out data."""
    train_count: int
    validation_count: int
    random_seed: int
    model: CalibrationModel
    uncalibrated_metrics: ErrorMetrics
    calibrated_metrics: ErrorMetrics
    mae_reduction_percent: float
    rmse_reduction_percent: float
    max_error_reduction_percent: float
    is_performance_improved: bool
    domain_warnings: List[str] = field(default_factory=list)
    split_strategy: str = "random"
    train_indices: Optional[List[int]] = None
    validation_indices: Optional[List[int]] = None


class CalibrationEngine:
    """
    Fits and validates conventional calibration models with strict leakage prevention.
    """

    def __init__(self, f_test_alpha: float = 0.05):
        self.f_test_alpha = f_test_alpha

    def fit_linear(
        self,
        x_dut: Union[List[float], np.ndarray],
        y_ref: Union[List[float], np.ndarray]
    ) -> CalibrationModel:
        """
        Fit linear calibration correction: y_ref ~ a0 + a1 * x_dut
        """
        x = np.asarray(x_dut, dtype=float)
        y = np.asarray(y_ref, dtype=float)
        n = len(x)

        if n < 3:
            raise ValueError("At least 3 points required to fit linear calibration.")

        # Design matrix X = [1, x]
        X = np.column_stack([np.ones(n), x])
        # Normal equations solution: beta = (X^T X)^-1 X^T y
        XtX_inv = np.linalg.pinv(X.T @ X)
        coeffs = XtX_inv @ X.T @ y

        a0 = float(coeffs[0])
        a1 = float(coeffs[1])

        # Residuals and variances
        y_fit = X @ coeffs
        residuals = y - y_fit
        sse = float(np.sum(residuals ** 2))
        sst = float(np.sum((y - np.mean(y)) ** 2))
        
        df_e = n - 2
        s_res_sq = sse / df_e if df_e > 0 else 0.0
        s_res = float(np.sqrt(s_res_sq))

        cov_beta = XtX_inv * s_res_sq
        se_coeffs = [float(np.sqrt(max(0.0, cov_beta[i, i]))) for i in range(2)]

        r2 = float(1.0 - (sse / sst)) if sst > 1e-12 else 1.0
        adj_r2 = float(1.0 - ((1.0 - r2) * (n - 1) / df_e)) if df_e > 0 else r2

        # Information criteria
        sigma_mle_sq = sse / n
        log_lik = -0.5 * n * (np.log(2 * np.pi * sigma_mle_sq) + 1.0) if sigma_mle_sq > 1e-15 else 0.0
        k_params = 2
        aic = float(-2.0 * log_lik + 2.0 * k_params)
        bic = float(-2.0 * log_lik + k_params * np.log(n))

        formula = f"y_cal = {a0:.6g} + {a1:.6g} * x"

        return CalibrationModel(
            model_type="linear",
            degree=1,
            coefficients=[a0, a1],
            coefficient_std_errors=se_coeffs,
            covariance_matrix=cov_beta.tolist(),
            r_squared=r2,
            adjusted_r_squared=adj_r2,
            residual_std_dev=s_res,
            domain_min=float(np.min(x)),
            domain_max=float(np.max(x)),
            aic=aic,
            bic=bic,
            formula_string=formula
        )

    def fit_polynomial(
        self,
        x_dut: Union[List[float], np.ndarray],
        y_ref: Union[List[float], np.ndarray],
        degree: int = 2
    ) -> CalibrationModel:
        """
        Fit polynomial calibration correction: y_ref ~ a0 + a1*x + ... + ad*x^d
        """
        x = np.asarray(x_dut, dtype=float)
        y = np.asarray(y_ref, dtype=float)
        n = len(x)

        if n <= degree + 1:
            raise ValueError(f"Need at least {degree + 2} points to fit polynomial of degree {degree}.")

        # Design matrix X = [1, x, x^2, ..., x^degree]
        powers = np.arange(degree + 1)
        X = x[:, np.newaxis] ** powers

        XtX_inv = np.linalg.pinv(X.T @ X)
        coeffs = XtX_inv @ X.T @ y

        y_fit = X @ coeffs
        residuals = y - y_fit
        sse = float(np.sum(residuals ** 2))
        sst = float(np.sum((y - np.mean(y)) ** 2))

        df_e = n - (degree + 1)
        s_res_sq = sse / df_e if df_e > 0 else 0.0
        s_res = float(np.sqrt(s_res_sq))

        cov_beta = XtX_inv * s_res_sq
        se_coeffs = [float(np.sqrt(max(0.0, cov_beta[i, i]))) for i in range(degree + 1)]

        r2 = float(1.0 - (sse / sst)) if sst > 1e-12 else 1.0
        adj_r2 = float(1.0 - ((1.0 - r2) * (n - 1) / df_e)) if df_e > 0 else r2

        sigma_mle_sq = sse / n
        log_lik = -0.5 * n * (np.log(2 * np.pi * sigma_mle_sq) + 1.0) if sigma_mle_sq > 1e-15 else 0.0
        k_params = degree + 1
        aic = float(-2.0 * log_lik + 2.0 * k_params)
        bic = float(-2.0 * log_lik + k_params * np.log(n))

        poly_parts = [f"{coeffs[0]:.6g}"]
        for p in range(1, degree + 1):
            poly_parts.append(f"{coeffs[p]:.6g} * x^{p}")
        formula = "y_cal = " + " + ".join(poly_parts)

        return CalibrationModel(
            model_type=f"polynomial_deg{degree}",
            degree=degree,
            coefficients=[float(c) for c in coeffs],
            coefficient_std_errors=se_coeffs,
            covariance_matrix=cov_beta.tolist(),
            r_squared=r2,
            adjusted_r_squared=adj_r2,
            residual_std_dev=s_res,
            domain_min=float(np.min(x)),
            domain_max=float(np.max(x)),
            aic=aic,
            bic=bic,
            formula_string=formula
        )

    def select_best_model(
        self,
        x_dut: Union[List[float], np.ndarray],
        y_ref: Union[List[float], np.ndarray],
        max_degree: int = 3
    ) -> CalibrationModel:
        """
        Model order selection: Compares linear vs polynomial models using sequential F-tests.
        A polynomial of degree d is adopted ONLY if the reduction in sum of squared errors
        is statistically significant (p < f_test_alpha) compared to degree d-1.
        """
        x = np.asarray(x_dut, dtype=float)
        y = np.asarray(y_ref, dtype=float)
        n = len(x)

        current_best = self.fit_linear(x, y)

        for deg in range(2, max_degree + 1):
            if n <= deg + 2:
                break
            cand = self.fit_polynomial(x, y, degree=deg)

            # F-test comparing reduced model (deg-1) to full model (deg)
            # F = ((SSE_reduced - SSE_full) / (p_full - p_reduced)) / (SSE_full / df_full)
            sse_red = (current_best.residual_std_dev ** 2) * (n - current_best.degree - 1)
            sse_full = (cand.residual_std_dev ** 2) * (n - deg - 1)
            df_full = n - deg - 1

            diff_sse = sse_red - sse_full
            if diff_sse > 1e-12 and sse_full > 1e-12 and df_full > 0:
                f_stat = float((diff_sse / 1.0) / (sse_full / df_full))
                p_val = float(1.0 - stats.f.cdf(f_stat, dfn=1, dfd=df_full))
                cand.f_statistic = f_stat
                cand.f_p_value = p_val
                if p_val < self.f_test_alpha and cand.bic < current_best.bic:
                    cand.is_polynomial_justified = True
                    current_best = cand
                else:
                    break
            else:
                break

        return current_best

    def evaluate_train_validation_split(
        self,
        x_dut: Union[List[float], np.ndarray],
        y_ref: Union[List[float], np.ndarray],
        train_ratio: float = 0.6,
        model_type: str = "auto",  # 'auto', 'linear', 'polynomial'
        poly_degree: int = 2,
        random_seed: int = 42,
        split_strategy: str = "random"  # 'random', 'chronological', 'blocked'
    ) -> CalibrationValidationComparison:
        """
        Evaluate calibration with strict train/validation partition.
        Fits solely on training set, evaluates solely on held-out validation set.

        Split Strategies:
        - 'random': Randomized permutation partition.
        - 'chronological': Contiguous time-series split (first 100*train_ratio % train, remainder val).
          Prevents temporal data leakage and autocorrelation contamination.
        - 'blocked': Interleaved block partition to ensure even range coverage without pointwise adjacency leakage.
        """
        x = np.asarray(x_dut, dtype=float)
        y = np.asarray(y_ref, dtype=float)
        n = len(x)

        if n < 6:
            raise ValueError("At least 6 observations required for independent train/validation split.")

        if split_strategy == "random":
            rng = np.random.default_rng(random_seed)
            shuffled_indices = rng.permutation(n)
            n_train = int(np.floor(n * train_ratio))
            train_idx = shuffled_indices[:n_train]
            val_idx = shuffled_indices[n_train:]
        elif split_strategy == "chronological":
            n_train = int(np.floor(n * train_ratio))
            train_idx = np.arange(0, n_train)
            val_idx = np.arange(n_train, n)
        elif split_strategy == "blocked":
            num_blocks = 4
            block_size = n // num_blocks
            train_list = []
            val_list = []
            for b in range(num_blocks):
                b_start = b * block_size
                b_end = (b + 1) * block_size if b < num_blocks - 1 else n
                b_train = int(np.floor((b_end - b_start) * train_ratio))
                train_list.extend(range(b_start, b_start + b_train))
                val_list.extend(range(b_start + b_train, b_end))
            train_idx = np.array(train_list)
            val_idx = np.array(val_list)
        else:
            raise ValueError(f"Unknown split_strategy '{split_strategy}'. Must be 'random', 'chronological', or 'blocked'.")

        x_train, y_train = x[train_idx], y[train_idx]
        x_val, y_val = x[val_idx], y[val_idx]

        # 1. Fit model on training data ONLY
        if model_type == "linear":
            model = self.fit_linear(x_train, y_train)
        elif model_type == "polynomial":
            model = self.fit_polynomial(x_train, y_train, degree=poly_degree)
        else:
            model = self.select_best_model(x_train, y_train, max_degree=poly_degree)

        # 2. Evaluate uncalibrated readings on validation set
        uncal_metrics = compute_error_metrics(x_val, y_val)

        # 3. Apply calibration model to validation set
        x_val_calibrated = model.predict(x_val)
        cal_metrics = compute_error_metrics(x_val_calibrated, y_val)

        # 4. Domain extrapolation check
        _, warnings = model.check_extrapolation(x_val)

        # 5. Calculate performance changes
        mae_uncal = uncal_metrics.mae
        mae_cal = cal_metrics.mae
        mae_red = ((mae_uncal - mae_cal) / mae_uncal * 100.0) if mae_uncal > 1e-12 else 0.0

        rmse_uncal = uncal_metrics.rmse
        rmse_cal = cal_metrics.rmse
        rmse_red = ((rmse_uncal - rmse_cal) / rmse_uncal * 100.0) if rmse_uncal > 1e-12 else 0.0

        max_uncal = uncal_metrics.max_absolute_error
        max_cal = cal_metrics.max_absolute_error
        max_red = ((max_uncal - max_cal) / max_uncal * 100.0) if max_uncal > 1e-12 else 0.0

        is_improved = (mae_cal <= mae_uncal) and (rmse_cal <= rmse_uncal)

        return CalibrationValidationComparison(
            train_count=len(train_idx),
            validation_count=len(val_idx),
            random_seed=random_seed,
            model=model,
            uncalibrated_metrics=uncal_metrics,
            calibrated_metrics=cal_metrics,
            mae_reduction_percent=mae_red,
            rmse_reduction_percent=rmse_red,
            max_error_reduction_percent=max_red,
            is_performance_improved=is_improved,
            domain_warnings=warnings,
            split_strategy=split_strategy,
            train_indices=train_idx.tolist(),
            validation_indices=val_idx.tolist()
        )
