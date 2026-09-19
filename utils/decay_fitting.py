"""
Single-exponential decay fitting for the pixel decay inspector.

TCSPC model: IRF reconvolution + Poisson deviance, for one ROI/pixel.

---
FUTURE / NOT IN UI:
  The orange 1-exp fitted curve, IRF toggle, and peak-align controls stay hidden.
  Baseline check still shows the measured decay and the purple map-τ overlay
  (slidable). Set DECAY_FIT_UI_ENABLED = True to restore the extra fit controls
  in utils/decay_window.py.
"""

from __future__ import annotations

# Re-enable Baseline check fit overlays when the UI is ready to ship.
DECAY_FIT_UI_ENABLED = False

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from utils.shared_data import SharedData

_MIN_TAU_NS = 0.15
_MAX_TAU_NS = 50.0
_AUTOSAMPLE_MIN_COUNTS = 8.0  # photons per merged bin
_SPARSE_PHOTON_WARN = 150


def autosample_decay(
  t_ns: np.ndarray,
  counts: np.ndarray,
  *,
  n_bin_min: int = 2,
  min_counts_per_bin: float = _AUTOSAMPLE_MIN_COUNTS,
  smoothing_area: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, bool]:
  """
  Time rebinning of sparse decays (merge adjacent bins from the tail).

  Merges adjacent bins (from the tail backward) until each super-bin holds
  enough photons for a stable monoexponential fit on sparse pixels
  (default target: 8 photons/bin).
  """
  t = np.asarray(t_ns, dtype=np.float64)
  y = np.asarray(counts, dtype=np.float64)
  n_t = t.size
  if n_t < 4 or y.sum() <= 0:
    return t, y, False

  max_w = max(n_t // 5, 1)
  min_c = min_counts_per_bin / max(smoothing_area, 1e-12)
  total_count = float(y.sum())
  if total_count < n_bin_min * min_c:
    min_c = total_count / max(n_bin_min, 1)

  resample_idx = np.zeros(n_t, dtype=np.int32)
  c = float(y[-1])
  w = 0
  n_bin = 1
  last = -1

  for i in range(n_t - 2, -1, -1):
    if c < min_c and w < max_w:
      c += float(y[i])
      w += 1
    else:
      c = float(y[i])
      resample_idx[i] = 1
      last = i
      w = 1
      n_bin += 1

  if c < min_c and n_bin > n_bin_min and last >= 0:
    resample_idx[last] = 0

  boundaries = [0]
  for i in range(1, n_t):
    if resample_idx[i]:
      boundaries.append(i)
  boundaries.append(n_t)

  if len(boundaries) - 1 >= n_t:
    return t, y, False

  t_out: list[float] = []
  y_out: list[float] = []
  for start, end in zip(boundaries[:-1], boundaries[1:]):
    segment_y = y[start:end]
    segment_t = t[start:end]
    if segment_y.sum() <= 0:
      continue
    t_out.append(float(np.dot(segment_t, segment_y) / segment_y.sum()))
    y_out.append(float(segment_y.sum()))

  if len(y_out) < 4 or len(y_out) >= n_t:
    return t, y, False
  return np.asarray(t_out, dtype=np.float64), np.asarray(y_out, dtype=np.float64), True


def _tau_search_range(
  tau_hint_ns: float | None,
  tau_ma_ns: float,
  shared: SharedData,
) -> tuple[float, float, float]:
  """
  τ bounds centred on the mean-lifetime estimate.

  Unlike the old 0.1×–5× map-τ window, this avoids τ_fit = τ_map/10 artefacts.
  """
  ref_lt = float(shared.config.get("ref_lifetime", 4) or 4)
  centre = tau_ma_ns if tau_ma_ns > 0 and np.isfinite(tau_ma_ns) else None
  if centre is None and tau_hint_ns is not None and tau_hint_ns > 0 and np.isfinite(tau_hint_ns):
    centre = float(tau_hint_ns)
  if centre is None:
    centre = ref_lt
  centre = float(np.clip(centre, _MIN_TAU_NS, _MAX_TAU_NS))
  tau_min = max(_MIN_TAU_NS, centre * 0.4)
  tau_max = min(_MAX_TAU_NS, max(centre * 3.0, tau_min * 2.0))
  return tau_min, tau_max, centre


@dataclass
class DecayFitResult:
  """Fitted single-exponential decay at one pixel."""

  tau_ns: float
  amplitude: float  # peak height A in y = A·h(t), h max = 1
  offset: float
  chi2_reduced: float
  model_counts: np.ndarray
  used_irf: bool
  converged: bool
  message: str = ""
  autosampled: bool = False
  n_bins_fit: int = 0
  hit_tau_lower_bound: bool = False
  hit_tau_upper_bound: bool = False
  tau_ma_ns: float | None = None
  t0_ns: float = 0.0
  peak_shift_ns: float = 0.0  # legacy alias: shift applied to anchor model at t₀


def format_fit_equation(
  fit: DecayFitResult,
  *,
  used_irf: bool,
  data_peak: float | None = None,
) -> str:
  """Human-readable fit equation (Excel-style) for the decay window."""
  a = fit.amplitude
  tau = fit.tau_ns
  if used_irf:
    core = f"y = A·exp(−(t−t₀)/τ) ⊗ IRF"
  else:
    core = f"y = A·exp(−(t−t₀)/τ)"
  parts = [f"{core}    A = {a:.2f}    τ = {tau:.2f} ns"]
  if fit.t0_ns > 0 or abs(fit.t0_ns) > 1e-6:
    parts.append(f"t₀ = {fit.t0_ns:.2f} ns (fit window start; baseline corrected)")
  if abs(fit.peak_shift_ns) > 1e-6:
    parts.append(f"peak align Δt = {fit.peak_shift_ns:.2f} ns")
  if data_peak is not None and data_peak > 0:
    parts.append(f"data peak {data_peak:.0f}")
  return "    ".join(parts)


def _reference_irf(shared: SharedData) -> tuple[np.ndarray, np.ndarray] | None:
  """Instrument response from the loaded reference sample (summed over space)."""
  ref_name = shared.config.get("ref_file")
  if not ref_name or ref_name not in shared.ref_files_dict:
    return None
  entry = shared.ref_files_dict[ref_name]
  ref_data = np.asarray(entry.get("ref_data"), dtype=np.float64)
  t_series = np.asarray(entry.get("t_series"), dtype=np.float64)
  if ref_data.size == 0 or t_series.size == 0:
    return None
  if ref_data.ndim == 3:
    irf = ref_data.sum(axis=(1, 2))
  else:
    irf = ref_data.ravel()
  irf = np.maximum(irf, 0.0)
  if irf.sum() <= 0:
    return None
  return t_series, irf / irf.sum()


def _align_irf(t_sample_s: np.ndarray, t_irf_s: np.ndarray, irf: np.ndarray) -> np.ndarray:
  """Resample IRF onto the sample delay-time grid."""
  if t_irf_s.size == t_sample_s.size and np.allclose(t_irf_s, t_sample_s, rtol=0, atol=1e-12):
    return irf.astype(np.float64)
  return np.interp(t_sample_s, t_irf_s, irf, left=0.0, right=0.0)


def conv_irf_exponential(t_s: np.ndarray, irf: np.ndarray, tau_s: float) -> np.ndarray:
  """
  Exponential reconvolution with a discrete IRF.
  t_s and tau_s in seconds.
  """
  t_s = np.asarray(t_s, dtype=np.float64)
  g = np.asarray(irf, dtype=np.float64)
  if t_s.size < 2 or g.size != t_s.size:
    return np.zeros_like(t_s)
  dt = float(t_s[1] - t_s[0])
  if dt <= 0:
    return np.zeros_like(t_s)
  tg = t_s - t_s[0]
  T = float(t_s[-1] - t_s[0])
  tau_s = max(float(tau_s), 1e-15)

  rhoi = np.exp(tg / tau_s)
  G = np.cumsum(g * rhoi)
  G = np.roll(G, 1)
  G[0] = 0.0
  rho = np.exp(dt / tau_s)
  A = tau_s**2 / dt * (1.0 - rho) ** 2 / rho
  B = tau_s**2 / dt * (dt / tau_s - 1.0 + 1.0 / rho)
  C = A * G + B * g * rhoi
  denom = np.exp(T / tau_s) - 1.0
  if abs(denom) < 1e-30:
    f = 0.0
  else:
    f = 1.0 / denom
  return (C + f * C[-1]) / rhoi / tau_s * dt


def _decay_shape_peak_normalized(
  t_s: np.ndarray,
  tau_s: float,
  *,
  used_irf: bool,
  irf_on_grid: np.ndarray | None,
) -> np.ndarray | None:
  """
  Unit peak reconvolved shape h(t; τ) with max(h) = 1.

  Amplitude A in y(t) = A·h(t) is then the model height at the first maximum
  (scale is solved separately on the unscaled shape).
  """
  tau_s = max(float(tau_s), 1e-15)
  if used_irf and irf_on_grid is not None:
    kernel = conv_irf_exponential(t_s, irf_on_grid, tau_s)
    kernel = np.maximum(kernel, 0.0)
  else:
    tg = t_s - t_s[0]
    T = float(t_s[-1] - t_s[0])
    kernel = np.exp(-tg / tau_s)
    norm = 1.0 - np.exp(-T / tau_s)
    if norm <= 1e-30:
      kernel = np.ones_like(t_s, dtype=np.float64)
    else:
      kernel = kernel / norm
  peak = float(kernel.max())
  if peak <= 0:
    return None
  return kernel / peak


def _peak_align_shape(
  t_ns: np.ndarray,
  counts: np.ndarray,
  shape: np.ndarray,
) -> tuple[np.ndarray, float]:
  """
  Shift model shape so its peak aligns with the measured data peak (t₀ correction).

  Positive shift_ns moves the model curve left on the plot (earlier in time).
  """
  counts = np.asarray(counts, dtype=np.float64)
  shape = np.asarray(shape, dtype=np.float64)
  t_ns = np.asarray(t_ns, dtype=np.float64)
  if counts.max() <= 0 or shape.max() <= 0 or t_ns.size != shape.size:
    return shape, 0.0
  i_data = int(np.argmax(counts))
  i_shape = int(np.argmax(shape))
  shift_ns = float(t_ns[i_shape] - t_ns[i_data])
  if abs(shift_ns) < 1e-9:
    return shape, 0.0
  aligned = np.interp(t_ns + shift_ns, t_ns, shape, left=0.0, right=0.0)
  peak = float(aligned.max())
  if peak > 0:
    aligned = aligned / peak
  return aligned, shift_ns


def shift_model_on_time_axis(
  t_ns: np.ndarray,
  model: np.ndarray,
  shift_ns: float,
) -> np.ndarray:
  """
  Slide a model curve along the time axis for display.

  Positive shift_ns moves the curve to the right on the plot.
  """
  t_ns = np.asarray(t_ns, dtype=np.float64)
  model = np.asarray(model, dtype=np.float64)
  if abs(shift_ns) < 1e-12 or t_ns.size != model.size:
    return model
  return np.interp(t_ns - shift_ns, t_ns, model, left=0.0, right=0.0)


def _optimal_amplitude(counts: np.ndarray, shape: np.ndarray) -> float:
  """
  Amplitude A in y ≈ A·shape (max(shape)=1), so model peak height = A.

  Uses √y weighting on bins with photons. Capped at measured peak — avoids
  blow-up when shape(t_peak) ≪ 1 because τ / IRF alignment is wrong.
  """
  counts = np.asarray(counts, dtype=np.float64)
  shape = np.asarray(shape, dtype=np.float64)
  pos = counts > 0
  if not np.any(pos):
    return 0.0

  y_max = float(counts.max())
  w = np.sqrt(counts[pos])
  s = shape[pos]
  y = counts[pos]
  denom = float(np.dot(w * s, w * s))
  if denom <= 0:
    return y_max
  a_weighted = float(np.dot(w * y, w * s) / denom)
  return float(np.clip(max(a_weighted, 0.0), 0.0, y_max * 1.05))


def _model_no_irf(t_s: np.ndarray, tau_s: float, amplitude: float, offset: float) -> np.ndarray:
  """Fallback: pulsed-window exponential; amplitude scales peak-normalised shape."""
  shape = _decay_shape_peak_normalized(t_s, tau_s, used_irf=False, irf_on_grid=None)
  if shape is None:
    return np.zeros_like(t_s)
  return amplitude * shape + offset


def _model_with_irf(t_s: np.ndarray, irf: np.ndarray, tau_s: float, amplitude: float, offset: float) -> np.ndarray:
  shape = _decay_shape_peak_normalized(t_s, tau_s, used_irf=True, irf_on_grid=irf)
  if shape is None:
    return _model_no_irf(t_s, tau_s, amplitude, offset)
  return amplitude * shape + offset


def _poisson_deviance(observed: np.ndarray, expected: np.ndarray) -> float:
  """
  Reduced Poisson deviance.

  Includes y=0 bins so a model that stays high in the tail is penalised.
  """
  obs = np.asarray(observed, dtype=np.float64)
  exp = np.maximum(np.asarray(expected, dtype=np.float64), 1e-12)
  valid = obs > 0
  if not np.any(valid):
    return float(np.sum((obs - exp) ** 2))
  term = obs[valid] * np.log(exp[valid] / obs[valid])
  chi2 = -2.0 * (np.sum(obs - exp) + np.sum(term))
  return float(max(chi2, 0.0))


def _estimate_tau_tcspc(t_s: np.ndarray, counts: np.ndarray) -> float:
  """Mean-lifetime seed from FLIMGlobalFitController.cpp (TCSPC branch)."""
  y = np.maximum(np.asarray(counts, dtype=np.float64), 0.0)
  t = np.asarray(t_s, dtype=np.float64)
  n = y.sum()
  if n <= 0 or t.size < 2:
    return 2.0e-9
  t0 = t[0]
  T = t[-1] - t0
  if T <= 0:
    return 2.0e-9
  t_mean = np.sum(y * (t - t0)) / n / T
  tau = max(float(t_mean), 1e-12)
  for _ in range(5):
    e = np.exp(1.0 / tau)
    iem1 = 1.0 / (e - 1.0)
    denom = e * iem1 * iem1 / (tau * tau) - 1.0
    if abs(denom) < 1e-30:
      break
    tau = tau - (-tau + t_mean + iem1) / denom
    tau = max(tau, 1e-12)
  return tau * T


def _prepare_forward_context(
  t_ns: np.ndarray,
  shared: SharedData,
) -> tuple[np.ndarray, bool, np.ndarray | None]:
  t_s = np.asarray(t_ns, dtype=np.float64) * 1e-9
  irf_info = _reference_irf(shared)
  used_irf = False
  irf_on_grid: np.ndarray | None = None
  if irf_info is not None:
    t_irf_s, irf = irf_info
    irf_on_grid = _align_irf(t_s, t_irf_s, irf)
    if irf_on_grid.sum() > 0:
      irf_on_grid = irf_on_grid / irf_on_grid.sum()
      used_irf = True
  return t_s, used_irf, irf_on_grid


def _forward_model(
  t_s: np.ndarray,
  tau_ns: float,
  counts: np.ndarray,
  offset: float,
  *,
  used_irf: bool,
  irf_on_grid: np.ndarray | None,
  fixed_amplitude: float | None = None,
  peak_align: bool = False,
) -> tuple[np.ndarray, float, float] | tuple[None, float, float]:
  """
  y = A·h(t; τ) on the instrument delay grid.

  t₀ from baseline correction only gates which bins enter the fit — the model is
  not time-shifted; baseline subtraction is the temporal correction.
  """
  tau_s = max(float(tau_ns) * 1e-9, 1e-15)
  shape = _decay_shape_peak_normalized(t_s, tau_s, used_irf=used_irf, irf_on_grid=irf_on_grid)
  if shape is None:
    return None, 0.0, 0.0
  t_ns = np.asarray(t_s, dtype=np.float64) * 1e9
  shift_ns = 0.0
  if peak_align:
    shape, shift_ns = _peak_align_shape(t_ns, counts, shape)
  if fixed_amplitude is not None:
    amp = float(fixed_amplitude)
  else:
    amp = _optimal_amplitude(counts, shape)
  return amp * shape + offset, amp, shift_ns


def predict_decay_at_tau(
  t_ns: np.ndarray,
  counts: np.ndarray,
  tau_ns: float,
  *,
  shared: SharedData | None = None,
  t0_ns: float | None = None,
  peak_align: bool = False,
  use_irf: bool | None = None,
) -> np.ndarray | None:
  """
  Model decay for a fixed τ (e.g. lifetime-map value), scaled to the measured total photons.
  Uses the same IRF reconvolution as the fitter when a reference is loaded.

  use_irf: None = auto (reference if available); True/False = force on/off (test UI).
  """
  t_ns = np.asarray(t_ns, dtype=np.float64)
  counts = np.asarray(counts, dtype=np.float64)
  if t_ns.size != counts.size or t_ns.size < 2:
    return None
  if counts.sum() <= 0 or tau_ns <= 0 or not np.isfinite(tau_ns):
    return None
  shared = shared or SharedData()
  t_s, used_irf, irf_on_grid = _prepare_forward_context(t_ns, shared)
  if use_irf is False:
    used_irf, irf_on_grid = False, None
  if t0_ns is not None:
    fit_mask = t_ns >= float(t0_ns) - 1e-9
    a_fixed = float(counts[fit_mask].max()) if np.any(fit_mask) else float(counts.max())
  else:
    a_fixed = float(counts.max())
  out = _forward_model(
    t_s, float(tau_ns), counts, 0.0,
    used_irf=used_irf, irf_on_grid=irf_on_grid,
    fixed_amplitude=a_fixed,
    peak_align=peak_align,
  )
  if out[0] is None:
    return None
  return out[0]


def fit_single_exponential(
  t_ns: np.ndarray,
  counts: np.ndarray,
  *,
  fit_offset: bool = False,
  tau_hint_ns: float | None = None,
  t0_ns: float | None = None,
  peak_align: bool = False,
  use_irf: bool | None = None,
  shared: SharedData | None = None,
) -> DecayFitResult | None:
  """
  Fit one single-exponential decay with optional IRF from the reference file.

  Requires t₀ from baseline correction (first channel after the baseline window).
  Amplitude A is fixed to max(measured counts) at/after t₀ before τ is optimised.
  The IRF⊗exp model stays on the instrument time grid; baseline correction is the offset fix.

  use_irf: None = auto; True/False = force (test UI).
  """
  t_ns = np.asarray(t_ns, dtype=np.float64)
  counts = np.asarray(counts, dtype=np.float64)
  if t_ns.size != counts.size or t_ns.size < 4:
    return None
  if counts.sum() <= 0:
    return None
  if t0_ns is None or not np.isfinite(t0_ns):
    return None

  t0_ns = float(t0_ns)
  fit_mask = t_ns >= t0_ns - 1e-9
  if not np.any(fit_mask) or int(np.sum(fit_mask)) < 4:
    return None

  shared = shared or SharedData()
  t_ns_orig = t_ns.copy()
  counts_orig = counts.copy()

  avg_per_bin = float(counts_orig.sum()) / max(len(counts_orig), 1)
  if avg_per_bin < 2.0 or counts_orig.sum() < 400:
    t_fit_ns, counts_fit, autosampled = autosample_decay(t_ns_orig, counts_orig)
  else:
    t_fit_ns, counts_fit, autosampled = t_ns_orig, counts_orig, False
  if len(t_fit_ns) < 4:
    t_fit_ns, counts_fit, autosampled = t_ns_orig, counts_orig, False

  total = float(counts_orig.sum())
  a_fixed = float(counts_orig[fit_mask].max())

  t_s_fit = np.asarray(t_fit_ns, dtype=np.float64) * 1e-9
  tau0_s = _estimate_tau_tcspc(t_s_fit, counts_fit)
  tau0_ns = float(np.clip(tau0_s * 1e9, _MIN_TAU_NS, _MAX_TAU_NS))
  tau_min, tau_max, centre_ns = _tau_search_range(tau_hint_ns, tau0_ns, shared)

  n_params = 2 if fit_offset else 1
  n_fit_bins = int(np.sum(fit_mask))
  sparse_fit = total < _SPARSE_PHOTON_WARN

  def model_at_tau(
    t_ns_grid: np.ndarray,
    y_ref: np.ndarray,
    tau_ns: float,
    offset: float = 0.0,
  ) -> tuple[np.ndarray, float, float] | tuple[None, float, float]:
    t_s, used_irf, irf_on_grid = _prepare_forward_context(t_ns_grid, shared)
    if use_irf is False:
      used_irf, irf_on_grid = False, None
    return _forward_model(
      t_s, tau_ns, y_ref, offset,
      used_irf=used_irf, irf_on_grid=irf_on_grid,
      fixed_amplitude=a_fixed,
      peak_align=peak_align,
    )

  def objective(x: np.ndarray) -> float:
    tau_ns = float(np.clip(x[0], tau_min, tau_max))
    offset = float(np.exp(x[1])) if fit_offset else 0.0
    model, _, _ = model_at_tau(t_ns_orig, counts_orig, tau_ns, offset)
    if model is None:
      return np.inf
    return _poisson_deviance(counts_orig[fit_mask], model[fit_mask]) / max(n_fit_bins - n_params, 1)

  starts = [tau0_ns, centre_ns]
  if tau_hint_ns is not None and tau_hint_ns > 0 and np.isfinite(tau_hint_ns):
    starts.append(float(tau_hint_ns))
  starts.append((tau_min + tau_max) / 2.0)
  starts = [float(np.clip(s, tau_min, tau_max)) for s in starts]

  best_res = None
  best_obj = np.inf
  used_irf = _prepare_forward_context(t_fit_ns, shared)[1]
  if use_irf is False:
    used_irf = False
  for tau_start in dict.fromkeys(round(s, 4) for s in starts):
    x0 = np.array([tau_start] + ([np.log(0.5)] if fit_offset else []), dtype=np.float64)
    bounds = [(tau_min, tau_max)]
    if fit_offset:
      bounds.append((np.log(1e-3), np.log(max(total, 1.0))))
    res = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
    if float(res.fun) < best_obj:
      best_obj = float(res.fun)
      best_res = res

  res = best_res
  if res is None:
    return None

  tau_fit = float(np.clip(res.x[0], tau_min, tau_max))
  offset_fit = float(np.exp(res.x[1])) if fit_offset else 0.0
  model, amp_fit, shift_ns = model_at_tau(t_ns_orig, counts_orig, tau_fit, offset_fit)
  if model is None:
    return None
  chi2 = _poisson_deviance(counts_orig[fit_mask], model[fit_mask]) / max(n_fit_bins - n_params, 1)

  hit_lower = tau_fit <= tau_min * 1.02
  hit_upper = tau_fit >= tau_max * 0.98

  msg = "IRF from reference" if used_irf else "no IRF — exponential only (load a reference to use IRF reconvolution)"
  y_peak = float(counts_orig[fit_mask].max())
  msg += f"; A = {amp_fit:.1f} (fixed to data peak {y_peak:.0f} at/after t₀ before τ fit)"
  msg += f"; t₀ = {t0_ns:.2f} ns (fit from baseline window; model not time-shifted)"
  if peak_align and abs(shift_ns) > 1e-6:
    msg += f"; peak aligned to data (Δt = {shift_ns:.2f} ns)"
  elif peak_align:
    msg += "; peak aligned to data"
  if sparse_fit:
    msg += "; Poisson fit from t₀ onward (tail zeros penalised)"
  if autosampled:
    msg += f"; autosampled {len(t_ns_orig)}→{len(t_fit_ns)} bins"
  if total < _SPARSE_PHOTON_WARN:
    msg += "; sparse pixel — prefer τ map or a brighter pixel"
  if hit_lower:
    msg += f"; WARNING: τ hit lower bound ({tau_min:.2f} ns) — fit unreliable"
  elif hit_upper:
    msg += f"; WARNING: τ hit upper bound ({tau_max:.2f} ns) — fit unreliable"
  if tau_hint_ns is not None and tau_hint_ns > 0:
    msg += f"; map τ≈{tau_hint_ns:.2f} ns"
  return DecayFitResult(
    tau_ns=tau_fit,
    amplitude=amp_fit,
    offset=offset_fit,
    chi2_reduced=chi2,
    model_counts=model,
    used_irf=used_irf,
    converged=bool(res.success),
    message=msg,
    autosampled=autosampled,
    n_bins_fit=int(len(t_fit_ns) if autosampled else len(t_ns_orig)),
    hit_tau_lower_bound=hit_lower,
    hit_tau_upper_bound=hit_upper,
    tau_ma_ns=tau0_ns,
    t0_ns=t0_ns,
    peak_shift_ns=shift_ns,
  )
