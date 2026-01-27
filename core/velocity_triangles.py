"""GUI-independent velocity triangle models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

_EPS = 1e-10


def _safe_tan(angle: float) -> float:
    """Return tan(angle) with a small guard against singularities."""
    tan_val = float(np.tan(angle))
    if abs(tan_val) < _EPS:
        return _EPS if tan_val >= 0 else -_EPS
    return tan_val


def _safe_cu_from_alpha(c_m: float, alpha: float) -> float:
    """Compute cu from alpha with guards for alpha near 90°."""
    if abs(float(np.cos(alpha))) < _EPS:
        return 0.0
    return c_m / _safe_tan(alpha)


@dataclass(frozen=True)
class InletTriangle:
    """Velocity triangle model for an inlet station."""

    r: float
    omega: float
    c_m: float
    alpha: float
    blade_number: int
    blockage: float = 1.0
    incidence: float = 0.0
    beta_blade: float | None = None

    @property
    def u(self) -> float:
        return self.omega * self.r

    @property
    def cu(self) -> float:
        return _safe_cu_from_alpha(self.c_m, self.alpha)

    @property
    def wu(self) -> float:
        return self.u - self.cu

    @property
    def c(self) -> float:
        return float(np.hypot(self.cu, self.c_m))

    @property
    def w(self) -> float:
        return float(np.hypot(self.wu, self.c_m))

    @property
    def beta(self) -> float:
        return float(np.arctan2(self.c_m, self.wu))

    @property
    def cm_blocked(self) -> float:
        return self.c_m * max(self.blockage, _EPS)

    @property
    def beta_blocked(self) -> float:
        return float(np.arctan2(self.cm_blocked, self.wu))

    @property
    def beta_blade_effective(self) -> float:
        if self.beta_blade is None:
            return self.beta_blocked + self.incidence
        return self.beta_blade

    @property
    def pitch(self) -> float:
        if self.blade_number <= 0:
            raise ValueError("blade_number must be > 0 for pitch calculation.")
        return float(2.0 * np.pi * self.r / self.blade_number)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready dictionary of inputs and computed values."""
        return {
            "r": float(self.r),
            "omega": float(self.omega),
            "c_m": float(self.c_m),
            "alpha": float(self.alpha),
            "blade_number": int(self.blade_number),
            "blockage": float(self.blockage),
            "incidence": float(self.incidence),
            "beta_blade": float(self.beta_blade_effective),
            "u": float(self.u),
            "cu": float(self.cu),
            "wu": float(self.wu),
            "c": float(self.c),
            "w": float(self.w),
            "beta": float(self.beta),
            "cm_blocked": float(self.cm_blocked),
            "beta_blocked": float(self.beta_blocked),
            "pitch": float(self.pitch),
        }


@dataclass(frozen=True)
class OutletTriangle:
    """Velocity triangle model for an outlet station."""

    r: float
    omega: float
    c_m: float
    beta_blade: float
    blade_number: int
    blockage: float = 1.0
    slip: float = 0.0
    slip_angle_mock: float | None = None
    slip_factor_gamma: float | None = None

    @property
    def u(self) -> float:
        return self.omega * self.r

    @property
    def beta(self) -> float:
        return self.beta_blade - self.slip

    @property
    def wu(self) -> float:
        return self.c_m / _safe_tan(self.beta)

    @property
    def cu(self) -> float:
        return self.u - self.wu

    @property
    def c(self) -> float:
        return float(np.hypot(self.cu, self.c_m))

    @property
    def w(self) -> float:
        return float(np.hypot(self.wu, self.c_m))

    @property
    def alpha(self) -> float:
        return float(np.arctan2(self.c_m, self.cu))

    @property
    def cm_blocked(self) -> float:
        return self.c_m * max(self.blockage, _EPS)

    @property
    def beta_blocked(self) -> float:
        return float(np.arctan2(self.cm_blocked, self.wu))

    @property
    def deviation(self) -> float:
        return self.beta_blade - self.beta

    @property
    def pitch(self) -> float:
        if self.blade_number <= 0:
            raise ValueError("blade_number must be > 0 for pitch calculation.")
        return float(2.0 * np.pi * self.r / self.blade_number)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready dictionary of inputs and computed values."""
        return {
            "r": float(self.r),
            "omega": float(self.omega),
            "c_m": float(self.c_m),
            "beta": float(self.beta),
            "beta_blade": float(self.beta_blade),
            "blade_number": int(self.blade_number),
            "blockage": float(self.blockage),
            "slip": float(self.slip),
            "slip_angle_mock": float(self.slip_angle_mock) if self.slip_angle_mock is not None else None,
            "slip_factor_gamma": float(self.slip_factor_gamma) if self.slip_factor_gamma is not None else None,
            "deviation": float(self.deviation),
            "u": float(self.u),
            "cu": float(self.cu),
            "wu": float(self.wu),
            "c": float(self.c),
            "w": float(self.w),
            "alpha": float(self.alpha),
            "cm_blocked": float(self.cm_blocked),
            "beta_blocked": float(self.beta_blocked),
            "pitch": float(self.pitch),
            "cu_slipped": float(self.cu),
        }
