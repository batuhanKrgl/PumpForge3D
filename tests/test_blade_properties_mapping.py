"""Tests for Blade Properties mapping to Inducer fields."""

import math

from pumpforge3d_core.analysis.blade_properties import BladeThicknessMatrix

from core.inducer import Inducer
from apps.PumpForge3D.app.controllers.blade_properties_binder import (
    map_blade_inputs_to_inducer_payload,
)


def test_mapping_updates_inducer_fields():
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
        "blade_number": 7,
        "incidence_deg_hub": 3.0,
        "incidence_deg_tip": 4.0,
        "slip_mode": "Mock",
        "mock_slip_deg_hub": 6.0,
        "mock_slip_deg_tip": 7.0,
        "thickness": BladeThicknessMatrix(hub_inlet=2.0, tip_inlet=3.0, hub_outlet=1.5, tip_outlet=2.5),
    }

    updates = map_blade_inputs_to_inducer_payload(inputs, inducer)

    assert updates["blade_number"] == 7
    assert updates["incidence_hub"] == math.radians(3.0)
    assert updates["incidence_tip"] == math.radians(4.0)
    assert updates["slip_angle_mock_hub"] == math.radians(6.0)
    assert updates["slip_angle_mock_tip"] == math.radians(7.0)
    assert updates["thickness"]["hub_le"] == 2.0 / 1000.0
    assert updates["thickness"]["hub_te"] == 1.5 / 1000.0
    assert updates["thickness"]["shroud_le"] == 3.0 / 1000.0
    assert updates["thickness"]["shroud_te"] == 2.5 / 1000.0
