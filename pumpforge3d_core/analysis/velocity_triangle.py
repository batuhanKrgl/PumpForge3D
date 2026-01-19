"""
Velocity Triangle Computation Module.

Based on CFturbo manual definitions:
- u = ω × r (blade speed)
- cm = meridional velocity (same as wm)
- wu = cm / tan(β) (relative circumferential)
- cu = u - wu (absolute circumferential, from identity: wu + cu = u)
- c = √(cu² + cm²) (absolute velocity)
- w = √(wu² + cm²) (relative velocity)
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import math


@dataclass
class TriangleData:
    """
    Velocity triangle data for a single station (inlet/outlet) and span (hub/tip).
    
    All velocities in m/s, angles in degrees.
    """
    # Blade speed
    u: float
    
    # Meridional velocity (same for absolute and relative)
    cm: float
    
    # Circumferential components
    cu: float  # Absolute
    wu: float  # Relative
    
    # Velocity magnitudes
    c: float   # Absolute velocity
    w: float   # Relative velocity
    
    # Flow angles (degrees)
    beta: float   # Relative flow angle
    alpha: float  # Absolute flow angle
    
    # Radius and rpm used
    radius: float
    rpm: float
    
    # Warning message if any
    warning: Optional[str] = None
    
    def get_c_vector(self) -> Tuple[float, float]:
        """Get absolute velocity as (cu, cm) vector."""
        return (self.cu, self.cm)
    
    def get_w_vector(self) -> Tuple[float, float]:
        """Get relative velocity as (wu, cm) vector."""
        return (self.wu, self.cm)
    
    def get_u_vector(self) -> Tuple[float, float]:
        """Get blade speed as (u, 0) vector."""
        return (self.u, 0.0)


def compute_triangle(
    beta_deg: float,
    radius: float,
    rpm: float,
    cm: float,
    alpha1_deg: float = 90.0,
    use_beta: bool = True
) -> TriangleData:
    """
    Compute velocity triangle for a single station.
    
    Uses CFturbo velocity relations:
    - u = ω × r
    - Identity: wu + cu = u (always holds)
    
    Args:
        beta_deg: Relative flow angle (degrees)
        radius: Radius at this station (m)
        rpm: Rotational speed (rev/min)
        cm: Meridional velocity (m/s)
        alpha1_deg: Inlet absolute flow angle (degrees), default 90°
        use_beta: If True (outlet mode), wu is calculated from tan(β)=cm/wu, cu from identity.
                  If False (inlet mode), cu is calculated from alpha, wu from identity.
        
    Returns:
        TriangleData with all velocity components
    """
    warning = None
    
    # Convert rpm to rad/s
    omega = rpm * 2 * math.pi / 60
    
    # Blade speed
    u = omega * radius
    
    # Handle edge cases for beta
    beta_rad = math.radians(beta_deg)
    
    # Clamp beta away from singularities
    if abs(beta_deg) < 1.0:
        warning = f"β={beta_deg:.1f}° too small, clamped to 1°"
        beta_rad = math.radians(1.0 if beta_deg >= 0 else -1.0)
    elif abs(beta_deg - 90) < 1.0 or abs(beta_deg + 90) < 1.0:
        warning = f"β={beta_deg:.1f}° near 90°, clamped"
        beta_rad = math.radians(89.0 if beta_deg > 0 else -89.0)
    
    # Handle alpha input for pre-swirl
    # α=90° means pure meridional (cu=0), α<90° means positive preswirl
    # Use epsilon-based guard for robust handling of α=90°
    alpha_rad = math.radians(alpha1_deg)
    cos_alpha = math.cos(alpha_rad)
    sin_alpha = math.sin(alpha_rad)
    
    # Robust alpha=90° handling: avoid division by zero when cos(α)≈0
    EPS = 1e-10
    if abs(cos_alpha) < EPS:
        # Pure meridional, α=90°: cu=0
        cu_from_alpha = 0.0
    elif abs(sin_alpha) < EPS:
        # α≈0° or 180°: all circumferential (rare case)
        cu_from_alpha = cm * 1e6  # Very large, will be clamped
    else:
        # Normal case: cu = cm * cos(α) / sin(α) = cm / tan(α)
        cu_from_alpha = cm * cos_alpha / sin_alpha
    
    # Relative circumferential velocity
    # tan(β) = cm / wu => wu = cm / tan(β)
    tan_beta = math.tan(beta_rad)
    if abs(tan_beta) < 0.01:
        wu = cm / 0.01 * (1 if tan_beta >= 0 else -1)
        warning = "tan(β) near zero, wu clamped"
    else:
        wu = cm / tan_beta
    
    # Two computation modes:
    # 1. use_beta=True (outlet): wu from tan(β), cu from identity
    # 2. use_beta=False (inlet): cu from alpha, wu from identity
    
    if use_beta:
        # Outlet mode: wu from beta, cu from identity
        # wu was already calculated above from tan(β)
        cu = u - wu
    else:
        # Inlet mode: cu from alpha, wu from identity
        if abs(cos_alpha) < EPS:
            # Alpha=90°: pure meridional c, cu=0
            cu = 0.0
        else:
            cu = cu_from_alpha
        # wu from identity
        wu = u - cu
    
    # Velocity magnitudes
    c = math.sqrt(cu**2 + cm**2)
    w = math.sqrt(wu**2 + cm**2)
    
    # Recalculate actual alpha from cu, cm
    if abs(cu) < 0.001:
        alpha = 90.0
    else:
        alpha = math.degrees(math.atan(cm / abs(cu)))
        if cu < 0:
            alpha = 180 - alpha
    
    return TriangleData(
        u=u,
        cm=cm,
        cu=cu,
        wu=wu,
        c=c,
        w=w,
        beta=beta_deg,
        alpha=alpha,
        radius=radius,
        rpm=rpm,
        warning=warning
    )


def compute_triangles_for_station(
    beta_hub: float,
    beta_tip: float,
    r_hub: float,
    r_tip: float,
    rpm: float,
    cm: float,
    alpha1_deg: float = 90.0
) -> Tuple[TriangleData, TriangleData]:
    """
    Compute velocity triangles for both hub and tip at a station.
    
    Args:
        beta_hub: Hub relative flow angle (degrees)
        beta_tip: Tip relative flow angle (degrees)
        r_hub: Hub radius (m)
        r_tip: Tip radius (m)
        rpm: Rotational speed (rev/min)
        cm: Meridional velocity (m/s)
        alpha1_deg: Inlet flow angle (degrees), default 90° (no preswirl)
        
    Returns:
        (hub_triangle, tip_triangle)
    """
    hub = compute_triangle(beta_hub, r_hub, rpm, cm, alpha1_deg)
    tip = compute_triangle(beta_tip, r_tip, rpm, cm, alpha1_deg)
    return (hub, tip)

