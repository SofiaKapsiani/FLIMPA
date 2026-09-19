"""Tests for per-pixel decay extraction."""

import numpy as np

from utils.decay_inspector import get_pixel_decay, baseline_t0_ns, pixel_block_edge
from utils.shared_data import SharedData


def test_get_pixel_decay_single_pixel():
    shared = SharedData()
    shared.raw_data_dict.clear()
    t = np.linspace(0, 10e-9, 8, dtype=np.float32)
    data = np.zeros((8, 4, 4), dtype=np.float32)
    data[:, 2, 3] = np.arange(8, dtype=np.float32) + 1

    shared.raw_data_dict["sample"] = {
        "data": data,
        "t_series": t,
        "masked_data": None,
        "condition": "test",
    }
    shared.config["selected_file"] = "sample"
    shared.config["subtract_offset"] = "False"
    shared.config["bins"] = "None"

    decay = get_pixel_decay("sample", 3.0, 2.0, (4, 4))
    assert decay is not None
    assert decay.x == 3 and decay.y == 2
    assert decay.total_photons == int(np.sum(np.arange(1, 9)))
    assert len(decay.t_ns) == 8
    assert decay.counts[0] == 1.0
    assert decay.fit_allowed is False
    assert decay.block_size == 1


def test_get_pixel_decay_fit_allowed_with_baseline():
    shared = SharedData()
    shared.raw_data_dict.clear()
    t = np.linspace(0, 25e-9, 80, dtype=np.float32)
    data = np.zeros((80, 2, 2), dtype=np.float32)
    data[20:, 0, 0] = 2.0

    shared.raw_data_dict["b"] = {"data": data, "t_series": t, "masked_data": None, "condition": "t"}
    shared.config["selected_file"] = "b"
    shared.config["subtract_offset"] = "True"
    shared.config["fraction_offset"] = 3.5
    shared.config["bins"] = "None"

    decay = get_pixel_decay("b", 0.0, 0.0, (2, 2))
    assert decay is not None
    assert decay.baseline_corrected is True
    assert decay.fit_allowed is True
    assert decay.t0_ns == baseline_t0_ns(decay.t_ns, 3.5)


def test_get_pixel_decay_uses_masked_data():
    shared = SharedData()
    shared.raw_data_dict.clear()
    t = np.linspace(0, 10e-9, 4, dtype=np.float32)
    data = np.ones((4, 2, 2), dtype=np.float32)
    masked = np.zeros_like(data)

    shared.raw_data_dict["m"] = {
        "data": data,
        "t_series": t,
        "masked_data": masked,
        "condition": "test",
    }
    shared.config["selected_file"] = "m"
    shared.config["subtract_offset"] = "False"
    shared.config["bins"] = "None"

    decay = get_pixel_decay("m", 0.0, 0.0, (2, 2))
    assert decay is not None
    assert decay.masked_out is True
    assert decay.total_photons == 0


def test_get_pixel_decay_sums_pixel_block():
    shared = SharedData()
    shared.raw_data_dict.clear()
    t = np.linspace(0, 10e-9, 4, dtype=np.float32)
    data = np.ones((4, 5, 5), dtype=np.float32)

    shared.raw_data_dict["blk"] = {
        "data": data,
        "t_series": t,
        "masked_data": None,
        "condition": "test",
    }
    shared.config["selected_file"] = "blk"
    shared.config["subtract_offset"] = "False"
    shared.config["bins"] = "3x3"

    assert pixel_block_edge(shared) == 3
    decay = get_pixel_decay("blk", 2.0, 2.0, (5, 5))
    assert decay is not None
    assert decay.block_size == 3
    # 3×3 neighbourhood of ones → 9 counts per time channel
    assert decay.counts[0] == 9.0
    assert decay.total_photons == 4 * 9
