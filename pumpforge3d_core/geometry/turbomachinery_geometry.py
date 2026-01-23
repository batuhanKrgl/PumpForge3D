"""
Turbomachinery Geometry Class.

Provides geometric data for turbomachinery calculations including:
- Flow areas at inlet/outlet
- Radii at different span positions
- Blade geometry (thickness, angles)
- Integration with MeridionalContour
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
import math
import numpy as np
from numpy.typing import NDArray

from .meridional import MainDimensions, MeridionalContour
from .curve import MeridionalCurve


@dataclass
class StationGeometry:
    """
    Geometry data at a single axial station (inlet or outlet).

    Contains all geometric parameters needed for velocity triangle
    calculations at one station.
    """
    # Radii (m)
    r_hub: float
    r_tip: float

    # Blade properties
    blade_count: int = 6
    thickness_hub: float = 0.002  # m
    thickness_tip: float = 0.002  # m

    # Blade angles (degrees)
    beta_blade_hub: float = 30.0
    beta_blade_tip: float = 25.0

    # Station identifier
    name: str = "station"

    @property
    def r_mean(self) -> float:
        """Mean radius (arithmetic mean)."""
        return (self.r_hub + self.r_tip) / 2.0

    @property
    def r_rms(self) -> float:
        """RMS radius (area-weighted mean)."""
        return math.sqrt((self.r_hub**2 + self.r_tip**2) / 2.0)

    @property
    def d_hub(self) -> float:
        """Hub diameter (m)."""
        return 2.0 * self.r_hub

    @property
    def d_tip(self) -> float:
        """Tip diameter (m)."""
        return 2.0 * self.r_tip

    @property
    def d_mean(self) -> float:
        """Mean diameter (m)."""
        return 2.0 * self.r_mean

    @property
    def annulus_height(self) -> float:
        """Blade span / annulus height (m)."""
        return self.r_tip - self.r_hub

    @property
    def hub_to_tip_ratio(self) -> float:
        """Hub-to-tip radius ratio."""
        if self.r_tip <= 0:
            return 0.0
        return self.r_hub / self.r_tip

    @property
    def flow_area(self) -> float:
        """Annular flow area (m²)."""
        return math.pi * (self.r_tip**2 - self.r_hub**2)

    @property
    def thickness_mean(self) -> float:
        """Mean blade thickness (m)."""
        return (self.thickness_hub + self.thickness_tip) / 2.0

    def get_radius_at_span(self, span_fraction: float) -> float:
        """
        Get radius at specified span fraction.

        Args:
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Radius at span position (m)
        """
        span_fraction = max(0.0, min(1.0, span_fraction))
        return self.r_hub + span_fraction * (self.r_tip - self.r_hub)

    def get_thickness_at_span(self, span_fraction: float) -> float:
        """
        Get blade thickness at specified span fraction.

        Args:
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Blade thickness at span position (m)
        """
        span_fraction = max(0.0, min(1.0, span_fraction))
        return self.thickness_hub + span_fraction * (self.thickness_tip - self.thickness_hub)

    def get_beta_blade_at_span(self, span_fraction: float) -> float:
        """
        Get blade angle at specified span fraction.

        Args:
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Blade angle at span position (degrees)
        """
        span_fraction = max(0.0, min(1.0, span_fraction))
        return self.beta_blade_hub + span_fraction * (self.beta_blade_tip - self.beta_blade_hub)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "r_hub": self.r_hub,
            "r_tip": self.r_tip,
            "blade_count": self.blade_count,
            "thickness_hub": self.thickness_hub,
            "thickness_tip": self.thickness_tip,
            "beta_blade_hub": self.beta_blade_hub,
            "beta_blade_tip": self.beta_blade_tip,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StationGeometry":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", "station"),
            r_hub=data["r_hub"],
            r_tip=data["r_tip"],
            blade_count=data.get("blade_count", 6),
            thickness_hub=data.get("thickness_hub", 0.002),
            thickness_tip=data.get("thickness_tip", 0.002),
            beta_blade_hub=data.get("beta_blade_hub", 30.0),
            beta_blade_tip=data.get("beta_blade_tip", 25.0),
        )


@dataclass
class TurbomachineryGeometry:
    """
    Complete turbomachinery geometry for calculations.

    Combines meridional contour with blade properties to provide
    all geometric data needed for velocity triangle and head calculations.
    """
    # Main dimensions (stored in mm, converted to m for calculations)
    main_dims: MainDimensions = field(default_factory=MainDimensions)

    # Meridional contour
    contour: Optional[MeridionalContour] = None

    # Blade properties
    blade_count: int = 6

    # Blade thickness matrix (mm) - will be converted to m
    thickness_hub_inlet: float = 2.0
    thickness_hub_outlet: float = 1.5
    thickness_tip_inlet: float = 2.0
    thickness_tip_outlet: float = 1.5

    # Blade angles (degrees)
    beta_blade_hub_inlet: float = 30.0
    beta_blade_hub_outlet: float = 35.0
    beta_blade_tip_inlet: float = 25.0
    beta_blade_tip_outlet: float = 30.0

    # Incidence and slip
    incidence_hub: float = 0.0  # degrees
    incidence_tip: float = 0.0  # degrees
    slip_coefficient: float = 0.9  # γ (gamma)

    def __post_init__(self):
        """Initialize contour if not provided."""
        if self.contour is None:
            self.contour = MeridionalContour.create_from_dimensions(self.main_dims)

    @property
    def inlet(self) -> StationGeometry:
        """Get inlet station geometry."""
        return StationGeometry(
            name="inlet",
            r_hub=self.main_dims.r_h_in / 1000.0,  # mm to m
            r_tip=self.main_dims.r_t_in / 1000.0,
            blade_count=self.blade_count,
            thickness_hub=self.thickness_hub_inlet / 1000.0,
            thickness_tip=self.thickness_tip_inlet / 1000.0,
            beta_blade_hub=self.beta_blade_hub_inlet,
            beta_blade_tip=self.beta_blade_tip_inlet,
        )

    @property
    def outlet(self) -> StationGeometry:
        """Get outlet station geometry."""
        return StationGeometry(
            name="outlet",
            r_hub=self.main_dims.r_h_out / 1000.0,  # mm to m
            r_tip=self.main_dims.r_t_out / 1000.0,
            blade_count=self.blade_count,
            thickness_hub=self.thickness_hub_outlet / 1000.0,
            thickness_tip=self.thickness_tip_outlet / 1000.0,
            beta_blade_hub=self.beta_blade_hub_outlet,
            beta_blade_tip=self.beta_blade_tip_outlet,
        )

    @property
    def axial_length(self) -> float:
        """Axial length in meters."""
        return self.main_dims.L / 1000.0

    @property
    def inlet_area(self) -> float:
        """Inlet flow area (m²)."""
        return self.inlet.flow_area

    @property
    def outlet_area(self) -> float:
        """Outlet flow area (m²)."""
        return self.outlet.flow_area

    def get_station(self, station: str) -> StationGeometry:
        """
        Get geometry for specified station.

        Args:
            station: "inlet" or "outlet"

        Returns:
            StationGeometry for the specified station
        """
        if station.lower() == "inlet":
            return self.inlet
        elif station.lower() == "outlet":
            return self.outlet
        else:
            raise ValueError(f"Unknown station: {station}. Use 'inlet' or 'outlet'.")

    def get_radius_at_position(
        self,
        station: str,
        span_fraction: float
    ) -> float:
        """
        Get radius at specific station and span position.

        Args:
            station: "inlet" or "outlet"
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Radius (m)
        """
        return self.get_station(station).get_radius_at_span(span_fraction)

    def get_area_at_z(self, z_mm: float) -> float:
        """
        Get flow area at specified axial position.

        Uses meridional contour for interpolation.

        Args:
            z_mm: Axial position (mm)

        Returns:
            Flow area (m²)
        """
        if self.contour is None:
            # Linear interpolation between inlet and outlet
            t = z_mm / self.main_dims.L if self.main_dims.L > 0 else 0.0
            r_hub = (self.main_dims.r_h_in + t * (self.main_dims.r_h_out - self.main_dims.r_h_in)) / 1000.0
            r_tip = (self.main_dims.r_t_in + t * (self.main_dims.r_t_out - self.main_dims.r_t_in)) / 1000.0
        else:
            # Use contour for accurate interpolation
            area_mm2 = self.contour.compute_area_at_z(z_mm)
            return area_mm2 / 1e6  # mm² to m²

        return math.pi * (r_tip**2 - r_hub**2)

    def get_radii_at_z(self, z_mm: float) -> Tuple[float, float]:
        """
        Get hub and tip radii at specified axial position.

        Args:
            z_mm: Axial position (mm)

        Returns:
            (r_hub, r_tip) in meters
        """
        if self.contour is None:
            t = z_mm / self.main_dims.L if self.main_dims.L > 0 else 0.0
            r_hub = self.main_dims.r_h_in + t * (self.main_dims.r_h_out - self.main_dims.r_h_in)
            r_tip = self.main_dims.r_t_in + t * (self.main_dims.r_t_out - self.main_dims.r_t_in)
        else:
            # Use contour curves
            t_hub = self.contour._find_t_for_z(self.contour.hub_curve, z_mm)
            t_tip = self.contour._find_t_for_z(self.contour.tip_curve, z_mm)
            _, r_hub = self.contour.hub_curve.evaluate(t_hub)
            _, r_tip = self.contour.tip_curve.evaluate(t_tip)

        return (r_hub / 1000.0, r_tip / 1000.0)

    def get_thickness_at_position(
        self,
        station: str,
        span_fraction: float
    ) -> float:
        """
        Get blade thickness at specific station and span.

        Args:
            station: "inlet" or "outlet"
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Thickness (m)
        """
        return self.get_station(station).get_thickness_at_span(span_fraction)

    def get_beta_blade_at_position(
        self,
        station: str,
        span_fraction: float
    ) -> float:
        """
        Get blade angle at specific station and span.

        Args:
            station: "inlet" or "outlet"
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Blade angle (degrees)
        """
        return self.get_station(station).get_beta_blade_at_span(span_fraction)

    def get_incidence_at_span(self, span_fraction: float) -> float:
        """
        Get incidence angle at span position.

        Args:
            span_fraction: 0.0 = hub, 1.0 = tip

        Returns:
            Incidence angle (degrees)
        """
        span_fraction = max(0.0, min(1.0, span_fraction))
        return self.incidence_hub + span_fraction * (self.incidence_tip - self.incidence_hub)

    def get_hub_curve(self) -> Optional[MeridionalCurve]:
        """Get hub meridional curve."""
        if self.contour is None:
            return None
        points = self.contour.hub_curve.evaluate_many(100)
        return MeridionalCurve.from_array(points, name="hub")

    def get_tip_curve(self) -> Optional[MeridionalCurve]:
        """Get tip meridional curve."""
        if self.contour is None:
            return None
        points = self.contour.tip_curve.evaluate_many(100)
        return MeridionalCurve.from_array(points, name="tip")

    def get_streamline_at_span(
        self,
        span_fraction: float,
        n_points: int = 100
    ) -> MeridionalCurve:
        """
        Get interpolated streamline at span fraction.

        Args:
            span_fraction: 0.0 = hub, 1.0 = tip
            n_points: Number of sample points

        Returns:
            MeridionalCurve for the streamline
        """
        span_fraction = max(0.0, min(1.0, span_fraction))

        if self.contour is None:
            # Linear interpolation
            z = np.linspace(0, self.main_dims.L, n_points)
            r_hub = self.main_dims.r_h_in + (z / self.main_dims.L) * (self.main_dims.r_h_out - self.main_dims.r_h_in)
            r_tip = self.main_dims.r_t_in + (z / self.main_dims.L) * (self.main_dims.r_t_out - self.main_dims.r_t_in)
            r = r_hub + span_fraction * (r_tip - r_hub)
        else:
            # Interpolate between hub and tip curves
            hub_points = self.contour.hub_curve.evaluate_many(n_points)
            tip_points = self.contour.tip_curve.evaluate_many(n_points)

            z = hub_points[:, 0]  # Use hub z coordinates
            r_hub = hub_points[:, 1]
            r_tip = tip_points[:, 1]
            r = r_hub + span_fraction * (r_tip - r_hub)

        return MeridionalCurve(z=z, r=r, name=f"span_{span_fraction:.2f}")

    def compute_area_distribution(self, n_points: int = 50) -> NDArray[np.float64]:
        """
        Compute area distribution along meridional axis.

        Returns:
            Array of shape (n, 2) with (z_mm, area_m2) values
        """
        z_values = np.linspace(0, self.main_dims.L, n_points)
        areas = np.array([self.get_area_at_z(z) for z in z_values])
        return np.column_stack([z_values, areas])

    def update_from_main_dims(self, dims: MainDimensions):
        """Update geometry from new main dimensions."""
        self.main_dims = dims
        if self.contour is not None:
            self.contour.update_from_dimensions(dims)

    def update_blade_thickness(
        self,
        hub_inlet: float,
        hub_outlet: float,
        tip_inlet: float,
        tip_outlet: float
    ):
        """
        Update blade thickness matrix (values in mm).

        Args:
            hub_inlet, hub_outlet, tip_inlet, tip_outlet: Thickness values (mm)
        """
        self.thickness_hub_inlet = hub_inlet
        self.thickness_hub_outlet = hub_outlet
        self.thickness_tip_inlet = tip_inlet
        self.thickness_tip_outlet = tip_outlet

    def update_blade_angles(
        self,
        hub_inlet: float,
        hub_outlet: float,
        tip_inlet: float,
        tip_outlet: float
    ):
        """
        Update blade angle matrix (values in degrees).

        Args:
            hub_inlet, hub_outlet, tip_inlet, tip_outlet: Blade angles (degrees)
        """
        self.beta_blade_hub_inlet = hub_inlet
        self.beta_blade_hub_outlet = hub_outlet
        self.beta_blade_tip_inlet = tip_inlet
        self.beta_blade_tip_outlet = tip_outlet

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "main_dims": self.main_dims.to_dict(),
            "contour": self.contour.to_dict() if self.contour else None,
            "blade_count": self.blade_count,
            "thickness_hub_inlet": self.thickness_hub_inlet,
            "thickness_hub_outlet": self.thickness_hub_outlet,
            "thickness_tip_inlet": self.thickness_tip_inlet,
            "thickness_tip_outlet": self.thickness_tip_outlet,
            "beta_blade_hub_inlet": self.beta_blade_hub_inlet,
            "beta_blade_hub_outlet": self.beta_blade_hub_outlet,
            "beta_blade_tip_inlet": self.beta_blade_tip_inlet,
            "beta_blade_tip_outlet": self.beta_blade_tip_outlet,
            "incidence_hub": self.incidence_hub,
            "incidence_tip": self.incidence_tip,
            "slip_coefficient": self.slip_coefficient,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TurbomachineryGeometry":
        """Deserialize from dictionary."""
        main_dims = MainDimensions.from_dict(data["main_dims"])
        contour = None
        if data.get("contour"):
            contour = MeridionalContour.from_dict(data["contour"])

        return cls(
            main_dims=main_dims,
            contour=contour,
            blade_count=data.get("blade_count", 6),
            thickness_hub_inlet=data.get("thickness_hub_inlet", 2.0),
            thickness_hub_outlet=data.get("thickness_hub_outlet", 1.5),
            thickness_tip_inlet=data.get("thickness_tip_inlet", 2.0),
            thickness_tip_outlet=data.get("thickness_tip_outlet", 1.5),
            beta_blade_hub_inlet=data.get("beta_blade_hub_inlet", 30.0),
            beta_blade_hub_outlet=data.get("beta_blade_hub_outlet", 35.0),
            beta_blade_tip_inlet=data.get("beta_blade_tip_inlet", 25.0),
            beta_blade_tip_outlet=data.get("beta_blade_tip_outlet", 30.0),
            incidence_hub=data.get("incidence_hub", 0.0),
            incidence_tip=data.get("incidence_tip", 0.0),
            slip_coefficient=data.get("slip_coefficient", 0.9),
        )
