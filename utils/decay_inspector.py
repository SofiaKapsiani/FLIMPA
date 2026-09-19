"""Extract per-pixel fluorescence decay curves from loaded TCSPC data."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from utils.shared_data import SharedData

_BIN_EDGE = {
    "None": 1,
    "3x3": 3,
    "7x7": 7,
    "9x9": 9,
    "12x12": 12,
}


@dataclass
class PixelDecay:
    """Decay curve and metadata for one spatial location."""

    filename: str
    x: int
    y: int
    t_ns: np.ndarray
    counts: np.ndarray
    total_photons: int
    tau_ns: float | None
    masked_out: bool
    baseline_corrected: bool
    t0_ns: float | None = None
    baseline_fraction_pct: float | None = None
    fit_allowed: bool = False
    block_size: int = 1


def pixel_block_edge(shared: SharedData | None = None) -> int:
    """Spatial block edge from Pixel block size (same mapping as LifetimeData.get_bins)."""
    if shared is None:
        shared = SharedData()
    return int(_BIN_EDGE.get(shared.config.get("bins", "None"), 1))


def baseline_t0_ns(t_ns: np.ndarray, fraction_percent: float) -> float | None:
    """
    Time origin for decay fitting: first delay channel after the baseline window.

    Matches calc_Coordinates / % time channels (baseline corr.) — bins before t₀
    are used only to estimate and subtract offset, not for τ fitting.
    """
    t = np.asarray(t_ns, dtype=np.float64)
    if t.size < 4 or fraction_percent <= 0:
        return None
    num_bins = int(fraction_percent / 100.0 * t.size)
    if num_bins < 1 or num_bins >= t.size - 2:
        return None
    return float(t[num_bins])


def _map_click_to_raw_indices(
    x_click: float,
    y_click: float,
    display_shape: tuple[int, int],
    raw_shape: tuple[int, int],
) -> tuple[int, int]:
    """Map matplotlib image coordinates to indices in the raw (y, x) data array."""
    ny_d, nx_d = display_shape
    ny_r, nx_r = raw_shape
    if ny_d <= 0 or nx_d <= 0:
        return int(round(y_click)), int(round(x_click))
    yi = int(round(y_click * (ny_r - 1) / max(ny_d - 1, 1)))
    xi = int(round(x_click * (nx_r - 1) / max(nx_d - 1, 1)))
    yi = int(np.clip(yi, 0, ny_r - 1))
    xi = int(np.clip(xi, 0, nx_r - 1))
    return yi, xi


def _apply_baseline_correction(counts: np.ndarray, fraction_percent: float) -> np.ndarray:
    """Match calc_Coordinates baseline subtraction for a single decay vector."""
    if counts.size == 0 or fraction_percent <= 0:
        return counts.astype(np.float64)
    num_bins = int(fraction_percent / 100.0 * counts.shape[0])
    if num_bins < 1:
        return counts.astype(np.float64)
    corrected = counts.astype(np.float64).copy()
    corrected -= np.mean(corrected[:num_bins])
    return np.clip(corrected, 0, None)


def _block_sum_counts(cube: np.ndarray, yi: int, xi: int, block: int) -> np.ndarray:
    """Sum TCSPC counts over an N×N neighbourhood centred on (yi, xi), clipped to bounds."""
    if block <= 1:
        return np.asarray(cube[:, yi, xi], dtype=np.float64)
    ny, nx = cube.shape[1], cube.shape[2]
    half = block // 2
    y0 = max(0, yi - half)
    y1 = min(ny, yi + half + 1)
    x0 = max(0, xi - half)
    x1 = min(nx, xi + half + 1)
    return np.asarray(cube[:, y0:y1, x0:x1], dtype=np.float64).sum(axis=(1, 2))


def _tau_at_pixel(filename: str, yi: int, xi: int, shared: SharedData) -> float | None:
    """Mean lifetime (ns) at pixel from analysis results, if available."""
    if filename not in shared.results_dict:
        return None
    entry = shared.results_dict[filename]
    lifetime_key = shared.config.get("lifetime_map", "tau_m")
    tau = entry.get(lifetime_key)
    if tau is None:
        return None
    tau = np.asarray(tau, dtype=np.float64).ravel()
    img_shape = entry.get("img_shape")
    if img_shape is None or len(img_shape) < 3:
        return None
    _, y_dim, x_dim = img_shape
    if tau.size != y_dim * x_dim:
        return None
    idx = yi * x_dim + xi
    if idx < 0 or idx >= tau.size:
        return None
    val = float(tau[idx]) * 1e9
    return val if val > 0 and np.isfinite(val) else None


def get_pixel_decay(
    filename: str,
    x_click: float,
    y_click: float,
    display_shape: tuple[int, int] | None = None,
    *,
    apply_baseline: bool | None = None,
) -> PixelDecay | None:
    """
    Build decay curve for the pixel under (x_click, y_click) in image coordinates.

    Uses masked_data when present; optional baseline correction follows the
    Baseline correction parameter unless apply_baseline overrides it.

    Spatial averaging follows Pixel block size (same N×N as phasor analysis).
    Map τ is taken from the centre pixel.
    """
    shared = SharedData()
    if not filename or filename not in shared.raw_data_dict:
        return None

    entry = shared.raw_data_dict[filename]
    raw = np.asarray(entry["data"])
    if raw.ndim != 3:
        return None

    spatial = raw.shape[1:]
    disp = display_shape if display_shape is not None else spatial
    yi, xi = _map_click_to_raw_indices(x_click, y_click, disp, spatial)

    use_masked = entry.get("masked_data")
    cube = np.asarray(use_masked if use_masked is not None else raw)
    block = pixel_block_edge(shared)
    counts = _block_sum_counts(cube, yi, xi, block)

    masked_out = bool(np.all(counts == 0))

    fraction_pct = float(shared.config.get("fraction_offset", 3.5))
    if apply_baseline is None:
        apply_baseline = shared.config.get("subtract_offset", "False") == "True"
    if apply_baseline:
        counts = _apply_baseline_correction(counts, fraction_pct)

    t_raw = entry.get("t_series")
    t_series = np.asarray(t_raw, dtype=np.float64) if t_raw is not None else np.array([], dtype=np.float64)
    if t_series.size != raw.shape[0]:
        freq = float(shared.config.get("frequency", 40)) * 1e6
        t_series = np.linspace(0, (raw.shape[0] - 1) / (freq * raw.shape[0]), raw.shape[0])

    t_ns = t_series * 1e9
    t0_ns = baseline_t0_ns(t_ns, fraction_pct) if apply_baseline else None
    fit_allowed = bool(apply_baseline and t0_ns is not None)

    return PixelDecay(
        filename=filename,
        x=xi,
        y=yi,
        t_ns=t_ns,
        counts=counts,
        total_photons=int(np.sum(counts)),
        tau_ns=_tau_at_pixel(filename, yi, xi, shared),
        masked_out=masked_out,
        baseline_corrected=bool(apply_baseline),
        t0_ns=t0_ns,
        baseline_fraction_pct=fraction_pct if apply_baseline else None,
        fit_allowed=fit_allowed,
        block_size=block,
    )
