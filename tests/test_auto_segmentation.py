"""Tests for intensity auto-segmentation."""

import numpy as np

from utils.auto_segmentation import (
    AUTO_SEGMENT_UI_ENABLED,
    nth_segmentation,
    otsu_oht_segmentation,
    run_segmentation,
)


def test_auto_segment_ui_disabled_by_default():
    assert AUTO_SEGMENT_UI_ENABLED is False


def _blob_image(size=128, center=(64, 64), radius=25, background=10.0, signal=200.0):
    y, x = np.ogrid[:size, :size]
    cy, cx = center
    img = np.full((size, size), background, dtype=np.float64)
    img[(y - cy) ** 2 + (x - cx) ** 2 <= radius ** 2] = signal
    return img


def test_otsu_finds_blob():
    img = _blob_image()
    mask = otsu_oht_segmentation(img, scale=20, sensitivity=1.0, smoothing=3, min_size=50)
    assert mask.max() >= 1
    assert mask[64, 64] > 0


def test_nth_finds_blob():
    img = _blob_image()
    mask = nth_segmentation(img, scale=20, rel_bg_scale=2.0, threshold=0.05, smoothing=3, min_size=50)
    assert mask.max() >= 1
    assert mask[64, 64] > 0


def test_run_segmentation_by_name():
    img = _blob_image()
    mask = run_segmentation("Otsu + top-hat", img, {"min_size": 50, "scale": 20, "smoothing": 3})
    assert mask.dtype == np.uint16


def test_empty_image_returns_zeros():
    img = np.zeros((64, 64), dtype=np.float64)
    mask = otsu_oht_segmentation(img)
    assert mask.max() == 0
