"""
Tests for velocity triangle computation.
"""

import pytest
import math

from pumpforge3d_core.analysis.velocity_triangle import (
    compute_triangle, compute_triangles_for_station, TriangleData
)


class TestVelocityTriangle:
    """Tests for velocity triangle computation."""
    
    def test_wu_plus_cu_equals_u(self):
        """Test CFturbo identity: wu + cu = u."""
        tri = compute_triangle(beta_deg=30, radius=0.05, rpm=3000, cm=5.0)
        
        assert tri.wu + tri.cu == pytest.approx(tri.u, rel=0.001)
    
    def test_wu_plus_cu_equals_u_various_betas(self):
        """Test identity for various beta values."""
        for beta in [15, 20, 30, 45, 60, 75]:
            tri = compute_triangle(beta_deg=beta, radius=0.05, rpm=3000, cm=5.0)
            assert tri.wu + tri.cu == pytest.approx(tri.u, rel=0.001)
    
    def test_cm_is_same_for_c_and_w(self):
        """Test that cm component is same for absolute and relative velocities."""
        tri = compute_triangle(beta_deg=30, radius=0.05, rpm=3000, cm=5.0)
        
        # cm should equal input cm
        assert tri.cm == 5.0
        
        # c vector and w vector should have same meridional component
        c_vec = tri.get_c_vector()
        w_vec = tri.get_w_vector()
        assert c_vec[1] == w_vec[1]  # Both have cm as y-component
    
    def test_blade_speed_calculation(self):
        """Test u = ω × r calculation."""
        tri = compute_triangle(beta_deg=30, radius=0.05, rpm=3000, cm=5.0)
        
        omega = 3000 * 2 * math.pi / 60
        expected_u = omega * 0.05
        
        assert tri.u == pytest.approx(expected_u, rel=0.001)
    
    def test_relative_flow_angle_relation(self):
        """Test tan(β) = cm / wu."""
        tri = compute_triangle(beta_deg=45, radius=0.05, rpm=3000, cm=5.0)
        
        # At 45°, tan(45) = 1, so cm = wu
        assert tri.wu == pytest.approx(tri.cm, rel=0.01)
    
    def test_velocity_magnitudes(self):
        """Test c and w magnitude calculations."""
        tri = compute_triangle(beta_deg=30, radius=0.05, rpm=3000, cm=5.0)
        
        # c = √(cu² + cm²)
        expected_c = math.sqrt(tri.cu**2 + tri.cm**2)
        assert tri.c == pytest.approx(expected_c, rel=0.001)
        
        # w = √(wu² + cm²)
        expected_w = math.sqrt(tri.wu**2 + tri.cm**2)
        assert tri.w == pytest.approx(expected_w, rel=0.001)
    
    def test_edge_case_small_beta(self):
        """Test handling of small beta (near tan singularity)."""
        tri = compute_triangle(beta_deg=0.5, radius=0.05, rpm=3000, cm=5.0)
        
        # Should have a warning
        assert tri.warning is not None
        
        # Should still satisfy identity
        assert tri.wu + tri.cu == pytest.approx(tri.u, rel=0.01)
    
    def test_hub_tip_computation(self):
        """Test computing both hub and tip triangles."""
        hub, tip = compute_triangles_for_station(
            beta_hub=25, beta_tip=30,
            r_hub=0.03, r_tip=0.05,
            rpm=3000, cm=5.0
        )
        
        # Both should satisfy identity
        assert hub.wu + hub.cu == pytest.approx(hub.u, rel=0.001)
        assert tip.wu + tip.cu == pytest.approx(tip.u, rel=0.001)
        
        # Tip u should be larger (larger radius)
        assert tip.u > hub.u
    
    def test_preswirl(self):
        """Test pre-swirl (alpha1 != 90) affects cu correctly."""
        # Without preswirl (alpha1 = 90°)
        tri_no_preswirl = compute_triangle(beta_deg=30, radius=0.05, rpm=3000, cm=5.0, alpha1_deg=90.0)
        
        # With preswirl (alpha1 = 45° means cu = cm / tan(45) = cm)
        tri_with_preswirl = compute_triangle(
            beta_deg=30, radius=0.05, rpm=3000, cm=5.0, alpha1_deg=45.0
        )
        
        # cu should be different (with preswirl, cu = cm / tan(45) = 5.0)
        assert tri_with_preswirl.cu == pytest.approx(5.0, rel=0.01)
        
        # Identity should still hold
        assert tri_with_preswirl.wu + tri_with_preswirl.cu == pytest.approx(
            tri_with_preswirl.u, rel=0.001
        )
    
    def test_get_vectors(self):
        """Test vector getter methods."""
        tri = compute_triangle(beta_deg=30, radius=0.05, rpm=3000, cm=5.0)
        
        c_vec = tri.get_c_vector()
        w_vec = tri.get_w_vector()
        u_vec = tri.get_u_vector()
        
        assert len(c_vec) == 2
        assert len(w_vec) == 2
        assert len(u_vec) == 2
        
        # c = (cu, cm)
        assert c_vec[0] == tri.cu
        assert c_vec[1] == tri.cm
        
        # w = (wu, cm)
        assert w_vec[0] == tri.wu
        assert w_vec[1] == tri.cm
        
        # u = (u, 0)
        assert u_vec[0] == tri.u
        assert u_vec[1] == 0.0
