"""Tests for single-exponential decay fitting."""

import numpy as np
import pytest

from utils.decay_fitting import (
    DECAY_FIT_UI_ENABLED,
    autosample_decay,
    conv_irf_exponential,
    fit_single_exponential,
    predict_decay_at_tau,
    shift_model_on_time_axis,
    _decay_shape_peak_normalized,
    _peak_align_shape,
    _poisson_deviance,
    _forward_model,
    _prepare_forward_context,
)
from utils.shared_data import SharedData


def _t0_start(t_ns: np.ndarray) -> float:
    """Synthetic decays: t₀ at first channel (minimal baseline window)."""
    return float(np.asarray(t_ns, dtype=np.float64)[0])


def test_decay_fit_hidden_from_ui():
    assert DECAY_FIT_UI_ENABLED is False


def test_conv_irf_exponential_positive():
    t = np.linspace(0, 10e-9, 64)
    irf = np.zeros_like(t)
    irf[5] = 1.0
    kernel = conv_irf_exponential(t, irf, 2e-9)
    assert kernel.shape == t.shape
    assert np.all(kernel >= 0)
    assert kernel.sum() > 0


def test_fit_recovers_tau_without_irf():
    shared = SharedData()
    shared.ref_files_dict.clear()

    t_ns = np.linspace(0, 20, 80)
    t_s = t_ns * 1e-9
    tau_true_s = 3.0e-9
    shape = _decay_shape_peak_normalized(t_s, tau_true_s, used_irf=False, irf_on_grid=None)
    assert shape is not None
    counts = (120.0 * shape).astype(np.float64)
    counts += np.random.default_rng(0).poisson(0.5, size=counts.shape)

    fit = fit_single_exponential(t_ns, counts, tau_hint_ns=3.0, t0_ns=_t0_start(t_ns), shared=shared)
    assert fit is not None
    assert abs(fit.tau_ns - tau_true_s * 1e9) < 2.5
    assert fit.model_counts.shape == counts.shape
    assert abs(fit.amplitude - counts.max()) < 15.0


def test_fit_uses_reference_irf():
    shared = SharedData()
    shared.ref_files_dict.clear()

    t_s = np.linspace(0, 20e-9, 80)
    t_ns = t_s * 1e9
    irf = np.zeros(80)
    irf[4:8] = [1, 3, 2, 1]
    shared.ref_files_dict["ref"] = {"ref_data": irf.reshape(80, 1, 1), "t_series": t_s}
    shared.config["ref_file"] = "ref"

    tau_true_s = 2.5e-9
    irf_norm = irf / irf.sum()
    shape = _decay_shape_peak_normalized(t_s, tau_true_s, used_irf=True, irf_on_grid=irf_norm)
    assert shape is not None
    counts = (55.0 * shape).astype(np.float64)

    fit = fit_single_exponential(t_ns, counts, tau_hint_ns=2.5, t0_ns=_t0_start(t_ns), shared=shared)
    assert fit is not None
    assert fit.used_irf is True
    assert abs(fit.tau_ns - tau_true_s * 1e9) < 2.5


def test_predict_decay_at_tau_matches_fit_at_same_tau():
    shared = SharedData()
    shared.ref_files_dict.clear()

    t_ns = np.linspace(0, 20, 80)
    t_s = t_ns * 1e-9
    tau_true_s = 3.0e-9
    shape = _decay_shape_peak_normalized(t_s, tau_true_s, used_irf=False, irf_on_grid=None)
    assert shape is not None
    counts = (40.0 * shape).astype(np.float64)

    predicted = predict_decay_at_tau(t_ns, counts, tau_true_s * 1e9, shared=shared)
    assert predicted is not None
    assert predicted.shape == counts.shape
    assert abs(predicted.max() - counts.max()) < 1e-6


def test_autosample_merges_sparse_bins():
    t = np.linspace(0, 20, 80)
    y = np.zeros(80)
    y[10:15] = [1, 2, 1, 1, 0]
    y[30] = 3
    y[50:55] = 5
    t_b, y_b, rebinned = autosample_decay(t, y, min_counts_per_bin=5.0)
    assert rebinned
    assert y_b.sum() == pytest.approx(y.sum())
    assert len(y_b) < len(y)


def test_fit_not_pinned_to_map_over_10():
    """Regression: fit τ must not sit at map_τ/10 from old 0.1× lower bound."""
    shared = SharedData()
    shared.ref_files_dict.clear()

    t_ns = np.linspace(0, 20, 80)
    t_s = t_ns * 1e-9
    tau_true_ns = 3.75
    shape = _decay_shape_peak_normalized(t_s, tau_true_ns * 1e-9, used_irf=False, irf_on_grid=None)
    assert shape is not None
    rng = np.random.default_rng(1)
    counts = (rng.poisson(0.15, size=shape.size) + shape * 2.0).astype(np.float64)

    fit = fit_single_exponential(t_ns, counts, tau_hint_ns=tau_true_ns, t0_ns=_t0_start(t_ns), shared=shared)
    assert fit is not None
    assert fit.tau_ns > tau_true_ns * 0.25
    assert not fit.hit_tau_lower_bound or fit.tau_ns > 0.5


def test_sparse_amplitude_matches_measured_peak():
    """Many empty bins must not pull A below the measured peak."""
    shared = SharedData()
    shared.ref_files_dict.clear()

    t_ns = np.linspace(0, 25, 120)
    t_s = t_ns * 1e-9
    tau_true_ns = 4.0
    shape = _decay_shape_peak_normalized(t_s, tau_true_ns * 1e-9, used_irf=False, irf_on_grid=None)
    assert shape is not None
    counts = np.zeros(120, dtype=np.float64)
    counts[12] = 5.0
    counts[14] = 2.0
    counts[20] = 1.0
    counts[35] = 1.0

    fit = fit_single_exponential(t_ns, counts, tau_hint_ns=tau_true_ns, t0_ns=float(t_ns[8]), shared=shared)
    assert fit is not None
    assert fit.amplitude == 5.0
    assert float(fit.model_counts.max()) == pytest.approx(5.0, rel=1e-6)


def test_peak_align_puts_model_peak_at_data_peak():
    t = np.linspace(0, 25, 100)
    shape = np.exp(-((t - 8.0) ** 2) / 4.0)
    shape /= shape.max()
    counts = np.zeros(100)
    counts[10] = 7.0
    aligned, shift = _peak_align_shape(t, counts, shape)
    assert shift > 0
    assert int(np.argmax(aligned)) == int(np.argmax(counts))


def test_tail_zeros_favour_shorter_tau_in_deviance():
    """Zero bins in the tail must penalise an overly long lifetime."""
    shared = SharedData()
    shared.ref_files_dict.clear()
    t_ns = np.linspace(0, 25, 80)
    counts = np.zeros(80, dtype=np.float64)
    counts[8:13] = [1, 4, 10, 5, 2]
    a_fixed = float(counts.max())

    t_s, used_irf, irf = _prepare_forward_context(t_ns, shared)
    short_model, _, _ = _forward_model(
        t_s, 3.5, counts, 0.0, used_irf=used_irf, irf_on_grid=irf, fixed_amplitude=a_fixed,
    )
    long_model, _, _ = _forward_model(
        t_s, 12.0, counts, 0.0, used_irf=used_irf, irf_on_grid=irf, fixed_amplitude=a_fixed,
    )
    assert short_model is not None and long_model is not None
    assert _poisson_deviance(counts, long_model) > _poisson_deviance(counts, short_model)


def test_sparse_fit_prefers_map_tau_over_upper_bound():
    shared = SharedData()
    shared.ref_files_dict.clear()
    t_ns = np.linspace(0, 25, 100)
    t_s = t_ns * 1e-9
    tau_true_ns = 3.6
    shape = _decay_shape_peak_normalized(t_s, tau_true_ns * 1e-9, used_irf=False, irf_on_grid=None)
    assert shape is not None
    counts = (shape * 8.0).astype(np.float64)
    counts = np.round(counts).astype(np.float64)
    counts[counts < 0] = 0

    fit = fit_single_exponential(t_ns, counts, tau_hint_ns=tau_true_ns, t0_ns=_t0_start(t_ns), shared=shared)
    assert fit is not None
    assert fit.tau_ns < 9.0


def test_fit_requires_t0_ns():
    shared = SharedData()
    shared.ref_files_dict.clear()
    t_ns = np.linspace(0, 20, 40)
    counts = np.ones(40, dtype=np.float64)
    assert fit_single_exponential(t_ns, counts, t0_ns=None, shared=shared) is None


def test_shift_model_on_time_axis_moves_right():
    t = np.linspace(0, 10, 50)
    y = np.exp(-((t - 3.0) ** 2) / 2.0)
    shifted = shift_model_on_time_axis(t, y, 1.0)
    assert float(np.argmax(shifted)) > int(np.argmax(y))


def test_fit_peak_align_sets_shift():
    shared = SharedData()
    shared.ref_files_dict.clear()
    t_ns = np.linspace(0, 20, 80)
    t_s = t_ns * 1e-9
    tau_true_ns = 3.0
    shape = _decay_shape_peak_normalized(t_s, tau_true_ns * 1e-9, used_irf=False, irf_on_grid=None)
    assert shape is not None
    counts = np.zeros(80, dtype=np.float64)
    counts[18] = 10.0
    counts[20] = 4.0
    fit = fit_single_exponential(
        t_ns, counts, tau_hint_ns=tau_true_ns, t0_ns=_t0_start(t_ns),
        peak_align=True, shared=shared,
    )
    assert fit is not None
    assert abs(fit.peak_shift_ns) > 1e-6
    assert int(np.argmax(fit.model_counts)) == int(np.argmax(counts))


def test_fit_not_run_without_baseline_t0():
    """Inspector gate: no t₀ when baseline correction is off."""
    from utils.decay_inspector import get_pixel_decay

    shared = SharedData()
    shared.raw_data_dict.clear()
    t = np.linspace(0, 10e-9, 40, dtype=np.float32)
    data = np.ones((40, 2, 2), dtype=np.float32)
    shared.raw_data_dict["s"] = {"data": data, "t_series": t, "masked_data": None, "condition": "t"}
    shared.config["selected_file"] = "s"
    shared.config["subtract_offset"] = "False"

    decay = get_pixel_decay("s", 0.0, 0.0, (2, 2))
    assert decay is not None
    assert decay.fit_allowed is False
    assert decay.t0_ns is None
