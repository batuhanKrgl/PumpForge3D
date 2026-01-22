"""
Blade Geometry module for turbomachinery calculations.

Provides geometry data at any span position (0=hub, 1=tip) including
radii, areas, and diameter information needed for velocity triangle
calculations.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import math
import numpy as np

from .meridional import MeridionalContour
from .curve import interpolate_radius_at_span


@dataclass
class GeometryAtSpan:
    """
    Geometry data at a specific span position.

    Contains all geometric parameters needed for velocity triangle
    calculation at a single spanwise location.
    """

    # Span position (0 = hub, 1 = tip)
    span: float

    # Inlet geometry
    r_inlet: float  # Inlet radius [m]
    d_inlet: float  # Inlet diameter [m]
    area_inlet: float  # Inlet annular area [m²]

    # Outlet geometry
    r_outlet: float  # Outlet radius [m]
    d_outlet: float  # Outlet diameter [m]
    area_outlet: float  # Outlet annular area [m²]

    # Mean values
    r_mean: float  # Mean radius (avg of inlet/outlet) [m]
    d_mean: float  # Mean diameter [m]

    @property
    def r_in(self) -> float:
        """Alias for inlet radius."""
        return self.r_inlet

    @property
    def r_out(self) -> float:
        """Alias for outlet radius."""
        return self.r_outlet


class BladeGeometry:
    """
    Complete blade geometry with span-wise query capabilities.

    Wraps MeridionalContour and provides easy access to geometric
    parameters at any span position for velocity triangle calculations.
    """

    def __init__(
        self,
        r_hub_inlet: float,
        r_tip_inlet: float,
        r_hub_outlet: float,
        r_tip_outlet: float,
        meridional_contour: Optional[MeridionalContour] = None
    ):
        """
        Initialize blade geometry.

        Args:
            r_hub_inlet: Hub radius at inlet [m]
            r_tip_inlet: Tip radius at inlet [m]
            r_hub_outlet: Hub radius at outlet [m]
            r_tip_outlet: Tip radius at outlet [m]
            meridional_contour: Optional meridional contour for advanced geometry
        """
        # Convert to meters if needed (assuming input in meters)
        self.r_hub_inlet = r_hub_inlet
        self.r_tip_inlet = r_tip_inlet
        self.r_hub_outlet = r_hub_outlet
        self.r_tip_outlet = r_tip_outlet

        # Optional detailed meridional contour
        self.meridional_contour = meridional_contour

        # Validate
        self._validate()

    def _validate(self):
        """Validate geometry constraints."""
        if self.r_hub_inlet >= self.r_tip_inlet:
            raise ValueError("Hub inlet radius must be less than tip inlet radius")
        if self.r_hub_outlet >= self.r_tip_outlet:
            raise ValueError("Hub outlet radius must be less than tip outlet radius")
        if self.r_hub_inlet <= 0 or self.r_tip_inlet <= 0:
            raise ValueError("Inlet radii must be positive")
        if self.r_hub_outlet <= 0 or self.r_tip_outlet <= 0:
            raise ValueError("Outlet radii must be positive")

    def get_radius_at_span(self, span: float, position: str = "inlet") -> float:
        """
        Get radius at given span position.

        Args:
            span: Span position (0 = hub, 1 = tip)
            position: "inlet" or "outlet"

        Returns:
            Radius at span [m]
        """
        span = max(0.0, min(1.0, span))  # Clamp to [0, 1]

        if position == "inlet":
            return interpolate_radius_at_span(self.r_hub_inlet, self.r_tip_inlet, span)
        elif position == "outlet":
            return interpolate_radius_at_span(self.r_hub_outlet, self.r_tip_outlet, span)
        else:
            raise ValueError(f"Invalid position: {position}")

    def get_area_at_span(self, position: str = "inlet") -> float:
        """
        Get annular area at inlet or outlet.

        Annular area: A = π × (r_tip² - r_hub²)

        Args:
            position: "inlet" or "outlet"

        Returns:
            Annular area [m²]
        """
        if position == "inlet":
            r_hub = self.r_hub_inlet
            r_tip = self.r_tip_inlet
        elif position == "outlet":
            r_hub = self.r_hub_outlet
            r_tip = self.r_tip_outlet
        else:
            raise ValueError(f"Invalid position: {position}")

        return math.pi * (r_tip**2 - r_hub**2)

    def get_geometry_at_span(self, span: float) -> GeometryAtSpan:
        """
        Get complete geometry data at given span position.

        Args:
            span: Span position (0 = hub, 1 = tip)

        Returns:
            GeometryAtSpan with all parameters
        """
        span = max(0.0, min(1.0, span))

        # Radii at this span
        r_inlet = self.get_radius_at_span(span, "inlet")
        r_outlet = self.get_radius_at_span(span, "outlet")

        # Diameters
        d_inlet = 2.0 * r_inlet
        d_outlet = 2.0 * r_outlet

        # Areas (full annular areas, not at specific span)
        area_inlet = self.get_area_at_span("inlet")
        area_outlet = self.get_area_at_span("outlet")

        # Mean values
        r_mean = (r_inlet + r_outlet) / 2.0
        d_mean = 2.0 * r_mean

        return GeometryAtSpan(
            span=span,
            r_inlet=r_inlet,
            d_inlet=d_inlet,
            area_inlet=area_inlet,
            r_outlet=r_outlet,
            d_outlet=d_outlet,
            area_outlet=area_outlet,
            r_mean=r_mean,
            d_mean=d_mean
        )

    def get_mean_diameter(self, position: str = "outlet") -> float:
        """
        Get mean diameter at inlet or outlet.

        Mean diameter: d_m = (d_hub + d_tip) / 2

        Args:
            position: "inlet" or "outlet"

        Returns:
            Mean diameter [m]
        """
        if position == "inlet":
            return self.r_hub_inlet + self.r_tip_inlet  # = (d_hub + d_tip) / 2
        elif position == "outlet":
            return self.r_hub_outlet + self.r_tip_outlet
        else:
            raise ValueError(f"Invalid position: {position}")

    def get_span_array(self, n_spans: int) -> np.ndarray:
        """
        Generate array of span positions.

        Args:
            n_spans: Number of span positions (minimum 2)

        Returns:
            Array of span values from 0 (hub) to 1 (tip)
        """
        n_spans = max(2, n_spans)
        return np.linspace(0, 1, n_spans)

    @classmethod
    def from_diameters(
        cls,
        d_hub_inlet: float,
        d_tip_inlet: float,
        d_hub_outlet: float,
        d_tip_outlet: float
    ) -> "BladeGeometry":
        """
        Create geometry from diameters instead of radii.

        Args:
            d_hub_inlet: Hub diameter at inlet [m]
            d_tip_inlet: Tip diameter at inlet [m]
            d_hub_outlet: Hub diameter at outlet [m]
            d_tip_outlet: Tip diameter at outlet [m]

        Returns:
            BladeGeometry instance
        """
        return cls(
            r_hub_inlet=d_hub_inlet / 2.0,
            r_tip_inlet=d_tip_inlet / 2.0,
            r_hub_outlet=d_hub_outlet / 2.0,
            r_tip_outlet=d_tip_outlet / 2.0
        )

    @classmethod
    def from_mm(
        cls,
        r_hub_inlet_mm: float,
        r_tip_inlet_mm: float,
        r_hub_outlet_mm: float,
        r_tip_outlet_mm: float
    ) -> "BladeGeometry":
        """
        Create geometry from radii in millimeters.

        Args:
            r_hub_inlet_mm: Hub radius at inlet [mm]
            r_tip_inlet_mm: Tip radius at inlet [mm]
            r_hub_outlet_mm: Hub radius at outlet [mm]
            r_tip_outlet_mm: Tip radius at outlet [mm]

        Returns:
            BladeGeometry instance (converted to meters)
        """
        return cls(
            r_hub_inlet=r_hub_inlet_mm / 1000.0,
            r_tip_inlet=r_tip_inlet_mm / 1000.0,
            r_hub_outlet=r_hub_outlet_mm / 1000.0,
            r_tip_outlet=r_tip_outlet_mm / 1000.0
        )
