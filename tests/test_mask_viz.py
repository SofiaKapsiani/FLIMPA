"""Mask overlay styling stays subtle without changing mask data."""

import numpy as np

from utils.mask_viz import MASK_EDGE_ALPHA, MASK_FILL_ALPHA, draw_mask_overlay


def test_mask_overlay_alpha_is_subtle():
    assert 0.20 <= MASK_FILL_ALPHA <= 0.35
    assert 0.60 <= MASK_EDGE_ALPHA <= 0.80


def test_draw_mask_overlay_does_not_mutate_mask():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mask = np.zeros((8, 8), dtype=np.uint16)
    mask[2:6, 2:6] = 1
    original = mask.copy()
    fig, ax = plt.subplots()
    ax.imshow(np.zeros((8, 8)), cmap="gray")
    draw_mask_overlay(ax, mask)
    np.testing.assert_array_equal(mask, original)
    plt.close(fig)
