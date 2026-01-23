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


@dataclass
class InletTriangleResult:
    """
    Complete inlet velocity triangle calculation result.

    Contains all intermediate and final values for the inlet calculation flow:
    1. Area calculation → cm
    2. u calculation from rpm and radius
    3. cu calculation (from alpha, typically 0 for axial inlet)
    4. wu calculation (u - cu)
    5. Beta calculation (arctan(cm/wu))
    6. Blockage calculation → cm_blocked
    7. Beta_blocked calculation
    8. Beta_blade calculation (beta_blocked + incidence)
    """
    # Input parameters
    flow_rate: float      # Q (m³/s)
    radius: float         # r (m)
    rpm: float            # n (rev/min)
    alpha_inlet: float    # α₁ (degrees), typically 90° for axial inlet

    # Area and basic velocities
    area: float           # A₁ (m²)
    cm: float             # cm₁ (m/s) - meridional velocity
    u: float              # u₁ (m/s) - blade speed

    # Absolute velocity components
    cu: float             # cu₁ (m/s) - circumferential absolute
    c: float              # c₁ (m/s) - absolute velocity magnitude
    alpha: float          # α₁ (degrees) - absolute flow angle

    # Relative velocity components
    wu: float             # wu₁ (m/s) - circumferential relative
    w: float              # w₁ (m/s) - relative velocity magnitude
    beta: float           # β₁ (degrees) - relative flow angle

    # Blockage parameters
    tau: float            # τ - obstruction factor
    k_blockage: float     # K = 1/(1-τ)
    cm_blocked: float     # cm₁_bl (m/s)

    # Blocked triangle
    wu_blocked: float     # wu₁_bl (m/s)
    w_blocked: float      # w₁_bl (m/s)
    beta_blocked: float   # β₁_bl (degrees)

    # Blade angle
    incidence: float      # i (degrees)
    beta_blade: float     # β₁B (degrees) = β₁_bl + i

    # Derived quantities
    cr: float = 0.0       # Radial component (typically same as cm for axial machines)
    cz: float = 0.0       # Axial component
    diameter: float = 0.0  # d (m)

    def __post_init__(self):
        """Calculate derived quantities."""
        self.diameter = 2.0 * self.radius
        # For axial inlet, cr ≈ cm, cz ≈ 0
        self.cr = self.cm
        self.cz = 0.0


@dataclass
class OutletTriangleResult:
    """
    Complete outlet velocity triangle calculation result.

    Contains all intermediate and final values for the outlet calculation flow:
    1. Area calculation → cm
    2. u calculation from rpm and radius
    3. Beta_blade input (design parameter)
    4. Blockage calculation → cm_blocked
    5. Slip calculation → γ, δ
    6. Beta_blocked calculation (beta_blade - δ)
    7. cu calculation from triangle
    8. wu calculation
    9. Alpha calculation
    """
    # Input parameters
    flow_rate: float      # Q (m³/s)
    radius: float         # r (m)
    rpm: float            # n (rev/min)
    beta_blade: float     # β₂B (degrees) - blade angle (design input)

    # Area and basic velocities
    area: float           # A₂ (m²)
    cm: float             # cm₂ (m/s) - meridional velocity
    u: float              # u₂ (m/s) - blade speed

    # Blockage parameters
    tau: float            # τ - obstruction factor
    k_blockage: float     # K = 1/(1-τ)
    cm_blocked: float     # cm₂_bl (m/s)

    # Slip parameters
    slip_method: str      # "Wiesner", "Gülich", "Mock"
    gamma: float          # γ - slip coefficient
    slip_angle: float     # δ (degrees) - slip/deviation angle

    # Blocked/slipped flow angle
    beta_blocked: float   # β₂_bl (degrees) = β₂B - δ

    # Relative velocity components (with slip)
    wu: float             # wu₂ (m/s) - circumferential relative
    w: float              # w₂ (m/s) - relative velocity magnitude
    beta: float           # β₂ (degrees) - actual relative flow angle

    # Absolute velocity components
    cu: float             # cu₂ (m/s) - circumferential absolute
    c: float              # c₂ (m/s) - absolute velocity magnitude
    alpha: float          # α₂ (degrees) - absolute flow angle

    # Derived quantities
    cr: float = 0.0       # Radial component
    cz: float = 0.0       # Axial component
    diameter: float = 0.0  # d (m)

    # Ideal (no-slip) values for comparison
    cu_ideal: float = 0.0
    c_ideal: float = 0.0

    def __post_init__(self):
        """Calculate derived quantities."""
        self.diameter = 2.0 * self.radius
        self.cr = self.cm
        self.cz = 0.0


def compute_inlet_triangle(
    flow_rate: float,
    r_hub: float,
    r_tip: float,
    rpm: float,
    span_fraction: float = 0.0,
    alpha_inlet: float = 90.0,
    incidence: float = 0.0,
    blade_count: int = 6,
    thickness: float = 0.002
) -> InletTriangleResult:
    """
    Compute complete inlet velocity triangle.

    Flow:
    1. A₁ = π(r_tip² - r_hub²)
    2. cm₁ = Q / A₁
    3. u₁ = ω × r = (2π × n/60) × r
    4. cu₁ = cm₁ / tan(α₁)  [typically 0 for α₁=90°]
    5. wu₁ = u₁ - cu₁
    6. β₁ = arctan(cm₁ / wu₁)
    7. τ = z × t / (π × d_m)
    8. K = 1/(1-τ)
    9. cm₁_bl = cm₁ × K
    10. β₁_bl = arctan(cm₁_bl / wu₁)
    11. β₁B = β₁_bl + i

    Args:
        flow_rate: Volume flow rate Q (m³/s)
        r_hub: Hub radius (m)
        r_tip: Tip radius (m)
        rpm: Rotational speed (rev/min)
        span_fraction: Position along span (0=hub, 1=tip)
        alpha_inlet: Inlet absolute flow angle (degrees), 90° = axial
        incidence: Incidence angle (degrees)
        blade_count: Number of blades
        thickness: Blade thickness at this span (m)

    Returns:
        InletTriangleResult with all calculation results
    """
    # 1. Calculate area
    area = calculate_flow_area(r_hub, r_tip)

    # 2. Calculate meridional velocity
    cm = flow_rate / area if area > 0 else 0.0

    # Get radius at span
    radius = r_hub + span_fraction * (r_tip - r_hub)

    # 3. Calculate blade speed
    omega = rpm * 2 * math.pi / 60
    u = omega * radius

    # 4. Calculate cu from alpha
    # α = 90° means pure axial flow (cu = 0)
    # α < 90° means positive preswirl
    alpha_rad = math.radians(alpha_inlet)
    if abs(math.cos(alpha_rad)) < 1e-10:
        cu = 0.0
    else:
        cu = cm / math.tan(alpha_rad) if abs(math.tan(alpha_rad)) > 1e-10 else 0.0

    # 5. Calculate wu from identity: wu + cu = u
    wu = u - cu

    # Calculate velocity magnitudes
    c = math.sqrt(cu**2 + cm**2)
    w = math.sqrt(wu**2 + cm**2)

    # 6. Calculate beta (relative flow angle)
    if abs(wu) < 1e-10:
        beta = 90.0
    else:
        beta = math.degrees(math.atan(cm / wu))

    # Recalculate actual alpha
    if abs(cu) < 1e-10:
        alpha = 90.0
    else:
        alpha = math.degrees(math.atan(cm / abs(cu)))
        if cu < 0:
            alpha = 180 - alpha

    # 7. Calculate blockage (obstruction factor)
    d_mean = calculate_mean_diameter(r_hub, r_tip)
    tau = calculate_obstruction_factor(blade_count, thickness, d_mean)

    # 8. Blockage multiplier
    k_blockage = 1.0 / (1.0 - tau) if tau < 1.0 else 1.5

    # 9. Blocked meridional velocity
    cm_blocked = cm * k_blockage

    # 10. Blocked velocities (wu unchanged, recalculate w)
    wu_blocked = wu  # wu doesn't change with blockage
    w_blocked = math.sqrt(wu_blocked**2 + cm_blocked**2)

    # Blocked beta
    if abs(wu_blocked) < 1e-10:
        beta_blocked = 90.0
    else:
        beta_blocked = math.degrees(math.atan(cm_blocked / wu_blocked))

    # 11. Blade angle with incidence
    beta_blade = beta_blocked + incidence

    return InletTriangleResult(
        flow_rate=flow_rate,
        radius=radius,
        rpm=rpm,
        alpha_inlet=alpha_inlet,
        area=area,
        cm=cm,
        u=u,
        cu=cu,
        c=c,
        alpha=alpha,
        wu=wu,
        w=w,
        beta=beta,
        tau=tau,
        k_blockage=k_blockage,
        cm_blocked=cm_blocked,
        wu_blocked=wu_blocked,
        w_blocked=w_blocked,
        beta_blocked=beta_blocked,
        incidence=incidence,
        beta_blade=beta_blade,
    )


def compute_outlet_triangle(
    flow_rate: float,
    r_hub: float,
    r_tip: float,
    rpm: float,
    beta_blade: float = 35.0,
    span_fraction: float = 0.0,
    blade_count: int = 6,
    thickness: float = 0.0015,
    slip_method: str = "Wiesner"
) -> OutletTriangleResult:
    """
    Compute complete outlet velocity triangle.

    Flow:
    1. A₂ = π(r_tip² - r_hub²)
    2. cm₂ = Q / A₂
    3. u₂ = ω × r
    4. β₂B = blade angle (design input, default 35°)
    5. τ = z × t / (π × d_m)
    6. K = 1/(1-τ)
    7. cm₂_bl = cm₂ × K
    8. γ = slip coefficient (from Wiesner/Gülich/Mock)
    9. δ = slip angle
    10. β₂_bl = β₂B - δ (or: cu₂ = γ × cu₂_ideal)
    11. wu₂ = cm₂_bl / tan(β₂_bl)
    12. cu₂ = u₂ - wu₂
    13. α₂ = arctan(cm₂ / cu₂)

    Args:
        flow_rate: Volume flow rate Q (m³/s)
        r_hub: Hub radius (m)
        r_tip: Tip radius (m)
        rpm: Rotational speed (rev/min)
        beta_blade: Blade exit angle (degrees), default 35°
        span_fraction: Position along span (0=hub, 1=tip)
        blade_count: Number of blades
        thickness: Blade thickness at this span (m)
        slip_method: "Wiesner", "Gülich", or "Mock"

    Returns:
        OutletTriangleResult with all calculation results
    """
    # 1. Calculate area
    area = calculate_flow_area(r_hub, r_tip)

    # 2. Calculate meridional velocity
    cm = flow_rate / area if area > 0 else 0.0

    # Get radius at span
    radius = r_hub + span_fraction * (r_tip - r_hub)

    # 3. Calculate blade speed
    omega = rpm * 2 * math.pi / 60
    u = omega * radius

    # 5-6. Calculate blockage
    d_mean = calculate_mean_diameter(r_hub, r_tip)
    tau = calculate_obstruction_factor(blade_count, thickness, d_mean)
    k_blockage = 1.0 / (1.0 - tau) if tau < 1.0 else 1.5

    # 7. Blocked meridional velocity
    cm_blocked = cm * k_blockage

    # 8-9. Calculate slip
    gamma, slip_angle = _calculate_slip(beta_blade, blade_count, slip_method)

    # Calculate ideal cu (no slip)
    beta_blade_rad = math.radians(beta_blade)
    if abs(math.tan(beta_blade_rad)) < 0.01:
        wu_ideal = cm_blocked * 100
    else:
        wu_ideal = cm_blocked / math.tan(beta_blade_rad)
    cu_ideal = u - wu_ideal
    c_ideal = math.sqrt(cu_ideal**2 + cm_blocked**2)

    # 10. Beta with slip
    beta_blocked = beta_blade - slip_angle

    # 11. Calculate wu from blocked beta
    beta_blocked_rad = math.radians(beta_blocked)
    if abs(math.tan(beta_blocked_rad)) < 0.01:
        wu = cm_blocked * 100 * (1 if beta_blocked >= 0 else -1)
    else:
        wu = cm_blocked / math.tan(beta_blocked_rad)

    # 12. Calculate cu from identity
    cu = u - wu

    # Alternative: apply slip coefficient directly
    # cu = gamma * cu_ideal

    # Velocity magnitudes
    w = math.sqrt(wu**2 + cm_blocked**2)
    c = math.sqrt(cu**2 + cm_blocked**2)

    # Actual beta (should match beta_blocked)
    if abs(wu) < 1e-10:
        beta = 90.0
    else:
        beta = math.degrees(math.atan(cm_blocked / wu))

    # 13. Calculate alpha
    if abs(cu) < 1e-10:
        alpha = 90.0
    else:
        alpha = math.degrees(math.atan(cm_blocked / abs(cu)))
        if cu < 0:
            alpha = 180 - alpha

    return OutletTriangleResult(
        flow_rate=flow_rate,
        radius=radius,
        rpm=rpm,
        beta_blade=beta_blade,
        area=area,
        cm=cm,
        u=u,
        tau=tau,
        k_blockage=k_blockage,
        cm_blocked=cm_blocked,
        slip_method=slip_method,
        gamma=gamma,
        slip_angle=slip_angle,
        beta_blocked=beta_blocked,
        wu=wu,
        w=w,
        beta=beta,
        cu=cu,
        c=c,
        alpha=alpha,
        cu_ideal=cu_ideal,
        c_ideal=c_ideal,
    )


def _calculate_slip(
    beta_blade_deg: float,
    blade_count: int,
    method: str = "Wiesner"
) -> Tuple[float, float]:
    """
    Calculate slip coefficient and slip angle.

    Args:
        beta_blade_deg: Blade exit angle (degrees)
        blade_count: Number of blades
        method: "Wiesner", "Gülich", or "Mock"

    Returns:
        (gamma, slip_angle_deg) - slip coefficient and slip angle
    """
    if method.lower() == "mock":
        # Fixed slip coefficient
        gamma = 0.9
        # Slip angle approximation: δ ≈ (1-γ) × β₂B
        slip_angle = (1 - gamma) * beta_blade_deg
        return (gamma, slip_angle)

    elif method.lower() == "wiesner":
        # Wiesner correlation (1967)
        # γ = 1 - sqrt(sin(β₂B)) / z^0.7
        beta_rad = math.radians(beta_blade_deg)
        sin_beta = abs(math.sin(beta_rad))

        if blade_count <= 0:
            gamma = 1.0
        else:
            gamma = 1.0 - math.sqrt(sin_beta) / (blade_count ** 0.7)
            gamma = max(0.5, min(1.0, gamma))

        # Slip angle from gamma
        # cu_actual = gamma × cu_ideal
        # From geometry: δ ≈ arctan((1-γ) × cu_ideal / cm)
        # Simplified: δ ≈ (1-γ) × β₂B (approximation)
        slip_angle = (1 - gamma) * abs(beta_blade_deg)
        return (gamma, slip_angle)

    elif method.lower() == "gülich" or method.lower() == "gulich":
        # Gülich correlation
        # Similar to Wiesner but with different constants
        beta_rad = math.radians(beta_blade_deg)
        sin_beta = abs(math.sin(beta_rad))

        if blade_count <= 0:
            gamma = 1.0
        else:
            # Gülich: γ = 1 - (π/z) × sqrt(sin(β₂B))
            gamma = 1.0 - (math.pi / blade_count) * math.sqrt(sin_beta)
            gamma = max(0.5, min(1.0, gamma))

        slip_angle = (1 - gamma) * abs(beta_blade_deg)
        return (gamma, slip_angle)

    else:
        # Default to Wiesner
        return _calculate_slip(beta_blade_deg, blade_count, "Wiesner")


def calculate_euler_head(
    cu_in: float,
    cu_out: float,
    u_in: float,
    u_out: float,
    g: float = 9.81
) -> float:
    """
    Calculate Euler head (theoretical head).

    H_euler = (u₂×cu₂ - u₁×cu₁) / g

    For pumps with axial inlet (cu₁=0):
    H_euler = u₂×cu₂ / g

    Args:
        cu_in: Inlet circumferential absolute velocity (m/s)
        cu_out: Outlet circumferential absolute velocity (m/s)
        u_in: Inlet blade speed (m/s)
        u_out: Outlet blade speed (m/s)
        g: Gravitational acceleration (m/s²)

    Returns:
        Euler head (m)
    """
    return (u_out * cu_out - u_in * cu_in) / g


def calculate_swirl_difference(
    cu_in: float,
    cu_out: float,
    r_in: float,
    r_out: float
) -> float:
    """
    Calculate swirl difference Δ(cu×r).

    Δ(cu×r) = cu₂×r₂ - cu₁×r₁

    This is related to torque and Euler work.

    Args:
        cu_in: Inlet circumferential absolute velocity (m/s)
        cu_out: Outlet circumferential absolute velocity (m/s)
        r_in: Inlet radius (m)
        r_out: Outlet radius (m)

    Returns:
        Swirl difference (m²/s)
    """
    return cu_out * r_out - cu_in * r_in


def calculate_torque(
    flow_rate: float,
    cu_in: float,
    cu_out: float,
    r_in: float,
    r_out: float,
    density: float = 1000.0
) -> float:
    """
    Calculate shaft torque.

    T = ρ × Q × Δ(cu×r)
    T = ρ × Q × (cu₂×r₂ - cu₁×r₁)

    Args:
        flow_rate: Volume flow rate (m³/s)
        cu_in: Inlet circumferential absolute velocity (m/s)
        cu_out: Outlet circumferential absolute velocity (m/s)
        r_in: Inlet radius (m)
        r_out: Outlet radius (m)
        density: Fluid density (kg/m³), default 1000 for water

    Returns:
        Torque (N·m)
    """
    delta_cur = calculate_swirl_difference(cu_in, cu_out, r_in, r_out)
    return density * flow_rate * delta_cur


def calculate_velocity_ratios(
    inlet: InletTriangleResult,
    outlet: OutletTriangleResult
) -> Tuple[float, float]:
    """
    Calculate velocity ratios w₂/w₁ and c₂/c₁.

    Args:
        inlet: Inlet triangle result
        outlet: Outlet triangle result

    Returns:
        (w2_w1, c2_c1) velocity ratios
    """
    w2_w1 = outlet.w / inlet.w if inlet.w > 0 else 0.0
    c2_c1 = outlet.c / inlet.c if inlet.c > 0 else 0.0
    return (w2_w1, c2_c1)


def calculate_deflection_angles(
    inlet: InletTriangleResult,
    outlet: OutletTriangleResult
) -> Tuple[float, float]:
    """
    Calculate flow deflection angles.

    Δα_F = α₂ - α₁
    Δβ_F = β₂ - β₁

    Args:
        inlet: Inlet triangle result
        outlet: Outlet triangle result

    Returns:
        (delta_alpha, delta_beta) deflection angles (degrees)
    """
    delta_alpha = outlet.alpha - inlet.alpha
    delta_beta = outlet.beta - inlet.beta
    return (delta_alpha, delta_beta)


def calculate_camber_angle(
    inlet: InletTriangleResult,
    outlet: OutletTriangleResult
) -> float:
    """
    Calculate blade camber angle.

    φ = Δβ_B = β₂B - β₁B

    Args:
        inlet: Inlet triangle result
        outlet: Outlet triangle result

    Returns:
        Camber angle (degrees)
    """
    return outlet.beta_blade - inlet.beta_blade
