"""Tests for Inducer info snapshot pair computations."""

import math

from core.inducer import Inducer, StationBlade, StationFlow, StationGeom


def test_inducer_info_snapshot_pairs():
    inducer = Inducer(
        r_in_hub=0.05,
        r_in_tip=0.07,
        r_out_hub=0.06,
        r_out_tip=0.08,
        omega=100.0,
        c_m_in=2.0,
        c_m_out=3.0,
        alpha_in=math.radians(90.0),
        beta_blade_in=math.radians(30.0),
        beta_blade_out=math.radians(60.0),
        blade_number=5,
        thickness_in=0.002,
        thickness_out=0.003,
        incidence_in=math.radians(2.0),
        blockage_in=1.1,
        blockage_out=1.1,
        slip_out=math.radians(5.0),
        flow_rate=0.01,
        rho=1140.0,
        g=9.80665,
        stations_geom={
            "hub_le": StationGeom(z=0.0, r=0.05),
            "hub_te": StationGeom(z=0.1, r=0.06),
            "shroud_le": StationGeom(z=0.0, r=0.07),
            "shroud_te": StationGeom(z=0.1, r=0.08),
        },
        stations_blade={
            "hub_le": StationBlade(beta_blade=math.radians(30.0), blade_number=5, thickness=0.002, incidence=math.radians(2.0)),
            "hub_te": StationBlade(beta_blade=math.radians(60.0), blade_number=5, thickness=0.003, slip_angle_mock=math.radians(5.0)),
            "shroud_le": StationBlade(beta_blade=math.radians(32.0), blade_number=5, thickness=0.002, incidence=math.radians(2.0)),
            "shroud_te": StationBlade(beta_blade=math.radians(62.0), blade_number=5, thickness=0.003, slip_angle_mock=math.radians(5.0)),
        },
        stations_flow={
            "hub_le": StationFlow(c_m=2.0, omega=100.0, alpha=math.radians(90.0)),
            "hub_te": StationFlow(c_m=3.0, omega=100.0, alpha=None),
            "shroud_le": StationFlow(c_m=2.0, omega=100.0, alpha=math.radians(90.0)),
            "shroud_te": StationFlow(c_m=3.0, omega=100.0, alpha=None),
        },
    )

    snapshot = inducer.build_info_snapshot()
    rows = snapshot["rows"]

    assert set(rows.keys()) >= {"ΔαF", "δ", "i", "H_euler", "Δp_t", "c_r", "c_z"}

    hub_te_idx = 1
    inlet_alpha = rows["αF"][0]
    outlet_alpha = rows["αF"][hub_te_idx]
    assert rows["ΔαF"][hub_te_idx] == outlet_alpha - inlet_alpha

    beta_blade_out = inducer.stations_blade["hub_te"].beta_blade
    beta_out = rows["βF"][hub_te_idx]
    assert rows["δ"][hub_te_idx] == beta_blade_out - beta_out

    beta_blade_in = inducer.stations_blade["hub_le"].beta_blade
    beta_in = rows["βF"][0]
    assert rows["i"][0] == beta_blade_in - beta_in

    h_euler = rows["H_euler"][hub_te_idx]
    dp_bar = rows["Δp_t"][hub_te_idx]
    assert dp_bar == (inducer.rho * inducer.g * h_euler / 1e5)

    assert rows["c_r"][0] is None
    assert rows["c_z"][0] is None
