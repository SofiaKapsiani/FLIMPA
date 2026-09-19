"""FRET efficiency from FLIM lifetimes (Spatola Rossi et al., Current Protocols 2022).

E = 1 - tau / tau_fluorophore
where tau is the measured donor lifetime and tau_fluorophore is the donor-only
lifetime in the absence of acceptor (tau_D). Pixels with tau > tau_fluorophore
are assigned E = 0.
"""

from __future__ import annotations

import numpy as np

# Default donor-only lifetime for Rhodamine 6G (ns), used when config is unset.
DEFAULT_TAU_FLUOROPHORE_NS = 4.0


def compute_fret_efficiency(
    tau_ns: np.ndarray,
    tau_fluorophore_ns: float = DEFAULT_TAU_FLUOROPHORE_NS,
) -> np.ndarray:
    """Pixel-wise FRET efficiency from lifetime map (values in ns).

    Parameters
    ----------
    tau_ns
        Measured fluorescence lifetimes per pixel (nanoseconds).
    tau_fluorophore_ns
        Donor-only reference lifetime tau_D (nanoseconds). Default 4 ns (Rhod6G).

    Returns
    -------
    np.ndarray
        FRET efficiency E in [0, 1]; invalid/zero-lifetime pixels are NaN.
    """
    tau_fluorophore_ns = float(tau_fluorophore_ns)
    if tau_fluorophore_ns <= 0:
        raise ValueError("tau_fluorophore_ns must be positive")

    tau = np.asarray(tau_ns, dtype=np.float64)
    valid = tau > 0
    e = np.full_like(tau, np.nan, dtype=np.float64)
    e[valid] = 1.0 - tau[valid] / tau_fluorophore_ns
    e[valid & (tau > tau_fluorophore_ns)] = 0.0
    e[valid] = np.clip(e[valid], 0.0, 1.0)
    return e
