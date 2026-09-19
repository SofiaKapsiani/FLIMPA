"""Tests for FRET efficiency calculation."""

import numpy as np
import pytest

from utils.fret_calc import DEFAULT_TAU_FLUOROPHORE_NS, compute_fret_efficiency


def test_default_tau_fluorophore_is_rhod6g():
    assert DEFAULT_TAU_FLUOROPHORE_NS == 4.0


def test_fret_efficiency_formula():
    tau_d = 4.0
    tau = np.array([0.0, 2.0, 4.0, 5.0, 8.0])
    e = compute_fret_efficiency(tau, tau_d)
    assert np.isnan(e[0])
    assert e[1] == pytest.approx(0.5)
    assert e[2] == pytest.approx(0.0)
    assert e[3] == pytest.approx(0.0)
    assert e[4] == pytest.approx(0.0)


def test_fret_efficiency_clips_to_unit_interval():
    e = compute_fret_efficiency(np.array([0.1]), 4.0)
    assert 0.0 <= e[0] <= 1.0


def test_fret_efficiency_requires_positive_tau_d():
    with pytest.raises(ValueError):
        compute_fret_efficiency(np.array([2.0]), 0.0)
