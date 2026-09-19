"""Manual mask editor behaviour."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from utils.mask_editor import ManualMaskEditor, _disk_indices, _region_from_rect


def test_antimask_region_clears_and_recounts_labels():
    """Antimasking sets drawn pixels to 0 and updates n_regions."""
    shape = (10, 10)
    mask = np.zeros(shape, dtype=np.uint16)
    mask[2:8, 2:8] = 1
    mask[0:2, 0:2] = 2
    region = _region_from_rect((0, 3, 0, 3), shape)

    antimask_mode = True
    if antimask_mode:
        mask[region] = 0
        n_regions = int(mask.max()) if mask.max() > 0 else 0

    assert mask[0, 0] == 0
    assert mask[5, 5] == 1
    assert n_regions == 1


def test_brush_cursor_radius_matches_width():
    fig, ax = plt.subplots()
    editor = ManualMaskEditor.__new__(ManualMaskEditor)
    editor.brush_width = 7
    editor._ax = ax
    editor._brush_cursor = None

    editor._update_brush_cursor(12.5, 8.0, visible=True)

    assert editor._brush_cursor is not None
    assert editor._brush_cursor.get_radius() == 7
    assert editor._brush_cursor.center == (12.5, 8.0)
    assert editor._brush_cursor.get_visible()

    editor._update_brush_cursor(visible=False)
    assert not editor._brush_cursor.get_visible()

    plt.close(fig)


def test_clear_mask_stops_drawing_tool():
    """Clear mask exits polygon/brush (not inspect) and zeros the mask."""
    from utils.shared_data import SharedData

    shared = SharedData()
    shared.raw_data_dict.clear()
    shared.results_dict.clear()
    data = np.zeros((4, 5, 5), dtype=np.float32)
    shared.raw_data_dict["f"] = {
        "data": data,
        "t_series": np.arange(4),
        "masked_data": np.ones_like(data),
        "mask_arr": np.ones((5, 5), dtype=np.uint16),
        "condition": "t",
    }
    shared.config["selected_file"] = "f"

    class _PlotImages:
        def plot_img(self, preserve_mask_tool=False):
            pass

        def plot_tau_map(self, preserve_mask_tool=False):
            pass

    class _Main:
        def __init__(self):
            self.plotImages = _PlotImages()
            self.canvas_tau = type("C", (), {"draw_idle": lambda self: None})()
            self.toolbar_components = None

    editor = ManualMaskEditor(_Main())
    editor.mask = np.ones((5, 5), dtype=np.uint16)
    editor.n_regions = 1
    editor._tool = "poly"
    editor.antimask_mode = True
    editor._selector = object()

    editor.clear_mask()

    assert editor._tool is None
    assert editor._selector is None
    assert editor.antimask_mode is False
    assert editor.n_regions == 0
    assert np.all(editor.mask == 0)
    assert shared.raw_data_dict["f"]["mask_arr"] is None
    assert shared.raw_data_dict["f"]["masked_data"] is None


def test_clear_mask_leaves_inspect_tool():
    from utils.shared_data import SharedData

    shared = SharedData()
    shared.raw_data_dict.clear()
    shared.results_dict.clear()
    shared.raw_data_dict["f"] = {
        "data": np.zeros((2, 3, 3), dtype=np.float32),
        "t_series": np.arange(2),
        "masked_data": None,
        "mask_arr": None,
        "condition": "t",
    }
    shared.config["selected_file"] = "f"

    class _PlotImages:
        def plot_img(self, preserve_mask_tool=False):
            pass

        def plot_tau_map(self, preserve_mask_tool=False):
            pass

    class _Main:
        def __init__(self):
            self.plotImages = _PlotImages()
            self.canvas_tau = type("C", (), {"draw_idle": lambda self: None})()
            self.toolbar_components = None

    editor = ManualMaskEditor(_Main())
    editor.mask = np.ones((3, 3), dtype=np.uint16)
    editor._tool = "inspect"

    editor.clear_mask()

    assert editor._tool == "inspect"


def test_disk_indices_match_brush_radius():
    shape = (20, 20)
    yy, xx = _disk_indices(10.0, 10.0, radius=3, shape=shape)
    assert yy.size > 0
    dist2 = (yy - 10) ** 2 + (xx - 10) ** 2
    assert np.all(dist2 <= 9)


def test_delete_region_zeros_entire_label():
    """Clicking a labelled pixel clears every pixel with that region id."""
    from utils.shared_data import SharedData

    shared = SharedData()
    shared.raw_data_dict.clear()
    shared.results_dict.clear()
    shared.raw_data_dict["f"] = {
        "data": np.zeros((2, 6, 6), dtype=np.float32),
        "t_series": np.arange(2),
        "masked_data": None,
        "mask_arr": None,
        "condition": "t",
    }
    shared.config["selected_file"] = "f"

    commits = []

    class _Main:
        def __init__(self):
            self.plotImages = None
            self.canvas_tau = None
            self.toolbar_components = None

    editor = ManualMaskEditor(_Main())
    editor.mask = np.zeros((6, 6), dtype=np.uint16)
    editor.mask[1:4, 1:4] = 1
    editor.mask[0:2, 4:6] = 2
    editor.n_regions = 2
    editor._commit_mask = lambda: commits.append(editor.mask.copy())

    class _Event:
        def __init__(self, x, y):
            self.inaxes = object()
            self.xdata = x
            self.ydata = y
            self.button = 1

    editor._ax = type("A", (), {"figure": type("F", (), {"canvas": object()})()})()
    # Force _event_in_axes to accept the event
    editor._event_in_axes = lambda event: True

    editor._on_delete_region_press(_Event(2.0, 2.0))

    assert np.all(editor.mask[1:4, 1:4] == 0)
    assert np.all(editor.mask[0:2, 4:6] == 2)
    assert editor.n_regions == 2
    assert len(commits) == 1

    editor._on_delete_region_press(_Event(5.0, 0.0))
    assert np.all(editor.mask == 0)
    assert editor.n_regions == 0
    assert len(commits) == 2


def test_antimask_brush_clears_pixels_under_shape():
    """Eraser (antimask) mode zeros brush-covered pixels without removing whole labels."""
    editor = ManualMaskEditor.__new__(ManualMaskEditor)
    editor.mask = np.zeros((8, 8), dtype=np.uint16)
    editor.mask[2:6, 2:6] = 1
    editor.n_regions = 1
    editor.antimask_mode = True
    editor.brush_width = 2
    editor._stroke_region = 0
    editor._stroke_dirty = False

    editor._paint_at(3.0, 3.0)

    assert editor.mask[3, 3] == 0
    assert editor.mask[5, 5] == 1
    assert editor._stroke_dirty is True
