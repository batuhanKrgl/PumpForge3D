"""
Blade Properties Module - CFturbo-referenced slip and blade parameter calculations.

Based on CFturbo manual section 7.3.1.4.2.1 (Slip coefficient by Gülich/Wiesner).

References:
- Outflow (slip) coefficient γ: γ = 1 - (cu2∞ - cu2)/u2
- Wiesner formula: γ = 1 - √(sin β2B) / z^0.7
- Gülich modification: γ = f_i * (1 - √(sin β2B) / z^0.7) * k_w

Correction factors:
- f_i: 0.98 for radial impellers, 1.02 + 1.2×10⁻³(r_q - 50) for mixed-flow
- k_w: blockage-related correction involving d_im/d_2 and ε_Lim
"""

from dataclasses import dataclass
from typing import Optional, Literal
import math


@dataclass
class BladeThicknessMatrix:
    """
    Blade thickness distribution at hub/tip × inlet/outlet.

    All thicknesses in mm.
    """
    hub_inlet: float = 2.0
    hub_outlet: float = 1.5
    tip_inlet: float = 2.0
    tip_outlet: float = 1.5

    def get_average_inlet(self) -> float:
        """Average inlet thickness."""
        return (self.hub_inlet + self.tip_inlet) / 2.0

    def get_average_outlet(self) -> float:
        """Average outlet thickness."""
        return (self.hub_outlet + self.tip_outlet) / 2.0


@dataclass
class SlipCalculationResult:
    """
    Result of slip coefficient calculation for a single station (hub or tip).
    """
    # Input parameters
    beta_blade_deg: float  # Blade angle at outlet (degrees)
    blade_count: int       # Number of blades z

    # Slip coefficient
    gamma: float           # Slip coefficient (dimensionless, 0-1)

    # Derived slip angle
    slip_angle_deg: float  # Deviation angle δ = β_flow - β_blade (degrees)

    # Correction factors used
    f_i: float = 1.0       # Impeller type correction
    k_w: float = 1.0       # Blockage correction

    # Method used
    method: str = "Gülich"  # "Gülich", "Wiesner", or "Mock"

    # Warning/info messages
    warning: Optional[str] = None


@dataclass
class BladeProperties:
    """
    Complete blade properties including thickness, count, incidence, and slip.
    """
    # Blade geometry
    thickness: BladeThicknessMatrix
    blade_count: int = 3

    # Inlet parameters
    incidence_deg: float = 0.0  # Incidence angle i (degrees)

    # Outlet slip parameters
    slip_mode: Literal["Mock", "Wiesner", "Gülich"] = "Mock"
    mock_slip_deg: float = 5.0  # Mock slip angle (degrees) when slip_mode="Mock"

    # Specific speed (for mixed-flow correction in Gülich)
    r_q: Optional[float] = None  # Specific speed (dimensionless)

    # Inlet/outlet diameters for k_w calculation (optional, for full Gülich)
    d_inlet_hub_mm: Optional[float] = None
    d_inlet_shroud_mm: Optional[float] = None
    d_outlet_mm: Optional[float] = None


def calculate_wiesner_slip(
    beta_blade_deg: float,
    blade_count: int
) -> SlipCalculationResult:
    """
    Calculate slip coefficient using Wiesner's empirical formula.

    Wiesner formula:
        γ = 1 - √(sin β₂B) / z^0.7

    Args:
        beta_blade_deg: Blade angle at outlet (degrees)
        blade_count: Number of blades z

    Returns:
        SlipCalculationResult with gamma and derived slip angle
    """
    if blade_count < 1:
        return SlipCalculationResult(
            beta_blade_deg=beta_blade_deg,
            blade_count=blade_count,
            gamma=1.0,
            slip_angle_deg=0.0,
            method="Wiesner",
            warning="Invalid blade count (z < 1)"
        )

    # Convert to radians
    beta_rad = math.radians(abs(beta_blade_deg))

    # Wiesner formula: γ = 1 - √(sin β₂B) / z^0.7
    sin_beta = math.sin(beta_rad)
    if sin_beta < 0:
        sin_beta = 0.0

    sqrt_sin_beta = math.sqrt(sin_beta)
    z_power = blade_count ** 0.7

    gamma = 1.0 - sqrt_sin_beta / z_power

    # Clamp gamma to [0, 1]
    gamma = max(0.0, min(1.0, gamma))

    # Derive slip angle approximation
    # From: γ ≈ cos(δ) for small δ => δ ≈ arccos(γ)
    # More accurate: use the fact that slip reduces cu
    # δ ≈ (1 - γ) * β_blade (rough approximation)
    slip_angle_deg = (1.0 - gamma) * abs(beta_blade_deg)

    return SlipCalculationResult(
        beta_blade_deg=beta_blade_deg,
        blade_count=blade_count,
        gamma=gamma,
        slip_angle_deg=slip_angle_deg,
        f_i=1.0,
        k_w=1.0,
        method="Wiesner"
    )


def calculate_gulich_slip(
    beta_blade_deg: float,
    blade_count: int,
    r_q: Optional[float] = None,
    d_inlet_hub_mm: Optional[float] = None,
    d_inlet_shroud_mm: Optional[float] = None,
    d_outlet_mm: Optional[float] = None
) -> SlipCalculationResult:
    """
    Calculate slip coefficient using Gülich's modified formula.

    Gülich formula:
        γ = f_i * (1 - √(sin β₂B) / z^0.7) * k_w

    Correction factors:
        f_i = 0.98 for radial impellers (r_q not provided)
        f_i = max(0.98, 1.02 + 1.2×10⁻³(r_q - 50)) for mixed-flow

        k_w requires inlet/outlet diameters:
            d_im = √(0.5 * (d_i,Shroud² + d_i,Hub²))
            ε_Lim = exp(-8.16 sin β₂B / z)
            k_w = 1 if d_im/d_2 ≤ ε_Lim
            k_w = 1 - ((d_im/d_2 - ε_Lim) / (1 - ε_Lim)) otherwise

    Args:
        beta_blade_deg: Blade angle at outlet (degrees)
        blade_count: Number of blades z
        r_q: Specific speed (dimensionless), optional
        d_inlet_hub_mm: Inlet hub diameter (mm), optional
        d_inlet_shroud_mm: Inlet shroud diameter (mm), optional
        d_outlet_mm: Outlet diameter (mm), optional

    Returns:
        SlipCalculationResult with gamma and derived slip angle
    """
    # Start with Wiesner as base
    base = calculate_wiesner_slip(beta_blade_deg, blade_count)

    # Calculate f_i correction
    if r_q is not None:
        # Mixed-flow correction
        f_i = max(0.98, 1.02 + 1.2e-3 * (r_q - 50))
    else:
        # Radial impeller
        f_i = 0.98

    # Calculate k_w correction if diameters are provided
    k_w = 1.0
    warning = None

    if all(d is not None for d in [d_inlet_hub_mm, d_inlet_shroud_mm, d_outlet_mm]):
        # Full Gülich calculation with k_w
        d_hub = d_inlet_hub_mm
        d_shroud = d_inlet_shroud_mm
        d_2 = d_outlet_mm

        # d_im = √(0.5 * (d_shroud² + d_hub²))
        d_im = math.sqrt(0.5 * (d_shroud**2 + d_hub**2))

        # ε_Lim = exp(-8.16 sin β₂B / z)
        beta_rad = math.radians(abs(beta_blade_deg))
        sin_beta = math.sin(beta_rad)
        epsilon_lim = math.exp(-8.16 * sin_beta / blade_count)

        # k_w calculation
        d_ratio = d_im / d_2 if d_2 > 0 else 0.0

        if d_ratio <= epsilon_lim:
            k_w = 1.0
        else:
            if epsilon_lim < 1.0:
                k_w = 1.0 - (d_ratio - epsilon_lim) / (1.0 - epsilon_lim)
            else:
                k_w = 1.0
                warning = "ε_Lim ≥ 1.0, k_w set to 1.0"

        # Clamp k_w to [0, 1]
        k_w = max(0.0, min(1.0, k_w))
    else:
        warning = "Diameters not provided, k_w = 1.0"

    # Apply corrections to base Wiesner gamma
    # γ_Gülich = f_i * γ_Wiesner * k_w
    # But Wiesner already has the (1 - √sin/z^0.7) term, so:
    # γ = f_i * (1 - √sin/z^0.7) * k_w
    gamma_wiesner_term = (1.0 - (1.0 - base.gamma))  # Extract the base term
    gamma = f_i * base.gamma * k_w

    # Clamp gamma to [0, 1]
    gamma = max(0.0, min(1.0, gamma))

    # Derive slip angle
    slip_angle_deg = (1.0 - gamma) * abs(beta_blade_deg)

    return SlipCalculationResult(
        beta_blade_deg=beta_blade_deg,
        blade_count=blade_count,
        gamma=gamma,
        slip_angle_deg=slip_angle_deg,
        f_i=f_i,
        k_w=k_w,
        method="Gülich",
        warning=warning
    )


def calculate_slip(
    beta_blade_deg: float,
    blade_count: int,
    slip_mode: Literal["Mock", "Wiesner", "Gülich"] = "Mock",
    mock_slip_deg: float = 5.0,
    r_q: Optional[float] = None,
    d_inlet_hub_mm: Optional[float] = None,
    d_inlet_shroud_mm: Optional[float] = None,
    d_outlet_mm: Optional[float] = None
) -> SlipCalculationResult:
    """
    Calculate slip using the selected method.

    Args:
        beta_blade_deg: Blade angle at outlet (degrees)
        blade_count: Number of blades z
        slip_mode: Calculation method ("Mock", "Wiesner", or "Gülich")
        mock_slip_deg: Mock slip angle (degrees), used when slip_mode="Mock"
        r_q: Specific speed (for Gülich mixed-flow correction)
        d_inlet_hub_mm: Inlet hub diameter (for Gülich k_w)
        d_inlet_shroud_mm: Inlet shroud diameter (for Gülich k_w)
        d_outlet_mm: Outlet diameter (for Gülich k_w)

    Returns:
        SlipCalculationResult with gamma and slip angle
    """
    if slip_mode == "Mock":
        # Direct slip angle input
        # Approximate gamma from slip angle: γ ≈ 1 - δ/β_blade
        if abs(beta_blade_deg) > 0.1:
            gamma = 1.0 - abs(mock_slip_deg) / abs(beta_blade_deg)
        else:
            gamma = 1.0

        gamma = max(0.0, min(1.0, gamma))

        return SlipCalculationResult(
            beta_blade_deg=beta_blade_deg,
            blade_count=blade_count,
            gamma=gamma,
            slip_angle_deg=mock_slip_deg,
            f_i=1.0,
            k_w=1.0,
            method="Mock"
        )

    elif slip_mode == "Wiesner":
        return calculate_wiesner_slip(beta_blade_deg, blade_count)

    elif slip_mode == "Gülich":
        return calculate_gulich_slip(
            beta_blade_deg,
            blade_count,
            r_q,
            d_inlet_hub_mm,
            d_inlet_shroud_mm,
            d_outlet_mm
        )

    else:
        # Default to Mock
        return calculate_slip(
            beta_blade_deg,
            blade_count,
            "Mock",
            mock_slip_deg
        )


def calculate_cu_slipped(
    u2: float,
    cu2_infinity: float,
    gamma: float
) -> float:
    """
    Calculate actual cu2 with slip from the theoretical cu2∞.

    From the definition:
        γ = 1 - (cu2∞ - cu2) / u2

    Rearranging:
        cu2 = cu2∞ - (1 - γ) * u2

    Args:
        u2: Blade speed at outlet (m/s)
        cu2_infinity: Theoretical circumferential velocity (m/s)
        gamma: Slip coefficient (0-1)

    Returns:
        Actual cu2 with slip (m/s)
    """
    return cu2_infinity - (1.0 - gamma) * u2


def calculate_average_slip(
    slip_hub: SlipCalculationResult,
    slip_tip: SlipCalculationResult
) -> SlipCalculationResult:
    """
    Calculate average slip coefficient from hub and tip values.

    Per CFturbo manual:
        γ = 0.5 * (γ_Hub + γ_Shroud)

    Args:
        slip_hub: Hub slip result
        slip_tip: Tip (shroud) slip result

    Returns:
        Averaged SlipCalculationResult
    """
    gamma_avg = 0.5 * (slip_hub.gamma + slip_tip.gamma)
    slip_angle_avg = 0.5 * (slip_hub.slip_angle_deg + slip_tip.slip_angle_deg)
    f_i_avg = 0.5 * (slip_hub.f_i + slip_tip.f_i)
    k_w_avg = 0.5 * (slip_hub.k_w + slip_tip.k_w)
    beta_avg = 0.5 * (slip_hub.beta_blade_deg + slip_tip.beta_blade_deg)

    warnings = []
    if slip_hub.warning:
        warnings.append(f"Hub: {slip_hub.warning}")
    if slip_tip.warning:
        warnings.append(f"Tip: {slip_tip.warning}")

    warning = "; ".join(warnings) if warnings else None

    return SlipCalculationResult(
        beta_blade_deg=beta_avg,
        blade_count=slip_hub.blade_count,
        gamma=gamma_avg,
        slip_angle_deg=slip_angle_avg,
        f_i=f_i_avg,
        k_w=k_w_avg,
        method=slip_hub.method,
        warning=warning
    )
