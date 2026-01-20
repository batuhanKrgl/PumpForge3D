"""
Unit tests for flow area and blockage calculations.
"""

import pytest
import math
from pumpforge3d_core.analysis.velocity_triangle import (
    calculate_flow_area,
    calculate_obstruction_factor,
    calculate_blockage_factor,
    calculate_meridional_velocity,
    calculate_mean_diameter
)


class TestFlowAreaCalculations:
    """Test flow area calculations."""

    def test_flow_area_basic(self):
        """Test basic annular area calculation."""
        r_hub = 0.03  # m
        r_tip = 0.05  # m

        # A = π(r_tip² - r_hub²)
        expected = math.pi * (0.05**2 - 0.03**2)
        result = calculate_flow_area(r_hub, r_tip)

        assert result == pytest.approx(expected, abs=1e-6)

    def test_flow_area_zero_hub(self):
        """Test flow area with zero hub radius (solid disk)."""
        r_hub = 0.0
        r_tip = 0.1

        # A = π × r_tip²
        expected = math.pi * 0.1**2
        result = calculate_flow_area(r_hub, r_tip)

        assert result == pytest.approx(expected, abs=1e-6)


class TestObstructionFactor:
    """Test blade obstruction factor calculation."""

    def test_obstruction_basic(self):
        """Test basic obstruction calculation."""
        blade_count = 3
        thickness_avg = 0.002  # 2mm in meters
        diameter_mean = 0.08  # 80mm in meters

        # τ = z × t / (π × d_m)
        expected = 3 * 0.002 / (math.pi * 0.08)
        result = calculate_obstruction_factor(blade_count, thickness_avg, diameter_mean)

        assert result == pytest.approx(expected, abs=1e-6)
        assert 0.0 <= result <= 0.5  # Reasonable range

    def test_obstruction_zero_diameter(self):
        """Test with zero diameter (edge case)."""
        result = calculate_obstruction_factor(5, 0.002, 0.0)
        assert result == 0.0  # Should return 0 for invalid diameter

    def test_obstruction_clamping(self):
        """Test that obstruction is clamped to [0, 0.5]."""
        # Very large thickness should be clamped
        blade_count = 10
        thickness_avg = 1.0  # Very large
        diameter_mean = 0.01  # Very small

        result = calculate_obstruction_factor(blade_count, thickness_avg, diameter_mean)
        assert result <= 0.5  # Should be clamped


class TestBlockageFactor:
    """Test blockage factor calculation."""

    def test_blockage_basic(self):
        """Test basic blockage factor calculation."""
        blade_count = 3
        thickness_avg = 0.002
        diameter_mean = 0.08

        # τ = z × t / (π × d_m)
        tau = 3 * 0.002 / (math.pi * 0.08)
        # K = 1 / (1 - τ)
        expected = 1.0 / (1.0 - tau)

        result = calculate_blockage_factor(blade_count, thickness_avg, diameter_mean)

        assert result == pytest.approx(expected, abs=1e-6)
        assert 1.0 <= result <= 1.5  # Typical range

    def test_blockage_no_blades(self):
        """Test with no blades (no blockage)."""
        result = calculate_blockage_factor(0, 0.0, 0.1)

        # K should be 1.0 (no blockage)
        assert result == pytest.approx(1.0, abs=1e-6)

    def test_blockage_clamping(self):
        """Test that blockage is clamped to maximum 1.5."""
        # Very high obstruction should result in clamped K
        blade_count = 20
        thickness_avg = 0.01
        diameter_mean = 0.05

        result = calculate_blockage_factor(blade_count, thickness_avg, diameter_mean)
        assert result <= 1.5  # Should be clamped


class TestMeridionalVelocity:
    """Test meridional velocity calculation."""

    def test_cm_without_blockage(self):
        """Test cm calculation without blockage correction."""
        Q = 0.01  # m³/s
        r_hub = 0.03  # m
        r_tip = 0.05  # m

        # A = π(r_tip² - r_hub²)
        A = math.pi * (0.05**2 - 0.03**2)
        # cm = Q / A
        expected = Q / A

        result = calculate_meridional_velocity(Q, r_hub, r_tip, include_blockage=False)

        assert result == pytest.approx(expected, abs=1e-6)

    def test_cm_with_blockage(self):
        """Test cm calculation with blockage correction."""
        Q = 0.01  # m³/s
        r_hub = 0.03
        r_tip = 0.05
        blade_count = 3
        thickness_avg = 0.002
        diameter_mean = 0.08

        # Calculate expected value
        A_geometric = math.pi * (0.05**2 - 0.03**2)
        tau = 3 * 0.002 / (math.pi * 0.08)
        A_effective = A_geometric * (1.0 - tau)
        expected = Q / A_effective

        result = calculate_meridional_velocity(
            Q, r_hub, r_tip,
            blade_count=blade_count,
            thickness_avg=thickness_avg,
            diameter_mean=diameter_mean,
            include_blockage=True
        )

        assert result == pytest.approx(expected, abs=1e-6)
        assert result > Q / A_geometric  # Blocked cm should be higher

    def test_cm_zero_area(self):
        """Test with zero flow area (edge case)."""
        result = calculate_meridional_velocity(0.01, 0.05, 0.05)  # Same radii
        assert result == 0.0  # Should return 0 for zero area


class TestMeanDiameter:
    """Test mean diameter calculation."""

    def test_mean_diameter_basic(self):
        """Test basic mean diameter calculation."""
        r_hub = 0.03
        r_tip = 0.05

        # d_m = r_hub + r_tip (for mean diameter = average of d_hub and d_tip)
        expected = 2.0 * (r_hub + r_tip) / 2.0

        result = calculate_mean_diameter(r_hub, r_tip)

        assert result == pytest.approx(expected, abs=1e-6)

    def test_mean_diameter_symmetric(self):
        """Test that mean diameter is symmetric."""
        r_hub = 0.02
        r_tip = 0.06

        result1 = calculate_mean_diameter(r_hub, r_tip)
        result2 = calculate_mean_diameter(r_tip, r_hub)

        # Should be same regardless of order (though physically wrong)
        assert result1 == result2
