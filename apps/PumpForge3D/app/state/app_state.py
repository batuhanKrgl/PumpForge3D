"""GUI app state container."""

from __future__ import annotations

from dataclasses import replace
import logging
import math
from typing import Dict, Iterable

from PySide6.QtCore import QObject, Signal

from core.inducer import Inducer

logger = logging.getLogger(__name__)


def rpm_to_omega(rpm: float) -> float:
    """Convert RPM to angular velocity in radians per second."""
    return rpm * 2.0 * math.pi / 60.0


def make_default_inducer() -> Inducer:
    """Return deterministic defaults for a new inducer model."""
    rpm = 3000.0
    omega = rpm_to_omega(rpm)
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
    triangles_spanwise_changed = Signal(dict)
    beta_distribution_changed = Signal(dict)
    span_count_changed = Signal(int)
    validation_failed = Signal(str)
    inducer_info_changed = Signal(dict)
    numeric_inputs_applied = Signal(dict)

    def __init__(self, inducer: Inducer, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._inducer = inducer
        self._linear_inlet = False
        self._linear_outlet = False
        self._spanwise_triangles: Dict[int, tuple] = inducer.build_spanwise_triangles()

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
        self._recompute_spanwise_triangles()
        self._emit_beta_distribution_changed()

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

    def apply_numeric_inputs(self, payload: Dict[str, float]) -> None:
        working = dict(payload)
        rpm = working.get("rpm")
        if rpm is None and "n" in working:
            rpm = working.get("n")
        if rpm is not None:
            rpm = float(rpm)
            working["omega"] = rpm_to_omega(rpm)

        flow_rate = working.get("flow_rate_m3s")
        if flow_rate is None and "Q" in working:
            flow_rate = working.get("Q")

        alpha_deg = working.get("alpha_in_deg")
        if alpha_deg is None and "alpha1" in working:
            alpha_deg = working.get("alpha1")

        inducer = self._inducer
        omega = float(working.get("omega", inducer.omega))
        alpha_rad = inducer.alpha_in if alpha_deg is None else math.radians(float(alpha_deg))
        flow_rate = inducer.flow_rate if flow_rate is None else float(flow_rate)

        area_in = math.pi * (inducer.r_in_tip ** 2 - inducer.r_in_hub ** 2)
        area_out = math.pi * (inducer.r_out_tip ** 2 - inducer.r_out_hub ** 2)
        c_m_in = flow_rate / area_in if area_in > 0.0 else inducer.c_m_in
        c_m_out = flow_rate / area_out if area_out > 0.0 else inducer.c_m_out

        operating_point = dict(inducer.operating_point)
        if rpm is not None:
            operating_point["rpm"] = rpm

        velocity_triangle_inputs = dict(inducer.velocity_triangle_inputs)
        if alpha_deg is not None:
            velocity_triangle_inputs["alpha_in_deg"] = float(alpha_deg)
        if rpm is not None:
            velocity_triangle_inputs["rpm"] = rpm
        if flow_rate is not None:
            velocity_triangle_inputs["flow_rate_m3s"] = flow_rate

        stations_flow = dict(inducer.stations_flow)
        for key, flow in inducer.stations_flow.items():
            if key.endswith("_le"):
                new_c_m = c_m_in
                new_alpha = alpha_rad
            else:
                new_c_m = c_m_out
                new_alpha = None
            stations_flow[key] = replace(
                flow,
                c_m=new_c_m,
                omega=omega,
                alpha=new_alpha,
            )

        updated = replace(
            inducer,
            omega=omega,
            flow_rate=flow_rate,
            alpha_in=alpha_rad,
            c_m_in=c_m_in,
            c_m_out=c_m_out,
            operating_point=operating_point,
            velocity_triangle_inputs=velocity_triangle_inputs,
            stations_flow=stations_flow,
        )
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        inlet_hub, outlet_hub = updated.build_triangles_pair("hub")
        logger.debug(
            "Applied numeric inputs rpm=%s omega=%.3f inlet_u=%.3f outlet_u=%.3f",
            rpm if rpm is not None else operating_point.get("rpm"),
            omega,
            inlet_hub.u,
            outlet_hub.u,
        )
        self.numeric_inputs_applied.emit(working)
        self.set_inducer(updated, source="numeric_inputs")

    def set_linear_modes(self, *, inlet: bool, outlet: bool) -> None:
        self._linear_inlet = inlet
        self._linear_outlet = outlet
        self._apply_linear_modes()

    def apply_span_settings(self, payload: Dict[str, int]) -> None:
        span_count = int(payload.get("span_count", self._inducer.span_count))
        updated = self._inducer.set_span_count(span_count)
        if self._linear_inlet or self._linear_outlet:
            updated = self._apply_linear_distribution(updated)
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        self.set_inducer(updated, source="span_settings")
        self.span_count_changed.emit(updated.span_count)

    def apply_beta_table_edit(self, payload: Dict[str, object]) -> None:
        span_index = int(payload["index"])
        side = str(payload["side"])
        value_deg = float(payload["value_deg"])
        value_rad = math.radians(value_deg)

        beta_in = list(self._inducer.beta_blade_in_span)
        beta_out = list(self._inducer.beta_blade_out_span)
        if side == "inlet":
            beta_in[span_index] = value_rad
            linear_enabled = self._linear_inlet
        else:
            beta_out[span_index] = value_rad
            linear_enabled = self._linear_outlet

        recompute_all = False
        if linear_enabled:
            if side == "inlet":
                beta_in = Inducer.linear_span_distribution(beta_in[0], beta_in[-1], len(beta_in))
            else:
                beta_out = Inducer.linear_span_distribution(beta_out[0], beta_out[-1], len(beta_out))
            recompute_all = True

        updated = self._inducer.set_beta_blade_distribution(beta_in, beta_out)
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return

        self._inducer = updated
        self.inducer_changed.emit(updated)
        self.triangles_changed.emit(self._build_triangles_payload(updated))
        self.inducer_info_changed.emit(updated.build_info_snapshot())
        if recompute_all:
            self._recompute_spanwise_triangles()
        else:
            self._recompute_spanwise_triangles(indices=[span_index])
        self._emit_beta_distribution_changed()

    def run_calc_current_method(self) -> None:
        inducer = self._inducer
        inlet_hub, outlet_hub = inducer.build_triangles_pair("hub")
        inlet_tip, outlet_tip = inducer.build_triangles_pair("shroud")
        beta_in_hub = inlet_hub.beta_blade_effective
        beta_in_tip = inlet_tip.beta_blade_effective
        beta_out_hub = outlet_hub.beta_blade
        beta_out_tip = outlet_tip.beta_blade

        beta_in = list(inducer.beta_blade_in_span)
        beta_out = list(inducer.beta_blade_out_span)
        beta_in[0] = beta_in_hub
        beta_in[-1] = beta_in_tip
        beta_out[0] = beta_out_hub
        beta_out[-1] = beta_out_tip

        if self._linear_inlet:
            beta_in = Inducer.linear_span_distribution(beta_in_hub, beta_in_tip, inducer.span_count)
        if self._linear_outlet:
            beta_out = Inducer.linear_span_distribution(beta_out_hub, beta_out_tip, inducer.span_count)

        if not self._linear_inlet:
            beta_in = self._fill_intermediate_values(beta_in, beta_in_hub, beta_in_tip)
        if not self._linear_outlet:
            beta_out = self._fill_intermediate_values(beta_out, beta_out_hub, beta_out_tip)

        updated = inducer.set_beta_blade_distribution(beta_in, beta_out)
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        self.set_inducer(updated, source="beta_calc")

    def get_spanwise_triangles(self) -> Dict[int, tuple]:
        return dict(self._spanwise_triangles)

    def get_beta_distribution_deg(self) -> Dict[str, object]:
        return {
            "span_count": self._inducer.span_count,
            "beta_in_deg": [math.degrees(val) for val in self._inducer.beta_blade_in_span],
            "beta_out_deg": [math.degrees(val) for val in self._inducer.beta_blade_out_span],
            "linear_inlet": self._linear_inlet,
            "linear_outlet": self._linear_outlet,
        }

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

    def _apply_linear_distribution(self, inducer: Inducer) -> Inducer:
        beta_in = list(inducer.beta_blade_in_span)
        beta_out = list(inducer.beta_blade_out_span)
        if self._linear_inlet:
            beta_in = Inducer.linear_span_distribution(beta_in[0], beta_in[-1], inducer.span_count)
        if self._linear_outlet:
            beta_out = Inducer.linear_span_distribution(beta_out[0], beta_out[-1], inducer.span_count)
        return inducer.set_beta_blade_distribution(beta_in, beta_out)

    def _apply_linear_modes(self) -> None:
        updated = self._apply_linear_distribution(self._inducer)
        try:
            updated.validate()
        except ValueError as exc:
            self.validation_failed.emit(str(exc))
            return
        self.set_inducer(updated, source="linear_modes")

    @staticmethod
    def _fill_intermediate_values(values: list[float], hub: float, tip: float) -> list[float]:
        if len(values) <= 2:
            return values
        midpoint = (hub + tip) / 2.0
        filled = list(values)
        for idx in range(1, len(values) - 1):
            filled[idx] = midpoint
        return filled

    def _recompute_spanwise_triangles(self, indices: Iterable[int] | None = None) -> None:
        triangles = self._inducer.build_spanwise_triangles(indices)
        for idx, tri in triangles.items():
            self._spanwise_triangles[idx] = tri
        self.triangles_spanwise_changed.emit(
            {"triangles": triangles, "indices": list(triangles.keys()), "span_count": self._inducer.span_count}
        )

    def _emit_beta_distribution_changed(self) -> None:
        payload = self.get_beta_distribution_deg()
        self.beta_distribution_changed.emit(payload)
