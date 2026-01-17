"""
4th-order Bezier curve implementation.

A 4th-order Bezier curve is defined by 5 control points (P0-P4).
Based on CFturbo-inspired design:
- P0 and P4 are endpoints (fixed by main dimensions)
- P1 and P3 can be constrained along tangent directions
- P2 is freely movable
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional
import numpy as np
from numpy.typing import NDArray


def _bernstein(n: int, i: int, t: float) -> float:
    """Compute Bernstein polynomial B_{i,n}(t)."""
    from math import comb
    return comb(n, i) * (t ** i) * ((1 - t) ** (n - i))


def _bernstein_derivative(n: int, i: int, t: float) -> float:
    """Compute derivative of Bernstein polynomial."""
    if i == 0:
        return -n * ((1 - t) ** (n - 1))
    elif i == n:
        return n * (t ** (n - 1))
    else:
        from math import comb
        return comb(n, i) * (
            i * (t ** (i - 1)) * ((1 - t) ** (n - i))
            - (n - i) * (t ** i) * ((1 - t) ** (n - i - 1))
        )


def _bernstein_second_derivative(n: int, i: int, t: float) -> float:
    """Compute second derivative of Bernstein polynomial."""
    if n < 2:
        return 0.0
    from math import comb
    
    # Using the formula: B''_{i,n}(t) = n(n-1) * [B_{i-2,n-2}(t) - 2*B_{i-1,n-2}(t) + B_{i,n-2}(t)]
    result = 0.0
    for j, coef in [(-2, 1), (-1, -2), (0, 1)]:
        idx = i + j
        if 0 <= idx <= n - 2:
            result += coef * _bernstein(n - 2, idx, t)
    return n * (n - 1) * result


@dataclass
class ControlPoint:
    """
    A Bezier control point with optional constraints.
    
    Coordinates can be stored as normalized (0..1) or absolute (z, r in mm).
    The normalized form allows automatic scaling when main dimensions change.
    """
    z: float  # Axial coordinate (mm or normalized 0..1)
    r: float  # Radial coordinate (mm or normalized 0..1)
    is_normalized: bool = False
    is_locked: bool = False  # If True, point cannot be moved
    angle_locked: bool = False  # If True for P1/P3, constrains to tangent direction
    
    def to_tuple(self) -> Tuple[float, float]:
        """Return (z, r) tuple."""
        return (self.z, self.r)
    
    def to_array(self) -> NDArray[np.float64]:
        """Return as numpy array [z, r]."""
        return np.array([self.z, self.r], dtype=np.float64)
    
    def copy(self) -> "ControlPoint":
        """Create a copy of this control point."""
        return ControlPoint(
            z=self.z, r=self.r,
            is_normalized=self.is_normalized,
            is_locked=self.is_locked,
            angle_locked=self.angle_locked
        )


@dataclass
class BezierCurve4:
    """
    4th-order Bezier curve defined by 5 control points.
    
    The curve is parameterized by t in [0, 1]:
    C(t) = sum_{i=0}^{4} B_{i,4}(t) * P_i
    
    where B_{i,4}(t) are Bernstein basis polynomials of degree 4.
    
    Attributes:
        control_points: List of 5 ControlPoint objects (P0-P4)
        name: Optional identifier for this curve
    """
    control_points: List[ControlPoint] = field(default_factory=list)
    name: str = ""
    
    def __post_init__(self):
        """Validate control points."""
        if len(self.control_points) != 5:
            raise ValueError(f"BezierCurve4 requires exactly 5 control points, got {len(self.control_points)}")
    
    @classmethod
    def from_points(
        cls,
        points: List[Tuple[float, float]],
        name: str = "",
        endpoints_locked: bool = True
    ) -> "BezierCurve4":
        """
        Create a Bezier curve from a list of 5 (z, r) tuples.
        
        Args:
            points: List of 5 (z, r) coordinate pairs
            name: Optional curve identifier
            endpoints_locked: If True, P0 and P4 are locked
        
        Returns:
            BezierCurve4 instance
        """
        if len(points) != 5:
            raise ValueError(f"Expected 5 points, got {len(points)}")
        
        control_points = []
        for i, (z, r) in enumerate(points):
            is_locked = endpoints_locked and (i == 0 or i == 4)
            control_points.append(ControlPoint(z=z, r=r, is_locked=is_locked))
        
        return cls(control_points=control_points, name=name)
    
    @classmethod
    def create_default(
        cls,
        p0: Tuple[float, float],
        p4: Tuple[float, float],
        name: str = ""
    ) -> "BezierCurve4":
        """
        Create a default Bezier curve with endpoints and interpolated interior points.
        
        The interior points P1, P2, P3 are placed at 1/4, 1/2, 3/4 along 
        the straight line from P0 to P4.
        
        Args:
            p0: Start point (z, r)
            p4: End point (z, r)
            name: Optional curve identifier
        
        Returns:
            BezierCurve4 instance
        """
        z0, r0 = p0
        z4, r4 = p4
        
        # Linear interpolation for intermediate points
        points = [
            (z0, r0),
            (z0 + 0.25 * (z4 - z0), r0 + 0.25 * (r4 - r0)),
            (z0 + 0.50 * (z4 - z0), r0 + 0.50 * (r4 - r0)),
            (z0 + 0.75 * (z4 - z0), r0 + 0.75 * (r4 - r0)),
            (z4, r4),
        ]
        
        return cls.from_points(points, name=name, endpoints_locked=True)
    
    def get_point(self, index: int) -> ControlPoint:
        """Get control point by index (0-4)."""
        return self.control_points[index]
    
    def set_point(self, index: int, z: float, r: float) -> bool:
        """
        Set a control point's position.
        
        Returns False if the point is locked and cannot be moved.
        """
        pt = self.control_points[index]
        if pt.is_locked:
            return False
        pt.z = z
        pt.r = r
        return True
    
    def get_control_array(self) -> NDArray[np.float64]:
        """Return control points as Nx2 numpy array."""
        return np.array([pt.to_tuple() for pt in self.control_points], dtype=np.float64)
    
    def evaluate(self, t: float) -> Tuple[float, float]:
        """
        Evaluate the curve at parameter t.
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            (z, r) coordinates at parameter t
        """
        t = np.clip(t, 0.0, 1.0)
        points = self.get_control_array()
        
        result = np.zeros(2, dtype=np.float64)
        for i in range(5):
            result += _bernstein(4, i, t) * points[i]
        
        return (float(result[0]), float(result[1]))
    
    def evaluate_many(self, n: int = 100) -> NDArray[np.float64]:
        """
        Sample n points along the curve.
        
        Args:
            n: Number of sample points
        
        Returns:
            Array of shape (n, 2) with (z, r) coordinates
        """
        t_values = np.linspace(0.0, 1.0, n)
        points = self.get_control_array()
        
        result = np.zeros((n, 2), dtype=np.float64)
        for i in range(5):
            coeffs = np.array([_bernstein(4, i, t) for t in t_values])
            result += np.outer(coeffs, points[i])
        
        return result
    
    def evaluate_derivative(self, t: float) -> Tuple[float, float]:
        """
        Compute first derivative (tangent) at parameter t.
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            (dz/dt, dr/dt) derivative components
        """
        t = np.clip(t, 0.0, 1.0)
        points = self.get_control_array()
        
        result = np.zeros(2, dtype=np.float64)
        for i in range(5):
            result += _bernstein_derivative(4, i, t) * points[i]
        
        return (float(result[0]), float(result[1]))
    
    def evaluate_second_derivative(self, t: float) -> Tuple[float, float]:
        """
        Compute second derivative at parameter t.
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            (d²z/dt², d²r/dt²) second derivative components
        """
        t = np.clip(t, 0.0, 1.0)
        points = self.get_control_array()
        
        result = np.zeros(2, dtype=np.float64)
        for i in range(5):
            result += _bernstein_second_derivative(4, i, t) * points[i]
        
        return (float(result[0]), float(result[1]))
    
    def compute_curvature(self, t: float) -> float:
        """
        Compute signed curvature at parameter t.
        
        Curvature κ = (z'r'' - r'z'') / (z'² + r'²)^(3/2)
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            Signed curvature value
        """
        dz, dr = self.evaluate_derivative(t)
        ddz, ddr = self.evaluate_second_derivative(t)
        
        # Cross product magnitude (2D)
        cross = dz * ddr - dr * ddz
        
        # Magnitude of tangent vector
        speed_sq = dz * dz + dr * dr
        
        if speed_sq < 1e-12:
            return 0.0
        
        return cross / (speed_sq ** 1.5)
    
    def compute_curvature_progression(self, n: int = 100) -> NDArray[np.float64]:
        """
        Compute curvature along the curve.
        
        Args:
            n: Number of sample points
        
        Returns:
            Array of shape (n, 2) with (t, curvature) values
        """
        t_values = np.linspace(0.0, 1.0, n)
        curvatures = np.array([self.compute_curvature(t) for t in t_values])
        return np.column_stack([t_values, curvatures])
    
    def compute_arc_length(self, n: int = 100) -> float:
        """
        Compute approximate arc length using numerical integration.
        
        Args:
            n: Number of integration segments
        
        Returns:
            Total arc length
        """
        points = self.evaluate_many(n)
        diffs = np.diff(points, axis=0)
        segment_lengths = np.sqrt(np.sum(diffs ** 2, axis=1))
        return float(np.sum(segment_lengths))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "name": self.name,
            "control_points": [
                {
                    "z": pt.z,
                    "r": pt.r,
                    "is_normalized": pt.is_normalized,
                    "is_locked": pt.is_locked,
                    "angle_locked": pt.angle_locked,
                }
                for pt in self.control_points
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BezierCurve4":
        """Deserialize from dictionary."""
        control_points = [
            ControlPoint(
                z=pt["z"],
                r=pt["r"],
                is_normalized=pt.get("is_normalized", False),
                is_locked=pt.get("is_locked", False),
                angle_locked=pt.get("angle_locked", False),
            )
            for pt in data["control_points"]
        ]
        return cls(control_points=control_points, name=data.get("name", ""))


class StraightLine:
    """
    A straight line between two points.
    
    Used for leading/trailing edges when not using Bezier mode.
    """
    
    def __init__(self, p0: Tuple[float, float], p1: Tuple[float, float], name: str = ""):
        self.p0 = p0
        self.p1 = p1
        self.name = name
    
    def evaluate(self, t: float) -> Tuple[float, float]:
        """Evaluate at parameter t in [0, 1]."""
        t = np.clip(t, 0.0, 1.0)
        z = self.p0[0] + t * (self.p1[0] - self.p0[0])
        r = self.p0[1] + t * (self.p1[1] - self.p0[1])
        return (z, r)
    
    def evaluate_many(self, n: int = 100) -> NDArray[np.float64]:
        """Sample n points along the line."""
        t_values = np.linspace(0.0, 1.0, n)
        result = np.zeros((n, 2), dtype=np.float64)
        for i, t in enumerate(t_values):
            result[i] = self.evaluate(t)
        return result
    
    def compute_curvature(self, t: float) -> float:
        """Curvature of a straight line is always 0."""
        return 0.0
    
    def compute_arc_length(self, n: int = 100) -> float:
        """Compute length of the line."""
        dz = self.p1[0] - self.p0[0]
        dr = self.p1[1] - self.p0[1]
        return float(np.sqrt(dz * dz + dr * dr))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "p0": list(self.p0),
            "p1": list(self.p1),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "StraightLine":
        """Deserialize from dictionary."""
        return cls(
            p0=tuple(data["p0"]),
            p1=tuple(data["p1"]),
            name=data.get("name", ""),
        )


@dataclass
class BezierCurve2:
    """
    2nd-order (quadratic) Bezier curve defined by 3 control points.
    
    The curve is parameterized by t in [0, 1]:
    C(t) = sum_{i=0}^{2} B_{i,2}(t) * P_i
    
    Used for leading/trailing edge curves in Bezier mode.
    
    Attributes:
        control_points: List of 3 ControlPoint objects (P0, P1, P2)
        name: Optional identifier for this curve
    """
    control_points: List[ControlPoint] = field(default_factory=list)
    name: str = ""
    
    def __post_init__(self):
        """Validate control points."""
        if len(self.control_points) != 3:
            raise ValueError(f"BezierCurve2 requires exactly 3 control points, got {len(self.control_points)}")
    
    @classmethod
    def from_points(
        cls,
        points: List[Tuple[float, float]],
        name: str = "",
        endpoints_locked: bool = True
    ) -> "BezierCurve2":
        """
        Create a quadratic Bezier curve from a list of 3 (z, r) tuples.
        
        Args:
            points: List of 3 (z, r) coordinate pairs
            name: Optional curve identifier
            endpoints_locked: If True, P0 and P2 are locked
        
        Returns:
            BezierCurve2 instance
        """
        if len(points) != 3:
            raise ValueError(f"Expected 3 points, got {len(points)}")
        
        control_points = []
        for i, (z, r) in enumerate(points):
            is_locked = endpoints_locked and (i == 0 or i == 2)
            control_points.append(ControlPoint(z=z, r=r, is_locked=is_locked))
        
        return cls(control_points=control_points, name=name)
    
    @classmethod
    def create_default(
        cls,
        p0: Tuple[float, float],
        p2: Tuple[float, float],
        name: str = ""
    ) -> "BezierCurve2":
        """
        Create a default quadratic Bezier with P1 at midpoint.
        
        Args:
            p0: Start point (z, r)
            p2: End point (z, r)
            name: Optional curve identifier
        
        Returns:
            BezierCurve2 instance
        """
        z0, r0 = p0
        z2, r2 = p2
        
        # P1 at midpoint
        p1 = (z0 + 0.5 * (z2 - z0), r0 + 0.5 * (r2 - r0))
        
        return cls.from_points([p0, p1, p2], name=name, endpoints_locked=False)
    
    def get_point(self, index: int) -> ControlPoint:
        """Get control point by index (0-2)."""
        return self.control_points[index]
    
    def set_point(self, index: int, z: float, r: float) -> bool:
        """
        Set a control point's position.
        
        Returns False if the point is locked and cannot be moved.
        """
        pt = self.control_points[index]
        if pt.is_locked:
            return False
        pt.z = z
        pt.r = r
        return True
    
    def get_control_array(self) -> NDArray[np.float64]:
        """Return control points as Nx2 numpy array."""
        return np.array([pt.to_tuple() for pt in self.control_points], dtype=np.float64)
    
    def evaluate(self, t: float) -> Tuple[float, float]:
        """
        Evaluate the curve at parameter t.
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            (z, r) coordinates at parameter t
        """
        t = np.clip(t, 0.0, 1.0)
        points = self.get_control_array()
        
        result = np.zeros(2, dtype=np.float64)
        for i in range(3):
            result += _bernstein(2, i, t) * points[i]
        
        return (float(result[0]), float(result[1]))
    
    def evaluate_many(self, n: int = 100) -> NDArray[np.float64]:
        """
        Sample n points along the curve.
        
        Args:
            n: Number of sample points
        
        Returns:
            Array of shape (n, 2) with (z, r) coordinates
        """
        t_values = np.linspace(0.0, 1.0, n)
        points = self.get_control_array()
        
        result = np.zeros((n, 2), dtype=np.float64)
        for i in range(3):
            coeffs = np.array([_bernstein(2, i, t) for t in t_values])
            result += np.outer(coeffs, points[i])
        
        return result
    
    def evaluate_derivative(self, t: float) -> Tuple[float, float]:
        """
        Compute first derivative (tangent) at parameter t.
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            (dz/dt, dr/dt) derivative components
        """
        t = np.clip(t, 0.0, 1.0)
        points = self.get_control_array()
        
        result = np.zeros(2, dtype=np.float64)
        for i in range(3):
            result += _bernstein_derivative(2, i, t) * points[i]
        
        return (float(result[0]), float(result[1]))
    
    def compute_curvature(self, t: float) -> float:
        """
        Compute signed curvature at parameter t.
        
        Args:
            t: Parameter in [0, 1]
        
        Returns:
            Signed curvature value
        """
        dz, dr = self.evaluate_derivative(t)
        
        # For quadratic Bezier, second derivative is constant
        points = self.get_control_array()
        ddz = 2 * (points[0, 0] - 2 * points[1, 0] + points[2, 0])
        ddr = 2 * (points[0, 1] - 2 * points[1, 1] + points[2, 1])
        
        cross = dz * ddr - dr * ddz
        speed_sq = dz * dz + dr * dr
        
        if speed_sq < 1e-12:
            return 0.0
        
        return cross / (speed_sq ** 1.5)
    
    def compute_arc_length(self, n: int = 100) -> float:
        """Compute approximate arc length."""
        points = self.evaluate_many(n)
        diffs = np.diff(points, axis=0)
        segment_lengths = np.sqrt(np.sum(diffs ** 2, axis=1))
        return float(np.sum(segment_lengths))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON export."""
        return {
            "name": self.name,
            "degree": 2,
            "control_points": [
                {
                    "z": pt.z,
                    "r": pt.r,
                    "is_normalized": pt.is_normalized,
                    "is_locked": pt.is_locked,
                }
                for pt in self.control_points
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BezierCurve2":
        """Deserialize from dictionary."""
        control_points = [
            ControlPoint(
                z=pt["z"],
                r=pt["r"],
                is_normalized=pt.get("is_normalized", False),
                is_locked=pt.get("is_locked", False),
            )
            for pt in data["control_points"]
        ]
        return cls(control_points=control_points, name=data.get("name", ""))

