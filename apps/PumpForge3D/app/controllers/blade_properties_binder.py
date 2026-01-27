"""Blade Properties UI binder to Inducer model updates."""

from __future__ import annotations

import math
from typing import Any, Dict

from PySide6.QtCore import QObject, QTimer

from pumpforge3d_core.analysis.blade_properties import (
    BladeThicknessMatrix,
    calculate_slip,
)

from core.inducer import Inducer
from ..state.app_state import AppState


def map_blade_inputs_to_inducer_payload(
    inputs: Dict[str, Any],
    inducer: Inducer,
) -> Dict[str, Any]:
    """Map Blade Properties UI inputs to Inducer fields.

    Thickness values are stored in mm in the BladeThicknessMatrix and converted to meters.
    """
    blade_number = int(inputs["blade_number"])
    incidence_hub_rad = math.radians(inputs["incidence_deg_hub"])
    incidence_tip_rad = math.radians(inputs["incidence_deg_tip"])

    thickness: BladeThicknessMatrix = inputs["thickness"]
    thickness_map = {
        "hub_le": thickness.hub_inlet / 1000.0,
        "hub_te": thickness.hub_outlet / 1000.0,
        "shroud_le": thickness.tip_inlet / 1000.0,
        "shroud_te": thickness.tip_outlet / 1000.0,
    }

    slip_mode = inputs["slip_mode"]
    mock_slip_hub_deg = inputs["mock_slip_deg_hub"]
    mock_slip_tip_deg = inputs["mock_slip_deg_tip"]
    beta_blade_out_deg = math.degrees(inducer.beta_blade_out)
    slip_result = calculate_slip(
        beta_blade_deg=beta_blade_out_deg,
        blade_count=blade_number,
        slip_mode=slip_mode,
        mock_slip_deg=(mock_slip_hub_deg + mock_slip_tip_deg) / 2.0,
        r_q=inputs.get("r_q"),
        d_inlet_hub_mm=inputs.get("d_inlet_hub_mm"),
        d_inlet_shroud_mm=inputs.get("d_inlet_shroud_mm"),
        d_outlet_mm=inputs.get("d_outlet_mm"),
    )
    slip_hub_rad = math.radians(slip_result.slip_angle_deg if slip_mode != "Mock" else mock_slip_hub_deg)
    slip_tip_rad = math.radians(slip_result.slip_angle_deg if slip_mode != "Mock" else mock_slip_tip_deg)

    return {
        "blade_number": blade_number,
        "incidence_hub": incidence_hub_rad,
        "incidence_tip": incidence_tip_rad,
        "slip_angle_mock_hub": slip_hub_rad,
        "slip_angle_mock_tip": slip_tip_rad,
        "thickness": thickness_map,
    }


class BladePropertiesBinder(QObject):
    """Wire Blade Properties UI inputs to AppState/Inducer updates."""

    def __init__(self, blade_properties_widget, app_state: AppState, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._widget = blade_properties_widget
        self._state = app_state
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._apply_update)

    def connect_signals(self) -> None:
        inputs = self._widget.get_blade_inputs_widget()
        thickness = self._widget.get_thickness_widget()

        inputs.inputsCommitted.connect(self._schedule_update)
        thickness.thicknessChanged.connect(self._schedule_update)

        self._schedule_update()

    def _schedule_update(self, *args) -> None:
        self._timer.start()

    def _apply_update(self) -> None:
        inducer = self._state.get_inducer()
        inputs = self._collect_inputs()
        payload = map_blade_inputs_to_inducer_payload(inputs, inducer)
        self._state.apply_blade_properties_payload(payload)

    def refresh_from_state(self, reason: str = "refresh") -> None:
        """Trigger a refresh from the current state without changing inputs."""
        self._state.set_inducer(self._state.get_inducer(), source=reason)

    def _collect_inputs(self) -> Dict[str, Any]:
        blade_inputs = self._widget.get_blade_inputs_widget()
        thickness_widget = self._widget.get_thickness_widget()

        return {
            "blade_number": blade_inputs.get_blade_count(),
            "incidence_deg_hub": blade_inputs.get_incidence_hub(),
            "incidence_deg_tip": blade_inputs.get_incidence_tip(),
            "slip_mode": blade_inputs.get_slip_mode(),
            "mock_slip_deg_hub": blade_inputs.get_mock_slip_hub(),
            "mock_slip_deg_tip": blade_inputs.get_mock_slip_tip(),
            "thickness": thickness_widget.get_thickness(),
        }
