"""
Tests for meridional contour model.
"""

import pytest
import numpy as np
from numpy.testing import assert_almost_equal, assert_array_almost_equal

from pumpforge3d_core.geometry.meridional import (
    MainDimensions, MeridionalContour, EdgeCurve, CurveMode,
    _normalized_to_absolute, _absolute_to_normalized
)
from pumpforge3d_core.geometry.bezier import BezierCurve4


class TestMainDimensions:
    """Test MainDimensions class."""
    
    def test_default_values(self):
        dims = MainDimensions()
        assert dims.r_h_in == 20.0
        assert dims.r_t_in == 50.0
        assert dims.L == 80.0
    
    def test_custom_values(self):
        dims = MainDimensions(r_h_in=10, r_t_in=40, r_h_out=15, r_t_out=35, L=100)
        assert dims.r_h_in == 10
        assert dims.L == 100
    
    def test_validation_negative_radius(self):
        with pytest.raises(ValueError):
            MainDimensions(r_h_in=-5)
    
    def test_validation_hub_greater_than_tip(self):
        with pytest.raises(ValueError):
            MainDimensions(r_h_in=60, r_t_in=50)  # Hub > Tip is invalid
    
    def test_validation_zero_length(self):
        with pytest.raises(ValueError):
            MainDimensions(L=0)
    
    def test_endpoint_properties(self):
        dims = MainDimensions(r_h_in=20, r_t_in=50, r_h_out=30, r_t_out=45, L=80)
        
        assert dims.hub_inlet == (0.0, 20.0)
        assert dims.hub_outlet == (80.0, 30.0)
        assert dims.tip_inlet == (0.0, 50.0)
        assert dims.tip_outlet == (80.0, 45.0)
    
    def test_serialization_roundtrip(self):
        dims = MainDimensions(r_h_in=15, r_t_in=45, r_h_out=25, r_t_out=40, L=100)
        data = dims.to_dict()
        restored = MainDimensions.from_dict(data)
        
        assert restored.r_h_in == dims.r_h_in
        assert restored.r_t_in == dims.r_t_in
        assert restored.L == dims.L


class TestCoordinateConversion:
    """Test normalized <-> absolute coordinate conversion."""
    
    @pytest.fixture
    def dims(self):
        return MainDimensions(r_h_in=20, r_t_in=50, r_h_out=30, r_t_out=45, L=80)
    
    def test_hub_normalized_endpoints(self, dims):
        """Normalized (0,0) should map to hub inlet, (1,1) to hub outlet."""
        p00 = _normalized_to_absolute((0, 0), dims, "hub")
        p11 = _normalized_to_absolute((1, 1), dims, "hub")
        
        assert_almost_equal(p00, (0, 20))  # z=0, r=r_h_in
        assert_almost_equal(p11, (80, 30))  # z=L, r=r_h_out
    
    def test_tip_normalized_endpoints(self, dims):
        """Check tip curve endpoints."""
        p00 = _normalized_to_absolute((0, 0), dims, "tip")
        p11 = _normalized_to_absolute((1, 1), dims, "tip")
        
        assert_almost_equal(p00, (0, 50))  # z=0, r=r_t_in
        assert_almost_equal(p11, (80, 45))  # z=L, r=r_t_out
    
    def test_roundtrip_conversion(self, dims):
        """Converting to absolute and back should preserve values."""
        original = (0.5, 0.3)
        absolute = _normalized_to_absolute(original, dims, "hub")
        restored = _absolute_to_normalized(absolute, dims, "hub")
        
        assert_almost_equal(restored, original, decimal=5)


class TestMeridionalContour:
    """Test MeridionalContour class."""
    
    def test_create_from_dimensions(self):
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        # Check hub curve endpoints
        p0 = contour.hub_curve.evaluate(0)
        p1 = contour.hub_curve.evaluate(1)
        assert_almost_equal(p0, dims.hub_inlet)
        assert_almost_equal(p1, dims.hub_outlet)
        
        # Check tip curve endpoints
        p0 = contour.tip_curve.evaluate(0)
        p1 = contour.tip_curve.evaluate(1)
        assert_almost_equal(p0, dims.tip_inlet)
        assert_almost_equal(p1, dims.tip_outlet)
    
    def test_edges_initialized(self):
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        assert contour.leading_edge is not None
        assert contour.trailing_edge is not None
        assert contour.leading_edge.mode == CurveMode.STRAIGHT
    
    def test_update_from_dimensions(self):
        """Contour should update when dimensions change."""
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        # Change dimensions
        new_dims = MainDimensions(r_h_in=25, r_t_in=55, r_h_out=35, r_t_out=50, L=100)
        contour.update_from_dimensions(new_dims)
        
        # Check endpoints updated
        p0 = contour.hub_curve.evaluate(0)
        p1 = contour.hub_curve.evaluate(1)
        assert_almost_equal(p0, new_dims.hub_inlet)
        assert_almost_equal(p1, new_dims.hub_outlet)
    
    def test_area_at_inlet(self):
        """Area at inlet should be π(r_tip² - r_hub²)."""
        dims = MainDimensions(r_h_in=20, r_t_in=50, r_h_out=30, r_t_out=45, L=80)
        contour = MeridionalContour.create_from_dimensions(dims)
        
        area = contour.compute_area_at_z(0)
        expected = np.pi * (50**2 - 20**2)
        assert_almost_equal(area, expected, decimal=0)
    
    def test_area_progression_shape(self):
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        progression = contour.compute_area_progression(n=20)
        assert progression.shape == (20, 2)
        assert progression[0, 0] == 0.0  # Start at z=0
    
    def test_get_all_sample_points(self):
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        samples = contour.get_all_sample_points(n=100)
        
        assert 'hub' in samples
        assert 'tip' in samples
        assert 'leading' in samples
        assert 'trailing' in samples
        
        assert samples['hub'].shape == (100, 2)
    
    def test_serialization_roundtrip(self):
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        data = contour.to_dict()
        restored = MeridionalContour.from_dict(data)
        
        # Check hub curve preserved
        orig_hub = contour.hub_curve.evaluate_many(10)
        rest_hub = restored.hub_curve.evaluate_many(10)
        assert_array_almost_equal(orig_hub, rest_hub)


class TestEdgeCurve:
    """Test EdgeCurve class."""
    
    def test_straight_mode(self):
        from pumpforge3d_core.geometry.bezier import StraightLine
        
        edge = EdgeCurve(
            mode=CurveMode.STRAIGHT,
            straight_line=StraightLine((0, 20), (0, 50)),
            name="leading"
        )
        
        assert_almost_equal(edge.get_hub_point(), (0, 20))
        assert_almost_equal(edge.get_tip_point(), (0, 50))
    
    def test_bezier_mode(self):
        curve = BezierCurve4.create_default((0, 20), (0, 50))
        edge = EdgeCurve(
            mode=CurveMode.BEZIER,
            bezier_curve=curve,
            name="leading"
        )
        
        assert_almost_equal(edge.get_hub_point(), (0, 20))
        assert_almost_equal(edge.get_tip_point(), (0, 50))
