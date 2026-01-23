"""
Curve class for handling cartesian and cylindrical coordinates.

Provides a unified interface for geometric curves with support for:
- Cartesian coordinates (x, y, z)
- Cylindrical coordinates (r, theta, z)
- Coordinate system conversions
- Arc-length parameterization
- Interpolation methods
"""

from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Union
from enum import Enum
import numpy as np
from numpy.typing import NDArray


class CoordinateSystem(Enum):
    """Coordinate system enumeration."""
    CARTESIAN = "cartesian"      # (x, y, z)
    CYLINDRICAL = "cylindrical"  # (r, theta, z)
    MERIDIONAL = "meridional"    # (z, r) - axisymmetric meridional plane


@dataclass
class Point3D:
    """
    A 3D point that can be represented in multiple coordinate systems.

    Internal storage is Cartesian (x, y, z).
    Cylindrical access: r = sqrt(x² + y²), theta = atan2(y, x), z = z
    """
    x: float
    y: float
    z: float

    @classmethod
    def from_cartesian(cls, x: float, y: float, z: float) -> "Point3D":
        """Create point from Cartesian coordinates."""
        return cls(x=x, y=y, z=z)

    @classmethod
    def from_cylindrical(cls, r: float, theta: float, z: float) -> "Point3D":
        """
        Create point from cylindrical coordinates.

        Args:
            r: Radial distance from z-axis
            theta: Azimuthal angle (radians)
            z: Axial position
        """
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        return cls(x=x, y=y, z=z)

    @classmethod
    def from_meridional(cls, z_axial: float, r: float, theta: float = 0.0) -> "Point3D":
        """
        Create point from meridional coordinates.

        Args:
            z_axial: Axial position
            r: Radial position
            theta: Azimuthal angle (radians), default 0 for meridional plane
        """
        return cls.from_cylindrical(r, theta, z_axial)

    @property
    def r(self) -> float:
        """Radial distance from z-axis (cylindrical r)."""
        return np.sqrt(self.x**2 + self.y**2)

    @property
    def theta(self) -> float:
        """Azimuthal angle in radians (cylindrical theta)."""
        return np.arctan2(self.y, self.x)

    @property
    def cartesian(self) -> Tuple[float, float, float]:
        """Return (x, y, z) tuple."""
        return (self.x, self.y, self.z)

    @property
    def cylindrical(self) -> Tuple[float, float, float]:
        """Return (r, theta, z) tuple."""
        return (self.r, self.theta, self.z)

    @property
    def meridional(self) -> Tuple[float, float]:
        """Return (z, r) tuple for meridional plane."""
        return (self.z, self.r)

    def to_array(self, system: CoordinateSystem = CoordinateSystem.CARTESIAN) -> NDArray[np.float64]:
        """Return point as numpy array in specified coordinate system."""
        if system == CoordinateSystem.CARTESIAN:
            return np.array([self.x, self.y, self.z], dtype=np.float64)
        elif system == CoordinateSystem.CYLINDRICAL:
            return np.array([self.r, self.theta, self.z], dtype=np.float64)
        else:  # MERIDIONAL
            return np.array([self.z, self.r], dtype=np.float64)

    def distance_to(self, other: "Point3D") -> float:
        """Euclidean distance to another point."""
        return np.sqrt(
            (self.x - other.x)**2 +
            (self.y - other.y)**2 +
            (self.z - other.z)**2
        )

    def copy(self) -> "Point3D":
        """Create a copy of this point."""
        return Point3D(x=self.x, y=self.y, z=self.z)


@dataclass
class Curve:
    """
    A parametric curve in 3D space with coordinate system support.

    The curve is stored as a sequence of sample points and supports:
    - Multiple coordinate system representations
    - Arc-length parameterization
    - Interpolation between sample points
    - Conversion between coordinate systems

    Attributes:
        points: List of Point3D objects defining the curve
        name: Optional identifier for this curve
        is_closed: Whether the curve forms a closed loop
    """
    points: List[Point3D] = field(default_factory=list)
    name: str = ""
    is_closed: bool = False
    _arc_lengths: Optional[NDArray[np.float64]] = field(default=None, repr=False)

    def __post_init__(self):
        """Compute arc lengths on initialization."""
        if len(self.points) > 1:
            self._compute_arc_lengths()

    def _compute_arc_lengths(self):
        """Compute cumulative arc lengths for parameterization."""
        n = len(self.points)
        if n < 2:
            self._arc_lengths = np.array([0.0])
            return

        lengths = np.zeros(n)
        for i in range(1, n):
            lengths[i] = lengths[i-1] + self.points[i-1].distance_to(self.points[i])

        self._arc_lengths = lengths

    @property
    def total_length(self) -> float:
        """Total arc length of the curve."""
        if self._arc_lengths is None or len(self._arc_lengths) == 0:
            return 0.0
        return float(self._arc_lengths[-1])

    @property
    def n_points(self) -> int:
        """Number of sample points."""
        return len(self.points)

    @classmethod
    def from_cartesian_arrays(
        cls,
        x: NDArray[np.float64],
        y: NDArray[np.float64],
        z: NDArray[np.float64],
        name: str = ""
    ) -> "Curve":
        """
        Create curve from Cartesian coordinate arrays.

        Args:
            x, y, z: Arrays of equal length
            name: Optional curve identifier
        """
        if not (len(x) == len(y) == len(z)):
            raise ValueError("Coordinate arrays must have equal length")

        points = [Point3D(x=float(x[i]), y=float(y[i]), z=float(z[i]))
                  for i in range(len(x))]
        return cls(points=points, name=name)

    @classmethod
    def from_cylindrical_arrays(
        cls,
        r: NDArray[np.float64],
        theta: NDArray[np.float64],
        z: NDArray[np.float64],
        name: str = ""
    ) -> "Curve":
        """
        Create curve from cylindrical coordinate arrays.

        Args:
            r: Radial distances
            theta: Azimuthal angles (radians)
            z: Axial positions
            name: Optional curve identifier
        """
        if not (len(r) == len(theta) == len(z)):
            raise ValueError("Coordinate arrays must have equal length")

        points = [Point3D.from_cylindrical(float(r[i]), float(theta[i]), float(z[i]))
                  for i in range(len(r))]
        return cls(points=points, name=name)

    @classmethod
    def from_meridional_array(
        cls,
        zr_array: NDArray[np.float64],
        theta: float = 0.0,
        name: str = ""
    ) -> "Curve":
        """
        Create curve from meridional (z, r) array.

        Args:
            zr_array: Array of shape (n, 2) with [z, r] coordinates
            theta: Azimuthal angle for all points (default 0)
            name: Optional curve identifier
        """
        if zr_array.ndim != 2 or zr_array.shape[1] != 2:
            raise ValueError("Expected (n, 2) array for meridional coordinates")

        points = [Point3D.from_meridional(float(zr_array[i, 0]), float(zr_array[i, 1]), theta)
                  for i in range(len(zr_array))]
        return cls(points=points, name=name)

    def to_cartesian(self) -> NDArray[np.float64]:
        """
        Return curve points as Cartesian array.

        Returns:
            Array of shape (n, 3) with [x, y, z] coordinates
        """
        return np.array([p.cartesian for p in self.points], dtype=np.float64)

    def to_cylindrical(self) -> NDArray[np.float64]:
        """
        Return curve points as cylindrical array.

        Returns:
            Array of shape (n, 3) with [r, theta, z] coordinates
        """
        return np.array([p.cylindrical for p in self.points], dtype=np.float64)

    def to_meridional(self) -> NDArray[np.float64]:
        """
        Return curve points as meridional array.

        Returns:
            Array of shape (n, 2) with [z, r] coordinates
        """
        return np.array([p.meridional for p in self.points], dtype=np.float64)

    def get_x(self) -> NDArray[np.float64]:
        """Get x-coordinates array."""
        return np.array([p.x for p in self.points], dtype=np.float64)

    def get_y(self) -> NDArray[np.float64]:
        """Get y-coordinates array."""
        return np.array([p.y for p in self.points], dtype=np.float64)

    def get_z(self) -> NDArray[np.float64]:
        """Get z-coordinates (axial) array."""
        return np.array([p.z for p in self.points], dtype=np.float64)

    def get_r(self) -> NDArray[np.float64]:
        """Get radial coordinates array."""
        return np.array([p.r for p in self.points], dtype=np.float64)

    def get_theta(self) -> NDArray[np.float64]:
        """Get azimuthal angle array."""
        return np.array([p.theta for p in self.points], dtype=np.float64)

    def evaluate_at(self, t: float) -> Point3D:
        """
        Evaluate curve at normalized parameter t ∈ [0, 1].

        Uses linear interpolation between sample points based on
        arc-length parameterization.

        Args:
            t: Parameter in [0, 1]

        Returns:
            Interpolated Point3D
        """
        t = np.clip(t, 0.0, 1.0)

        if len(self.points) < 2:
            return self.points[0].copy() if self.points else Point3D(0, 0, 0)

        # Target arc length
        target_s = t * self.total_length

        # Find segment containing target
        idx = np.searchsorted(self._arc_lengths, target_s) - 1
        idx = max(0, min(idx, len(self.points) - 2))

        # Local interpolation parameter
        s0 = self._arc_lengths[idx]
        s1 = self._arc_lengths[idx + 1]
        ds = s1 - s0

        if ds < 1e-12:
            local_t = 0.0
        else:
            local_t = (target_s - s0) / ds

        # Linear interpolation
        p0 = self.points[idx]
        p1 = self.points[idx + 1]

        x = p0.x + local_t * (p1.x - p0.x)
        y = p0.y + local_t * (p1.y - p0.y)
        z = p0.z + local_t * (p1.z - p0.z)

        return Point3D(x=x, y=y, z=z)

    def evaluate_at_arc_length(self, s: float) -> Point3D:
        """
        Evaluate curve at specific arc length.

        Args:
            s: Arc length from start of curve

        Returns:
            Interpolated Point3D
        """
        if self.total_length < 1e-12:
            return self.points[0].copy() if self.points else Point3D(0, 0, 0)

        t = s / self.total_length
        return self.evaluate_at(t)

    def resample(self, n: int) -> "Curve":
        """
        Resample curve with uniform arc-length spacing.

        Args:
            n: Number of sample points

        Returns:
            New Curve with n uniformly spaced points
        """
        if n < 2:
            raise ValueError("Need at least 2 points for resampling")

        t_values = np.linspace(0.0, 1.0, n)
        new_points = [self.evaluate_at(t) for t in t_values]

        return Curve(points=new_points, name=self.name, is_closed=self.is_closed)

    def revolve(self, n_theta: int = 36) -> List["Curve"]:
        """
        Revolve meridional curve around z-axis.

        Creates n_theta copies of the curve at different azimuthal angles.

        Args:
            n_theta: Number of azimuthal divisions

        Returns:
            List of Curves at different theta angles
        """
        theta_values = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
        curves = []

        for theta in theta_values:
            new_points = []
            for p in self.points:
                new_p = Point3D.from_cylindrical(p.r, theta, p.z)
                new_points.append(new_p)
            curves.append(Curve(points=new_points, name=f"{self.name}_theta_{np.degrees(theta):.0f}"))

        return curves

    def get_point_at_index(self, idx: int) -> Point3D:
        """Get point by index."""
        return self.points[idx]

    def get_start(self) -> Point3D:
        """Get first point of curve."""
        return self.points[0] if self.points else Point3D(0, 0, 0)

    def get_end(self) -> Point3D:
        """Get last point of curve."""
        return self.points[-1] if self.points else Point3D(0, 0, 0)

    def reverse(self) -> "Curve":
        """Return reversed curve."""
        return Curve(
            points=list(reversed(self.points)),
            name=self.name,
            is_closed=self.is_closed
        )

    def transform_theta(self, delta_theta: float) -> "Curve":
        """
        Rotate curve around z-axis.

        Args:
            delta_theta: Rotation angle (radians)

        Returns:
            New rotated Curve
        """
        new_points = []
        for p in self.points:
            new_p = Point3D.from_cylindrical(p.r, p.theta + delta_theta, p.z)
            new_points.append(new_p)
        return Curve(points=new_points, name=self.name, is_closed=self.is_closed)

    def scale(self, factor: float) -> "Curve":
        """
        Scale curve uniformly from origin.

        Args:
            factor: Scale factor

        Returns:
            New scaled Curve
        """
        new_points = [Point3D(x=p.x * factor, y=p.y * factor, z=p.z * factor)
                      for p in self.points]
        return Curve(points=new_points, name=self.name, is_closed=self.is_closed)

    def translate(self, dx: float = 0, dy: float = 0, dz: float = 0) -> "Curve":
        """
        Translate curve.

        Args:
            dx, dy, dz: Translation amounts

        Returns:
            New translated Curve
        """
        new_points = [Point3D(x=p.x + dx, y=p.y + dy, z=p.z + dz)
                      for p in self.points]
        return Curve(points=new_points, name=self.name, is_closed=self.is_closed)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "is_closed": self.is_closed,
            "points": [
                {"x": p.x, "y": p.y, "z": p.z}
                for p in self.points
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Curve":
        """Deserialize from dictionary."""
        points = [Point3D(x=p["x"], y=p["y"], z=p["z"]) for p in data["points"]]
        return cls(
            points=points,
            name=data.get("name", ""),
            is_closed=data.get("is_closed", False)
        )


@dataclass
class MeridionalCurve:
    """
    Specialized curve for meridional plane (z, r) coordinates.

    This is an optimized version for 2D axisymmetric geometry
    where we only need (z, r) coordinates.
    """
    z: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    r: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    name: str = ""
    _arc_lengths: Optional[NDArray[np.float64]] = field(default=None, repr=False)

    def __post_init__(self):
        """Validate and compute arc lengths."""
        if len(self.z) != len(self.r):
            raise ValueError("z and r arrays must have equal length")
        if len(self.z) > 1:
            self._compute_arc_lengths()

    def _compute_arc_lengths(self):
        """Compute cumulative arc lengths."""
        n = len(self.z)
        lengths = np.zeros(n)
        for i in range(1, n):
            dz = self.z[i] - self.z[i-1]
            dr = self.r[i] - self.r[i-1]
            lengths[i] = lengths[i-1] + np.sqrt(dz**2 + dr**2)
        self._arc_lengths = lengths

    @property
    def total_length(self) -> float:
        """Total arc length."""
        if self._arc_lengths is None or len(self._arc_lengths) == 0:
            return 0.0
        return float(self._arc_lengths[-1])

    @property
    def n_points(self) -> int:
        """Number of points."""
        return len(self.z)

    @classmethod
    def from_array(cls, zr: NDArray[np.float64], name: str = "") -> "MeridionalCurve":
        """Create from (n, 2) array with [z, r] columns."""
        return cls(z=zr[:, 0].copy(), r=zr[:, 1].copy(), name=name)

    def to_array(self) -> NDArray[np.float64]:
        """Return as (n, 2) array with [z, r] columns."""
        return np.column_stack([self.z, self.r])

    def evaluate_at(self, t: float) -> Tuple[float, float]:
        """
        Evaluate at normalized parameter t ∈ [0, 1].

        Returns:
            (z, r) tuple
        """
        t = np.clip(t, 0.0, 1.0)

        if len(self.z) < 2:
            return (float(self.z[0]), float(self.r[0])) if len(self.z) > 0 else (0.0, 0.0)

        target_s = t * self.total_length
        idx = np.searchsorted(self._arc_lengths, target_s) - 1
        idx = max(0, min(idx, len(self.z) - 2))

        s0 = self._arc_lengths[idx]
        s1 = self._arc_lengths[idx + 1]
        ds = s1 - s0

        local_t = (target_s - s0) / ds if ds > 1e-12 else 0.0

        z_interp = self.z[idx] + local_t * (self.z[idx + 1] - self.z[idx])
        r_interp = self.r[idx] + local_t * (self.r[idx + 1] - self.r[idx])

        return (float(z_interp), float(r_interp))

    def get_radius_at_z(self, z_target: float) -> Optional[float]:
        """
        Get radius at specific z position (linear interpolation).

        Returns None if z_target is outside curve range.
        """
        if len(self.z) < 2:
            return None

        z_min, z_max = self.z.min(), self.z.max()
        if z_target < z_min or z_target > z_max:
            return None

        # Find interpolation index
        idx = np.searchsorted(self.z, z_target) - 1
        idx = max(0, min(idx, len(self.z) - 2))

        z0, z1 = self.z[idx], self.z[idx + 1]
        r0, r1 = self.r[idx], self.r[idx + 1]

        if abs(z1 - z0) < 1e-12:
            return float(r0)

        t = (z_target - z0) / (z1 - z0)
        return float(r0 + t * (r1 - r0))

    def resample(self, n: int) -> "MeridionalCurve":
        """Resample with uniform arc-length spacing."""
        t_values = np.linspace(0.0, 1.0, n)
        points = [self.evaluate_at(t) for t in t_values]
        z_new = np.array([p[0] for p in points])
        r_new = np.array([p[1] for p in points])
        return MeridionalCurve(z=z_new, r=r_new, name=self.name)

    def to_3d_curve(self, theta: float = 0.0) -> Curve:
        """Convert to 3D Curve at specified azimuthal angle."""
        points = [Point3D.from_meridional(float(self.z[i]), float(self.r[i]), theta)
                  for i in range(len(self.z))]
        return Curve(points=points, name=self.name)

    def get_start(self) -> Tuple[float, float]:
        """Get (z, r) at start."""
        return (float(self.z[0]), float(self.r[0])) if len(self.z) > 0 else (0.0, 0.0)

    def get_end(self) -> Tuple[float, float]:
        """Get (z, r) at end."""
        return (float(self.z[-1]), float(self.r[-1])) if len(self.z) > 0 else (0.0, 0.0)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "z": self.z.tolist(),
            "r": self.r.tolist()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MeridionalCurve":
        """Deserialize from dictionary."""
        return cls(
            z=np.array(data["z"], dtype=np.float64),
            r=np.array(data["r"], dtype=np.float64),
            name=data.get("name", "")
        )
