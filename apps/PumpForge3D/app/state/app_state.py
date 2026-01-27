"""GUI app state container."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Dict

from PySide6.QtCore import QObject, Signal

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


class AppState(QObject):
    """Lightweight GUI state container."""

    inducer_changed = Signal(object)
    triangles_changed = Signal(dict)
    validation_failed = Signal(str)
    inducer_info_changed = Signal(dict)

    def __init__(self, inducer: Inducer, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._inducer = inducer

    @classmethod
    def create_default(cls) -> "AppState":
        return cls(inducer=make_default_inducer())

    def get_inducer(self) -> Inducer:
        return self._inducer

    def set_inducer(self, inducer: Inducer, *, source: str = "") -> None:
        self._inducer = inducer
        self.inducer_changed.emit(inducer)
        triangles = self._build_triangles_payload(inducer)
        self.triangles_changed.emit(triangles)
        self.inducer_info_changed.emit(inducer.build_info_snapshot())

    def update_inducer_fields(self, **kwargs) -> None:
        try:
            updated = replace(self._inducer, **kwargs)
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        self.set_inducer(updated, source="update")

    def apply_geometry_payload(self, payload: Dict[str, Dict[str, float]]) -> None:
        updated = self._inducer.update_from_geometry(payload)
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        self.set_inducer(updated, source="geometry")

    def apply_blade_properties_payload(self, payload: Dict[str, object]) -> None:
        updated = self._inducer.update_from_blade_properties(payload)
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        self.set_inducer(updated, source="blade_properties")

    @staticmethod
    def _build_triangles_payload(inducer: Inducer) -> Dict[str, object]:
        inlet_hub, outlet_hub = inducer.build_triangles_pair("hub")
        inlet_shroud, outlet_shroud = inducer.build_triangles_pair("shroud")
        return {
            "inlet_hub": inlet_hub,
            "inlet_tip": inlet_shroud,
            "outlet_hub": outlet_hub,
            "outlet_tip": outlet_shroud,
        }
