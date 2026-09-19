"""
Manual region drawing on the intensity / lifetime image.

Tools: polygon, rectangle, lasso, brush, delete_region, auto-segmentation (via run_auto_segmentation).
Labelled uint16 mask: 0 = background, 1..N = regions.

See README.md (Masking) for user-facing documentation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath
from matplotlib.patches import Circle
from matplotlib.widgets import LassoSelector, PolygonSelector, RectangleSelector

from utils.mask_io import apply_mask_to_sample, save_mask_tif
from utils.mask_viz import SELECT_COLOR, SELECT_FILL, MASK_FILL_CMAP, MASK_FILL_ALPHA, fit_region_to_shape
from utils.shared_data import SharedData


def _region_from_polygon(verts, shape):
    ny, nx = shape
    x, y = np.meshgrid(np.arange(nx), np.arange(ny))
    points = np.vstack((x.ravel(), y.ravel())).T
    inside = MplPath(verts).contains_points(points)
    return inside.reshape(ny, nx)


def _region_from_rect(extents, shape):
    x0, x1, y0, y1 = extents
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    ny, nx = shape
    mask = np.zeros(shape, dtype=bool)
    yi0 = max(0, int(np.floor(y0)))
    yi1 = min(ny, int(np.ceil(y1)))
    xi0 = max(0, int(np.floor(x0)))
    xi1 = min(nx, int(np.ceil(x1)))
    mask[yi0:yi1, xi0:xi1] = True
    return mask


def _region_from_lasso(verts, shape):
    return _region_from_polygon(verts, shape)


def _disk_indices(y: float, x: float, radius: int, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Pixel indices inside a brush disk."""
    ny, nx = shape
    r = max(1, int(radius))
    yi = int(round(y))
    xi = int(round(x))
    y0, y1 = max(0, yi - r), min(ny, yi + r + 1)
    x0, x1 = max(0, xi - r), min(nx, xi + r + 1)
    if y0 >= y1 or x0 >= x1:
        return np.array([], dtype=int), np.array([], dtype=int)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    dist2 = (yy - yi) ** 2 + (xx - xi) ** 2
    inside = dist2 <= r * r
    return yy[inside], xx[inside]


class ManualMaskEditor:
    """
    Draw and edit labelled masks on the active matplotlib axes.

    Coordinates with plot_imgs (set_axes, load_mask_for_current_file) and
    apply_mask_to_sample for persistence and analysis.
    """

    def __init__(self, main_window):
        self.main_window = main_window
        self.shared_info = SharedData()
        self.mask = None
        self.n_regions = 0
        self._selector = None
        self._ax = None
        self._tool = None
        self._preserve_tool = False
        self.antimask_mode = False
        self.brush_width = 5
        # Matplotlib canvas connection ids for brush tool (disconnected when switching tools)
        self._event_cids: list[int] = []
        self._brushing = False
        self._stroke_region: int | None = None  # label used for current brush stroke
        self._stroke_dirty = False
        self._inspect_xy: tuple[float, float] | None = None
        self._inspect_marker = None
        self._brush_cursor: Circle | None = None
        self._brush_preview_im = None

    def _selected_filename(self):
        return self.shared_info.config.get("selected_file")

    def _image_shape(self):
        filename = self._selected_filename()
        if not filename or filename not in self.shared_info.raw_data_dict:
            return None
        return self.shared_info.raw_data_dict[filename]["data"].shape[1:]

    def _display_shape(self):
        """Shape of the image currently shown on the active axes."""
        if self._ax is not None and self._ax.images:
            arr = self._ax.images[0].get_array()
            if arr is not None and getattr(arr, "ndim", 0) == 2:
                return arr.shape
        return self._image_shape()

    def _intensity_for_segmentation(self) -> np.ndarray | None:
        """Integrated intensity (sum over time) used by auto-segmentation algorithms."""
        filename = self._selected_filename()
        if not filename:
            return None
        entry = self.shared_info.intensity_img_dict.get(filename)
        if entry is not None:
            return np.asarray(entry["intensity_image"], dtype=np.float64)
        raw = self.shared_info.raw_data_dict.get(filename, {}).get("data")
        if raw is None:
            return None
        return np.asarray(raw, dtype=np.float64).sum(axis=0)

    def load_mask_for_current_file(self):
        shape = self._image_shape()
        if shape is None:
            self.mask = None
            self.n_regions = 0
            return
        filename = self._selected_filename()
        existing = self.shared_info.raw_data_dict.get(filename, {}).get("mask_arr")
        if existing is not None and np.asarray(existing).shape == shape:
            self.mask = np.asarray(existing, dtype=np.uint16).copy()
            self.n_regions = int(self.mask.max()) if self.mask.max() > 0 else 0
        else:
            self.mask = np.zeros(shape, dtype=np.uint16)
            self.n_regions = 0

    def set_axes(self, ax):
        self._ax = ax

    def set_brush_width(self, width: int):
        self.brush_width = max(1, min(30, int(width)))
        if self._brush_cursor is not None:
            self._brush_cursor.set_radius(self.brush_width)

    def _remove_brush_cursor(self):
        if self._brush_cursor is not None:
            try:
                self._brush_cursor.remove()
            except Exception:
                pass
            self._brush_cursor = None

    def _remove_brush_preview(self):
        if self._brush_preview_im is not None:
            try:
                self._brush_preview_im.remove()
            except Exception:
                pass
            self._brush_preview_im = None

    def _clear_brush_graphics(self):
        self._remove_brush_cursor()
        self._remove_brush_preview()

    def _update_brush_cursor(self, x: float | None = None, y: float | None = None, visible: bool = True):
        if self._ax is None:
            return
        if self._brush_cursor is None:
            self._brush_cursor = Circle(
                (0, 0),
                radius=self.brush_width,
                fill=True,
                facecolor=SELECT_FILL,
                edgecolor=SELECT_COLOR,
                linewidth=1.5,
                linestyle="-",
                alpha=0.95,
                zorder=25,
            )
            self._ax.add_patch(self._brush_cursor)
        if visible and x is not None and y is not None:
            self._brush_cursor.set_center((x, y))
            self._brush_cursor.set_radius(self.brush_width)
            self._brush_cursor.set_visible(True)
        else:
            self._brush_cursor.set_visible(False)

    def _ensure_brush_preview(self):
        if self._brush_preview_im is not None or self._ax is None or self.mask is None:
            return
        from matplotlib import colormaps

        shape = self.mask.shape
        empty = np.ma.masked_all(shape)
        self._brush_preview_im = self._ax.imshow(
            empty,
            cmap=colormaps[MASK_FILL_CMAP],
            alpha=MASK_FILL_ALPHA,
            vmin=0,
            vmax=1,
            interpolation="nearest",
            zorder=18,
        )

    def _update_brush_preview(self):
        if self.mask is None or self._ax is None:
            return
        self._ensure_brush_preview()
        if self._brush_preview_im is None:
            return
        if self.mask.max() == 0:
            self._brush_preview_im.set_visible(False)
            return
        filled = np.ma.masked_where(self.mask == 0, self.mask.astype(float))
        self._brush_preview_im.set_data(filled)
        self._brush_preview_im.set_clim(0, max(float(self.mask.max()), 1.0))
        self._brush_preview_im.set_visible(True)

    def _disconnect_canvas_tools(self):
        """Remove matplotlib callbacks for brush / inspect tools."""
        if self._ax is not None and self._event_cids:
            canvas = self._ax.figure.canvas
            for cid in self._event_cids:
                try:
                    canvas.mpl_disconnect(cid)
                except Exception:
                    pass
        self._event_cids = []
        self._brushing = False
        self._stroke_region = None
        self._stroke_dirty = False
        self._clear_brush_graphics()

    def _disconnect_brush(self):
        self._disconnect_canvas_tools()

    def _remove_inspect_marker_artist(self):
        if self._inspect_marker is not None:
            try:
                self._inspect_marker.remove()
            except Exception:
                pass
            self._inspect_marker = None

    def _clear_inspect_marker(self):
        self._remove_inspect_marker_artist()
        self._inspect_xy = None

    def _draw_inspect_marker(self):
        if self._inspect_xy is None or self._ax is None:
            return
        self._remove_inspect_marker_artist()
        x, y = self._inspect_xy
        (self._inspect_marker,) = self._ax.plot(
            [x], [y], "+", color="#FFE066", markersize=14, markeredgewidth=2, zorder=20,
        )

    def deactivate(self):
        if self._preserve_tool:
            return
        self._disconnect_canvas_tools()
        self._clear_inspect_marker()
        if self._selector is not None:
            try:
                self._selector.set_active(False)
                self._selector.set_visible(False)
            except Exception:
                pass
            self._selector = None
        self._tool = None
        if self._ax is not None and self._ax.figure.canvas:
            self._ax.figure.canvas.draw_idle()
        self._sync_baseline_check_ui()

    def _sync_baseline_check_ui(self):
        tb = getattr(self.main_window, "toolbar_components", None)
        if tb is not None:
            tb.sync_baseline_check_ui()

    def set_antimask_mode(self, enabled: bool):
        """Antimasking: drawing tools remove mask (delete regions / holes)."""
        self.antimask_mode = bool(enabled)

    def set_erase_mode(self, enabled: bool):
        """Legacy alias for antimask_mode."""
        self.set_antimask_mode(enabled)

    @property
    def erase_mode(self) -> bool:
        return self.antimask_mode

    def _exit_drawing_tool(self):
        """Stop polygon / rectangle / lasso / brush / delete_region. Leave Baseline check (inspect) on."""
        if self._tool is not None and self._tool != "inspect":
            self.deactivate()
        self.antimask_mode = False

    def clear_mask(self):
        # Disconnect selectors while the current axes still exist, then drop the mask.
        self._exit_drawing_tool()
        shape = self._image_shape()
        if shape is None:
            return
        self.mask = np.zeros(shape, dtype=np.uint16)
        self.n_regions = 0
        filename = self._selected_filename()
        if filename and filename in self.shared_info.raw_data_dict:
            self.shared_info.raw_data_dict[filename]["mask_arr"] = None
            self.shared_info.raw_data_dict[filename]["masked_data"] = None
        keep_inspect = self._tool == "inspect"
        self.main_window.plotImages.plot_img(preserve_mask_tool=keep_inspect)
        if self.shared_info.results_dict and filename in self.shared_info.results_dict:
            self.main_window.plotImages.plot_tau_map(preserve_mask_tool=keep_inspect)
            self.main_window.canvas_tau.draw_idle()

    def _apply_region(self, region_bool):
        if self.mask is None or region_bool is None:
            return
        target = self._image_shape()
        region_bool = fit_region_to_shape(region_bool, target)
        if region_bool.shape != self.mask.shape:
            return

        if self.antimask_mode:
            self.mask[region_bool] = 0
            self.n_regions = int(self.mask.max()) if self.mask.max() > 0 else 0
        else:
            self.n_regions += 1
            self.mask[region_bool] = self.n_regions

        self._commit_mask()

    def _commit_mask(self):
        """Push mask to shared_data, refresh plots, and keep the active drawing tool."""
        filename = self._selected_filename()
        if not filename or self.mask is None:
            return
        self._preserve_tool = True
        try:
            apply_mask_to_sample(self.main_window, filename, self.mask, preserve_mask_tool=True)
        finally:
            self._preserve_tool = False

    def set_labelled_mask(self, labelled: np.ndarray):
        """Replace mask with an auto-segmentation or external labelled image."""
        if self.mask is None:
            return
        labelled = fit_region_to_shape(np.asarray(labelled, dtype=np.uint16), self.mask.shape)
        if labelled.shape != self.mask.shape:
            return
        self.mask = labelled.astype(np.uint16)
        self.n_regions = int(self.mask.max()) if self.mask.max() > 0 else 0
        self._commit_mask()

    def run_auto_segmentation(self, algorithm: str, params: dict) -> bool:
        """Run intensity auto-segment; replaces mask. Returns False if no regions found.

        Archived from UI while AUTO_SEGMENT_UI_ENABLED is False — see auto_segmentation.py.
        """
        intensity = self._intensity_for_segmentation()
        if intensity is None:
            return False
        from utils.auto_segmentation import run_segmentation

        labelled = run_segmentation(algorithm, intensity, params)
        self.set_labelled_mask(labelled)
        return labelled.max() > 0

    def _on_region(self, region_bool):
        self._apply_region(region_bool)

    def _on_poly(self, verts):
        shape = self._display_shape()
        if shape is None or len(verts) < 3:
            return
        self._on_region(_region_from_polygon(verts, shape))

    def _on_rect(self, eclick, erelease=None):
        shape = self._display_shape()
        if shape is None:
            return
        if erelease is None and hasattr(eclick, "__len__") and len(eclick) == 4:
            x0, x1, y0, y1 = eclick
        else:
            x0, y0 = eclick.xdata, eclick.ydata
            x1, y1 = erelease.xdata, erelease.ydata
        if None in (x0, y0, x1, y1):
            return
        self._on_region(_region_from_rect((x0, x1, y0, y1), shape))

    def _on_lasso(self, verts):
        shape = self._display_shape()
        if shape is None or len(verts) < 3:
            return
        self._on_region(_region_from_lasso(verts, shape))

    def _event_in_axes(self, event) -> bool:
        return (
            event.inaxes is self._ax
            and event.xdata is not None
            and event.ydata is not None
            and event.button in (1, None)
        )

    def _start_stroke_region(self, x: float, y: float) -> int:
        """Paint: extend existing label under cursor, else allocate a new region id."""
        if self.antimask_mode:
            return 0
        yi = int(round(y))
        xi = int(round(x))
        shape = self.mask.shape
        if 0 <= yi < shape[0] and 0 <= xi < shape[1]:
            existing = int(self.mask[yi, xi])
            if existing > 0:
                return existing
        self.n_regions += 1
        return self.n_regions

    def _paint_at(self, x: float, y: float):
        if self.mask is None:
            return
        yy, xx = _disk_indices(y, x, self.brush_width, self.mask.shape)
        if yy.size == 0:
            return
        value = 0 if self.antimask_mode else (self._stroke_region or 0)
        if value == 0 and self.antimask_mode:
            self.mask[yy, xx] = 0
        elif value > 0:
            self.mask[yy, xx] = value
        self._stroke_dirty = True

    def _on_brush_press(self, event):
        if not self._event_in_axes(event) or event.button != 1:
            return
        self._brushing = True
        self._stroke_region = self._start_stroke_region(event.xdata, event.ydata)
        self._paint_at(event.xdata, event.ydata)

    def _on_brush_motion(self, event):
        if self._tool != "brush":
            return

        in_axes = self._event_in_axes(event)
        if in_axes:
            self._update_brush_cursor(event.xdata, event.ydata, visible=True)
        else:
            self._update_brush_cursor(visible=False)

        if self._brushing and in_axes:
            self._paint_at(event.xdata, event.ydata)
            self._update_brush_preview()

        if self._ax is not None and self._ax.figure.canvas:
            self._ax.figure.canvas.draw_idle()

    def _on_brush_release(self, event):
        if not self._brushing:
            return
        self._brushing = False
        self._stroke_region = None
        self._remove_brush_preview()
        if self._stroke_dirty:
            self._stroke_dirty = False
            self._commit_mask()
        elif self._ax is not None and self._ax.figure.canvas:
            self._ax.figure.canvas.draw_idle()

    def _disable_pan_for_active_plot(self):
        tabs = self.main_window.ui_layout.tabs_widget
        name = tabs.tabText(tabs.currentIndex())
        if name == "Lifetime maps":
            canvas = self.main_window.canvas_tau
        else:
            canvas = self.main_window.canvas
        for pan in getattr(self.main_window, "plot_pan_controllers", []):
            if pan.canvas is canvas:
                pan.disable_pan_mode()

    def _on_inspect_press(self, event):
        if not self._event_in_axes(event) or event.button != 1:
            return
        for pan in getattr(self.main_window, "plot_pan_controllers", []):
            if pan.canvas is self._ax.figure.canvas and pan.blocks_inspect_click:
                return
        self._inspect_xy = (event.xdata, event.ydata)
        self._draw_inspect_marker()
        shape = self._display_shape()
        self.main_window.decay_window.show_pixel(event.xdata, event.ydata, shape)
        self._ax.figure.canvas.draw_idle()

    def _setup_inspect(self):
        self._disconnect_canvas_tools()
        if self._ax is None:
            return
        canvas = self._ax.figure.canvas
        self._event_cids = [canvas.mpl_connect("button_press_event", self._on_inspect_press)]
        if self._inspect_xy is not None:
            self._draw_inspect_marker()

    def _on_delete_region_press(self, event):
        """Click a labelled pixel to zero every pixel with that region id."""
        if not self._event_in_axes(event) or event.button != 1 or self.mask is None:
            return
        yi = int(round(event.ydata))
        xi = int(round(event.xdata))
        shape = self.mask.shape
        if not (0 <= yi < shape[0] and 0 <= xi < shape[1]):
            return
        label = int(self.mask[yi, xi])
        if label <= 0:
            return
        self.mask[self.mask == label] = 0
        self.n_regions = int(self.mask.max()) if self.mask.max() > 0 else 0
        self._commit_mask()

    def _setup_delete_region(self):
        self._disconnect_canvas_tools()
        if self._ax is None:
            return
        canvas = self._ax.figure.canvas
        self._event_cids = [canvas.mpl_connect("button_press_event", self._on_delete_region_press)]

    def _setup_brush(self):
        self._disconnect_canvas_tools()
        if self._ax is None:
            return
        self._update_brush_cursor(visible=False)
        canvas = self._ax.figure.canvas
        self._event_cids = [
            canvas.mpl_connect("button_press_event", self._on_brush_press),
            canvas.mpl_connect("motion_notify_event", self._on_brush_motion),
            canvas.mpl_connect("button_release_event", self._on_brush_release),
        ]

    def _prepare_axes_for_tool(self):
        """Refresh the active image tab so drawing targets the visible canvas."""
        tabs = self.main_window.ui_layout.tabs_widget
        name = tabs.tabText(tabs.currentIndex())
        plots = self.main_window.plotImages
        self._preserve_tool = True
        try:
            if name == "Lifetime maps" and self.shared_info.results_dict:
                plots.plot_tau_map(preserve_mask_tool=True)
                self.main_window.canvas_tau.draw_idle()
            elif filename := self._selected_filename():
                if filename in self.shared_info.intensity_img_dict:
                    plots.plot_img(preserve_mask_tool=True)
                    self.main_window.canvas.draw_idle()
        finally:
            self._preserve_tool = False

    def activate_tool(self, tool: str):
        """tool: 'poly', 'rect', 'lasso', 'brush', 'delete_region', or 'inspect'."""
        if not self._selected_filename():
            return
        self._disable_pan_for_active_plot()
        self._tool = tool
        self._prepare_axes_for_tool()
        if self._ax is None or not self._ax.figure.canvas:
            return

        if self._selector is not None:
            try:
                self._selector.set_active(False)
                self._selector.set_visible(False)
            except Exception:
                pass
            self._selector = None

        if tool == "inspect":
            self._disconnect_canvas_tools()
            self.main_window.decay_window.show_and_raise()
            self._setup_inspect()
            self._ax.figure.canvas.draw_idle()
            self._sync_baseline_check_ui()
            return

        if tool == "brush":
            self._setup_brush()
            self._ax.figure.canvas.draw_idle()
            self._sync_baseline_check_ui()
            return

        if tool == "delete_region":
            self._setup_delete_region()
            self._ax.figure.canvas.draw_idle()
            self._sync_baseline_check_ui()
            return

        self._disconnect_canvas_tools()

        # RectangleSelector uses Patch props; PolygonSelector uses Line2D props
        patch_props = {
            "facecolor": SELECT_FILL,
            "edgecolor": SELECT_COLOR,
            "alpha": 1.0,
            "linewidth": 2.5,
        }
        patch_handle_props = {
            "markerfacecolor": SELECT_COLOR,
            "markeredgecolor": "white",
            "markersize": 9,
            "markeredgewidth": 1.2,
        }
        poly_line_props = {
            "color": SELECT_COLOR,
            "linewidth": 2.5,
            "alpha": 1.0,
            "linestyle": "-",
            "zorder": 12,
        }
        poly_handle_props = {
            "marker": "o",
            "markersize": 10,
            "markerfacecolor": SELECT_COLOR,
            "markeredgecolor": "white",
            "markeredgewidth": 2,
            "alpha": 1.0,
            "zorder": 13,
        }

        if tool == "poly":
            self._selector = PolygonSelector(
                self._ax,
                self._on_poly,
                useblit=False,
                props=poly_line_props,
                handle_props=poly_handle_props,
            )
        elif tool == "rect":
            self._selector = RectangleSelector(
                self._ax,
                self._on_rect,
                useblit=False,
                interactive=True,
                props=patch_props,
                handle_props=patch_handle_props,
            )
        elif tool == "lasso":
            self._selector = LassoSelector(
                self._ax,
                self._on_lasso,
                useblit=False,
                props={"color": SELECT_COLOR, "linewidth": 2.5},
            )
        if self._selector is not None:
            self._selector.set_active(True)
        self._ax.figure.canvas.draw_idle()
        self._sync_baseline_check_ui()

    def save_to_path(self, path: str | Path) -> str | None:
        filename = self._selected_filename()
        if not filename or self.mask is None or self.mask.max() == 0:
            return None
        from utils.mask_io import ensure_tif_path

        path = ensure_tif_path(path)
        save_mask_tif(path, self.mask)
        apply_mask_to_sample(self.main_window, filename, self.mask)
        return str(path)
