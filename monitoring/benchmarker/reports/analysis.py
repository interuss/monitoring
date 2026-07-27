from collections.abc import Iterable, Sequence
from datetime import datetime

import numpy as np
import scipy.optimize
import scipy.stats
from implicitdict import ImplicitDict

from monitoring.benchmarker.configurations.loads import OperationType
from monitoring.benchmarker.reports.report import (
    BenchmarkOperation,
    BenchmarkScenarioReport,
    OperationsByOrigin,
    OperationsByOutcome,
    OperationsByType,
)

OperationsHierarchyMember = (
    Sequence[OperationsByType]
    | OperationsByType
    | OperationsByOrigin
    | OperationsByOutcome
    | BenchmarkOperation
)


def select_operations(
    operations: OperationsHierarchyMember,
    types: Sequence[OperationType | str] | None = None,
    origins: Sequence[str] | None = None,
    outcomes: Sequence[bool] | None = None,
    completed_after: datetime | None = None,
    completed_before: datetime | None = None,
) -> Iterable[BenchmarkOperation]:
    def nest(sub_operations):
        for op in sub_operations:
            yield from select_operations(
                op, types, origins, outcomes, completed_after, completed_before
            )

    if isinstance(operations, Sequence):
        yield from nest(operations)
    elif isinstance(operations, OperationsByType):
        norm_types = {OperationType(t) for t in types} if types is not None else None
        types_match = (
            norm_types is None
            or operations.type in norm_types
            or str(operations.type) in {str(t) for t in norm_types}
        )
        if types_match:
            yield from nest(operations.origins)
    elif isinstance(operations, OperationsByOrigin):
        if origins is None or operations.origin in origins:
            yield from nest(operations.outcomes)
    elif isinstance(operations, OperationsByOutcome):
        if "successful" in operations and operations.successful:
            if outcomes is None or True in outcomes:
                yield from nest(operations.successful)
        if "unsuccessful" in operations and operations.unsuccessful:
            if outcomes is None or False in outcomes:
                yield from nest(operations.unsuccessful)
    elif isinstance(operations, BenchmarkOperation):
        if completed_after and operations.t1.datetime < completed_after:
            return
        if completed_before and operations.t1.datetime > completed_before:
            return
        yield operations
    else:
        raise ValueError(
            f"`operations` type '{type(operations).__name__}' is not valid"
        )


def throughput_of_operations(
    operations: OperationsHierarchyMember,
    start_time: datetime,
    end_time: datetime,
    **kwargs,
) -> float:
    """Determine the achieved throughput during a specified time range from a list of completed operations.

    Args:
      * operations: List of relevant operations over all time.
      * start_time: Beginning of time window in which to inspect throughput.
      * end_time: End of time window in which to inspect throughput.

    Returns: Throughput in operations of interest per second.

    Notes:
      Operation flux must have already been in steady-state at `start_time` for this throughput calculation to be
      valid.  What happens after `end_time` does not affect this calculation.  "Partial credit" is not given for
      eventually-successful operations in progress at `end_time` as attempting to do so would require operation
      flux to remain in steady-state after `end_time` until completion of the last operation started before
      `end_time` for the throughput calculation to be valid.  Instead, the partial work of operations in progress
      at `end_time` effectively discarded by this approach should be (statistically) exactly balanced by the
      partial work included "for free" of operations started before `start_time` that end within the time window.
    """
    dur = (end_time - start_time).total_seconds()
    if "outcomes" not in kwargs:
        kwargs["outcomes"] = (True,)
    kwargs["completed_after"] = start_time
    kwargs["completed_before"] = end_time
    return (
        sum(1 for _ in select_operations(operations, **kwargs)) / dur
        if dur > 0
        else 0.0
    )


def throughput_of_step(
    report: BenchmarkScenarioReport, step_index: int, **kwargs
) -> float:
    step = report.steps[step_index]
    return throughput_of_operations(
        report.operations,
        step.throughput_stability_time.datetime,
        step.end_time.datetime,
        **kwargs,
    )


class USLParameters(ImplicitDict):
    """Parameters describing a fit of measured data to the Universal Scalability Law model.

    X(N) = 𝛾N/[1 + 𝛼(N-1) + 𝛽N(N-1)]

    𝛾 is the scaling factor (how quickly throughput scales as load increases)
    𝛼 is the contention factor (how much throughput increases slow down as load increases)
    𝛽 is the coherency/crosstalk factor (how quickly throughput decreases as load increases)

    See:
    https://www.graphiumlabs.com/blog/part2-gunthers-universal-scalability-law
    https://raw.githubusercontent.com/VividCortex/ebooks/master/scalability.pdf"""

    scaling_factor: float
    contention_factor: float
    coherency_factor: float


class USLFit:
    parameters: USLParameters
    inlier_mask: list[bool] | None

    def __init__(
        self,
        parameters: USLParameters,
        inlier_mask: Sequence[bool] | None = None,
    ):
        self.parameters = parameters
        self.inlier_mask = list(inlier_mask) if inlier_mask is not None else None

    def compute_throughput(self, scale: Sequence[float]) -> Iterable[float]:
        gamma = self.parameters.scaling_factor
        alpha = self.parameters.contention_factor
        beta = self.parameters.coherency_factor
        for n in scale:
            yield gamma * n / (1 + alpha * (n - 1) + beta * n * (n - 1))

    @staticmethod
    def _fit_single(x: np.ndarray, y: np.ndarray) -> USLParameters:
        if (x == 0).any():
            raise ValueError("USL load factor may never be zero")
        if (y < 0).any():
            raise ValueError("USL throughput may never be negative")

        def rmse(params: Sequence[float]) -> float:
            gamma, alpha, beta = params
            alpha = pow(10, alpha)
            beta = pow(10, beta)
            denom = np.maximum(1.0 + alpha * (x - 1.0) + beta * x * (x - 1.0), 1e-12)
            y_pred = gamma * x / denom
            return float(np.sqrt(np.mean((y - y_pred) ** 2)))

        gamma_guess = np.max(y / x)

        bounds = [(0.0, None), (None, None), (None, None)]
        best_result: Sequence[float] | None = None
        best_score = float("inf")

        for a, b in ((-3, -5), (-5, -3), (-1, -1), (-7, -7)):
            res = scipy.optimize.minimize(
                rmse,
                x0=[gamma_guess, a, b],
                method="Nelder-Mead",
                bounds=bounds,
                options={"xatol": 1e-9, "fatol": 1e-9, "maxiter": 5000},
            )
            score = rmse(res.x)
            if score < best_score:
                best_score = score
                best_result = res.x

        if best_result is None:
            raise RuntimeError("No solution found to fit USL")

        gamma, alpha, beta = best_result
        return USLParameters(
            scaling_factor=float(gamma),
            contention_factor=pow(10, alpha),
            coherency_factor=pow(10, beta),
        )

    @staticmethod
    def from_data(
        x_data: Sequence[float],
        y_data: Sequence[float],
        discard_probability: float | None = 0.05,
    ) -> "USLFit":
        x_arr = np.array(x_data, dtype=float)
        y_arr = np.array(y_data, dtype=float)
        if len(x_arr) != len(y_arr):
            raise ValueError("x_data and y_data must have the same length")
        if len(x_arr) == 0:
            raise ValueError("Cannot fit USL model with no data points")

        inlier_mask = np.ones(len(x_arr), dtype=bool)

        while True:
            # Fit USL to all inlier data
            x_in = x_arr[inlier_mask]
            y_in = y_arr[inlier_mask]

            params = USLFit._fit_single(x_in, y_in)

            # Decide if any data should be discarded as outliers
            if (
                discard_probability is None
                or discard_probability <= 0.0
                or discard_probability >= 1.0
                or len(x_in) <= 3
            ):
                break

            denom = np.maximum(
                1.0
                + params.contention_factor * (x_in - 1.0)
                + params.coherency_factor * x_in * (x_in - 1.0),
                1e-12,
            )
            y_pred = params.scaling_factor * x_in / denom
            residuals = y_in - y_pred

            # Estimate standard deviation via median absolute deviation (MAD) to avoid outlier masking from RMS estimate
            med_res = np.median(residuals)
            mad = np.median(np.abs(residuals - med_res))
            sigma_mad = 1.4826 * mad

            if sigma_mad > 1e-12:
                sigma = float(sigma_mad)
            else:
                ddof = min(3, len(residuals) - 1)
                sigma = float(np.std(residuals, ddof=ddof))

            if sigma < 1e-12:
                break

            # Apply Dunn–Šidák correction
            m = len(x_in)
            prob_threshold = (1.0 + (1.0 - discard_probability) ** (1.0 / m)) / 2.0

            # Check for outliers exceeding the threshold
            k = float(scipy.stats.norm.ppf(prob_threshold))
            min_practical_error = max(1e-6, 1e-3 * float(np.max(np.abs(y_in))))
            max_error = max(k * sigma, min_practical_error)
            outliers_in_subset = np.abs(residuals) > max_error

            if not np.any(outliers_in_subset):
                # No outliers; we're done
                break

            # Remove the single worst outlier and iterate
            inlier_indices = np.where(inlier_mask)[0]
            worst_idx = int(np.argmax(np.abs(residuals)))
            inlier_mask[inlier_indices[worst_idx]] = False

        return USLFit(parameters=params, inlier_mask=inlier_mask.tolist())
