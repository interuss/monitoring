import pytest

from monitoring.benchmarker.reports.analysis import USLFit


def test_usl_fit_exact():
    gamma = 100.0
    alpha = 0.05
    beta = 0.001

    scale = [1.0, 2.0, 5.0, 10.0, 20.0, 40.0, 60.0]
    throughput = [
        gamma * n / (1.0 + alpha * (n - 1.0) + beta * n * (n - 1.0)) for n in scale
    ]

    fit = USLFit.from_data(scale, throughput)
    assert fit.parameters.scaling_factor == pytest.approx(gamma, rel=1e-3)
    assert fit.parameters.contention_factor == pytest.approx(alpha, rel=1e-3)
    assert fit.parameters.coherency_factor == pytest.approx(beta, rel=1e-3)

    assert fit.inlier_mask is not None
    assert all(fit.inlier_mask)

    computed_throughput = list(fit.compute_throughput(scale))
    assert len(computed_throughput) == len(throughput)
    for expected, actual in zip(throughput, computed_throughput, strict=True):
        assert actual == pytest.approx(expected, rel=1e-3)


def test_usl_fit_with_outlier():
    gamma = 100.0
    alpha = 0.05
    beta = 0.001

    scale = [1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 30.0]
    throughput = [
        gamma * n / (1.0 + alpha * (n - 1.0) + beta * n * (n - 1.0)) for n in scale
    ]

    # Inject a severe outlier at index 4 (N=8.0)
    outlier_idx = 4
    throughput[outlier_idx] = 2500.0  # Far above the true model value

    fit = USLFit.from_data(scale, throughput, discard_probability=0.05)
    assert fit.inlier_mask is not None
    assert not fit.inlier_mask[outlier_idx]
    assert sum(fit.inlier_mask) == len(scale) - 1

    # Parameters should still recover closely to true values despite the outlier
    assert fit.parameters.scaling_factor == pytest.approx(gamma, rel=1e-2)
    assert fit.parameters.contention_factor == pytest.approx(alpha, rel=1e-2)
    assert fit.parameters.coherency_factor == pytest.approx(beta, rel=1e-2)


def test_usl_fit_no_outlier_discarding():
    scale = [1.0, 2.0, 3.0, 4.0, 5.0]
    throughput = [10.0, 18.0, 1000.0, 22.0, 24.0]

    # Disable outlier discarding
    fit = USLFit.from_data(scale, throughput, discard_probability=None)
    assert fit.inlier_mask is not None
    assert all(fit.inlier_mask)


def test_usl_fit_invalid_input():
    with pytest.raises(ValueError, match="x_data and y_data must have the same length"):
        USLFit.from_data([1.0, 2.0], [10.0])

    with pytest.raises(ValueError, match="Cannot fit USL model with no data points"):
        USLFit.from_data([], [])


def test_usl_outlier_rejection_invariant_with_scale():
    """Verify that adding more non-outlier points does not appreciably increase
    or decrease the likelihood of discarding a specific outlier of identical magnitude,
    and that false positives remain controlled."""
    gamma = 50.0
    alpha = 0.02
    beta = 0.0005

    # Small dataset (10 points) vs larger dataset (50 points)
    scale_small = [1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0]
    scale_large = [float(i) for i in range(1, 51)]

    def generate_throughput(scale_vals, outlier_idx):
        tp = []
        for i, n in enumerate(scale_vals):
            base = gamma * n / (1.0 + alpha * (n - 1.0) + beta * n * (n - 1.0))
            if i == outlier_idx:
                # Add fixed massive anomaly
                base += 500.0
            tp.append(base)
        return tp

    tp_small = generate_throughput(scale_small, outlier_idx=3)
    tp_large = generate_throughput(scale_large, outlier_idx=3)

    fit_small = USLFit.from_data(scale_small, tp_small, discard_probability=0.05)
    fit_large = USLFit.from_data(scale_large, tp_large, discard_probability=0.05)

    assert fit_small.inlier_mask is not None and not fit_small.inlier_mask[3]
    assert fit_large.inlier_mask is not None and not fit_large.inlier_mask[3]

    # In both small and large sets, only the true outlier is rejected
    assert sum(fit_small.inlier_mask) == len(scale_small) - 1
    assert sum(fit_large.inlier_mask) == len(scale_large) - 1
