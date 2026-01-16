"""
Meridional contour model for inducer design.

Defines the hub, shroud (tip), and edge curves that form the meridional view.
Supports normalized control point storage for automatic scaling with dimensions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, List, Optional, Union
import numpy as np
from numpy.typing import NDArray

from .bezier import BezierCurve4, BezierCurve2, StraightLine, ControlPoint


class CurveMode(Enum):
    """Mode for edge curves."""
    STRAIGHT = "straight"
    BEZIER = "bezier"  # Uses BezierCurve2 (quadratic, 3 CPs)


@dataclass
class MainDimensions:
    """
    Main dimensions defining the inducer meridional bounds.
    
    All values in millimeters by default.
    
    Coordinate system:
    - z: axial direction (0 at inlet, L at outlet)
    - r: radial direction (hub to tip/shroud)
    """
    r_h_in: float = 20.0    # Inlet hub radius [mm]
    r_t_in: float = 50.0    # Inlet tip/shroud radius [mm]
    r_h_out: float = 30.0   # Outlet hub radius [mm]
    r_t_out: float = 45.0   # Outlet tip/shroud radius [mm]
    L: float = 80.0         # Axial length [mm]
    units: str = "mm"
    
    def __post_init__(self):
        """Validate dimensions."""
        self._validate()
    
    def _validate(self):
        """Check dimension constraints."""
        if self.r_h_in < 0 or self.r_t_in < 0:
            raise ValueError("Inlet radii must be non-negative")
        if self.r_h_out < 0 or self.r_t_out < 0:
            raise ValueError("Outlet radii must be non-negative")
        if self.L <= 0:
            raise ValueError("Axial length must be positive")
        if self.r_h_in >= self.r_t_in:
            raise ValueError("Inlet hub radius must be less than inlet tip radius")
        if self.r_h_out >= self.r_t_out:
            raise ValueError("Outlet hub radius must be less than outlet tip radius")
    
    @property
    def hub_inlet(self) -> Tuple[float, float]:
        """Hub curve inlet point (z, r)."""
        return (0.0, self.r_h_in)
    
    @property
    def hub_outlet(self) -> Tuple[float, float]:
        """Hub curve outlet point (z, r)."""
        return (self.L, self.r_h_out)
    
    @property
    def tip_inlet(self) -> Tuple[float, float]:
        """Tip/shroud curve inlet point (z, r)."""
        return (0.0, self.r_t_in)
    
    @property
    def tip_outlet(self) -> Tuple[float, float]:
        """Tip/shroud curve outlet point (z, r)."""
        return (self.L, self.r_t_out)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "r_h_in": self.r_h_in,
            "r_t_in": self.r_t_in,
            "r_h_out": self.r_h_out,
            "r_t_out": self.r_t_out,
            "L": self.L,
            "units": self.units,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MainDimensions":
        """Deserialize from dictionary."""
        return cls(
            r_h_in=data["r_h_in"],
            r_t_in=data["r_t_in"],
            r_h_out=data["r_h_out"],
            r_t_out=data["r_t_out"],
            L=data["L"],
            units=data.get("units", "mm"),
        )


def _normalized_to_absolute(
    normalized_point: Tuple[float, float],
    dims: MainDimensions,
    curve_type: str
) -> Tuple[float, float]:
    """
    Convert normalized (0..1) coordinates to absolute (z, r).
    
    Args:
        normalized_point: (u, v) in [0, 1]
        dims: Main dimensions
        curve_type: "hub", "tip", "leading", or "trailing"
    
    Returns:
        (z, r) in absolute coordinates
    """
    u, v = normalized_point
    
    if curve_type == "hub":
        z = u * dims.L
        r = dims.r_h_in + v * (dims.r_h_out - dims.r_h_in)
    elif curve_type == "tip":
        z = u * dims.L
        r = dims.r_t_in + v * (dims.r_t_out - dims.r_t_in)
    else:
        # For edges, u is along z, v interpolates between hub and tip at that z
        z = u * dims.L
        # Linear interpolation of radius bounds at this z position
        r_hub = dims.r_h_in + u * (dims.r_h_out - dims.r_h_in)
        r_tip = dims.r_t_in + u * (dims.r_t_out - dims.r_t_in)
        r = r_hub + v * (r_tip - r_hub)
    
    return (z, r)


def _absolute_to_normalized(
    absolute_point: Tuple[float, float],
    dims: MainDimensions,
    curve_type: str
) -> Tuple[float, float]:
    """
    Convert absolute (z, r) coordinates to normalized (0..1).
    
    Args:
        absolute_point: (z, r) in mm
        dims: Main dimensions
        curve_type: "hub", "tip", "leading", or "trailing"
    
    Returns:
        (u, v) in [0, 1]
    """
    z, r = absolute_point
    
    u = z / dims.L if dims.L > 0 else 0.0
    
    if curve_type == "hub":
        delta_r = dims.r_h_out - dims.r_h_in
        v = (r - dims.r_h_in) / delta_r if abs(delta_r) > 1e-9 else 0.0
    elif curve_type == "tip":
        delta_r = dims.r_t_out - dims.r_t_in
        v = (r - dims.r_t_in) / delta_r if abs(delta_r) > 1e-9 else 0.0
    else:
        # For edges
        r_hub = dims.r_h_in + u * (dims.r_h_out - dims.r_h_in)
        r_tip = dims.r_t_in + u * (dims.r_t_out - dims.r_t_in)
        delta_r = r_tip - r_hub
        v = (r - r_hub) / delta_r if abs(delta_r) > 1e-9 else 0.0
    
    return (u, v)


@dataclass
class EdgeCurve:
    """
    Leading or trailing edge curve.
    
    Can be either a straight line or a quadratic Bezier curve (3 CPs) between hub and tip.
    The attachment points on hub/tip curves are controlled by hub_t and tip_t parameters.
    """
    mode: CurveMode = CurveMode.STRAIGHT
    bezier_curve: Optional[BezierCurve2] = None  # Quadratic Bezier (3 CPs)
    straight_line: Optional[StraightLine] = None
    name: str = ""
    
    # Position along hub and tip curves (0 = inlet, 1 = outlet)
    # These define where the edge anchors to the hub/tip meridional curves
    hub_position: float = 0.0  # Legacy name, kept for compatibility
    tip_position: float = 0.0  # Legacy name, kept for compatibility
    hub_t: float = 0.0  # Parameter t on hub curve where edge attaches
    tip_t: float = 0.0  # Parameter t on tip curve where edge attaches
    
    def evaluate(self, t: float) -> Tuple[float, float]:
        """Evaluate edge curve at parameter t."""
        if self.mode == CurveMode.STRAIGHT and self.straight_line:
            return self.straight_line.evaluate(t)
        elif self.mode == CurveMode.BEZIER and self.bezier_curve:
            return self.bezier_curve.evaluate(t)
        else:
            raise ValueError("Edge curve not properly initialized")
    
    def update_from_meridional(self, hub_curve: BezierCurve4, tip_curve: BezierCurve4):
        """
        Update edge endpoints from hub/tip curves using current anchor parameters.
        
        Args:
            hub_curve: The hub meridional curve
            tip_curve: The tip meridional curve
        """
        hub_point = hub_curve.evaluate(self.hub_t)
        tip_point = tip_curve.evaluate(self.tip_t)
        
        if self.mode == CurveMode.STRAIGHT:
            self.straight_line = StraightLine(hub_point, tip_point, self.name)
        elif self.mode == CurveMode.BEZIER:
            if self.bezier_curve is None:
                self.bezier_curve = BezierCurve2.create_default(hub_point, tip_point, self.name)
            else:
                # Update only endpoints, keep middle CP shape
                self.bezier_curve.control_points[0].z = hub_point[0]
                self.bezier_curve.control_points[0].r = hub_point[1]
                self.bezier_curve.control_points[2].z = tip_point[0]
                self.bezier_curve.control_points[2].r = tip_point[1]
    
    def evaluate_many(self, n: int = 100) -> NDArray[np.float64]:
        """Sample n points along the edge."""
        if self.mode == CurveMode.STRAIGHT and self.straight_line:
            return self.straight_line.evaluate_many(n)
        elif self.mode == CurveMode.BEZIER and self.bezier_curve:
            return self.bezier_curve.evaluate_many(n)
        else:
            raise ValueError("Edge curve not properly initialized")
    
    def get_hub_point(self) -> Tuple[float, float]:
        """Get the point where edge meets hub."""
        return self.evaluate(0.0)
    
    def get_tip_point(self) -> Tuple[float, float]:
        """Get the point where edge meets tip."""
        return self.evaluate(1.0)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        data = {
            "name": self.name,
            "mode": self.mode.value,
            "hub_position": self.hub_position,
            "tip_position": self.tip_position,
        }
        if self.mode == CurveMode.BEZIER and self.bezier_curve:
            data["bezier_curve"] = self.bezier_curve.to_dict()
        elif self.mode == CurveMode.STRAIGHT and self.straight_line:
            data["straight_line"] = self.straight_line.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "EdgeCurve":
        """Deserialize from dictionary."""
        mode = CurveMode(data["mode"])
        bezier_curve = None
        straight_line = None
        
        if mode == CurveMode.BEZIER and "bezier_curve" in data:
            # Support both old BezierCurve4 and new BezierCurve2 formats
            curve_data = data["bezier_curve"]
            if curve_data.get("degree") == 2 or len(curve_data.get("control_points", [])) == 3:
                bezier_curve = BezierCurve2.from_dict(curve_data)
            else:
                # Legacy: convert BezierCurve4 to BezierCurve2
                cps = curve_data.get("control_points", [])
                if len(cps) == 5:
                    # Take P0, P2, P4 to make quadratic
                    new_cps = [cps[0], cps[2], cps[4]]
                    bezier_curve = BezierCurve2.from_dict({"control_points": new_cps, "name": curve_data.get("name", "")})
                else:
                    bezier_curve = BezierCurve2.from_dict(curve_data)
        elif mode == CurveMode.STRAIGHT and "straight_line" in data:
            straight_line = StraightLine.from_dict(data["straight_line"])
        
        return cls(
            mode=mode,
            bezier_curve=bezier_curve,
            straight_line=straight_line,
            name=data.get("name", ""),
            hub_position=data.get("hub_position", 0.0),
            tip_position=data.get("tip_position", 0.0),
            hub_t=data.get("hub_t", data.get("hub_position", 0.0)),
            tip_t=data.get("tip_t", data.get("tip_position", 0.0)),
        )


@dataclass
class MeridionalContour:
    """
    Complete meridional contour model.
    
    Contains hub and tip curves, plus leading and trailing edges.
    Provides methods for geometry analysis and validation.
    """
    hub_curve: BezierCurve4 = field(default_factory=lambda: BezierCurve4.from_points(
        [(0, 20), (20, 22), (40, 25), (60, 28), (80, 30)], name="hub"
    ))
    tip_curve: BezierCurve4 = field(default_factory=lambda: BezierCurve4.from_points(
        [(0, 50), (20, 48), (40, 47), (60, 46), (80, 45)], name="tip"
    ))
    leading_edge: EdgeCurve = field(default_factory=lambda: EdgeCurve(name="leading"))
    trailing_edge: EdgeCurve = field(default_factory=lambda: EdgeCurve(name="trailing"))
    
    def __post_init__(self):
        """Initialize edges if not set."""
        self._update_edges()
    
    def _update_edges(self):
        """Update edge endpoints based on hub/tip curves using anchor parameters."""
        # Use update_from_meridional method for consistent behavior
        self.leading_edge.update_from_meridional(self.hub_curve, self.tip_curve)
        self.trailing_edge.update_from_meridional(self.hub_curve, self.tip_curve)
    
    @classmethod
    def create_from_dimensions(cls, dims: MainDimensions) -> "MeridionalContour":
        """
        Create a default meridional contour from main dimensions.
        
        Args:
            dims: Main dimensions defining bounds
        
        Returns:
            MeridionalContour with default curve shapes
        """
        # Create hub curve
        hub_curve = BezierCurve4.create_default(
            dims.hub_inlet, dims.hub_outlet, name="hub"
        )
        
        # Create tip curve
        tip_curve = BezierCurve4.create_default(
            dims.tip_inlet, dims.tip_outlet, name="tip"
        )
        
        # Create edges (straight by default)
        leading_edge = EdgeCurve(
            mode=CurveMode.STRAIGHT,
            straight_line=StraightLine(dims.hub_inlet, dims.tip_inlet, "leading"),
            name="leading",
            hub_position=0.0,
            tip_position=0.0,
            hub_t=0.0,  # LE at inlet end of hub curve
            tip_t=0.0,  # LE at inlet end of tip curve
        )
        
        trailing_edge = EdgeCurve(
            mode=CurveMode.STRAIGHT,
            straight_line=StraightLine(dims.hub_outlet, dims.tip_outlet, "trailing"),
            name="trailing",
            hub_position=1.0,
            tip_position=1.0,
            hub_t=1.0,  # TE at outlet end of hub curve
            tip_t=1.0,  # TE at outlet end of tip curve
        )
        
        return cls(
            hub_curve=hub_curve,
            tip_curve=tip_curve,
            leading_edge=leading_edge,
            trailing_edge=trailing_edge,
        )
    
    def update_from_dimensions(self, dims: MainDimensions):
        """
        Update curve endpoints when main dimensions change.
        
        Preserves the normalized shape of the curves while updating endpoints.
        """
        # Update hub endpoints (P0 and P4)
        self.hub_curve.control_points[0].z = dims.hub_inlet[0]
        self.hub_curve.control_points[0].r = dims.hub_inlet[1]
        self.hub_curve.control_points[4].z = dims.hub_outlet[0]
        self.hub_curve.control_points[4].r = dims.hub_outlet[1]
        
        # Update tip endpoints
        self.tip_curve.control_points[0].z = dims.tip_inlet[0]
        self.tip_curve.control_points[0].r = dims.tip_inlet[1]
        self.tip_curve.control_points[4].z = dims.tip_outlet[0]
        self.tip_curve.control_points[4].r = dims.tip_outlet[1]
        
        # Update edges
        self._update_edges()
    
    def compute_area_at_z(self, z: float) -> float:
        """
        Compute cross-sectional area between hub and tip at axial position z.
        
        This is the annular area: A = π * (r_tip² - r_hub²)
        
        Args:
            z: Axial position [mm]
        
        Returns:
            Cross-sectional area [mm²]
        """
        # Find t parameter for this z on each curve
        # Use approximate search
        t_hub = self._find_t_for_z(self.hub_curve, z)
        t_tip = self._find_t_for_z(self.tip_curve, z)
        
        _, r_hub = self.hub_curve.evaluate(t_hub)
        _, r_tip = self.tip_curve.evaluate(t_tip)
        
        return np.pi * (r_tip ** 2 - r_hub ** 2)
    
    def _find_t_for_z(self, curve: BezierCurve4, target_z: float, n: int = 200) -> float:
        """Find parameter t where curve has given z coordinate."""
        points = curve.evaluate_many(n)
        z_values = points[:, 0]
        
        # Find closest z
        idx = np.argmin(np.abs(z_values - target_z))
        return idx / (n - 1)
    
    def compute_area_progression(self, n: int = 50) -> NDArray[np.float64]:
        """
        Compute area section along the meridional axis.
        
        Args:
            n: Number of sample points
        
        Returns:
            Array of shape (n, 2) with (z, area) values
        """
        # Get z range from hub curve
        hub_points = self.hub_curve.evaluate_many(n)
        z_values = hub_points[:, 0]
        
        areas = np.array([self.compute_area_at_z(z) for z in z_values])
        
        return np.column_stack([z_values, areas])
    
    def get_all_sample_points(self, n: int = 200) -> dict:
        """
        Get sampled points for all curves.
        
        Args:
            n: Number of sample points per curve
        
        Returns:
            Dictionary with "hub", "tip", "leading", "trailing" arrays
        """
        return {
            "hub": self.hub_curve.evaluate_many(n),
            "tip": self.tip_curve.evaluate_many(n),
            "leading": self.leading_edge.evaluate_many(n),
            "trailing": self.trailing_edge.evaluate_many(n),
        }
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "hub_curve": self.hub_curve.to_dict(),
            "tip_curve": self.tip_curve.to_dict(),
            "leading_edge": self.leading_edge.to_dict(),
            "trailing_edge": self.trailing_edge.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MeridionalContour":
        """Deserialize from dictionary."""
        return cls(
            hub_curve=BezierCurve4.from_dict(data["hub_curve"]),
            tip_curve=BezierCurve4.from_dict(data["tip_curve"]),
            leading_edge=EdgeCurve.from_dict(data["leading_edge"]),
            trailing_edge=EdgeCurve.from_dict(data["trailing_edge"]),
        )
