"""
Intensity auto-segmentation (editable after running).

Algorithms:
  - otsu_oht (Otsu threshold after morphological top-hat)
  - nth (nonlinear top-hat / local background)

See README.md (Masking) for parameter definitions and tuning.

---
FUTURE / NOT IN UI:
  Auto-segmentation is implemented here but is not shown in the Masking menu.
  Keep this module (and mask_segment_dialog.py) for a later, stable UI.
  To re-enable Instruments → Auto segment, set AUTO_SEGMENT_UI_ENABLED = True.
  Entry points: mask_instruments.MaskInstrumentsOverlay, ui_layout.run_auto_segmentation,
  mask_editor.run_auto_segmentation, mask_segment_dialog.AutoSegmentDialog.
"""

from __future__ import annotations

# Re-enable Masking → Auto segment when the UI is ready to ship.
AUTO_SEGMENT_UI_ENABLED = False

import numpy as np
from scipy import ndimage
from skimage import measure, morphology, filters


def _box_average(image: np.ndarray, diameter: int) -> np.ndarray:
    """Separable box filter with edge normalisation."""
    r = max(1, int(round(diameter)))
    kernel = np.ones(r, dtype=np.float64) / r
    z = ndimage.convolve1d(image.astype(np.float64), kernel, axis=0, mode="nearest")
    z = ndimage.convolve1d(z, kernel, axis=1, mode="nearest")
    # Normalise so box average is unbiased near image borders
    norm = ndimage.convolve1d(np.ones_like(image, dtype=np.float64), kernel, axis=0, mode="nearest")
    norm = ndimage.convolve1d(norm, kernel, axis=1, mode="nearest")
    return np.divide(z, norm, out=np.zeros_like(z), where=norm > 0)


def _nonlinear_tophat(image: np.ndarray, scale: float, rel_bg_scale: float) -> np.ndarray:
    """
    Local contrast enhancement using two box scales.
    rel_bg_scale > 1 uses a wider window for background estimation.
    """
    d = max(1, int(round(scale)))
    k = max(1.0, float(rel_bg_scale))
    u1 = _box_average(image, d)
    u2 = _box_average(image, k * d)
    denom = np.maximum(u2 * u2, 1e-12)
    return image * u1 / denom


def _morph_smooth(binary: np.ndarray, smoothing: int) -> np.ndarray:
    """Opening-like smooth: erode then dilate after thresholding."""
    radius = max(1, int(round(abs(smoothing))))
    se = morphology.disk(radius)
    eroded = morphology.erosion(binary, se)
    return morphology.dilation(eroded, se)


def _label_regions(
    binary: np.ndarray,
    min_size: int,
    max_eccentricity: float = 1.0,
) -> np.ndarray:
    """
    Label 8-connected foreground and renumber kept regions 1..N.
    Drops components smaller than min_size.
    """
    labelled = measure.label(binary, connectivity=2)
    if labelled.max() == 0:
        return np.zeros_like(labelled, dtype=np.uint16)

    props = measure.regionprops(labelled)
    keep = {
        p.label
        for p in props
        if p.area >= min_size and (max_eccentricity >= 1.0 or p.eccentricity < max_eccentricity)
    }
    if not keep:
        return np.zeros_like(labelled, dtype=np.uint16)

    out = np.zeros_like(labelled, dtype=np.uint16)
    new_id = 1
    for old_id in sorted(keep):
        out[labelled == old_id] = new_id
        new_id += 1
    return out


def otsu_oht_segmentation(
    intensity: np.ndarray,
    scale: float = 100,
    sensitivity: float = 1.0,
    smoothing: int = 5,
    min_size: int = 200,
) -> np.ndarray:
    """
    Histogram-based segmentation with local background removal (Otsu + top-hat).

    scale: morphological disk radius (~object width in px).
    sensitivity: divides Otsu threshold; >1 includes more pixels.
    smoothing: disk radius for binary cleanup.
    min_size: minimum region area in px².
    """
    u = np.asarray(intensity, dtype=np.float64)
    if u.size == 0 or float(u.max()) <= float(u.min()):
        return np.zeros(u.shape, dtype=np.uint16)

    radius = max(1, int(round(abs(scale))))
    se = morphology.disk(radius)
    tophat = morphology.white_tophat(u, se)
    bothat = morphology.black_tophat(u, se)
    j = u + tophat - bothat
    j_min, j_max = float(j.min()), float(j.max())
    if j_max > j_min:
        j = (j - j_min) / (j_max - j_min)
    else:
        j = np.zeros_like(j)

    otsu_level = filters.threshold_otsu(j) if np.any(j) else 0.0
    sensitivity = max(abs(float(sensitivity)), 1e-6)
    threshold = min(1.0, abs(otsu_level / sensitivity))
    binary = j >= threshold
    binary = _morph_smooth(binary, smoothing)
    return _label_regions(binary, min_size)


def nth_segmentation(
    intensity: np.ndarray,
    scale: float = 100,
    rel_bg_scale: float = 2.0,
    threshold: float = 0.1,
    smoothing: int = 5,
    min_size: int = 200,
) -> np.ndarray:
    """
    Local-threshold segmentation via nonlinear top-hat.

    scale: inner box width (~object size in px).
    rel_bg_scale: background box = scale × this ratio (≥1).
    threshold: on normalised nth image; lower → larger mask.
    smoothing, min_size: as in Otsu algorithm.
    """
    nth = _nonlinear_tophat(intensity, scale, rel_bg_scale) - 1.0
    norm = min(float(np.max(nth)), 10000.0)
    if norm <= 0:
        return np.zeros(intensity.shape, dtype=np.uint16)
    nth = nth / norm
    threshold = np.clip(threshold / norm, 0.0, 1.0)
    binary = nth >= threshold
    binary = _morph_smooth(binary, smoothing)
    return _label_regions(binary, min_size)


# Registry for AutoSegmentDialog: shipped default values
ALGORITHMS = {
    "Otsu + top-hat": {
        "fn": otsu_oht_segmentation,
        "defaults": {"scale": 100, "sensitivity": 1.0, "smoothing": 5, "min_size": 200},
        "fields": [
            ("scale", "Object width (pixels)"),
            ("sensitivity", "Threshold sensitivity (>1 expands)"),
            ("smoothing", "Smoothing radius (pixels)"),
            ("min_size", "Minimum region area (pixels²)"),
        ],
    },
    "Nonlinear top-hat (nth)": {
        "fn": nth_segmentation,
        "defaults": {"scale": 100, "rel_bg_scale": 2.0, "threshold": 0.1, "smoothing": 5, "min_size": 200},
        "fields": [
            ("scale", "Object width (pixels)"),
            ("rel_bg_scale", "Background / object scale ratio"),
            ("threshold", "Threshold (0–1 after normalisation)"),
            ("smoothing", "Smoothing radius (pixels)"),
            ("min_size", "Minimum region area (pixels²)"),
        ],
    },
}


def run_segmentation(name: str, intensity: np.ndarray, params: dict) -> np.ndarray:
    """Run a named algorithm; merges user params over ALGORITHMS defaults."""
    if name not in ALGORITHMS:
        raise ValueError(f"Unknown segmentation algorithm: {name}")
    spec = ALGORITHMS[name]
    merged = {**spec["defaults"], **params}
    result = spec["fn"](intensity, **merged)
    return np.asarray(result, dtype=np.uint16)
