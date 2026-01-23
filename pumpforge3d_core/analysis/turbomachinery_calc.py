"""
Turbomachinery Calculator Class.

Provides comprehensive calculation methods for turbomachinery design:
- Inlet and outlet velocity triangles
- Blockage calculations
- Slip calculations
- Head and torque calculations
- Performance parameters

Takes inputs from TurbomachineryGeometry class.
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
import math
import numpy as np
from numpy.typing import NDArray

from ..geometry.turbomachinery_geometry import TurbomachineryGeometry, StationGeometry
from .velocity_triangle import (
    InletTriangleResult,
    OutletTriangleResult,
    compute_inlet_triangle,
    compute_outlet_triangle,
    calculate_euler_head,
    calculate_swirl_difference,
    calculate_torque,
    calculate_velocity_ratios,
    calculate_deflection_angles,
    calculate_camber_angle,
    calculate_flow_area,
    calculate_obstruction_factor,
    calculate_blockage_factor,
)


@dataclass
class OperatingConditions:
    """
    Operating conditions for turbomachinery calculations.
    """
    flow_rate: float = 0.01      # Q (m³/s)
    rpm: float = 3000.0          # n (rev/min)
    density: float = 1000.0      # ρ (kg/m³)
    alpha_inlet: float = 90.0    # α₁ (degrees) - inlet flow angle

    @property
    def omega(self) -> float:
        """Angular velocity (rad/s)."""
        return self.rpm * 2 * math.pi / 60

    def to_dict(self) -> dict:
        return {
            "flow_rate": self.flow_rate,
            "rpm": self.rpm,
            "density": self.density,
            "alpha_inlet": self.alpha_inlet,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OperatingConditions":
        return cls(
            flow_rate=data.get("flow_rate", 0.01),
            rpm=data.get("rpm", 3000.0),
            density=data.get("density", 1000.0),
            alpha_inlet=data.get("alpha_inlet", 90.0),
        )


@dataclass
class StationCalculationResult:
    """
    Calculation results at a single station for both hub and tip.
    """
    station_name: str
    hub: InletTriangleResult | OutletTriangleResult
    tip: InletTriangleResult | OutletTriangleResult

    def get_value(self, param: str, span: str = "hub") -> float:
        """Get parameter value for hub or tip."""
        triangle = self.hub if span.lower() == "hub" else self.tip
        return getattr(triangle, param, 0.0)


@dataclass
class PerformanceResult:
    """
    Overall performance calculation results.
    """
    # Velocity ratios
    w2_w1_hub: float
    w2_w1_tip: float
    c2_c1_hub: float
    c2_c1_tip: float

    # Deflection angles
    delta_alpha_hub: float
    delta_alpha_tip: float
    delta_beta_hub: float
    delta_beta_tip: float

    # Camber angles
    camber_hub: float
    camber_tip: float

    # Swirl difference
    delta_cur_hub: float
    delta_cur_tip: float

    # Head and torque
    euler_head_hub: float
    euler_head_tip: float
    euler_head_mean: float
    torque: float
    power: float  # W

    # Slip coefficients
    gamma_hub: float
    gamma_tip: float


@dataclass
class InfoTableData:
    """
    Data structure for the info table display.

    Contains all parameters needed for the redesigned info table:
    - Hub inlet/outlet values
    - Tip inlet/outlet values
    - Merged (single) values for ratios and differences
    """
    # Position values (z, r, d)
    z_hub_in: float
    z_hub_out: float
    z_tip_in: float
    z_tip_out: float
    r_hub_in: float
    r_hub_out: float
    r_tip_in: float
    r_tip_out: float
    d_hub_in: float
    d_hub_out: float
    d_tip_in: float
    d_tip_out: float

    # Flow angles (αF, βF)
    alpha_hub_in: float
    alpha_hub_out: float
    alpha_tip_in: float
    alpha_tip_out: float
    beta_hub_in: float
    beta_hub_out: float
    beta_tip_in: float
    beta_tip_out: float

    # Velocities (u, cm, cu, cr, cz, c, wu, w)
    u_hub_in: float
    u_hub_out: float
    u_tip_in: float
    u_tip_out: float
    cm_hub_in: float
    cm_hub_out: float
    cm_tip_in: float
    cm_tip_out: float
    cu_hub_in: float
    cu_hub_out: float
    cu_tip_in: float
    cu_tip_out: float
    cr_hub_in: float
    cr_hub_out: float
    cr_tip_in: float
    cr_tip_out: float
    cz_hub_in: float
    cz_hub_out: float
    cz_tip_in: float
    cz_tip_out: float
    c_hub_in: float
    c_hub_out: float
    c_tip_in: float
    c_tip_out: float
    wu_hub_in: float
    wu_hub_out: float
    wu_tip_in: float
    wu_tip_out: float
    w_hub_in: float
    w_hub_out: float
    w_tip_in: float
    w_tip_out: float

    # cu·r values
    cur_hub_in: float
    cur_hub_out: float
    cur_tip_in: float
    cur_tip_out: float

    # Blockage (τ)
    tau_hub_in: float
    tau_hub_out: float
    tau_tip_in: float
    tau_tip_out: float

    # Incidence/Deviation (i|δ)
    i_hub_in: float  # incidence at inlet
    delta_hub_out: float  # deviation at outlet
    i_tip_in: float
    delta_tip_out: float

    # Merged values (single values spanning both columns)
    w2_w1_hub: float
    w2_w1_tip: float
    c2_c1_hub: float
    c2_c1_tip: float
    delta_alpha_hub: float
    delta_alpha_tip: float
    delta_beta_hub: float
    delta_beta_tip: float
    camber_hub: float  # φ = ΔβB
    camber_tip: float
    gamma_hub: float  # slip coefficient
    gamma_tip: float
    delta_cur_hub: float  # Δ(cu·r)
    delta_cur_tip: float
    torque: float  # T
    head: float  # H


class TurbomachineryCalculator:
    """
    Main calculator class for turbomachinery design.

    Takes geometry from TurbomachineryGeometry and operating conditions
    to compute velocity triangles, performance, and all derived parameters.
    """

    def __init__(
        self,
        geometry: TurbomachineryGeometry,
        operating: Optional[OperatingConditions] = None
    ):
        """
        Initialize calculator with geometry and operating conditions.

        Args:
            geometry: TurbomachineryGeometry instance
            operating: OperatingConditions (optional, uses defaults if None)
        """
        self.geometry = geometry
        self.operating = operating or OperatingConditions()

        # Cached results
        self._inlet_hub: Optional[InletTriangleResult] = None
        self._inlet_tip: Optional[InletTriangleResult] = None
        self._outlet_hub: Optional[OutletTriangleResult] = None
        self._outlet_tip: Optional[OutletTriangleResult] = None
        self._performance: Optional[PerformanceResult] = None
        self._dirty = True

    def set_operating_conditions(self, operating: OperatingConditions):
        """Update operating conditions and mark for recalculation."""
        self.operating = operating
        self._dirty = True

    def set_flow_rate(self, Q: float):
        """Set flow rate (m³/s)."""
        self.operating.flow_rate = Q
        self._dirty = True

    def set_rpm(self, rpm: float):
        """Set rotational speed (rev/min)."""
        self.operating.rpm = rpm
        self._dirty = True

    def set_geometry(self, geometry: TurbomachineryGeometry):
        """Update geometry and mark for recalculation."""
        self.geometry = geometry
        self._dirty = True

    def invalidate(self):
        """Mark results as dirty, forcing recalculation."""
        self._dirty = True

    def calculate_all(self) -> None:
        """
        Perform all calculations.

        Computes inlet and outlet triangles for hub and tip,
        then derives performance parameters.
        """
        if not self._dirty:
            return

        geo = self.geometry
        op = self.operating

        # Inlet triangles
        self._inlet_hub = compute_inlet_triangle(
            flow_rate=op.flow_rate,
            r_hub=geo.inlet.r_hub,
            r_tip=geo.inlet.r_tip,
            rpm=op.rpm,
            span_fraction=0.0,  # hub
            alpha_inlet=op.alpha_inlet,
            incidence=geo.incidence_hub,
            blade_count=geo.blade_count,
            thickness=geo.inlet.thickness_hub,
        )

        self._inlet_tip = compute_inlet_triangle(
            flow_rate=op.flow_rate,
            r_hub=geo.inlet.r_hub,
            r_tip=geo.inlet.r_tip,
            rpm=op.rpm,
            span_fraction=1.0,  # tip
            alpha_inlet=op.alpha_inlet,
            incidence=geo.incidence_tip,
            blade_count=geo.blade_count,
            thickness=geo.inlet.thickness_tip,
        )

        # Outlet triangles
        self._outlet_hub = compute_outlet_triangle(
            flow_rate=op.flow_rate,
            r_hub=geo.outlet.r_hub,
            r_tip=geo.outlet.r_tip,
            rpm=op.rpm,
            beta_blade=geo.beta_blade_hub_outlet,
            span_fraction=0.0,  # hub
            blade_count=geo.blade_count,
            thickness=geo.outlet.thickness_hub,
            slip_method="Wiesner",
        )

        self._outlet_tip = compute_outlet_triangle(
            flow_rate=op.flow_rate,
            r_hub=geo.outlet.r_hub,
            r_tip=geo.outlet.r_tip,
            rpm=op.rpm,
            beta_blade=geo.beta_blade_tip_outlet,
            span_fraction=1.0,  # tip
            blade_count=geo.blade_count,
            thickness=geo.outlet.thickness_tip,
            slip_method="Wiesner",
        )

        # Performance calculations
        self._calculate_performance()

        self._dirty = False

    def _calculate_performance(self):
        """Calculate derived performance parameters."""
        ih = self._inlet_hub
        it = self._inlet_tip
        oh = self._outlet_hub
        ot = self._outlet_tip

        # Velocity ratios
        w2_w1_hub = oh.w / ih.w if ih.w > 0 else 0.0
        w2_w1_tip = ot.w / it.w if it.w > 0 else 0.0
        c2_c1_hub = oh.c / ih.c if ih.c > 0 else 0.0
        c2_c1_tip = ot.c / it.c if it.c > 0 else 0.0

        # Deflection angles
        delta_alpha_hub = oh.alpha - ih.alpha
        delta_alpha_tip = ot.alpha - it.alpha
        delta_beta_hub = oh.beta - ih.beta
        delta_beta_tip = ot.beta - it.beta

        # Camber angles
        camber_hub = oh.beta_blade - ih.beta_blade
        camber_tip = ot.beta_blade - it.beta_blade

        # Swirl difference
        delta_cur_hub = oh.cu * oh.radius - ih.cu * ih.radius
        delta_cur_tip = ot.cu * ot.radius - it.cu * it.radius

        # Euler head
        euler_head_hub = calculate_euler_head(ih.cu, oh.cu, ih.u, oh.u)
        euler_head_tip = calculate_euler_head(it.cu, ot.cu, it.u, ot.u)
        euler_head_mean = (euler_head_hub + euler_head_tip) / 2.0

        # Torque (using mean values)
        torque = calculate_torque(
            self.operating.flow_rate,
            (ih.cu + it.cu) / 2,
            (oh.cu + ot.cu) / 2,
            (ih.radius + it.radius) / 2,
            (oh.radius + ot.radius) / 2,
            self.operating.density,
        )

        # Power
        power = torque * self.operating.omega

        self._performance = PerformanceResult(
            w2_w1_hub=w2_w1_hub,
            w2_w1_tip=w2_w1_tip,
            c2_c1_hub=c2_c1_hub,
            c2_c1_tip=c2_c1_tip,
            delta_alpha_hub=delta_alpha_hub,
            delta_alpha_tip=delta_alpha_tip,
            delta_beta_hub=delta_beta_hub,
            delta_beta_tip=delta_beta_tip,
            camber_hub=camber_hub,
            camber_tip=camber_tip,
            delta_cur_hub=delta_cur_hub,
            delta_cur_tip=delta_cur_tip,
            euler_head_hub=euler_head_hub,
            euler_head_tip=euler_head_tip,
            euler_head_mean=euler_head_mean,
            torque=torque,
            power=power,
            gamma_hub=oh.gamma,
            gamma_tip=ot.gamma,
        )

    @property
    def inlet_hub(self) -> InletTriangleResult:
        """Get inlet hub triangle result."""
        self.calculate_all()
        return self._inlet_hub

    @property
    def inlet_tip(self) -> InletTriangleResult:
        """Get inlet tip triangle result."""
        self.calculate_all()
        return self._inlet_tip

    @property
    def outlet_hub(self) -> OutletTriangleResult:
        """Get outlet hub triangle result."""
        self.calculate_all()
        return self._outlet_hub

    @property
    def outlet_tip(self) -> OutletTriangleResult:
        """Get outlet tip triangle result."""
        self.calculate_all()
        return self._outlet_tip

    @property
    def performance(self) -> PerformanceResult:
        """Get performance calculation result."""
        self.calculate_all()
        return self._performance

    def get_inlet_station(self) -> StationCalculationResult:
        """Get inlet station results."""
        self.calculate_all()
        return StationCalculationResult(
            station_name="inlet",
            hub=self._inlet_hub,
            tip=self._inlet_tip,
        )

    def get_outlet_station(self) -> StationCalculationResult:
        """Get outlet station results."""
        self.calculate_all()
        return StationCalculationResult(
            station_name="outlet",
            hub=self._outlet_hub,
            tip=self._outlet_tip,
        )

    def compute_blockage(
        self,
        thickness: float,
        blade_count: int,
        beta: float,
        radius: float
    ) -> Tuple[float, float]:
        """
        Compute blockage parameters.

        Args:
            thickness: Blade thickness (m)
            blade_count: Number of blades
            beta: Flow angle (degrees)
            radius: Radius (m)

        Returns:
            (tau, k_blockage) - obstruction factor and blockage multiplier
        """
        d_mean = 2.0 * radius
        tau = calculate_obstruction_factor(blade_count, thickness, d_mean)
        k = calculate_blockage_factor(blade_count, thickness, d_mean)
        return (tau, k)

    def compute_slip(
        self,
        beta_blade: float,
        blade_count: int,
        method: str = "Wiesner"
    ) -> Tuple[float, float]:
        """
        Compute slip coefficient and angle.

        Args:
            beta_blade: Blade exit angle (degrees)
            blade_count: Number of blades
            method: "Wiesner", "Gülich", or "Mock"

        Returns:
            (gamma, slip_angle) - slip coefficient and angle (degrees)
        """
        # Import from velocity_triangle
        from .velocity_triangle import _calculate_slip
        return _calculate_slip(beta_blade, blade_count, method)

    def compute_head(
        self,
        cu_in: float = None,
        cu_out: float = None,
        u_in: float = None,
        u_out: float = None
    ) -> float:
        """
        Compute Euler head.

        If no arguments provided, uses calculated values.

        Args:
            cu_in, cu_out: Circumferential velocities (m/s)
            u_in, u_out: Blade speeds (m/s)

        Returns:
            Euler head (m)
        """
        self.calculate_all()

        if cu_in is None:
            cu_in = (self._inlet_hub.cu + self._inlet_tip.cu) / 2
        if cu_out is None:
            cu_out = (self._outlet_hub.cu + self._outlet_tip.cu) / 2
        if u_in is None:
            u_in = (self._inlet_hub.u + self._inlet_tip.u) / 2
        if u_out is None:
            u_out = (self._outlet_hub.u + self._outlet_tip.u) / 2

        return calculate_euler_head(cu_in, cu_out, u_in, u_out)

    def get_info_table_data(self) -> InfoTableData:
        """
        Get all data needed for the info table display.

        Returns:
            InfoTableData with all parameters
        """
        self.calculate_all()

        ih = self._inlet_hub
        it = self._inlet_tip
        oh = self._outlet_hub
        ot = self._outlet_tip
        perf = self._performance
        geo = self.geometry

        return InfoTableData(
            # Position (z) - axial position in mm
            z_hub_in=0.0,
            z_hub_out=geo.main_dims.L,
            z_tip_in=0.0,
            z_tip_out=geo.main_dims.L,

            # Radial position (r) in mm
            r_hub_in=geo.main_dims.r_h_in,
            r_hub_out=geo.main_dims.r_h_out,
            r_tip_in=geo.main_dims.r_t_in,
            r_tip_out=geo.main_dims.r_t_out,

            # Diameter (d) in mm
            d_hub_in=2 * geo.main_dims.r_h_in,
            d_hub_out=2 * geo.main_dims.r_h_out,
            d_tip_in=2 * geo.main_dims.r_t_in,
            d_tip_out=2 * geo.main_dims.r_t_out,

            # Flow angles
            alpha_hub_in=ih.alpha,
            alpha_hub_out=oh.alpha,
            alpha_tip_in=it.alpha,
            alpha_tip_out=ot.alpha,
            beta_hub_in=ih.beta,
            beta_hub_out=oh.beta,
            beta_tip_in=it.beta,
            beta_tip_out=ot.beta,

            # Velocities (m/s)
            u_hub_in=ih.u,
            u_hub_out=oh.u,
            u_tip_in=it.u,
            u_tip_out=ot.u,
            cm_hub_in=ih.cm,
            cm_hub_out=oh.cm,
            cm_tip_in=it.cm,
            cm_tip_out=ot.cm,
            cu_hub_in=ih.cu,
            cu_hub_out=oh.cu,
            cu_tip_in=it.cu,
            cu_tip_out=ot.cu,
            cr_hub_in=ih.cr,
            cr_hub_out=oh.cr,
            cr_tip_in=it.cr,
            cr_tip_out=ot.cr,
            cz_hub_in=ih.cz,
            cz_hub_out=oh.cz,
            cz_tip_in=it.cz,
            cz_tip_out=ot.cz,
            c_hub_in=ih.c,
            c_hub_out=oh.c,
            c_tip_in=it.c,
            c_tip_out=ot.c,
            wu_hub_in=ih.wu,
            wu_hub_out=oh.wu,
            wu_tip_in=it.wu,
            wu_tip_out=ot.wu,
            w_hub_in=ih.w,
            w_hub_out=oh.w,
            w_tip_in=it.w,
            w_tip_out=ot.w,

            # cu·r
            cur_hub_in=ih.cu * ih.radius,
            cur_hub_out=oh.cu * oh.radius,
            cur_tip_in=it.cu * it.radius,
            cur_tip_out=ot.cu * ot.radius,

            # Blockage
            tau_hub_in=ih.tau,
            tau_hub_out=oh.tau,
            tau_tip_in=it.tau,
            tau_tip_out=ot.tau,

            # Incidence/Deviation
            i_hub_in=ih.incidence,
            delta_hub_out=oh.slip_angle,
            i_tip_in=it.incidence,
            delta_tip_out=ot.slip_angle,

            # Merged values
            w2_w1_hub=perf.w2_w1_hub,
            w2_w1_tip=perf.w2_w1_tip,
            c2_c1_hub=perf.c2_c1_hub,
            c2_c1_tip=perf.c2_c1_tip,
            delta_alpha_hub=perf.delta_alpha_hub,
            delta_alpha_tip=perf.delta_alpha_tip,
            delta_beta_hub=perf.delta_beta_hub,
            delta_beta_tip=perf.delta_beta_tip,
            camber_hub=perf.camber_hub,
            camber_tip=perf.camber_tip,
            gamma_hub=perf.gamma_hub,
            gamma_tip=perf.gamma_tip,
            delta_cur_hub=perf.delta_cur_hub,
            delta_cur_tip=perf.delta_cur_tip,
            torque=perf.torque,
            head=perf.euler_head_mean,
        )

    def calculate_triangle_at_span(
        self,
        station: str,
        span_fraction: float
    ) -> InletTriangleResult | OutletTriangleResult:
        """
        Calculate velocity triangle at arbitrary span position.

        Args:
            station: "inlet" or "outlet"
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Triangle result at the specified span
        """
        geo = self.geometry
        op = self.operating
        span_fraction = max(0.0, min(1.0, span_fraction))

        if station.lower() == "inlet":
            # Interpolate incidence
            incidence = geo.incidence_hub + span_fraction * (geo.incidence_tip - geo.incidence_hub)
            # Interpolate thickness
            thickness = geo.inlet.get_thickness_at_span(span_fraction)

            return compute_inlet_triangle(
                flow_rate=op.flow_rate,
                r_hub=geo.inlet.r_hub,
                r_tip=geo.inlet.r_tip,
                rpm=op.rpm,
                span_fraction=span_fraction,
                alpha_inlet=op.alpha_inlet,
                incidence=incidence,
                blade_count=geo.blade_count,
                thickness=thickness,
            )
        else:
            # Interpolate blade angle
            beta_blade = geo.outlet.get_beta_blade_at_span(span_fraction)
            thickness = geo.outlet.get_thickness_at_span(span_fraction)

            return compute_outlet_triangle(
                flow_rate=op.flow_rate,
                r_hub=geo.outlet.r_hub,
                r_tip=geo.outlet.r_tip,
                rpm=op.rpm,
                beta_blade=beta_blade,
                span_fraction=span_fraction,
                blade_count=geo.blade_count,
                thickness=thickness,
                slip_method="Wiesner",
            )

    def to_dict(self) -> dict:
        """Serialize calculator state."""
        return {
            "geometry": self.geometry.to_dict(),
            "operating": self.operating.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TurbomachineryCalculator":
        """Deserialize calculator from dictionary."""
        geometry = TurbomachineryGeometry.from_dict(data["geometry"])
        operating = OperatingConditions.from_dict(data["operating"])
        return cls(geometry=geometry, operating=operating)
