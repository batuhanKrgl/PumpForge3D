"""
Turbomachinery Calculation Engine.

Orchestrates complete velocity triangle calculation workflow:
- Inlet triangle: area → cm → u → cu → wu → beta → blockage → beta_blocked → beta_blade
- Outlet triangle: area → cm → beta_blade → blockage → slip → beta_blocked → wu → cu → alpha

Based on CFturbo methodology and velocity triangle theory.
"""

from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple
import math
import numpy as np

from .velocity_triangle import (
    TriangleData,
    calculate_flow_area,
    calculate_blockage_factor,
    calculate_meridional_velocity
)
from .blade_properties import (
    calculate_slip,
    SlipCalculationResult,
    BladeThicknessMatrix
)
from ..geometry.blade_geometry import BladeGeometry, GeometryAtSpan


@dataclass
class OperatingConditions:
    """Operating conditions for turbomachinery calculations."""

    rpm: float  # Rotational speed [rev/min]
    flow_rate: float  # Volume flow rate [m³/s]
    alpha_inlet_deg: float = 90.0  # Inlet absolute flow angle [degrees]

    # Optional fluid properties
    density: float = 1000.0  # Fluid density [kg/m³], default water


@dataclass
class InletTriangleResult:
    """
    Complete inlet triangle calculation result at a single span.

    Follows the calculation flow:
    1. Area calculation
    2. cm calculation (from Q and area)
    3. u calculation (from rpm and radius)
    4. cu calculation (from alpha)
    5. wu calculation (u - cu)
    6. beta calculation (arctan)
    7. Blockage calculation
    8. cm_blocked calculation
    9. beta_blocked calculation (recalculated with cm_blocked)
    10. beta_blade calculation (beta_blocked + incidence)
    """

    # Input parameters
    span: float
    geometry: GeometryAtSpan

    # Basic triangle (without blockage)
    triangle: TriangleData

    # Blockage effects
    k_blockage: float
    cm_blocked: float
    beta_blocked: float

    # Blade angle
    incidence: float
    beta_blade: float


@dataclass
class OutletTriangleResult:
    """
    Complete outlet triangle calculation result at a single span.

    Follows the calculation flow:
    1. Area calculation
    2. cm calculation (from Q and area)
    3. u calculation (from rpm and radius)
    4. beta_blade selection (user input)
    5. Blockage calculation
    6. Slip calculation (from beta_blade)
    7. beta_blocked calculation (beta_blade - slip)
    8. wu calculation (from beta_blocked and cm_blocked)
    9. cu calculation (u - wu)
    10. alpha calculation (arctan)
    """

    # Input parameters
    span: float
    geometry: GeometryAtSpan

    # Basic triangle (theoretical, without slip)
    triangle_theoretical: TriangleData

    # Blockage effects
    k_blockage: float
    cm_blocked: float

    # Slip effects
    slip_result: SlipCalculationResult
    beta_blocked: float
    beta_blade: float

    # Actual triangle (with slip)
    triangle_actual: TriangleData


class TurbomachineryCalculation:
    """
    Main calculation engine for velocity triangles.

    Handles complete calculation workflow for both inlet and outlet
    at multiple span positions.
    """

    def __init__(
        self,
        geometry: BladeGeometry,
        operating_conditions: OperatingConditions,
        thickness: BladeThicknessMatrix,
        blade_count: int = 3
    ):
        """
        Initialize calculation engine.

        Args:
            geometry: Blade geometry
            operating_conditions: Operating conditions (rpm, Q, alpha)
            thickness: Blade thickness matrix
            blade_count: Number of blades
        """
        self.geometry = geometry
        self.operating_conditions = operating_conditions
        self.thickness = thickness
        self.blade_count = blade_count

    def calculate_inlet_triangle(
        self,
        span: float,
        incidence: float = 0.0
    ) -> InletTriangleResult:
        """
        Calculate inlet velocity triangle at given span position.

        Calculation flow:
        1. Get geometry at span → area, radius
        2. Calculate cm = Q / area
        3. Calculate u = π × d × n / 60
        4. Calculate cu from alpha: cu = cm × tan(alpha) (or 0 if alpha=90°)
        5. Calculate wu = u - cu
        6. Calculate beta = arctan(cm / wu)
        7. Calculate blockage factor k
        8. Calculate cm_blocked = cm × k
        9. Recalculate beta_blocked = arctan(cm_blocked / wu)
        10. Calculate beta_blade = beta_blocked + incidence

        Args:
            span: Span position (0 = hub, 1 = tip)
            incidence: Incidence angle [degrees]

        Returns:
            InletTriangleResult with all calculated values
        """
        # 1. Get geometry at span
        geom = self.geometry.get_geometry_at_span(span)

        # 2. Calculate cm = Q / area
        Q = self.operating_conditions.flow_rate
        cm = Q / geom.area_inlet  # Simple formula: cm = Q / A

        # 3. Calculate u = ω × r = (2πn/60) × r
        rpm = self.operating_conditions.rpm
        omega = rpm * 2.0 * math.pi / 60.0  # [rad/s]
        u = omega * geom.r_inlet

        # 4. Calculate cu from alpha
        alpha_deg = self.operating_conditions.alpha_inlet_deg
        if abs(alpha_deg - 90.0) < 0.1:
            # Pure meridional flow (no preswirl)
            cu = 0.0
        else:
            alpha_rad = math.radians(alpha_deg)
            cu = cm / math.tan(alpha_rad)  # cu = cm / tan(α)

        # 5. Calculate wu = u - cu (velocity triangle identity)
        wu = u - cu

        # 6. Calculate beta = arctan(cm / wu)
        if abs(wu) < 0.001:
            beta = 90.0  # Purely meridional relative flow
        else:
            beta_rad = math.atan(cm / abs(wu))
            beta = math.degrees(beta_rad)
            if wu < 0:
                beta = 180.0 - beta

        # 7. Calculate blockage factor
        # Interpolate thickness at this span
        t_inlet = self.thickness.hub_inlet + span * (self.thickness.tip_inlet - self.thickness.hub_inlet)
        t_inlet_m = t_inlet / 1000.0  # Convert mm to m

        k_blockage = calculate_blockage_factor(
            blade_count=self.blade_count,
            thickness_avg=t_inlet_m,
            diameter_mean=geom.d_mean
        )

        # 8. Calculate cm_blocked = cm × k
        cm_blocked = cm * k_blockage

        # 9. Recalculate beta_blocked with cm_blocked
        if abs(wu) < 0.001:
            beta_blocked = 90.0
        else:
            beta_blocked_rad = math.atan(cm_blocked / abs(wu))
            beta_blocked = math.degrees(beta_blocked_rad)
            if wu < 0:
                beta_blocked = 180.0 - beta_blocked

        # 10. Calculate beta_blade = beta_blocked + incidence
        beta_blade = beta_blocked + incidence

        # Create base triangle data
        c = math.sqrt(cu**2 + cm**2)
        w = math.sqrt(wu**2 + cm**2)

        # Recalculate alpha
        if abs(cu) < 0.001:
            alpha = 90.0
        else:
            alpha = math.degrees(math.atan(cm / abs(cu)))
            if cu < 0:
                alpha = 180.0 - alpha

        triangle = TriangleData(
            u=u,
            cm=cm,
            cu=cu,
            wu=wu,
            c=c,
            w=w,
            beta=beta,
            alpha=alpha,
            radius=geom.r_inlet,
            rpm=rpm
        )

        return InletTriangleResult(
            span=span,
            geometry=geom,
            triangle=triangle,
            k_blockage=k_blockage,
            cm_blocked=cm_blocked,
            beta_blocked=beta_blocked,
            incidence=incidence,
            beta_blade=beta_blade
        )

    def calculate_outlet_triangle(
        self,
        span: float,
        beta_blade: float,
        slip_mode: Literal["Mock", "Wiesner", "Gülich"] = "Mock",
        mock_slip_deg: float = 5.0
    ) -> OutletTriangleResult:
        """
        Calculate outlet velocity triangle at given span position.

        Calculation flow:
        1. Get geometry at span → area, radius
        2. Calculate cm = Q / area
        3. Calculate u = π × d × n / 60
        4. Use selected beta_blade (user input)
        5. Calculate blockage factor k
        6. Calculate cm_blocked = cm × k
        7. Calculate slip angle (using selected method)
        8. Calculate beta_blocked = beta_blade - slip
        9. Calculate wu from beta_blocked: wu = cm_blocked / tan(beta_blocked)
        10. Calculate cu = u - wu
        11. Calculate alpha = arctan(cm / cu)

        Args:
            span: Span position (0 = hub, 1 = tip)
            beta_blade: Blade angle at outlet [degrees]
            slip_mode: Slip calculation method
            mock_slip_deg: Mock slip angle if using Mock mode

        Returns:
            OutletTriangleResult with all calculated values
        """
        # 1. Get geometry at span
        geom = self.geometry.get_geometry_at_span(span)

        # 2. Calculate cm = Q / area
        Q = self.operating_conditions.flow_rate
        cm = Q / geom.area_outlet

        # 3. Calculate u = ω × r
        rpm = self.operating_conditions.rpm
        omega = rpm * 2.0 * math.pi / 60.0
        u = omega * geom.r_outlet

        # 5. Calculate blockage factor
        t_outlet = self.thickness.hub_outlet + span * (self.thickness.tip_outlet - self.thickness.hub_outlet)
        t_outlet_m = t_outlet / 1000.0  # Convert mm to m

        k_blockage = calculate_blockage_factor(
            blade_count=self.blade_count,
            thickness_avg=t_outlet_m,
            diameter_mean=geom.d_mean
        )

        # 6. Calculate cm_blocked
        cm_blocked = cm * k_blockage

        # 7. Calculate slip
        slip_result = calculate_slip(
            beta_blade_deg=beta_blade,
            blade_count=self.blade_count,
            slip_mode=slip_mode,
            mock_slip_deg=mock_slip_deg,
            d_inlet_hub_mm=self.geometry.r_hub_inlet * 2000.0,  # Convert m to mm
            d_inlet_shroud_mm=self.geometry.r_tip_inlet * 2000.0,
            d_outlet_mm=geom.d_outlet * 1000.0
        )

        # 8. Calculate beta_blocked = beta_blade - slip
        beta_blocked = beta_blade - slip_result.slip_angle_deg

        # 9. Calculate wu from beta_blocked
        beta_blocked_rad = math.radians(beta_blocked)
        tan_beta_blocked = math.tan(beta_blocked_rad)

        if abs(tan_beta_blocked) < 0.01:
            wu = cm_blocked * 100.0  # Clamp for numerical stability
        else:
            wu = cm_blocked / tan_beta_blocked

        # 10. Calculate cu = u - wu
        cu = u - wu

        # 11. Calculate alpha
        if abs(cu) < 0.001:
            alpha = 90.0
        else:
            alpha = math.degrees(math.atan(cm / abs(cu)))
            if cu < 0:
                alpha = 180.0 - alpha

        # Calculate beta from wu
        if abs(wu) < 0.001:
            beta = 90.0
        else:
            beta = math.degrees(math.atan(cm / abs(wu)))
            if wu < 0:
                beta = 180.0 - beta

        # Create actual triangle (with slip)
        c = math.sqrt(cu**2 + cm**2)
        w = math.sqrt(wu**2 + cm**2)

        triangle_actual = TriangleData(
            u=u,
            cm=cm,
            cu=cu,
            wu=wu,
            c=c,
            w=w,
            beta=beta,
            alpha=alpha,
            radius=geom.r_outlet,
            rpm=rpm
        )

        # Create theoretical triangle (no slip, beta = beta_blade)
        wu_theoretical = cm / math.tan(math.radians(beta_blade))
        cu_theoretical = u - wu_theoretical
        c_theoretical = math.sqrt(cu_theoretical**2 + cm**2)
        w_theoretical = math.sqrt(wu_theoretical**2 + cm**2)

        triangle_theoretical = TriangleData(
            u=u,
            cm=cm,
            cu=cu_theoretical,
            wu=wu_theoretical,
            c=c_theoretical,
            w=w_theoretical,
            beta=beta_blade,
            alpha=math.degrees(math.atan(cm / abs(cu_theoretical))) if abs(cu_theoretical) > 0.001 else 90.0,
            radius=geom.r_outlet,
            rpm=rpm
        )

        return OutletTriangleResult(
            span=span,
            geometry=geom,
            triangle_theoretical=triangle_theoretical,
            k_blockage=k_blockage,
            cm_blocked=cm_blocked,
            slip_result=slip_result,
            beta_blocked=beta_blocked,
            beta_blade=beta_blade,
            triangle_actual=triangle_actual
        )

    def calculate_at_spans(
        self,
        spans: np.ndarray,
        incidence_hub: float = 0.0,
        incidence_tip: float = 0.0,
        beta_blade_hub_inlet: float = 25.0,
        beta_blade_tip_inlet: float = 30.0,
        beta_blade_hub_outlet: float = 55.0,
        beta_blade_tip_outlet: float = 60.0,
        slip_mode: Literal["Mock", "Wiesner", "Gülich"] = "Mock",
        mock_slip_deg: float = 5.0
    ) -> Tuple[List[InletTriangleResult], List[OutletTriangleResult]]:
        """
        Calculate velocity triangles at multiple span positions.

        Incidence and beta blade angles are linearly interpolated between
        hub and tip values.

        Args:
            spans: Array of span positions (0 = hub, 1 = tip)
            incidence_hub: Incidence at hub [degrees]
            incidence_tip: Incidence at tip [degrees]
            beta_blade_hub_inlet: Inlet blade angle at hub [degrees]
            beta_blade_tip_inlet: Inlet blade angle at tip [degrees]
            beta_blade_hub_outlet: Outlet blade angle at hub [degrees]
            beta_blade_tip_outlet: Outlet blade angle at tip [degrees]
            slip_mode: Slip calculation method
            mock_slip_deg: Mock slip angle

        Returns:
            (inlet_results, outlet_results) - Lists of results for each span
        """
        inlet_results = []
        outlet_results = []

        for span in spans:
            # Interpolate incidence
            incidence = incidence_hub + span * (incidence_tip - incidence_hub)

            # Interpolate outlet beta blade
            beta_blade_outlet = beta_blade_hub_outlet + span * (beta_blade_tip_outlet - beta_blade_hub_outlet)

            # Calculate inlet triangle
            inlet_result = self.calculate_inlet_triangle(span, incidence)
            inlet_results.append(inlet_result)

            # Calculate outlet triangle
            outlet_result = self.calculate_outlet_triangle(
                span, beta_blade_outlet, slip_mode, mock_slip_deg
            )
            outlet_results.append(outlet_result)

        return inlet_results, outlet_results

    def calculate_head(self, inlet_results: List[InletTriangleResult], outlet_results: List[OutletTriangleResult]) -> float:
        """
        Calculate theoretical head from Euler turbomachine equation.

        H = (u2 × cu2 - u1 × cu1) / g

        Uses average values across spans.

        Args:
            inlet_results: List of inlet triangle results
            outlet_results: List of outlet triangle results

        Returns:
            Theoretical head [m]
        """
        g = 9.81  # [m/s²]

        # Average inlet and outlet cu × u products
        u1_cu1_avg = np.mean([r.triangle.u * r.triangle.cu for r in inlet_results])
        u2_cu2_avg = np.mean([r.triangle_actual.u * r.triangle_actual.cu for r in outlet_results])

        # Euler head
        H = (u2_cu2_avg - u1_cu1_avg) / g

        return H