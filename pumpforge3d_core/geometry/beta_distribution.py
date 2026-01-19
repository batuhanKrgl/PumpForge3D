"""
Beta Distribution Model for blade angle distribution editing.

This module provides a model for editing blade beta angles using 4th-order Bezier curves.
Only hub and tip control points (j=1,2,3) are draggable. All other spans are computed
by linear interpolation along "coupled lines" between hub and tip.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
import numpy as np
from numpy.typing import NDArray


@dataclass
class BetaDistributionModel:
    """
    Model for beta angle distribution across spans.
    
    Each span has a 4th-order Bezier curve (5 CPs) defining beta vs theta*.
    
    Key design:
    - Only hub (span 0) and tip (span N-1) CPs for j=1,2,3 are stored/editable
    - Intermediate span CPs are computed by linear interpolation
    - Endpoints (j=0,4) come from beta_in/beta_out table
    
    Attributes:
        span_count: Number of span rows (hub to tip)
        span_fractions: Array of span positions [0..1] from hub to tip
        beta_in: Inlet angles (degrees) for each span
        beta_out: Outlet angles (degrees) for each span
        hub_theta: array (3,) theta positions for hub CPs j=1,2,3
        hub_beta: array (3,) beta values for hub CPs j=1,2,3
        tip_theta: array (3,) theta positions for tip CPs j=1,2,3
        tip_beta: array (3,) beta values for tip CPs j=1,2,3
    """
    span_count: int = 5
    span_fractions: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    beta_in: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    beta_out: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    
    # Hub CPs for j=1,2,3 (draggable)
    hub_theta: NDArray[np.float64] = field(default_factory=lambda: np.array([0.25, 0.5, 0.75]))
    hub_beta: NDArray[np.float64] = field(default_factory=lambda: np.array([30.0, 35.0, 40.0]))
    
    # Tip CPs for j=1,2,3 (draggable)
    tip_theta: NDArray[np.float64] = field(default_factory=lambda: np.array([0.25, 0.5, 0.75]))
    tip_beta: NDArray[np.float64] = field(default_factory=lambda: np.array([40.0, 50.0, 55.0]))
    
    # Linear distribution mode flags (inlet/outlet separately)
    linear_inlet: bool = False
    linear_outlet: bool = False
    
    # Angle lock for hub/tip CP1 and CP3 (indices 0 and 2 in arrays)
    # Format: [CP1_lock, CP3_lock] for each
    hub_angle_lock: List[bool] = field(default_factory=lambda: [False, False])
    hub_angle_value: List[float] = field(default_factory=lambda: [45.0, 45.0])
    tip_angle_lock: List[bool] = field(default_factory=lambda: [False, False])
    tip_angle_value: List[float] = field(default_factory=lambda: [45.0, 45.0])
    
    def __post_init__(self):
        """Initialize arrays if empty."""
        if len(self.span_fractions) == 0:
            self._initialize_default()
    
    def _initialize_default(self):
        """Set up default values for N spans."""
        N = self.span_count
        
        # Uniform span distribution from hub (0) to tip (1)
        self.span_fractions = np.linspace(0, 1, N)
        
        # Default inlet/outlet angles
        self.beta_in = np.linspace(20.0, 30.0, N)
        self.beta_out = np.linspace(50.0, 60.0, N)
        
        # Default hub/tip CPs (j=1,2,3)
        self.hub_theta = np.array([0.25, 0.5, 0.75])
        self.hub_beta = np.array([
            self.beta_in[0] + 0.25 * (self.beta_out[0] - self.beta_in[0]),
            self.beta_in[0] + 0.50 * (self.beta_out[0] - self.beta_in[0]),
            self.beta_in[0] + 0.75 * (self.beta_out[0] - self.beta_in[0]),
        ])
        
        self.tip_theta = np.array([0.25, 0.5, 0.75])
        self.tip_beta = np.array([
            self.beta_in[-1] + 0.25 * (self.beta_out[-1] - self.beta_in[-1]),
            self.beta_in[-1] + 0.50 * (self.beta_out[-1] - self.beta_in[-1]),
            self.beta_in[-1] + 0.75 * (self.beta_out[-1] - self.beta_in[-1]),
        ])
    
    def set_span_count(self, n: int):
        """Change the number of spans."""
        if n < 2:
            n = 2
        if n == self.span_count:
            return
        
        old_fracs = self.span_fractions.copy()
        old_beta_in = self.beta_in.copy()
        old_beta_out = self.beta_out.copy()
        
        # New uniform fractions
        new_fracs = np.linspace(0, 1, n)
        
        # Interpolate beta_in/out
        new_beta_in = np.interp(new_fracs, old_fracs, old_beta_in)
        new_beta_out = np.interp(new_fracs, old_fracs, old_beta_out)
        
        self.span_count = n
        self.span_fractions = new_fracs
        self.beta_in = new_beta_in
        self.beta_out = new_beta_out
        # hub/tip CPs remain unchanged
    
    def set_beta_in(self, span_idx: int, value: float):
        """Set inlet angle for a span."""
        if 0 <= span_idx < self.span_count:
            self.beta_in[span_idx] = value
    
    def set_beta_out(self, span_idx: int, value: float):
        """Set outlet angle for a span."""
        if 0 <= span_idx < self.span_count:
            self.beta_out[span_idx] = value
    
    def set_hub_cp(self, j: int, theta: float, beta: float):
        """
        Set hub CP position for index j (1,2,3 -> array index 0,1,2).
        
        Theta is clamped between neighbors (not sorted/pushed).
        
        Args:
            j: CP index (1, 2, or 3)
            theta: x position in (0..1)
            beta: y value (degrees)
        """
        if j in [1, 2, 3]:
            idx = j - 1
            # Clamp theta between neighbors
            theta = self._clamp_theta_between_neighbors(theta, idx, 'hub')
            self.hub_theta[idx] = theta
            self.hub_beta[idx] = beta
    
    def set_tip_cp(self, j: int, theta: float, beta: float):
        """
        Set tip CP position for index j (1,2,3 -> array index 0,1,2).
        
        Theta is clamped between neighbors (not sorted/pushed).
        
        Args:
            j: CP index (1, 2, or 3)
            theta: x position in (0..1)
            beta: y value (degrees)
        """
        if j in [1, 2, 3]:
            idx = j - 1
            # Clamp theta between neighbors
            theta = self._clamp_theta_between_neighbors(theta, idx, 'tip')
            self.tip_theta[idx] = theta
            self.tip_beta[idx] = beta
    
    def _clamp_theta_between_neighbors(self, theta: float, idx: int, which: str) -> float:
        """
        Clamp theta to stay between neighboring CPs.
        
        Args:
            theta: proposed theta value
            idx: array index (0, 1, or 2)
            which: 'hub' or 'tip'
            
        Returns:
            Clamped theta value
        """
        margin = 0.02  # Minimum gap between CPs
        
        if which == 'hub':
            thetas = self.hub_theta
        else:
            thetas = self.tip_theta
        
        # Get bounds from neighbors
        if idx == 0:  # CP1: between 0 and CP2
            min_theta = margin
            max_theta = thetas[1] - margin if len(thetas) > 1 else 0.99
        elif idx == 1:  # CP2: between CP1 and CP3
            min_theta = thetas[0] + margin
            max_theta = thetas[2] - margin if len(thetas) > 2 else 0.99
        else:  # CP3: between CP2 and 1.0
            min_theta = thetas[1] + margin if len(thetas) > 1 else 0.01
            max_theta = 1.0 - margin
        
        return max(min_theta, min(max_theta, theta))
    
    def apply_linear_mode(self):
        """
        Recompute beta_in/out using linear interpolation when linear mode is ON.
        
        Only hub (row 0) and tip (row N-1) values are kept.
        Intermediate rows are linearly interpolated.
        """
        if self.linear_inlet:
            hub_in = self.beta_in[0]
            tip_in = self.beta_in[-1]
            for i in range(self.span_count):
                s = self.span_fractions[i]
                self.beta_in[i] = hub_in + s * (tip_in - hub_in)
        
        if self.linear_outlet:
            hub_out = self.beta_out[0]
            tip_out = self.beta_out[-1]
            for i in range(self.span_count):
                s = self.span_fractions[i]
                self.beta_out[i] = hub_out + s * (tip_out - hub_out)
    
    def apply_angle_constraint(self, which: str, j: int, theta: float, beta: float) -> Tuple[float, float]:
        """
        Apply angle lock constraint to a CP position.
        
        Angle defines slope of beta change:
        - 0° = flat (no beta change as theta changes)
        - 45° = line from inlet to outlet
        
        Args:
            which: 'hub' or 'tip'
            j: CP index (1 or 3 for angle-lockable CPs)
            theta: proposed theta position
            beta: proposed beta position
            
        Returns:
            (constrained_theta, constrained_beta)
        """
        import math
        
        # Map j to lock index: j=1 -> 0, j=3 -> 1
        if j == 1:
            lock_idx = 0
        elif j == 3:
            lock_idx = 1
        else:
            return (theta, beta)
        
        if which == 'hub':
            is_locked = self.hub_angle_lock[lock_idx]
            angle_deg = self.hub_angle_value[lock_idx]
            beta_in = self.beta_in[0]
            beta_out = self.beta_out[0]
            if j == 1:
                anchor = (0.0, beta_in)
            else:
                anchor = (1.0, beta_out)
        else:
            is_locked = self.tip_angle_lock[lock_idx]
            angle_deg = self.tip_angle_value[lock_idx]
            beta_in = self.beta_in[-1]
            beta_out = self.beta_out[-1]
            if j == 1:
                anchor = (0.0, beta_in)
            else:
                anchor = (1.0, beta_out)
        
        if not is_locked:
            return (theta, beta)
        
        # Calculate normalized slope
        # At 45 degrees, slope should equal (beta_out - beta_in) / 1.0
        beta_range = beta_out - beta_in
        angle_rad = math.radians(angle_deg)
        
        # slope = tan(angle) * beta_range (normalized so 45° = full range)
        slope = math.tan(angle_rad) * abs(beta_range) if abs(beta_range) > 0.01 else math.tan(angle_rad) * 40
        
        # Constrain: beta = anchor_beta + slope * (theta - anchor_theta)
        new_theta = theta
        new_theta = max(0.01, min(0.99, new_theta))
        
        delta_theta = new_theta - anchor[0]
        new_beta = anchor[1] + slope * delta_theta
        
        return (new_theta, new_beta)
    
    def get_reference_line(self, which: str, j: int) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Get reference line endpoints for a lockable CP.
        
        Args:
            which: 'hub' or 'tip'
            j: CP index (1 or 3)
            
        Returns:
            (start_point, end_point) for the reference line
        """
        import math
        
        if j not in [1, 3]:
            return None
        
        lock_idx = 0 if j == 1 else 1
        
        if which == 'hub':
            angle_deg = self.hub_angle_value[lock_idx]
            beta_in = self.beta_in[0]
            beta_out = self.beta_out[0]
            if j == 1:
                anchor = (0.0, beta_in)
            else:
                anchor = (1.0, beta_out)
        else:
            angle_deg = self.tip_angle_value[lock_idx]
            beta_in = self.beta_in[-1]
            beta_out = self.beta_out[-1]
            if j == 1:
                anchor = (0.0, beta_in)
            else:
                anchor = (1.0, beta_out)
        
        # Calculate slope
        beta_range = beta_out - beta_in
        angle_rad = math.radians(angle_deg)
        slope = math.tan(angle_rad) * abs(beta_range) if abs(beta_range) > 0.01 else math.tan(angle_rad) * 40
        
        # Short line from anchor (length ~0.3 in theta)
        length = 0.3
        if j == 1:
            # Line goes forward from anchor
            end_theta = anchor[0] + length
            end_beta = anchor[1] + slope * length
        else:
            # Line goes backward from anchor
            end_theta = anchor[0] - length
            end_beta = anchor[1] - slope * length
        
        return (anchor, (end_theta, end_beta))
    
    def get_span_cps(self, span_idx: int) -> List[Tuple[float, float]]:
        """
        Get all 5 CP positions for a span.
        
        CP[0] and CP[4] come from table (endpoints).
        CP[1..3] come from linear interpolation between hub and tip.
        
        Returns:
            List of 5 (theta, beta) tuples
        """
        if not (0 <= span_idx < self.span_count):
            return []
        
        s = self.span_fractions[span_idx]  # 0 for hub, 1 for tip
        
        # Endpoints from table
        cp0 = (0.0, self.beta_in[span_idx])
        cp4 = (1.0, self.beta_out[span_idx])
        
        # Interior CPs from lerp
        cps = [cp0]
        for j in range(3):  # j=1,2,3 -> index 0,1,2
            theta = self.hub_theta[j] + s * (self.tip_theta[j] - self.hub_theta[j])
            beta = self.hub_beta[j] + s * (self.tip_beta[j] - self.hub_beta[j])
            cps.append((theta, beta))
        cps.append(cp4)
        
        return cps
    
    def get_coupled_lines(self) -> List[List[Tuple[float, float]]]:
        """
        Get 3 coupled lines connecting hub and tip CPs for j=1,2,3.
        
        Returns:
            List of 3 lines, each = [(hub_theta, hub_beta), (tip_theta, tip_beta)]
        """
        lines = []
        for j in range(3):  # j=1,2,3
            hub_pt = (self.hub_theta[j], self.hub_beta[j])
            tip_pt = (self.tip_theta[j], self.tip_beta[j])
            lines.append([hub_pt, tip_pt])
        return lines
    
    def sample_span_curve(self, span_idx: int, n_samples: int = 100) -> Tuple[NDArray, NDArray]:
        """Sample a span's Bezier curve."""
        cps = self.get_span_cps(span_idx)
        if len(cps) != 5:
            return np.array([]), np.array([])
        
        cp_theta = np.array([cp[0] for cp in cps])
        cp_beta = np.array([cp[1] for cp in cps])
        
        t = np.linspace(0, 1, n_samples)
        theta = self._bezier_eval(t, cp_theta)
        beta = self._bezier_eval(t, cp_beta)
        
        return theta, beta
    
    def sample_all(self, n_samples: int = 100) -> List[Tuple[NDArray, NDArray]]:
        """Sample all span curves."""
        return [self.sample_span_curve(i, n_samples) for i in range(self.span_count)]
    
    def _bezier_eval(self, t: NDArray, cps: NDArray) -> NDArray:
        """Evaluate 4th-order Bezier curve."""
        from math import comb
        n = 4
        result = np.zeros_like(t)
        for i in range(n + 1):
            binom = comb(n, i)
            basis = binom * (t ** i) * ((1 - t) ** (n - i))
            result += cps[i] * basis
        return result
    
    def copy(self) -> "BetaDistributionModel":
        """Create a deep copy."""
        return BetaDistributionModel(
            span_count=self.span_count,
            span_fractions=self.span_fractions.copy(),
            beta_in=self.beta_in.copy(),
            beta_out=self.beta_out.copy(),
            hub_theta=self.hub_theta.copy(),
            hub_beta=self.hub_beta.copy(),
            tip_theta=self.tip_theta.copy(),
            tip_beta=self.tip_beta.copy(),
        )
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "span_count": self.span_count,
            "span_fractions": self.span_fractions.tolist(),
            "beta_in": self.beta_in.tolist(),
            "beta_out": self.beta_out.tolist(),
            "hub_theta": self.hub_theta.tolist(),
            "hub_beta": self.hub_beta.tolist(),
            "tip_theta": self.tip_theta.tolist(),
            "tip_beta": self.tip_beta.tolist(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BetaDistributionModel":
        """Deserialize from dictionary."""
        return cls(
            span_count=data["span_count"],
            span_fractions=np.array(data["span_fractions"]),
            beta_in=np.array(data["beta_in"]),
            beta_out=np.array(data["beta_out"]),
            hub_theta=np.array(data["hub_theta"]),
            hub_beta=np.array(data["hub_beta"]),
            tip_theta=np.array(data["tip_theta"]),
            tip_beta=np.array(data["tip_beta"]),
        )
