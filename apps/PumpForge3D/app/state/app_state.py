"""GUI app state container."""

from __future__ import annotations

from dataclasses import dataclass
import math

from core.inducer import Inducer


def make_default_inducer() -> Inducer:
    """Return deterministic defaults for a new inducer model."""
    rpm = 3000.0
    omega = rpm * 2.0 * math.pi / 60.0
    return Inducer(
        r_in_hub=0.03,
        r_in_tip=0.05,
        r_out_hub=0.04,
        r_out_tip=0.06,
        omega=omega,
        c_m_in=5.0,
        c_m_out=4.0,
        alpha_in=math.radians(90.0),
        beta_blade_in=math.radians(30.0),
        beta_blade_out=math.radians(60.0),
        blade_number=3,
        thickness_in=0.002,
        thickness_out=0.002,
        incidence_in=math.radians(0.0),
        blockage_in=1.10,
        blockage_out=1.10,
        slip_out=math.radians(5.0),
        geometry={
            "inlet": {"hub_radius": 0.03, "tip_radius": 0.05},
            "outlet": {"hub_radius": 0.04, "tip_radius": 0.06},
        },
        operating_point={"rpm": rpm},
        blade_parameters={"note": "defaults for GUI preview"},
        velocity_triangle_inputs={"alpha_in_deg": 90.0},
    )


@dataclass
class AppState:
    """Lightweight GUI state container."""

    inducer: Inducer

    @classmethod
    def create_default(cls) -> "AppState":
        return cls(inducer=make_default_inducer())
