"""
Tests for BetaDistributionModel.
"""

import pytest
import numpy as np

from pumpforge3d_core.geometry.beta_distribution import BetaDistributionModel


class TestBetaDistributionModel:
    """Tests for BetaDistributionModel."""
    
    def test_default_initialization(self):
        """Test default model creation."""
        model = BetaDistributionModel()
        
        assert model.span_count == 5
        assert len(model.span_fractions) == 5
        assert len(model.beta_in) == 5
        assert len(model.beta_out) == 5
        assert len(model.hub_theta) == 3
        assert len(model.hub_beta) == 3
        assert len(model.tip_theta) == 3
        assert len(model.tip_beta) == 3
    
    def test_span_fractions_uniform(self):
        """Test that span fractions are uniformly distributed."""
        model = BetaDistributionModel(span_count=5)
        
        expected = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        np.testing.assert_array_almost_equal(model.span_fractions, expected)
    
    def test_hub_tip_cp_count(self):
        """Test that there are exactly 6 draggable CPs (3 hub + 3 tip)."""
        model = BetaDistributionModel()
        
        # Hub has 3 CPs for j=1,2,3
        assert len(model.hub_theta) == 3
        assert len(model.hub_beta) == 3
        
        # Tip has 3 CPs for j=1,2,3
        assert len(model.tip_theta) == 3
        assert len(model.tip_beta) == 3
        
        # Total = 6
        total_draggable = len(model.hub_theta) + len(model.tip_theta)
        assert total_draggable == 6
    
    def test_coupled_lines_count(self):
        """Test that there are exactly 3 coupled lines."""
        model = BetaDistributionModel()
        
        lines = model.get_coupled_lines()
        assert len(lines) == 3
        
        # Each line has 2 points (hub and tip)
        for line in lines:
            assert len(line) == 2
    
    def test_span_cps_endpoints_from_table(self):
        """Test that span CP endpoints come from beta table."""
        model = BetaDistributionModel(span_count=3)
        
        for i in range(model.span_count):
            cps = model.get_span_cps(i)
            
            # CP[0] should be (0, beta_in)
            assert cps[0][0] == 0.0
            assert cps[0][1] == pytest.approx(model.beta_in[i])
            
            # CP[4] should be (1, beta_out)
            assert cps[4][0] == 1.0
            assert cps[4][1] == pytest.approx(model.beta_out[i])
    
    def test_span_cps_interior_interpolation(self):
        """Test that interior CPs are linearly interpolated between hub and tip."""
        model = BetaDistributionModel(span_count=5)
        
        # Set distinct hub and tip values
        model.hub_theta = np.array([0.2, 0.5, 0.8])
        model.hub_beta = np.array([25.0, 35.0, 45.0])
        model.tip_theta = np.array([0.3, 0.6, 0.9])
        model.tip_beta = np.array([30.0, 50.0, 60.0])
        
        # Check hub (s=0)
        hub_cps = model.get_span_cps(0)
        for j in range(3):
            assert hub_cps[j+1][0] == pytest.approx(model.hub_theta[j])
            assert hub_cps[j+1][1] == pytest.approx(model.hub_beta[j])
        
        # Check tip (s=1)
        tip_cps = model.get_span_cps(4)
        for j in range(3):
            assert tip_cps[j+1][0] == pytest.approx(model.tip_theta[j])
            assert tip_cps[j+1][1] == pytest.approx(model.tip_beta[j])
        
        # Check middle span (s=0.5)
        mid_cps = model.get_span_cps(2)
        for j in range(3):
            expected_theta = 0.5 * model.hub_theta[j] + 0.5 * model.tip_theta[j]
            expected_beta = 0.5 * model.hub_beta[j] + 0.5 * model.tip_beta[j]
            assert mid_cps[j+1][0] == pytest.approx(expected_theta)
            assert mid_cps[j+1][1] == pytest.approx(expected_beta)
    
    def test_set_hub_cp(self):
        """Test setting hub CP."""
        model = BetaDistributionModel()
        
        model.set_hub_cp(2, 0.6, 40.0)  # j=2 -> index 1
        
        assert model.hub_theta[1] == pytest.approx(0.6)
        assert model.hub_beta[1] == pytest.approx(40.0)
    
    def test_set_tip_cp(self):
        """Test setting tip CP."""
        model = BetaDistributionModel()
        
        model.set_tip_cp(3, 0.8, 55.0)  # j=3 -> index 2
        
        assert model.tip_theta[2] == pytest.approx(0.8)
        assert model.tip_beta[2] == pytest.approx(55.0)
    
    def test_set_beta_in(self):
        """Test setting inlet angle."""
        model = BetaDistributionModel(span_count=3)
        
        model.set_beta_in(1, 42.0)
        
        assert model.beta_in[1] == 42.0
    
    def test_set_beta_out(self):
        """Test setting outlet angle."""
        model = BetaDistributionModel(span_count=3)
        
        model.set_beta_out(2, 77.0)
        
        assert model.beta_out[2] == 77.0
    
    def test_sample_curve_endpoints(self):
        """Test that sampled curve endpoints match table values."""
        model = BetaDistributionModel(span_count=3)
        
        for i in range(model.span_count):
            theta, beta = model.sample_span_curve(i, 100)
            
            # Curve starts at beta_in
            assert beta[0] == pytest.approx(model.beta_in[i], rel=0.01)
            # Curve ends at beta_out
            assert beta[-1] == pytest.approx(model.beta_out[i], rel=0.01)
    
    def test_drag_hub_does_not_affect_tip(self):
        """Test that dragging hub CP does not change tip CP."""
        model = BetaDistributionModel()
        
        old_tip_theta = model.tip_theta.copy()
        old_tip_beta = model.tip_beta.copy()
        
        # Drag hub CP
        model.set_hub_cp(2, 0.6, 50.0)
        
        # Tip should be unchanged
        np.testing.assert_array_almost_equal(model.tip_theta, old_tip_theta)
        np.testing.assert_array_almost_equal(model.tip_beta, old_tip_beta)
    
    def test_span_count_change(self):
        """Test changing span count preserves hub/tip CPs."""
        model = BetaDistributionModel(span_count=3)
        
        old_hub_theta = model.hub_theta.copy()
        old_hub_beta = model.hub_beta.copy()
        
        model.set_span_count(7)
        
        assert model.span_count == 7
        np.testing.assert_array_almost_equal(model.hub_theta, old_hub_theta)
        np.testing.assert_array_almost_equal(model.hub_beta, old_hub_beta)
    
    def test_copy(self):
        """Test deep copy."""
        model = BetaDistributionModel(span_count=3)
        model.hub_beta[0] = 99.0
        
        copy = model.copy()
        assert copy.hub_beta[0] == 99.0
        
        model.hub_beta[0] = 1.0
        assert copy.hub_beta[0] == 99.0
    
    def test_serialization(self):
        """Test to_dict and from_dict."""
        model = BetaDistributionModel(span_count=3)
        model.hub_beta[1] = 42.0
        
        data = model.to_dict()
        restored = BetaDistributionModel.from_dict(data)
        
        assert restored.span_count == model.span_count
        assert restored.hub_beta[1] == 42.0
