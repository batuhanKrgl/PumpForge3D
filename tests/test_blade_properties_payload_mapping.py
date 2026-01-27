"""Tests for blade properties payload mapping into station fields."""

import math

from pumpforge3d_core.analysis.blade_properties import BladeThicknessMatrix

from core.inducer import Inducer
from apps.PumpForge3D.app.controllers.blade_properties_binder import (
    map_blade_inputs_to_inducer_payload,
)


def test_payload_maps_station_thicknesses():
    inducer = Inducer(
        r_in_hub=0.03,
        r_in_tip=0.05,
        r_out_hub=0.04,
        r_out_tip=0.06,
        omega=120.0,
        c_m_in=5.0,
        c_m_out=4.0,
        alpha_in=math.radians(90.0),
        beta_blade_in=math.radians(30.0),
        beta_blade_out=math.radians(60.0),
        blade_number=3,
        thickness_in=0.002,
        thickness_out=0.002,
        incidence_in=math.radians(0.0),
        blockage_in=1.1,
        blockage_out=1.1,
        slip_out=math.radians(5.0),
    )

    inputs = {
        "blade_number": 6,
        "incidence_deg_hub": 4.0,
        "incidence_deg_tip": 5.0,
        "slip_mode": "Mock",
        "mock_slip_deg_hub": 5.0,
        "mock_slip_deg_tip": 6.0,
        "thickness": BladeThicknessMatrix(hub_inlet=1.0, tip_inlet=2.0, hub_outlet=3.0, tip_outlet=4.0),
    }

    payload = map_blade_inputs_to_inducer_payload(inputs, inducer)
    updated = inducer.update_from_blade_properties(payload)

    assert updated.stations_blade["hub_le"].thickness == 0.001
    assert updated.stations_blade["shroud_le"].thickness == 0.002
    assert updated.stations_blade["hub_te"].thickness == 0.003
    assert updated.stations_blade["shroud_te"].thickness == 0.004
    assert updated.stations_blade["hub_le"].incidence == math.radians(4.0)
    assert updated.stations_blade["shroud_le"].incidence == math.radians(5.0)
    assert updated.stations_blade["hub_te"].slip_angle_mock == math.radians(5.0)
    assert updated.stations_blade["shroud_te"].slip_angle_mock == math.radians(6.0)
