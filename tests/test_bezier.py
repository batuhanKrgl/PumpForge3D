"""
Tests for Bezier curve implementation.
"""

import pytest
import numpy as np
from numpy.testing import assert_array_almost_equal, assert_almost_equal

from pumpforge3d_core.geometry.bezier import (
    BezierCurve4, BezierCurve2, ControlPoint, StraightLine, _bernstein
)


class TestBernstein:
    """Test Bernstein polynomial computation."""
    
    def test_bernstein_endpoints(self):
        """Bernstein polynomials at t=0 and t=1."""
        # B_{0,4}(0) = 1, all others = 0
        assert _bernstein(4, 0, 0.0) == 1.0
        assert _bernstein(4, 1, 0.0) == 0.0
        assert _bernstein(4, 2, 0.0) == 0.0
        
        # B_{4,4}(1) = 1, all others = 0
        assert _bernstein(4, 4, 1.0) == 1.0
        assert _bernstein(4, 3, 1.0) == 0.0
    
    def test_bernstein_partition_of_unity(self):
        """Sum of all Bernstein polynomials equals 1 for any t."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            total = sum(_bernstein(4, i, t) for i in range(5))
            assert_almost_equal(total, 1.0)


class TestControlPoint:
    """Test ControlPoint class."""
    
    def test_to_tuple(self):
        pt = ControlPoint(z=10.0, r=20.0)
        assert pt.to_tuple() == (10.0, 20.0)
    
    def test_to_array(self):
        pt = ControlPoint(z=10.0, r=20.0)
        arr = pt.to_array()
        assert_array_almost_equal(arr, [10.0, 20.0])
    
    def test_copy(self):
        pt = ControlPoint(z=10.0, r=20.0, is_locked=True)
        copy = pt.copy()
        assert copy.z == pt.z
        assert copy.r == pt.r
        assert copy.is_locked == pt.is_locked
        
        # Modify copy shouldn't affect original
        copy.z = 99.0
        assert pt.z == 10.0


class TestBezierCurve4:
    """Test 4th-order Bezier curve."""
    
    @pytest.fixture
    def simple_curve(self):
        """A simple horizontal line as Bezier."""
        points = [(0, 10), (20, 10), (40, 10), (60, 10), (80, 10)]
        return BezierCurve4.from_points(points, name="test")
    
    @pytest.fixture
    def curved(self):
        """A curve with some vertical variation."""
        points = [(0, 20), (20, 22), (40, 25), (60, 23), (80, 20)]
        return BezierCurve4.from_points(points, name="curved")
    
    def test_from_points_length(self, simple_curve):
        """Curve should have exactly 5 control points."""
        assert len(simple_curve.control_points) == 5
    
    def test_from_points_invalid(self):
        """Should raise error for wrong number of points."""
        with pytest.raises(ValueError):
            BezierCurve4.from_points([(0, 0), (1, 1)])
    
    def test_endpoints_locked(self, simple_curve):
        """Endpoints should be locked by default."""
        assert simple_curve.control_points[0].is_locked
        assert simple_curve.control_points[4].is_locked
        assert not simple_curve.control_points[1].is_locked
        assert not simple_curve.control_points[2].is_locked
        assert not simple_curve.control_points[3].is_locked
    
    def test_evaluate_endpoints(self, simple_curve):
        """Curve should pass through endpoints."""
        p0 = simple_curve.evaluate(0.0)
        p4 = simple_curve.evaluate(1.0)
        
        assert_almost_equal(p0, (0.0, 10.0))
        assert_almost_equal(p4, (80.0, 10.0))
    
    def test_evaluate_midpoint(self, simple_curve):
        """For a straight line, midpoint should be at t=0.5."""
        mid = simple_curve.evaluate(0.5)
        assert_almost_equal(mid[0], 40.0, decimal=5)
        assert_almost_equal(mid[1], 10.0, decimal=5)
    
    def test_evaluate_many(self, simple_curve):
        """evaluate_many should return correct number of points."""
        points = simple_curve.evaluate_many(100)
        assert points.shape == (100, 2)
        
        # First and last should match endpoints
        assert_almost_equal(points[0], [0.0, 10.0])
        assert_almost_equal(points[-1], [80.0, 10.0])
    
    def test_set_point_locked(self, simple_curve):
        """Cannot move locked points."""
        result = simple_curve.set_point(0, 999, 999)
        assert result is False
        assert simple_curve.control_points[0].z == 0.0
    
    def test_set_point_unlocked(self, simple_curve):
        """Can move unlocked points."""
        result = simple_curve.set_point(2, 45.0, 15.0)
        assert result is True
        assert simple_curve.control_points[2].z == 45.0
        assert simple_curve.control_points[2].r == 15.0
    
    def test_curvature_straight_line(self, simple_curve):
        """Curvature of a straight line should be ~0."""
        for t in [0.2, 0.5, 0.8]:
            curv = simple_curve.compute_curvature(t)
            assert abs(curv) < 0.01
    
    def test_curvature_curved(self, curved):
        """Curved section should have non-zero curvature."""
        curv = curved.compute_curvature(0.5)
        assert curv != 0.0
    
    def test_arc_length_straight(self, simple_curve):
        """Arc length of straight line should be distance between endpoints."""
        length = simple_curve.compute_arc_length()
        expected = 80.0  # From z=0 to z=80, r constant
        assert_almost_equal(length, expected, decimal=1)
    
    def test_create_default(self):
        """create_default should create valid intermediate points."""
        curve = BezierCurve4.create_default((0, 10), (100, 50), name="default")
        
        assert len(curve.control_points) == 5
        assert curve.control_points[0].z == 0
        assert curve.control_points[4].z == 100
        
        # Check intermediate points are between endpoints
        for i in [1, 2, 3]:
            pt = curve.control_points[i]
            assert 0 < pt.z < 100
    
    def test_serialization_roundtrip(self, curved):
        """to_dict/from_dict should preserve curve."""
        data = curved.to_dict()
        restored = BezierCurve4.from_dict(data)
        
        assert restored.name == curved.name
        assert len(restored.control_points) == 5
        
        for i in range(5):
            orig = curved.control_points[i]
            rest = restored.control_points[i]
            assert_almost_equal(orig.z, rest.z)
            assert_almost_equal(orig.r, rest.r)


class TestStraightLine:
    """Test StraightLine class."""
    
    def test_evaluate_endpoints(self):
        line = StraightLine((0, 10), (0, 50), "vertical")
        
        assert_almost_equal(line.evaluate(0.0), (0, 10))
        assert_almost_equal(line.evaluate(1.0), (0, 50))
    
    def test_evaluate_midpoint(self):
        line = StraightLine((0, 0), (100, 100))
        mid = line.evaluate(0.5)
        assert_almost_equal(mid, (50, 50))
    
    def test_curvature_always_zero(self):
        line = StraightLine((0, 0), (100, 100))
        for t in [0.0, 0.5, 1.0]:
            assert line.compute_curvature(t) == 0.0
    
    def test_arc_length(self):
        line = StraightLine((0, 0), (3, 4))
        assert_almost_equal(line.compute_arc_length(), 5.0)


class TestBezierCurve2:
    """Test quadratic (2nd-order) Bezier curve."""
    
    @pytest.fixture
    def simple_curve(self):
        """A simple quadratic curve."""
        points = [(0, 10), (40, 15), (80, 10)]
        return BezierCurve2.from_points(points, name="test")
    
    def test_from_points_length(self, simple_curve):
        """Curve should have exactly 3 control points."""
        assert len(simple_curve.control_points) == 3
    
    def test_from_points_invalid(self):
        """Should raise error for wrong number of points."""
        with pytest.raises(ValueError):
            BezierCurve2.from_points([(0, 0), (1, 1)])
    
    def test_endpoints_locked(self, simple_curve):
        """Endpoints should be locked by default."""
        assert simple_curve.control_points[0].is_locked
        assert simple_curve.control_points[2].is_locked
        assert not simple_curve.control_points[1].is_locked
    
    def test_evaluate_endpoints(self, simple_curve):
        """Curve should pass through endpoints."""
        p0 = simple_curve.evaluate(0.0)
        p2 = simple_curve.evaluate(1.0)
        
        assert_almost_equal(p0, (0.0, 10.0))
        assert_almost_equal(p2, (80.0, 10.0))
    
    def test_evaluate_many(self, simple_curve):
        """evaluate_many should return correct number of points."""
        points = simple_curve.evaluate_many(50)
        assert points.shape == (50, 2)
        
        # First and last should match endpoints
        assert_almost_equal(points[0], [0.0, 10.0])
        assert_almost_equal(points[-1], [80.0, 10.0])
    
    def test_create_default(self):
        """create_default should create valid intermediate point."""
        curve = BezierCurve2.create_default((0, 10), (100, 50), name="default")
        
        assert len(curve.control_points) == 3
        assert curve.control_points[0].z == 0
        assert curve.control_points[2].z == 100
        
        # Check middle point is between endpoints
        pt = curve.control_points[1]
        assert 0 < pt.z < 100
    
    def test_serialization_roundtrip(self, simple_curve):
        """to_dict/from_dict should preserve curve."""
        data = simple_curve.to_dict()
        restored = BezierCurve2.from_dict(data)
        
        assert restored.name == simple_curve.name
        assert len(restored.control_points) == 3
        
        for i in range(3):
            orig = simple_curve.control_points[i]
            rest = restored.control_points[i]
            assert_almost_equal(orig.z, rest.z)
            assert_almost_equal(orig.r, rest.r)

