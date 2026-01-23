"""
Unit tests for conformal mapping module.

Tests cover:
- solve_theta3_array correctness
- Grid generation
- Cumulative theta computation
- Coupled theta0/wrap behavior with anchoring
- Shape and unit consistency
"""

import pytest
import numpy as np
from numpy.testing import assert_allclose, assert_array_equal

from pumpforge3d_core.analysis.conformal_mapping import (
    solve_theta3_array,
    generate_meridional_grid,
    generate_mock_phi_grid,
    generate_phi_grid_from_beta,
    compute_conformal_mapping,
    compute_conformal_mapping_with_state,
    CoupledAngleState,
    ConformalMappingResult,
    normalize_angle_deg,
)


class TestSolveTheta3Array:
    """Tests for the core solver function."""

    def test_basic_scalar_inputs(self):
        """Test with simple scalar inputs."""
        r1 = np.array([1.0])
        r2 = np.array([2.0])
        z1 = np.array([0.0])
        z2 = np.array([1.0])
        phi = np.array([np.radians(45)])

        dtheta = solve_theta3_array(r1, r2, z1, z2, phi)

        assert dtheta.shape == (1,)
        assert dtheta[0] > 0  # Should be positive angle
        assert dtheta[0] < np.pi  # Should be less than 180 degrees

    def test_vectorized_computation(self):
        """Test vectorized computation with multiple segments."""
        n = 10
        r1 = np.full(n, 1.0)
        r2 = np.full(n, 2.0)
        z1 = np.zeros(n)
        z2 = np.ones(n)
        phi = np.radians(np.linspace(10, 80, n))

        dtheta = solve_theta3_array(r1, r2, z1, z2, phi)

        assert dtheta.shape == (n,)
        # All results should be positive
        assert np.all(dtheta > 0)
        # Larger phi should give larger dtheta (generally)
        assert dtheta[-1] > dtheta[0]

    def test_2d_grid_computation(self):
        """Test with 2D grid inputs."""
        n_i, n_j = 5, 3
        r1 = np.full((n_i, n_j), 1.0)
        r2 = np.full((n_i, n_j), 1.5)
        z1 = np.full((n_i, n_j), 0.0)
        z2 = np.full((n_i, n_j), 0.5)
        phi = np.radians(np.full((n_i, n_j), 45.0))

        dtheta = solve_theta3_array(r1, r2, z1, z2, phi)

        assert dtheta.shape == (n_i, n_j)
        # All values should be approximately equal (same inputs)
        assert_allclose(dtheta, dtheta[0, 0], rtol=1e-10)

    def test_degenerate_case_zero_radius_change(self):
        """Test when r1 == r2 (no radial change)."""
        r1 = np.array([1.0])
        r2 = np.array([1.0])
        z1 = np.array([0.0])
        z2 = np.array([1.0])
        phi = np.array([np.radians(30)])

        dtheta = solve_theta3_array(r1, r2, z1, z2, phi)

        # Should still produce a valid result
        assert np.isfinite(dtheta[0])


class TestGenerateMeridionalGrid:
    """Tests for grid generation from curve points."""

    def test_basic_grid_generation(self):
        """Test basic grid generation."""
        n_i = 10
        n_spans = 5

        # Simple hub and tip curves
        hub_points = np.column_stack([
            np.linspace(0, 1, n_i),  # z
            np.full(n_i, 0.5),       # r (constant hub radius)
        ])
        tip_points = np.column_stack([
            np.linspace(0, 1, n_i),  # z
            np.full(n_i, 1.0),       # r (constant tip radius)
        ])

        r_grid, z_grid = generate_meridional_grid(hub_points, tip_points, n_spans)

        assert r_grid.shape == (n_i, n_spans)
        assert z_grid.shape == (n_i, n_spans)

        # Hub should be at r=0.5
        assert_allclose(r_grid[:, 0], 0.5)
        # Tip should be at r=1.0
        assert_allclose(r_grid[:, -1], 1.0)
        # Middle span should be at r=0.75
        assert_allclose(r_grid[:, n_spans // 2], 0.75, rtol=0.1)

    def test_z_coordinates_match_at_boundaries(self):
        """Test that z coordinates match hub/tip at boundaries."""
        n_i = 20
        n_spans = 4

        hub_points = np.column_stack([
            np.linspace(0, 10, n_i),
            np.linspace(1, 2, n_i),
        ])
        tip_points = np.column_stack([
            np.linspace(0, 10, n_i),
            np.linspace(3, 4, n_i),
        ])

        r_grid, z_grid = generate_meridional_grid(hub_points, tip_points, n_spans)

        # Z should be same for all spans (same meridional path)
        for j in range(n_spans):
            assert_allclose(z_grid[:, j], hub_points[:, 0], rtol=1e-10)


class TestGenerateMockPhiGrid:
    """Tests for mock phi grid generation."""

    def test_mock_phi_shape(self):
        """Test mock phi grid has correct shape."""
        n_i, n_j = 50, 6

        phi_grid = generate_mock_phi_grid(n_i, n_j)

        assert phi_grid.shape == (n_i - 1, n_j)

    def test_mock_phi_range(self):
        """Test mock phi values are in expected range."""
        n_i, n_j = 50, 6

        phi_grid = generate_mock_phi_grid(n_i, n_j)
        phi_deg = np.degrees(phi_grid)

        # Should be in range 5-80 degrees
        assert phi_deg.min() >= 4.9
        assert phi_deg.max() <= 80.1

    def test_mock_phi_constant_across_spans(self):
        """Test mock phi is constant across spans."""
        n_i, n_j = 20, 5

        phi_grid = generate_mock_phi_grid(n_i, n_j)

        # All spans should have same phi at each meridional station
        for i in range(n_i - 1):
            assert_allclose(phi_grid[i, :], phi_grid[i, 0])


class TestComputeConformalMapping:
    """Tests for the main conformal mapping computation."""

    @pytest.fixture
    def simple_grid(self):
        """Create a simple test grid."""
        n_i, n_j = 10, 4

        # Create a simple cylindrical grid
        r_vals = np.linspace(0.5, 1.0, n_j)
        z_vals = np.linspace(0, 2, n_i)

        r_grid = np.tile(r_vals, (n_i, 1))
        z_grid = np.tile(z_vals[:, np.newaxis], (1, n_j))

        phi_grid = generate_mock_phi_grid(n_i, n_j)

        return r_grid, z_grid, phi_grid

    def test_dtheta_cumulative_matches_expected_simple_case(self, simple_grid):
        """Test that cumulative theta increases monotonically and wrap equals sum."""
        r_grid, z_grid, phi_grid = simple_grid
        theta0 = np.zeros(r_grid.shape[1])

        result = compute_conformal_mapping(r_grid, z_grid, phi_grid, theta0)

        # Theta should increase monotonically
        for j in range(result.n_j):
            diffs = np.diff(result.theta_grid[:, j])
            assert np.all(diffs >= 0), f"Theta not monotonic at span {j}"

        # Wrap should equal sum of dtheta
        expected_wrap = np.sum(result.dtheta_grid, axis=0)
        assert_allclose(result.wrap_per_span, expected_wrap, rtol=1e-10)

        # Wrap should also equal theta[-1] - theta0
        assert_allclose(
            result.wrap_per_span,
            result.theta_grid[-1, :] - result.theta0,
            rtol=1e-10,
        )

    def test_output_shapes(self, simple_grid):
        """Test all outputs have correct shapes."""
        r_grid, z_grid, phi_grid = simple_grid
        n_i, n_j = r_grid.shape

        result = compute_conformal_mapping(r_grid, z_grid, phi_grid)

        assert result.theta_grid.shape == (n_i, n_j)
        assert result.dtheta_grid.shape == (n_i - 1, n_j)
        assert result.wrap_per_span.shape == (n_j,)
        assert result.xyz_lines.shape == (n_j, n_i, 3)
        assert result.theta0.shape == (n_j,)
        assert result.n_i == n_i
        assert result.n_j == n_j

    def test_xyz_conversion_radius_preserved(self, simple_grid):
        """Test that radius is preserved in Cartesian conversion."""
        r_grid, z_grid, phi_grid = simple_grid

        result = compute_conformal_mapping(r_grid, z_grid, phi_grid)

        # Compute radius from x, y
        for j in range(result.n_j):
            xyz = result.xyz_lines[j]  # (n_i, 3)
            r_computed = np.sqrt(xyz[:, 0]**2 + xyz[:, 1]**2)
            assert_allclose(r_computed, r_grid[:, j], rtol=1e-10)

    def test_xyz_conversion_z_preserved(self, simple_grid):
        """Test that z coordinate is preserved in Cartesian conversion."""
        r_grid, z_grid, phi_grid = simple_grid

        result = compute_conformal_mapping(r_grid, z_grid, phi_grid)

        for j in range(result.n_j):
            xyz = result.xyz_lines[j]
            assert_allclose(xyz[:, 2], z_grid[:, j], rtol=1e-10)

    def test_custom_theta0(self, simple_grid):
        """Test computation with non-zero theta0."""
        r_grid, z_grid, phi_grid = simple_grid
        n_j = r_grid.shape[1]

        theta0_custom = np.radians(np.array([0, 30, 60, 90])[:n_j])

        result = compute_conformal_mapping(r_grid, z_grid, phi_grid, theta0_custom)

        assert_allclose(result.theta_grid[0, :], theta0_custom, rtol=1e-10)
        assert_allclose(result.theta0, theta0_custom, rtol=1e-10)


class TestCoupledAngleState:
    """Tests for coupled theta0/wrap behavior."""

    def test_wrap_scaling_rule(self):
        """Test that wrap scaling works correctly."""
        n_j = 4
        state = CoupledAngleState(n_j=n_j)

        # Set initial values
        state.wrap_raw = np.radians(np.array([100, 110, 120, 130]))
        state.theta0 = np.zeros(n_j)
        state.theta_end_anchor = state.theta0 + state.wrap_raw

        # Edit wrap to double it
        original_wrap = state.wrap_raw.copy()
        for j in range(n_j):
            state.edit_wrap(j, state.wrap_raw[j] * 2)

        # Check scale factors doubled
        assert_allclose(state.wrap_scale, 2.0, rtol=1e-10)

        # Check wrap_current doubled
        assert_allclose(state.wrap_current, original_wrap * 2, rtol=1e-10)

    def test_theta0_wrap_coupling_anchor(self):
        """Test theta0 and wrap coupling via anchor."""
        n_j = 3
        state = CoupledAngleState(n_j=n_j)

        # Set initial values
        state.theta0 = np.radians(np.array([0, 10, 20]))
        state.wrap_raw = np.radians(np.array([100, 110, 120]))
        state.theta_end_anchor = state.theta0 + state.wrap_raw

        initial_theta_end = state.theta_end_anchor.copy()

        # Edit wrap, theta0 should update to keep theta_end constant
        wrap_new = np.radians(150)  # Increase wrap
        state.edit_wrap(1, wrap_new)

        expected_theta0 = initial_theta_end[1] - wrap_new
        assert_allclose(state.theta0[1], expected_theta0, rtol=1e-10)

        # theta_end should still match anchor
        assert_allclose(state.theta_end[1], initial_theta_end[1], rtol=1e-10)

    def test_theta0_edit_keeps_wrap_unchanged(self):
        """Test that editing theta0 keeps wrap unchanged."""
        n_j = 4
        state = CoupledAngleState(n_j=n_j)

        state.wrap_raw = np.radians(np.array([100, 110, 120, 130]))
        state.theta0 = np.zeros(n_j)
        state.wrap_scale = np.ones(n_j)

        original_wrap = state.wrap_current.copy()

        # Edit theta0
        state.edit_theta0(2, np.radians(45))

        # Wrap should be unchanged
        assert_allclose(state.wrap_current, original_wrap, rtol=1e-10)

    def test_scaled_dtheta_application(self):
        """Test that scaled dtheta is computed correctly."""
        n_j = 3
        state = CoupledAngleState(n_j=n_j)
        state.wrap_scale = np.array([1.0, 2.0, 0.5])

        dtheta_raw = np.ones((5, n_j))  # All ones

        dtheta_scaled = state.get_scaled_dtheta(dtheta_raw)

        assert_allclose(dtheta_scaled[:, 0], 1.0)
        assert_allclose(dtheta_scaled[:, 1], 2.0)
        assert_allclose(dtheta_scaled[:, 2], 0.5)


class TestComputeConformalMappingWithState:
    """Tests for computation with coupled state."""

    @pytest.fixture
    def test_setup(self):
        """Create test data."""
        n_i, n_j = 10, 4

        r_vals = np.linspace(0.5, 1.0, n_j)
        z_vals = np.linspace(0, 2, n_i)
        r_grid = np.tile(r_vals, (n_i, 1))
        z_grid = np.tile(z_vals[:, np.newaxis], (1, n_j))
        phi_grid = generate_mock_phi_grid(n_i, n_j)

        state = CoupledAngleState(n_j=n_j)

        return r_grid, z_grid, phi_grid, state

    def test_state_theta0_applied(self, test_setup):
        """Test that state theta0 is used in computation."""
        r_grid, z_grid, phi_grid, state = test_setup

        # Set custom theta0
        state.theta0 = np.radians(np.array([0, 30, 60, 90]))

        result = compute_conformal_mapping_with_state(
            r_grid, z_grid, phi_grid, state
        )

        assert_allclose(result.theta_grid[0, :], state.theta0, rtol=1e-10)

    def test_state_scaling_applied(self, test_setup):
        """Test that state scaling is applied to dtheta."""
        r_grid, z_grid, phi_grid, state = test_setup

        # First compute without scaling
        state.wrap_scale = np.ones(state.n_j)
        result_unscaled = compute_conformal_mapping_with_state(
            r_grid, z_grid, phi_grid, state
        )

        # Now with 2x scaling on span 1
        state.wrap_scale[1] = 2.0
        result_scaled = compute_conformal_mapping_with_state(
            r_grid, z_grid, phi_grid, state
        )

        # Wrap on span 1 should be doubled
        assert_allclose(
            result_scaled.wrap_per_span[1],
            result_unscaled.wrap_per_span[1] * 2,
            rtol=1e-10,
        )


class TestNormalizeAngleDeg:
    """Tests for angle normalization."""

    def test_symmetric_mode(self):
        """Test symmetric mode (-180, 180]."""
        assert normalize_angle_deg(0, "symmetric") == 0
        assert normalize_angle_deg(180, "symmetric") == 180
        assert normalize_angle_deg(-180, "symmetric") == 180
        assert normalize_angle_deg(270, "symmetric") == -90
        assert normalize_angle_deg(-270, "symmetric") == 90
        assert normalize_angle_deg(360, "symmetric") == 0
        assert normalize_angle_deg(720, "symmetric") == 0

    def test_positive_mode(self):
        """Test positive mode [0, 360)."""
        assert normalize_angle_deg(0, "positive") == 0
        assert normalize_angle_deg(180, "positive") == 180
        assert normalize_angle_deg(-90, "positive") == 270
        assert normalize_angle_deg(360, "positive") == 0
        assert normalize_angle_deg(450, "positive") == 90


class TestShapesAndUnits:
    """Tests for shape consistency and unit conversions."""

    def test_result_degree_properties(self):
        """Test that degree conversion properties work correctly."""
        n_i, n_j = 10, 4

        r_grid = np.full((n_i, n_j), 1.0)
        z_grid = np.tile(np.linspace(0, 1, n_i)[:, np.newaxis], (1, n_j))
        phi_grid = generate_mock_phi_grid(n_i, n_j)

        result = compute_conformal_mapping(r_grid, z_grid, phi_grid)

        # Check degree conversion
        assert_allclose(
            result.wrap_per_span_deg,
            np.degrees(result.wrap_per_span),
            rtol=1e-10,
        )
        assert_allclose(
            result.theta0_deg,
            np.degrees(result.theta0),
            rtol=1e-10,
        )

    def test_state_degree_properties(self):
        """Test CoupledAngleState degree properties."""
        n_j = 3
        state = CoupledAngleState(n_j=n_j)
        state.theta0 = np.radians(np.array([10, 20, 30]))
        state.wrap_raw = np.radians(np.array([100, 110, 120]))
        state.wrap_scale = np.ones(n_j)

        assert_allclose(state.theta0_deg, [10, 20, 30], rtol=1e-10)
        assert_allclose(state.wrap_current_deg, [100, 110, 120], rtol=1e-10)


class TestIntegration:
    """Integration tests for full workflow."""

    def test_full_workflow_simple_case(self):
        """Test complete workflow from grid to xyz."""
        # Create simple test geometry
        n_i, n_j = 20, 5

        # Conical hub and tip
        hub_points = np.column_stack([
            np.linspace(0, 10, n_i),  # z
            np.linspace(5, 7, n_i),   # r
        ])
        tip_points = np.column_stack([
            np.linspace(0, 10, n_i),
            np.linspace(10, 12, n_i),
        ])

        # Generate grid
        r_grid, z_grid = generate_meridional_grid(hub_points, tip_points, n_j)

        # Generate mock angles
        phi_grid = generate_mock_phi_grid(n_i, n_j)

        # Initialize state
        state = CoupledAngleState(n_j=n_j)

        # Compute
        result = compute_conformal_mapping_with_state(
            r_grid, z_grid, phi_grid, state
        )

        # Verify basic properties
        assert result.n_i == n_i
        assert result.n_j == n_j
        assert result.xyz_lines.shape == (n_j, n_i, 3)

        # All points should have positive radius
        for j in range(n_j):
            xyz = result.xyz_lines[j]
            r_computed = np.sqrt(xyz[:, 0]**2 + xyz[:, 1]**2)
            assert np.all(r_computed > 0)

        # Update state from result
        state.update_from_result(result)
        assert_allclose(state.wrap_raw, result.wrap_per_span, rtol=1e-10)
