"""GUI-independent inducer information model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict
import math

from .velocity_triangles import InletTriangle, OutletTriangle


@dataclass
class Inducer:
    """Single source of truth for inducer-related inputs and derived helpers."""

    r_in_hub: float
    r_in_tip: float
    r_out_hub: float
    r_out_tip: float
    omega: float
    c_m_in: float
    c_m_out: float
    alpha_in: float
    beta_blade_in: float
    beta_blade_out: float
    blade_number: int
    thickness_in: float
    thickness_out: float
    incidence_in: float
    blockage_in: float
    blockage_out: float
    slip_out: float
    geometry: Dict[str, Any] = field(default_factory=dict)
    operating_point: Dict[str, Any] = field(default_factory=dict)
    blade_parameters: Dict[str, Any] = field(default_factory=dict)
    velocity_triangle_inputs: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate required inputs and raise ValueError on invalid values."""
        self._validate_positive("r_in_hub", self.r_in_hub)
        self._validate_positive("r_in_tip", self.r_in_tip)
        self._validate_positive("r_out_hub", self.r_out_hub)
        self._validate_positive("r_out_tip", self.r_out_tip)
        self._validate_positive("omega", self.omega)
        self._validate_positive("c_m_in", self.c_m_in)
        self._validate_positive("c_m_out", self.c_m_out)
        self._validate_positive("blade_number", float(self.blade_number))
        self._validate_positive("blockage_in", self.blockage_in)
        self._validate_positive("blockage_out", self.blockage_out)
        self._validate_non_negative("thickness_in", self.thickness_in)
        self._validate_non_negative("thickness_out", self.thickness_out)

        for name, value in [
            ("alpha_in", self.alpha_in),
            ("beta_blade_in", self.beta_blade_in),
            ("beta_blade_out", self.beta_blade_out),
            ("incidence_in", self.incidence_in),
            ("slip_out", self.slip_out),
        ]:
            self._validate_finite(name, value)

    def make_inlet_triangle(self, radius: float | None = None) -> InletTriangle:
        """Create an inlet triangle for the requested radius."""
        r = self.r_in_hub if radius is None else radius
        return InletTriangle(
            r=r,
            omega=self.omega,
            c_m=self.c_m_in,
            alpha=self.alpha_in,
            blade_number=self.blade_number,
            blockage=self.blockage_in,
            incidence=self.incidence_in,
            beta_blade=self.beta_blade_in,
        )

    def make_outlet_triangle(self, radius: float | None = None) -> OutletTriangle:
        """Create an outlet triangle for the requested radius."""
        r = self.r_out_hub if radius is None else radius
        return OutletTriangle(
            r=r,
            omega=self.omega,
            c_m=self.c_m_out,
            beta_blade=self.beta_blade_out,
            blade_number=self.blade_number,
            blockage=self.blockage_out,
            slip=self.slip_out,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready dictionary of inputs."""
        return {
            "r_in_hub": float(self.r_in_hub),
            "r_in_tip": float(self.r_in_tip),
            "r_out_hub": float(self.r_out_hub),
            "r_out_tip": float(self.r_out_tip),
            "omega": float(self.omega),
            "c_m_in": float(self.c_m_in),
            "c_m_out": float(self.c_m_out),
            "alpha_in": float(self.alpha_in),
            "beta_blade_in": float(self.beta_blade_in),
            "beta_blade_out": float(self.beta_blade_out),
            "blade_number": int(self.blade_number),
            "thickness_in": float(self.thickness_in),
            "thickness_out": float(self.thickness_out),
            "incidence_in": float(self.incidence_in),
            "blockage_in": float(self.blockage_in),
            "blockage_out": float(self.blockage_out),
            "slip_out": float(self.slip_out),
            "geometry": dict(self.geometry),
            "operating_point": dict(self.operating_point),
            "blade_parameters": dict(self.blade_parameters),
            "velocity_triangle_inputs": dict(self.velocity_triangle_inputs),
            "extras": dict(self.extras),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Inducer":
        """Create an Inducer instance from a dictionary."""
        return cls(
            r_in_hub=float(data["r_in_hub"]),
            r_in_tip=float(data["r_in_tip"]),
            r_out_hub=float(data["r_out_hub"]),
            r_out_tip=float(data["r_out_tip"]),
            omega=float(data["omega"]),
            c_m_in=float(data["c_m_in"]),
            c_m_out=float(data["c_m_out"]),
            alpha_in=float(data["alpha_in"]),
            beta_blade_in=float(data["beta_blade_in"]),
            beta_blade_out=float(data["beta_blade_out"]),
            blade_number=int(data["blade_number"]),
            thickness_in=float(data["thickness_in"]),
            thickness_out=float(data["thickness_out"]),
            incidence_in=float(data["incidence_in"]),
            blockage_in=float(data["blockage_in"]),
            blockage_out=float(data["blockage_out"]),
            slip_out=float(data["slip_out"]),
            geometry=dict(data.get("geometry", {})),
            operating_point=dict(data.get("operating_point", {})),
            blade_parameters=dict(data.get("blade_parameters", {})),
            velocity_triangle_inputs=dict(data.get("velocity_triangle_inputs", {})),
            extras=dict(data.get("extras", {})),
        )

    @staticmethod
    def _validate_positive(name: str, value: float) -> None:
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite value.")

    @staticmethod
    def _validate_non_negative(name: str, value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a non-negative finite value.")

    @staticmethod
    def _validate_finite(name: str, value: float) -> None:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be a finite value.")
