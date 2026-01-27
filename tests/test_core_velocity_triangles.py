"""Tests for GUI-independent velocity triangle models and inducer."""

import math

import pytest

from core.inducer import Inducer
from core.velocity_triangles import InletTriangle, OutletTriangle


def test_velocity_triangles_inlet_basic():
    inlet = InletTriangle(
        r=0.05,
        omega=100.0,
        c_m=2.0,
        alpha=math.radians(90.0),
        blade_number=5,
        blockage=1.10,
        incidence=math.radians(2.0),
        beta_blade=math.radians(25.0),
    )

    assert inlet.u == pytest.approx(5.0)
    assert inlet.pitch == pytest.approx(2.0 * math.pi * 0.05 / 5.0)
    assert inlet.cu == pytest.approx(0.0, abs=1e-6)
    assert inlet.beta == pytest.approx(math.atan2(2.0, 5.0))
    assert inlet.cm_blocked == pytest.approx(2.2)


def test_velocity_triangles_outlet_basic():
    outlet = OutletTriangle(
        r=0.06,
        omega=120.0,
        c_m=2.5,
        beta_blade=math.radians(60.0),
        blade_number=6,
        blockage=1.08,
        slip=math.radians(5.0),
    )

    assert outlet.u == pytest.approx(7.2)
    assert outlet.cu == pytest.approx(5.4494811545)
    assert outlet.cm_blocked == pytest.approx(2.7)
    assert outlet.deviation == pytest.approx(math.radians(5.0))


def test_inducer_serialization_roundtrip():
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
        blade_number=5,
        thickness_in=0.002,
        thickness_out=0.002,
        incidence_in=math.radians(1.0),
        blockage_in=1.1,
        blockage_out=1.08,
        slip_out=math.radians(5.0),
        geometry={"label": "test"},
    )

    payload = inducer.to_dict()
    restored = Inducer.from_dict(payload)

    assert restored.r_in_hub == pytest.approx(inducer.r_in_hub)
    assert restored.r_out_tip == pytest.approx(inducer.r_out_tip)
    assert restored.omega == pytest.approx(inducer.omega)
    assert restored.blade_number == inducer.blade_number
    assert restored.geometry == inducer.geometry


def test_inducer_builds_triangles():
    inducer = Inducer(
        r_in_hub=0.03,
        r_in_tip=0.05,
        r_out_hub=0.04,
        r_out_tip=0.06,
        omega=100.0,
        c_m_in=2.0,
        c_m_out=2.5,
        alpha_in=math.radians(90.0),
        beta_blade_in=math.radians(30.0),
        beta_blade_out=math.radians(60.0),
        blade_number=4,
        thickness_in=0.002,
        thickness_out=0.002,
        incidence_in=math.radians(0.0),
        blockage_in=1.1,
        blockage_out=1.08,
        slip_out=math.radians(5.0),
    )

    inlet = inducer.make_inlet_triangle(inducer.r_in_hub)
    outlet = inducer.make_outlet_triangle(inducer.r_out_hub)

    assert isinstance(inlet, InletTriangle)
    assert isinstance(outlet, OutletTriangle)
    assert inlet.blockage == pytest.approx(1.1)
    assert outlet.blockage == pytest.approx(1.08)
