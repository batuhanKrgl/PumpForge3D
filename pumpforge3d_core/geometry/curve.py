"""
Curve module for handling Cartesian and cylindrical coordinates.

Provides coordinate system conversion and curve evaluation utilities
for turbomachinery geometry.
"""

from dataclasses import dataclass
from typing import List, Tuple, Literal
import math
import numpy as np
from numpy.typing import NDArray


@dataclass
class Point3D:
    """3D point in either Cartesian or cylindrical coordinates."""

    x: float  # Cartesian x OR cylindrical r
    y: float  # Cartesian y OR cylindrical theta (radians)
    z: float  # Cartesian z OR cylindrical z

    coordinate_system: Literal["cartesian", "cylindrical"] = "cartesian"

    def to_cartesian(self) -> "Point3D":
        """Convert to Cartesian coordinates."""
        if self.coordinate_system == "cartesian":
            return self

        # Cylindrical to Cartesian: (r, θ, z) → (x, y, z)
        r, theta, z = self.x, self.y, self.z
        x = r * math.cos(theta)
        y = r * math.sin(theta)

        return Point3D(x, y, z, coordinate_system="cartesian")

    def to_cylindrical(self) -> "Point3D":
        """Convert to cylindrical coordinates."""
        if self.coordinate_system == "cylindrical":
            return self

        # Cartesian to Cylindrical: (x, y, z) → (r, θ, z)
        x, y, z = self.x, self.y, self.z
        r = math.sqrt(x**2 + y**2)
        theta = math.atan2(y, x)

        return Point3D(r, theta, z, coordinate_system="cylindrical")

    def to_tuple(self) -> Tuple[float, float, float]:
        """Get coordinates as tuple (x, y, z) or (r, θ, z)."""
        return (self.x, self.y, self.z)


class Curve3D:
    """
    3D curve representation with coordinate system support.

    Stores points and provides evaluation methods for both Cartesian
    and cylindrical coordinate systems.
    """

    def __init__(
        self,
        points: List[Point3D],
        coordinate_system: Literal["cartesian", "cylindrical"] = "cartesian"
    ):
        """
        Initialize curve from points.

        Args:
            points: List of 3D points defining the curve
            coordinate_system: Native coordinate system for storage
        """
        self.points = points
        self.coordinate_system = coordinate_system

        # Ensure all points are in the same coordinate system
        self._normalize_points()

    def _normalize_points(self):
        """Convert all points to the curve's native coordinate system."""
        normalized = []
        for point in self.points:
            if self.coordinate_system == "cartesian":
                normalized.append(point.to_cartesian())
            else:
                normalized.append(point.to_cylindrical())
        self.points = normalized

    def evaluate_at_parameter(self, t: float) -> Point3D:
        """
        Evaluate curve at parameter t using linear interpolation.

        Args:
            t: Parameter in [0, 1]

        Returns:
            Point3D at parameter t
        """
        if not self.points:
            raise ValueError("Curve has no points")

        if len(self.points) == 1:
            return self.points[0]

        # Clamp t to [0, 1]
        t = max(0.0, min(1.0, t))

        # Find segment
        n_segments = len(self.points) - 1
        segment_idx = min(int(t * n_segments), n_segments - 1)
        local_t = (t * n_segments) - segment_idx

        # Linear interpolation
        p0 = self.points[segment_idx]
        p1 = self.points[segment_idx + 1]

        x = p0.x + local_t * (p1.x - p0.x)
        y = p0.y + local_t * (p1.y - p0.y)
        z = p0.z + local_t * (p1.z - p0.z)

        return Point3D(x, y, z, coordinate_system=self.coordinate_system)

    def evaluate_many(self, n: int = 100) -> NDArray[np.float64]:
        """
        Sample n points along the curve.

        Args:
            n: Number of sample points

        Returns:
            Array of shape (n, 3) with sampled points
        """
        t_values = np.linspace(0, 1, n)
        points = [self.evaluate_at_parameter(t) for t in t_values]

        return np.array([p.to_tuple() for p in points])

    def get_length(self) -> float:
        """
        Approximate curve length by summing segment lengths.

        Returns:
            Approximate curve length
        """
        if len(self.points) < 2:
            return 0.0

        total_length = 0.0
        for i in range(len(self.points) - 1):
            p0 = self.points[i]
            p1 = self.points[i + 1]

            dx = p1.x - p0.x
            dy = p1.y - p0.y
            dz = p1.z - p0.z

            segment_length = math.sqrt(dx**2 + dy**2 + dz**2)
            total_length += segment_length

        return total_length

    @classmethod
    def from_tuples(
        cls,
        points: List[Tuple[float, float, float]],
        coordinate_system: Literal["cartesian", "cylindrical"] = "cartesian"
    ) -> "Curve3D":
        """
        Create curve from list of tuples.

        Args:
            points: List of (x, y, z) or (r, θ, z) tuples
            coordinate_system: Coordinate system for input points

        Returns:
            Curve3D instance
        """
        point_objects = [
            Point3D(x, y, z, coordinate_system=coordinate_system)
            for x, y, z in points
        ]
        return cls(point_objects, coordinate_system)


def convert_meridional_to_3d(
    z: float,
    r: float,
    theta: float = 0.0
) -> Point3D:
    """
    Convert meridional (z, r) coordinates to 3D cylindrical.

    Meridional view shows (z, r) in 2D. To get 3D, add theta angle.

    Args:
        z: Axial coordinate
        r: Radial coordinate
        theta: Angular position (radians), default 0.0

    Returns:
        Point3D in cylindrical coordinates
    """
    return Point3D(r, theta, z, coordinate_system="cylindrical")


def interpolate_radius_at_span(
    r_hub: float,
    r_tip: float,
    span: float
) -> float:
    """
    Linearly interpolate radius at given span position.

    Args:
        r_hub: Hub radius
        r_tip: Tip/shroud radius
        span: Span position (0 = hub, 1 = tip)

    Returns:
        Interpolated radius
    """
    return r_hub + span * (r_tip - r_hub)
