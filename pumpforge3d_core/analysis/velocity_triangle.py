"""
Velocity Triangle Computation Module.

Based on CFturbo manual definitions:
- u = ω × r (blade speed)
- cm = meridional velocity (same as wm)
- wu = cm / tan(β) (relative circumferential)
- cu = u - wu (absolute circumferential, from identity: wu + cu = u)
- c = √(cu² + cm²) (absolute velocity)
- w = √(wu² + cm²) (relative velocity)

Blockage and flow area calculations:
- τ (obstruction) = z × t_avg / (π × d_m)
- A_effective = A_geometric × (1 - τ)
- cm = Q / A_effective
- K_blockage = 1 / (1 - τ)
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


@dataclass
class DerivedTriangleData:
    """
    Derived velocity triangle data including blockage and slip effects.
    
    Contains:
    - Flow: base triangle (no corrections)
    - Blocked: triangle with blockage-corrected cm
    - Blade: blade angle (beta_blade) with incidence (inlet) or slip (outlet)
    """
    # Base flow triangle
    flow: TriangleData
    
    # Blockage parameters
    k_blockage: float
    cm_blocked: float
    
    # Blocked triangle values
    cu_blocked: float
    wu_blocked: float
    c_blocked: float
    w_blocked: float
    alpha_blocked: float
    beta_blocked: float
    
    # Blade/slip parameters (inlet: incidence, outlet: slip)
    incidence: float = 0.0      # Inlet incidence (deg)
    slip: float = 0.0           # Outlet slip/deviation (deg)
    beta_blade: float = 0.0     # Blade angle
    
    # Slipped values (outlet only)
    cu_slipped: float = 0.0
    wu_slipped: float = 0.0
    c_slipped: float = 0.0
    w_slipped: float = 0.0
    beta_slipped: float = 0.0


def compute_derived_triangle(
    base: TriangleData,
    k_blockage: float = 1.10,
    incidence: float = 0.0,
    slip: float = 0.0,
    is_inlet: bool = True
) -> DerivedTriangleData:
    """
    Compute derived triangle with blockage and incidence/slip effects.
    
    Args:
        base: Base flow triangle
        k_blockage: Blockage multiplier (1.0-1.5), default 1.10
        incidence: Inlet incidence angle (degrees), ignored for outlet
        slip: Outlet slip/deviation angle (degrees), ignored for inlet
        is_inlet: True for inlet, False for outlet
        
    Returns:
        DerivedTriangleData with all derived values
    """
    # A) Blockage: cm_blocked = cm × K_blockage
    cm_blocked = base.cm * k_blockage
    
    # u and cu unchanged for blocked
    u = base.u
    cu_blocked = base.cu
    
    # Recompute blocked triangle
    # c_blocked = sqrt(cu² + cm_blocked²)
    c_blocked = math.sqrt(cu_blocked**2 + cm_blocked**2)
    
    # w_blocked from: w = c - u (vectorially)
    # wu_blocked = cu_blocked - u? No, wu = u - cu per our convention
    # Actually, from identity: wu + cu = u => wu = u - cu
    wu_blocked = u - cu_blocked
    w_blocked = math.sqrt(wu_blocked**2 + cm_blocked**2)
    
    # Blocked angles
    # beta_blocked = atan(cm_blocked / wu_blocked)
    if abs(wu_blocked) < 0.001:
        beta_blocked = 90.0
    else:
        beta_blocked = math.degrees(math.atan(cm_blocked / abs(wu_blocked)))
        if wu_blocked < 0:
            beta_blocked = 180 - beta_blocked
    
    # alpha_blocked = atan(cm_blocked / cu_blocked)
    if abs(cu_blocked) < 0.001:
        alpha_blocked = 90.0
    else:
        alpha_blocked = math.degrees(math.atan(cm_blocked / abs(cu_blocked)))
        if cu_blocked < 0:
            alpha_blocked = 180 - alpha_blocked
    
    # B) Inlet: blade angle = beta_blocked + incidence
    # C) Outlet: beta_slipped = beta_blocked + slip
    if is_inlet:
        beta_blade = beta_blocked + incidence
        # For inlet, slip values are not used
        cu_slipped = cu_blocked
        wu_slipped = wu_blocked
        c_slipped = c_blocked
        w_slipped = w_blocked
        beta_slipped = beta_blocked
    else:
        # Outlet: apply slip
        beta_slipped = beta_blocked + slip
        beta_blade = beta_slipped  # Blade angle at outlet
        
        # Compute slipped wu from beta_slipped
        # tan(beta_slipped) = cm_blocked / wu_slipped
        beta_s_rad = math.radians(beta_slipped)
        tan_beta_s = math.tan(beta_s_rad)
        
        if abs(tan_beta_s) < 0.01:
            wu_slipped = cm_blocked * 100  # Clamp
        else:
            wu_slipped = cm_blocked / tan_beta_s
        
        # cu_slipped from identity: wu + cu = u => cu = u - wu
        cu_slipped = u - wu_slipped
        
        # Recompute slipped velocities
        c_slipped = math.sqrt(cu_slipped**2 + cm_blocked**2)
        w_slipped = math.sqrt(wu_slipped**2 + cm_blocked**2)
    
    return DerivedTriangleData(
        flow=base,
        k_blockage=k_blockage,
        cm_blocked=cm_blocked,
        cu_blocked=cu_blocked,
        wu_blocked=wu_blocked,
        c_blocked=c_blocked,
        w_blocked=w_blocked,
        alpha_blocked=alpha_blocked,
        beta_blocked=beta_blocked,
        incidence=incidence,
        slip=slip,
        beta_blade=beta_blade,
        cu_slipped=cu_slipped,
        wu_slipped=wu_slipped,
        c_slipped=c_slipped,
        w_slipped=w_slipped,
        beta_slipped=beta_slipped
    )


def calculate_flow_area(r_hub: float, r_tip: float) -> float:
    """
    Calculate meridional flow area (annular area).

    Args:
        r_hub: Hub radius (m)
        r_tip: Tip radius (m)

    Returns:
        Flow area (m²)
    """
    return math.pi * (r_tip**2 - r_hub**2)


def calculate_obstruction_factor(
    blade_count: int,
    thickness_avg: float,
    diameter_mean: float
) -> float:
    """
    Calculate blade obstruction factor τ (tau).

    CFturbo formula:
        τ = z × t_avg / (π × d_m)

    where:
        z = blade count
        t_avg = average blade thickness (m)
        d_m = mean diameter (m)

    Args:
        blade_count: Number of blades
        thickness_avg: Average blade thickness (m)
        diameter_mean: Mean diameter (m)

    Returns:
        Obstruction factor τ (dimensionless, typically 0.05-0.15)
    """
    if diameter_mean <= 0:
        return 0.0

    tau = blade_count * thickness_avg / (math.pi * diameter_mean)
    return max(0.0, min(tau, 0.5))  # Clamp to reasonable range


def calculate_blockage_factor(
    blade_count: int,
    thickness_avg: float,
    diameter_mean: float
) -> float:
    """
    Calculate blockage multiplier K_blockage.

    Relationship:
        K_blockage = 1 / (1 - τ)

    where τ is the obstruction factor.

    Args:
        blade_count: Number of blades
        thickness_avg: Average blade thickness (m)
        diameter_mean: Mean diameter (m)

    Returns:
        Blockage factor K (dimensionless, typically 1.05-1.15)
    """
    tau = calculate_obstruction_factor(blade_count, thickness_avg, diameter_mean)

    if tau >= 1.0:
        return 1.5  # Maximum reasonable value

    k_blockage = 1.0 / (1.0 - tau)
    return min(k_blockage, 1.5)  # Clamp to reasonable maximum


def calculate_meridional_velocity(
    flow_rate: float,
    r_hub: float,
    r_tip: float,
    blade_count: int = 0,
    thickness_avg: float = 0.0,
    diameter_mean: float = 0.0,
    include_blockage: bool = False
) -> float:
    """
    Calculate meridional velocity from flow rate and geometry.

    Formula:
        cm = Q / A_effective

    where:
        A_effective = A_geometric              (without blockage)
        A_effective = A_geometric × (1 - τ)    (with blockage)

    Args:
        flow_rate: Volume flow rate Q (m³/s)
        r_hub: Hub radius (m)
        r_tip: Tip radius (m)
        blade_count: Number of blades (for blockage)
        thickness_avg: Average blade thickness (m, for blockage)
        diameter_mean: Mean diameter (m, for blockage)
        include_blockage: Whether to include blade blockage effect

    Returns:
        Meridional velocity cm (m/s)
    """
    # Geometric flow area
    A_geometric = calculate_flow_area(r_hub, r_tip)

    if A_geometric <= 0:
        return 0.0

    if include_blockage and blade_count > 0 and thickness_avg > 0:
        # Calculate effective area with blockage
        tau = calculate_obstruction_factor(blade_count, thickness_avg, diameter_mean)
        A_effective = A_geometric * (1.0 - tau)
    else:
        # No blockage correction
        A_effective = A_geometric

    # Avoid division by zero
    if A_effective <= 0:
        return 0.0

    cm = flow_rate / A_effective
    return cm


def calculate_mean_diameter(r_hub: float, r_tip: float) -> float:
    """
    Calculate mean diameter from hub and tip radii.

    d_m = (d_hub + d_tip) / 2 = r_hub + r_tip

    Args:
        r_hub: Hub radius (m)
        r_tip: Tip radius (m)

    Returns:
        Mean diameter (m)
    """
    return 2.0 * (r_hub + r_tip) / 2.0
