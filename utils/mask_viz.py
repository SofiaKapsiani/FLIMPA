"""
Draw manual mask regions on matplotlib axes (fill + contour + labels).

Overlay colours match FLIMPA teal theme; SELECT_* used while drawing tools are active.
"""

import numpy as np
from matplotlib import colormaps
from PIL import Image
from scipy.ndimage import center_of_mass


MASK_EDGE_COLOR = "#3ca2a1"
MASK_FILL_CMAP = "spring"
MASK_FILL_ALPHA = 0.28
MASK_EDGE_ALPHA = 0.70
MASK_EDGE_WIDTH = 1.4
SELECT_COLOR = "#FFE066"
SELECT_FILL = (1.0, 0.88, 0.4, 0.28)


def resize_mask(mask, target_shape):
    """Nearest-neighbour resize to (height, width)."""
    mask = np.asarray(mask)
    if mask.shape == target_shape:
        return mask
    img = Image.fromarray(mask.astype(np.uint16))
    img = img.resize((target_shape[1], target_shape[0]), Image.NEAREST)
    return np.array(img, dtype=mask.dtype)


def fit_region_to_shape(region_bool, target_shape):
    """Expand or shrink a boolean region to target (H, W)."""
    region_bool = np.asarray(region_bool, dtype=bool)
    if region_bool.shape == target_shape:
        return region_bool
    scaled = resize_mask(region_bool.astype(np.uint16), target_shape)
    return scaled > 0


def draw_mask_overlay(ax, manual_mask, show_labels=True):
    """Semi-transparent fill, teal outlines, and region IDs."""
    if manual_mask is None:
        return
    mask = np.asarray(manual_mask)
    if mask.size == 0 or mask.max() == 0:
        return

    if ax.images:
        arr = ax.images[0].get_array()
        if arr is not None and getattr(arr, "ndim", 0) == 2 and arr.shape != mask.shape:
            mask = resize_mask(mask, arr.shape)

    filled = np.ma.masked_where(mask == 0, mask.astype(float))
    vmax = max(float(filled.max()), 1.0)
    ax.imshow(
        filled,
        cmap=colormaps[MASK_FILL_CMAP],
        alpha=MASK_FILL_ALPHA,
        vmin=0,
        vmax=vmax,
        interpolation="nearest",
    )

    try:
        from skimage import measure

        for region in np.unique(mask):
            if region == 0:
                continue
            for contour in measure.find_contours(mask == region, 0.5):
                ax.plot(
                    contour[:, 1], contour[:, 0],
                    color=MASK_EDGE_COLOR,
                    alpha=MASK_EDGE_ALPHA,
                    linewidth=MASK_EDGE_WIDTH,
                    solid_capstyle="round",
                )
    except ImportError:
        binary = np.where(mask > 0, 1, 0)
        ax.contour(
            binary,
            levels=[0.5],
            colors=[MASK_EDGE_COLOR],
            linewidths=MASK_EDGE_WIDTH,
            alpha=MASK_EDGE_ALPHA,
        )

    if show_labels:
        for region in np.unique(mask):
            if region == 0:
                continue
            region_mask = mask == region
            cy, cx = center_of_mass(region_mask)
            ax.text(
                cx, cy, str(int(region)),
                color="white", fontsize=9, fontweight="bold",
                ha="center", va="center",
                bbox=dict(
                    boxstyle="round,pad=0.18",
                    facecolor=(0.08, 0.08, 0.08, 0.82),
                    edgecolor=MASK_EDGE_COLOR,
                    linewidth=0.8,
                ),
            )
