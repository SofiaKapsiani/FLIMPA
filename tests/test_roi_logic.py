"""Phasor ellipse ROI → lifetime-map mask (logic only, no plots)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from utils.helper_functions import Helpers
from utils.shared_data import SharedData


def ellipse_mask(g, s, x0, y0, a, b):
    """Same membership test as phasor_plot.onselect."""
    return ((g - x0) ** 2 / a**2) + ((s - y0) ** 2 / b**2) <= 1


def test_ellipse_mask_selects_center_pixel():
    g = np.array([0.5, 0.9])
    s = np.array([0.3, 0.3])
    inside = ellipse_mask(g, s, x0=0.5, y0=0.3, a=0.2, b=0.2)
    assert inside[0] is np.True_
    assert inside[1] is np.False_


@pytest.fixture
def roi_helpers(qapp):
    window = SimpleNamespace()
    window.plotImages = MagicMock()
    window.canvas_tau = MagicMock()
    h = Helpers(window)
    sd = SharedData()
    tau = np.array([1.0, 2.0, 3.0, 4.0])
    sd.config["selected_file"] = "sample.tif"
    sd.config["lifetime_map"] = "average"
    sd.results_dict = {"sample.tif": {"average": tau}}
    return h, window, sd


def test_update_data_with_roi_builds_masked_array(roi_helpers):
    h, window, _sd = roi_helpers
    inside = np.array([True, True, False, False])
    h.update_data_with_roi(inside)

    window.plotImages.plot_tau_map.assert_called_once()
    masked = window.plotImages.plot_tau_map.call_args.kwargs["masked_image"]
    assert masked.shape == (4,)
    assert masked[0] == 1.0
    assert masked[2] == 0.0


def test_update_data_with_roi_no_op_without_results(qapp):
    window = SimpleNamespace()
    window.plotImages = MagicMock()
    window.canvas_tau = MagicMock()
    h = Helpers(window)
    SharedData().results_dict = {}
    h.update_data_with_roi(np.array([True, False]))
    window.plotImages.plot_tau_map.assert_not_called()
