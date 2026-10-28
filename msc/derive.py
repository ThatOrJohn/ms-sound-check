"""Derived variables."""
from __future__ import annotations

import numpy as np


def salinity_from_specific_conductance(sc_us_cm):
    """Specific conductance (uS/cm at 25 C) -> practical salinity (PSS-78)."""
    import gsw
    sc = np.asarray(sc_us_cm, dtype=float)
    return gsw.SP_from_C(sc / 1000.0, 25.0, 0.0)
