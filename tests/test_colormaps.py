"""Colormap presets and custom file loading (no GUI)."""

from pathlib import Path

import numpy as np
import pytest
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

from utils.colormaps import (
    LIFETIME_CMAP_PRESETS,
    clear_custom_colormap_cache,
    load_colormap_from_file,
    resolve_lifetime_cmap,
)


def test_all_presets_resolve():
    for preset in LIFETIME_CMAP_PRESETS:
        cmap = resolve_lifetime_cmap({"lifetime_cmap": preset})
        rgba = np.asarray(cmap(0.5))
        assert rgba.shape[-1] == 4
        assert np.all(rgba[..., :3] >= 0) and np.all(rgba[..., :3] <= 1)


def test_custom_missing_file_falls_back_to_rainbow():
    cmap = resolve_lifetime_cmap(
        {"lifetime_cmap": "Custom", "lifetime_cmap_file": "/nonexistent/path.csv"}
    )
    assert cmap.name == "gist_rainbow_r"


def test_custom_none_file_falls_back_to_rainbow():
    cmap = resolve_lifetime_cmap(
        {"lifetime_cmap": "Custom", "lifetime_cmap_file": "None"}
    )
    assert cmap.name == "gist_rainbow_r"


def test_load_colormap_from_csv(tmp_path):
    csv_path = tmp_path / "test_cmap.csv"
    csv_path.write_text(
        "R,G,B\n"
        "0,0,0\n"
        "255,0,0\n"
        "0,0,255\n",
        encoding="utf-8",
    )
    clear_custom_colormap_cache()
    cmap = load_colormap_from_file(csv_path)
    assert isinstance(cmap, LinearSegmentedColormap)
    assert np.allclose(cmap(0.0)[:3], [0, 0, 0], atol=0.02)
    assert np.allclose(cmap(1.0)[:3], [0, 0, 1], atol=0.02)


def test_load_colormap_from_csv_cached(tmp_path):
    csv_path = tmp_path / "cache.csv"
    csv_path.write_text("0,0,0\n255,255,255\n", encoding="utf-8")
    clear_custom_colormap_cache()
    first = load_colormap_from_file(csv_path)
    second = load_colormap_from_file(csv_path)
    assert first is second


def test_load_colormap_from_image_strip(tmp_path):
    from PIL import Image

    img_path = tmp_path / "strip.png"
    arr = np.zeros((10, 100, 3), dtype=np.uint8)
    arr[:, :50] = [255, 0, 0]
    arr[:, 50:] = [0, 0, 255]
    Image.fromarray(arr).save(img_path)

    clear_custom_colormap_cache()
    cmap = load_colormap_from_file(img_path)
    assert isinstance(cmap, ListedColormap)
    assert cmap.N == 256


def test_csv_needs_at_least_two_rows(tmp_path):
    bad = tmp_path / "one_row.csv"
    bad.write_text("128,128,128\n", encoding="utf-8")
    with pytest.raises(ValueError, match="at least two"):
        load_colormap_from_file(bad)


def test_unsupported_extension(tmp_path):
    bad = tmp_path / "cmap.xyz"
    bad.write_text("data", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported"):
        load_colormap_from_file(bad)
