"""Lifetime colormap presets and custom colormap loading.

Used by Lifetime maps, Gallery (tau), and exports via resolve_lifetime_cmap().

UI: Intensity display Settings — Colormap dropdown + Load custom...
    (see TabSettingsWidgets.intensity_box / ToolBarComponents.setup_analysis_controls).

Presets: Rainbow, Binary, Viridis, etc. (see LIFETIME_CMAP_PRESETS).
Custom: set lifetime_cmap to "Custom" and lifetime_cmap_file to:
  - CSV/TXT — one RGB row per colour (low → high lifetime)
  - PNG/JPG — horizontal colour strip (sampled left → right)
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

LIFETIME_CMAP_PRESETS = [
    "Rainbow",
    "Binary (black-white)",
    "Binary (blue-red)",
    "Viridis",
    "Plasma",
    "Inferno",
    "Cividis",
    "Jet",
    "Hot",
]

_PRESET_MPL = {
    "Rainbow": "gist_rainbow_r",
    "Viridis": "viridis",
    "Plasma": "plasma",
    "Inferno": "inferno",
    "Cividis": "cividis",
    "Jet": "jet",
    "Hot": "hot",
}

_BINARY_PRESETS = {
    "Binary (black-white)": [(0.0, 0.0, 0.0), (1.0, 1.0, 1.0)],
    "Binary (blue-red)": [(0.0, 0.0, 0.8), (1.0, 0.0, 0.0)],
}

_custom_cache = {}


def clear_custom_colormap_cache():
    _custom_cache.clear()


def _normalize_rgb(values):
    arr = np.asarray(values, dtype=float)
    if arr.max() > 1.0:
        arr = arr / 255.0
    return np.clip(arr, 0.0, 1.0)


def load_colormap_from_file(path):
    """
    Load a custom colormap from file.

    Supported formats:
    - CSV/TXT: one color per row, columns R,G,B (0-255 or 0-1). Optional header row.
    - PNG/JPG: horizontal color strip; colors are sampled left-to-right along the middle row.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Colormap file not found: {path}")

    cache_key = (str(path.resolve()), path.stat().st_mtime)
    if cache_key in _custom_cache:
        return _custom_cache[cache_key]

    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        cmap = _load_colormap_from_image(path)
    elif suffix in {".csv", ".txt", ".tsv"}:
        cmap = _load_colormap_from_table(path)
    else:
        raise ValueError(
            "Unsupported colormap file type. Use .csv/.txt (R,G,B columns) "
            "or a horizontal color-strip image (.png, .jpg)."
        )

    _custom_cache[cache_key] = cmap
    return cmap


def _load_colormap_from_table(path):
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = [part.strip() for part in stripped.replace(";", ",").split(",")]
            if len(parts) < 3:
                continue
            header = {part.lower() for part in parts[:3]}
            if header >= {"r", "g", "b"} or header >= {"red", "green", "blue"}:
                continue
            try:
                rgb = [float(parts[0]), float(parts[1]), float(parts[2])]
            except ValueError:
                continue
            rows.append(rgb)

    if len(rows) < 2:
        raise ValueError(
            "Colormap table must contain at least two RGB rows (low → high lifetime)."
        )

    colors = _normalize_rgb(rows)
    name = f"custom_{path.stem}"
    return LinearSegmentedColormap.from_list(name, colors, N=256)


def _load_colormap_from_image(path):
    image = plt.imread(path)
    if image.ndim == 2:
        image = np.stack([image, image, image], axis=-1)
    if image.shape[-1] == 4:
        image = image[..., :3]

    row = image[image.shape[0] // 2]
    if row.shape[0] < 2:
        raise ValueError("Colormap image must be at least 2 pixels wide.")

    colors = _normalize_rgb(row)
    name = f"custom_{path.stem}"
    return ListedColormap(colors, name=name, N=256)


def resolve_lifetime_cmap(config):
    """Return matplotlib colormap from config lifetime_cmap / lifetime_cmap_file keys."""
    preset = config.get("lifetime_cmap", "Rainbow")
    if preset == "Custom":
        cmap_file = config.get("lifetime_cmap_file", "None")
        if not cmap_file or cmap_file == "None":
            return plt.get_cmap("gist_rainbow_r")
        try:
            return load_colormap_from_file(cmap_file)
        except (OSError, ValueError):
            return plt.get_cmap("gist_rainbow_r")

    if preset in _BINARY_PRESETS:
        return LinearSegmentedColormap.from_list(
            preset.replace(" ", "_").lower(),
            _BINARY_PRESETS[preset],
            N=256,
        )

    mpl_name = _PRESET_MPL.get(preset, "gist_rainbow_r")
    return plt.get_cmap(mpl_name)
