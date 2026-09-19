"""Phasor gallery layer cleanup (matplotlib artist removal)."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors

from utils.phasor_plot import PhasorPlot


class _StubMainWindow:
    figure_phasor = plt.figure()
    canvas_phasor = None


class _StubComboBox:
    def __init__(self):
        self._text = "Histogram"
        self._blocked = False
        self.enabled = False

    def setEnabled(self, value):
        self.enabled = value

    def blockSignals(self, block):
        self._blocked = block
        return not block

    def setCurrentText(self, text):
        self._text = text

    def currentText(self):
        return self._text


def _make_phasor_plot():
    stub = _StubMainWindow()
    stub.canvas_phasor = type("C", (), {"draw_idle": lambda self: None, "draw": lambda self: None})()
    plot = PhasorPlot.__new__(PhasorPlot)
    plot.main_window = stub
    plot.figure_phasor = stub.figure_phasor
    plot.canvas_phasor = stub.canvas_phasor
    plot.layer_artists = {}
    plot.shared_info = type(
        "S",
        (),
        {"phasor_settings": {"scatter_type": "histogram", "plot_type": "individual"}},
    )()
    plot.ax = plot.figure_phasor.subplots()
    plot.display_dropdown = _StubComboBox()
    plot.scatter_dropdown = _StubComboBox()
    plot._gallery_scatter_initialized = False
    plot.tau_labels_active = False
    return plot


def test_safe_remove_hist2d_image():
    plot = _make_phasor_plot()
    g = np.random.default_rng(0).random(200)
    s = np.random.default_rng(1).random(200)
    _, _, _, image = plot.ax.hist2d(g, s, bins=8, norm=colors.LogNorm(), alpha=0.75)
    plot.layer_artists["layer"] = image

    plot._clear_layer_artists()

    assert plot.layer_artists == {}
    assert image not in plot.ax.images


def test_discard_layer_artists_after_figure_clear():
    plot = _make_phasor_plot()
    scatter = plot.ax.scatter([0.2], [0.1], s=10)
    plot.layer_artists["a"] = scatter
    plot.figure_phasor.clear()

    plot._discard_layer_artists()

    assert plot.layer_artists == {}
    assert not hasattr(plot, "highlighted_sample")


def test_prepare_phasor_figure_single_axes():
    plot = _make_phasor_plot()
    plot.figure_phasor.clear()
    plot.figure_phasor.add_subplot(111)
    plot.figure_phasor.add_subplot(212)
    assert len(plot.figure_phasor.axes) == 2

    plot._prepare_phasor_figure()
    plot._draw_phasor_base()

    assert len(plot.figure_phasor.axes) == 1
    assert plot.layer_artists == {}


def test_gallery_defaults_scatter_on_first_open():
    plot = _make_phasor_plot()
    plot.shared_info.phasor_settings["scatter_type"] = "histogram"

    plot._prepare_gallery_controls()

    assert plot.shared_info.phasor_settings["scatter_type"] == "scatter"
    assert plot.scatter_dropdown.currentText() == "Scatter"
    assert plot._gallery_scatter_initialized is True

    plot.shared_info.phasor_settings["scatter_type"] = "histogram"
    plot.scatter_dropdown.setCurrentText("Histogram")
    plot._prepare_gallery_controls()

    assert plot.shared_info.phasor_settings["scatter_type"] == "histogram"
    assert plot.scatter_dropdown.currentText() == "Histogram"
