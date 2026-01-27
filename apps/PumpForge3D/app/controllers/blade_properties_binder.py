"""Blade Properties UI binder to Inducer model updates."""

from __future__ import annotations

from dataclasses import replace
import math
from typing import Any, Dict

from PySide6.QtCore import QObject, QTimer

from pumpforge3d_core.analysis.blade_properties import (
    BladeThicknessMatrix,
    calculate_slip,
)

from core.inducer import Inducer
from ..state.app_state import AppState


def map_blade_inputs_to_inducer_kwargs(
    inputs: Dict[str, Any],
    inducer: Inducer,
) -> Dict[str, Any]:
    """Map Blade Properties UI inputs to Inducer fields.

    Thickness values are stored in mm in the BladeThicknessMatrix and converted to meters.
    """
    blade_number = int(inputs["blade_number"])
    incidence_rad = math.radians(inputs["incidence_deg"])

    thickness: BladeThicknessMatrix = inputs["thickness"]
    thickness_in_mm = (thickness.hub_inlet + thickness.tip_inlet) / 2.0
    thickness_out_mm = (thickness.hub_outlet + thickness.tip_outlet) / 2.0

    slip_mode = inputs["slip_mode"]
    mock_slip_deg = inputs["mock_slip_deg"]
    beta_blade_out_deg = math.degrees(inducer.beta_blade_out)
    slip_result = calculate_slip(
        beta_blade_deg=beta_blade_out_deg,
        blade_count=blade_number,
        slip_mode=slip_mode,
        mock_slip_deg=mock_slip_deg,
        r_q=inputs.get("r_q"),
        d_inlet_hub_mm=inputs.get("d_inlet_hub_mm"),
        d_inlet_shroud_mm=inputs.get("d_inlet_shroud_mm"),
        d_outlet_mm=inputs.get("d_outlet_mm"),
    )
    slip_rad = math.radians(slip_result.slip_angle_deg)

    return {
        "blade_number": blade_number,
        "incidence_in": incidence_rad,
        "slip_out": slip_rad,
        "thickness_in": thickness_in_mm / 1000.0,
        "thickness_out": thickness_out_mm / 1000.0,
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

        inputs.bladeCountChanged.connect(self._schedule_update)
        inputs.incidenceChanged.connect(self._schedule_update)
        inputs.slipModeChanged.connect(self._schedule_update)
        inputs.mockSlipChanged.connect(self._schedule_update)
        thickness.thicknessChanged.connect(self._schedule_update)

        self._schedule_update()

    def _schedule_update(self, *args) -> None:
        self._timer.start()

    def _apply_update(self) -> None:
        inducer = self._state.get_inducer()
        inputs = self._collect_inputs()
        updates = map_blade_inputs_to_inducer_kwargs(inputs, inducer)

        try:
            updated = replace(inducer, **updates)
            updated.validate()
        except ValueError as exc:
            self._state.validation_failed.emit(str(exc))
            return

        self._state.set_inducer(updated, source="blade_properties")

    def _collect_inputs(self) -> Dict[str, Any]:
        blade_inputs = self._widget.get_blade_inputs_widget()
        thickness_widget = self._widget.get_thickness_widget()

        return {
            "blade_number": blade_inputs.get_blade_count(),
            "incidence_deg": blade_inputs.get_incidence(),
            "slip_mode": blade_inputs.get_slip_mode(),
            "mock_slip_deg": blade_inputs.get_mock_slip(),
            "thickness": thickness_widget.get_thickness(),
        }
