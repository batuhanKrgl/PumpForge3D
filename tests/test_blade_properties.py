"""
Unit tests for blade properties and slip calculation module.
"""

import pytest
import math
from pumpforge3d_core.analysis.blade_properties import (
    BladeThicknessMatrix,
    BladeProperties,
    calculate_wiesner_slip,
    calculate_gulich_slip,
    calculate_slip,
    calculate_cu_slipped,
    calculate_average_slip
)


class TestBladeThicknessMatrix:
    """Test blade thickness matrix."""

    def test_default_values(self):
        """Test default thickness values."""
        thickness = BladeThicknessMatrix()
        assert thickness.hub_inlet == 2.0
        assert thickness.hub_outlet == 1.5
        assert thickness.tip_inlet == 2.0
        assert thickness.tip_outlet == 1.5

    def test_average_calculations(self):
        """Test average thickness calculations."""
        thickness = BladeThicknessMatrix(
            hub_inlet=2.0,
            hub_outlet=1.5,
            tip_inlet=3.0,
            tip_outlet=2.5
        )
        assert thickness.get_average_inlet() == 2.5
        assert thickness.get_average_outlet() == 2.0


class TestWiesnerSlip:
    """Test Wiesner slip calculation."""

    def test_basic_calculation(self):
        """Test basic Wiesner slip formula."""
        result = calculate_wiesner_slip(beta_blade_deg=60.0, blade_count=5)

        # Expected: γ = 1 - √(sin 60°) / 5^0.7
        # sin(60°) ≈ 0.866, √0.866 ≈ 0.931
        # 5^0.7 ≈ 3.62
        # γ ≈ 1 - 0.931/3.62 ≈ 1 - 0.257 ≈ 0.743

        assert result.method == "Wiesner"
        assert 0.7 < result.gamma < 0.8
        assert result.f_i == 1.0
        assert result.k_w == 1.0

    def test_invalid_blade_count(self):
        """Test with invalid blade count."""
        result = calculate_wiesner_slip(beta_blade_deg=60.0, blade_count=0)
        assert result.gamma == 1.0
        assert result.warning is not None

    def test_slip_angle_derivation(self):
        """Test slip angle derivation from gamma."""
        result = calculate_wiesner_slip(beta_blade_deg=60.0, blade_count=5)

        # Slip angle should be positive and reasonable
        assert 0 < result.slip_angle_deg < 30.0


class TestGulichSlip:
    """Test Gülich slip calculation."""

    def test_radial_impeller_no_diameters(self):
        """Test Gülich slip for radial impeller without diameter data."""
        result = calculate_gulich_slip(beta_blade_deg=60.0, blade_count=5)

        assert result.method == "Gülich"
        # f_i should be 0.98 for radial (no r_q provided)
        assert result.f_i == 0.98
        # k_w should be 1.0 (no diameters provided)
        assert result.k_w == 1.0
        assert result.warning is not None  # Should warn about missing diameters

    def test_mixed_flow_correction(self):
        """Test Gülich slip with mixed-flow correction."""
        result = calculate_gulich_slip(
            beta_blade_deg=60.0,
            blade_count=5,
            r_q=100.0  # High specific speed → mixed-flow
        )

        # f_i = max(0.98, 1.02 + 1.2e-3 * (100 - 50))
        #     = max(0.98, 1.02 + 0.06) = max(0.98, 1.08) = 1.08
        assert result.f_i == pytest.approx(1.08, abs=0.001)

    def test_with_diameters_kw_calculation(self):
        """Test Gülich slip with diameter data for k_w calculation."""
        result = calculate_gulich_slip(
            beta_blade_deg=60.0,
            blade_count=5,
            d_inlet_hub_mm=60.0,
            d_inlet_shroud_mm=100.0,
            d_outlet_mm=120.0
        )

        assert result.method == "Gülich"
        # k_w should be calculated (not necessarily 1.0)
        assert 0.0 <= result.k_w <= 1.0


class TestSlipDispatcher:
    """Test slip calculation dispatcher."""

    def test_mock_mode(self):
        """Test mock slip mode."""
        result = calculate_slip(
            beta_blade_deg=60.0,
            blade_count=5,
            slip_mode="Mock",
            mock_slip_deg=7.5
        )

        assert result.method == "Mock"
        assert result.slip_angle_deg == 7.5
        # γ ≈ 1 - 7.5/60 = 1 - 0.125 = 0.875
        assert result.gamma == pytest.approx(0.875, abs=0.001)

    def test_wiesner_mode(self):
        """Test Wiesner slip mode."""
        result = calculate_slip(
            beta_blade_deg=60.0,
            blade_count=5,
            slip_mode="Wiesner"
        )

        assert result.method == "Wiesner"

    def test_gulich_mode(self):
        """Test Gülich slip mode."""
        result = calculate_slip(
            beta_blade_deg=60.0,
            blade_count=5,
            slip_mode="Gülich"
        )

        assert result.method == "Gülich"


class TestCuSlipped:
    """Test cu slipped calculation."""

    def test_cu_slipped_calculation(self):
        """Test cu2 calculation with slip."""
        u2 = 30.0  # m/s
        cu2_inf = 25.0  # m/s (theoretical)
        gamma = 0.9  # slip coefficient

        # cu2 = cu2∞ - (1 - γ) * u2
        #     = 25.0 - (1 - 0.9) * 30.0
        #     = 25.0 - 0.1 * 30.0
        #     = 25.0 - 3.0
        #     = 22.0
        cu2 = calculate_cu_slipped(u2, cu2_inf, gamma)
        assert cu2 == pytest.approx(22.0, abs=0.001)

    def test_no_slip(self):
        """Test with gamma = 1.0 (no slip)."""
        u2 = 30.0
        cu2_inf = 25.0
        gamma = 1.0

        cu2 = calculate_cu_slipped(u2, cu2_inf, gamma)
        # cu2 should equal cu2_inf when no slip
        assert cu2 == pytest.approx(cu2_inf, abs=0.001)


class TestAverageSlip:
    """Test average slip calculation."""

    def test_average_slip_calculation(self):
        """Test averaging hub and tip slip coefficients."""
        slip_hub = calculate_wiesner_slip(beta_blade_deg=55.0, blade_count=5)
        slip_tip = calculate_wiesner_slip(beta_blade_deg=60.0, blade_count=5)

        slip_avg = calculate_average_slip(slip_hub, slip_tip)

        # Gamma should be average
        expected_gamma = (slip_hub.gamma + slip_tip.gamma) / 2.0
        assert slip_avg.gamma == pytest.approx(expected_gamma, abs=0.001)

        # Slip angle should be average
        expected_slip_angle = (slip_hub.slip_angle_deg + slip_tip.slip_angle_deg) / 2.0
        assert slip_avg.slip_angle_deg == pytest.approx(expected_slip_angle, abs=0.001)

    def test_average_preserves_method(self):
        """Test that averaging preserves the calculation method."""
        slip_hub = calculate_gulich_slip(beta_blade_deg=55.0, blade_count=5)
        slip_tip = calculate_gulich_slip(beta_blade_deg=60.0, blade_count=5)

        slip_avg = calculate_average_slip(slip_hub, slip_tip)

        assert slip_avg.method == slip_hub.method


class TestBladeProperties:
    """Test blade properties data model."""

    def test_default_properties(self):
        """Test default blade properties."""
        props = BladeProperties(thickness=BladeThicknessMatrix())

        assert props.blade_count == 3
        assert props.incidence_deg == 0.0
        assert props.slip_mode == "Mock"
        assert props.mock_slip_deg == 5.0

    def test_custom_properties(self):
        """Test custom blade properties."""
        thickness = BladeThicknessMatrix(
            hub_inlet=2.5,
            hub_outlet=2.0,
            tip_inlet=3.0,
            tip_outlet=2.5
        )

        props = BladeProperties(
            thickness=thickness,
            blade_count=5,
            incidence_deg=2.5,
            slip_mode="Gülich",
            r_q=80.0
        )

        assert props.blade_count == 5
        assert props.incidence_deg == 2.5
        assert props.slip_mode == "Gülich"
        assert props.r_q == 80.0
