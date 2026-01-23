"""
Conformal Mapping for blade mean-line generation.

Implements the t,m conformal mapping workflow (CFturbo manual §7.3.2.1.1) to convert
2D meridional geometry + beta angle field into 3D mean-line curves.

Key concepts:
- Input geometry is an (n_i, n_j) grid: r_grid[i,j], z_grid[i,j]
- theta3 is incremental angle (dtheta), requiring cumulative sum along meridional index i
- theta[i+1,j] = theta[i,j] + dtheta[i,j] with theta[0,j] = theta0[j]

This module is GUI-independent and can be used for testing and batch processing.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
import numpy as np
from numpy.typing import NDArray


def solve_theta3_array(
    r1: NDArray[np.float64],
    r2: NDArray[np.float64],
    z1: NDArray[np.float64],
    z2: NDArray[np.float64],
    phi: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Solve for incremental theta (dtheta) given segment geometry and blade angle.

    This is the core conformal mapping solver that computes the angular increment
    needed to achieve a given blade angle phi for a segment from (r1,z1) to (r2,z2).

    Args:
        r1: Radial coordinate at segment start, shape (n_segments,) or (n_i-1, n_j)
        r2: Radial coordinate at segment end, shape matching r1
        z1: Axial coordinate at segment start, shape matching r1
        z2: Axial coordinate at segment end, shape matching r1
        phi: Blade angle in radians (angle from meridional direction), shape matching r1

    Returns:
        dtheta: Incremental theta angle in radians, shape matching input

    Notes:
        The solver uses a quadratic equation derived from the conformal mapping
        constraint. For numerical stability, the discriminant is clamped to >= 0
        and cos values are clipped to [-1, 1].
    """
    # Ensure inputs are arrays
    r1 = np.asarray(r1, dtype=np.float64)
    r2 = np.asarray(r2, dtype=np.float64)
    z1 = np.asarray(z1, dtype=np.float64)
    z2 = np.asarray(z2, dtype=np.float64)
    phi = np.asarray(phi, dtype=np.float64)

    D = z2 - z1
    alpha = np.cos(phi)

    K0 = r1**2 - r1 * r2 + D**2
    K1 = r2 * (r2 - r1)

    A = (r1 - r2)**2 + D**2
    L0 = r1**2 + r2**2 + D**2

    a_q = K1**2
    b_q = 2 * K0 * K1 + 2 * alpha**2 * A * r1 * r2
    c_q = K0**2 - alpha**2 * A * L0

    disc = b_q**2 - 4 * a_q * c_q
    disc = np.maximum(disc, 0.0)  # Numerical stability
    sqrt_disc = np.sqrt(disc)

    # Avoid division by zero
    a_q_safe = np.where(np.abs(a_q) < 1e-15, 1e-15, a_q)

    C1 = (-b_q + sqrt_disc) / (2 * a_q_safe)
    C2 = (-b_q - sqrt_disc) / (2 * a_q_safe)

    C1 = np.clip(C1, -1.0, 1.0)
    C2 = np.clip(C2, -1.0, 1.0)

    delta1 = np.arccos(C1)
    delta2 = np.arccos(C2)

    # Choose positive solution
    theta3 = np.where(delta1 > 0, delta1, delta2)

    # Handle degenerate cases where a_q is near zero
    theta3 = np.where(np.abs(a_q) < 1e-15, 0.0, theta3)

    return theta3


def generate_meridional_grid(
    hub_points: NDArray[np.float64],
    tip_points: NDArray[np.float64],
    n_spans: int,
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Generate r_grid and z_grid by interpolating between hub and tip curves.

    Args:
        hub_points: Hub curve points as (n_i, 2) array with columns [z, r]
        tip_points: Tip curve points as (n_i, 2) array with columns [z, r]
        n_spans: Number of spanwise stations (including hub and tip)

    Returns:
        r_grid: Radial coordinates, shape (n_i, n_spans)
        z_grid: Axial coordinates, shape (n_i, n_spans)

    Notes:
        Span fractions are uniformly distributed from 0 (hub) to 1 (tip).
        Points are linearly interpolated in both z and r directions.
    """
    n_i = hub_points.shape[0]

    r_grid = np.zeros((n_i, n_spans), dtype=np.float64)
    z_grid = np.zeros((n_i, n_spans), dtype=np.float64)

    span_fractions = np.linspace(0, 1, n_spans)

    for j, s in enumerate(span_fractions):
        # Linear interpolation between hub and tip
        z_grid[:, j] = hub_points[:, 0] + s * (tip_points[:, 0] - hub_points[:, 0])
        r_grid[:, j] = hub_points[:, 1] + s * (tip_points[:, 1] - hub_points[:, 1])

    return r_grid, z_grid


def generate_phi_grid_from_beta(
    beta_grid: NDArray[np.float64],
) -> NDArray[np.float64]:
    """
    Convert beta angle grid to phi angle grid.

    Beta is the blade angle measured from axial direction (typical CFD convention).
    Phi is the blade angle measured from meridional direction (conformal mapping convention).

    For a meridional flow, phi = beta (they coincide when flow is purely axial).
    In general: phi ≈ beta for small deviations.

    Args:
        beta_grid: Beta angles in degrees, shape (n_i, n_j) or (n_i-1, n_j)

    Returns:
        phi_grid: Phi angles in radians, same shape as input
    """
    # Convert degrees to radians
    # For now, assume phi ≈ beta (valid for meridional planes)
    return np.radians(beta_grid)


def generate_mock_phi_grid(n_i: int, n_j: int) -> NDArray[np.float64]:
    """
    Generate mock phi grid for testing when angle data is not available.

    Creates a deterministic phi distribution:
    - Linear progression from 5° to 80° along meridional direction (i)
    - Constant across spans (j)

    Args:
        n_i: Number of meridional stations (segments, so n_i-1 for grid)
        n_j: Number of spanwise stations

    Returns:
        phi_grid: Mock phi angles in radians, shape (n_i-1, n_j)
    """
    phi_vals_deg = np.linspace(5, 80, n_i - 1)
    phi_grid = np.tile(phi_vals_deg[:, np.newaxis], (1, n_j))
    return np.radians(phi_grid)


@dataclass
class ConformalMappingResult:
    """
    Result container for conformal mapping computation.

    Attributes:
        theta_grid: Cumulative theta angles, shape (n_i, n_j), radians
        dtheta_grid: Incremental theta angles, shape (n_i-1, n_j), radians
        wrap_per_span: Total wrap angle per span, shape (n_j,), radians
        xyz_lines: 3D mean-line coordinates, shape (n_j, n_i, 3)
        theta0: Initial theta angle per span, shape (n_j,), radians
        n_i: Number of meridional stations
        n_j: Number of spans
    """
    theta_grid: NDArray[np.float64]
    dtheta_grid: NDArray[np.float64]
    wrap_per_span: NDArray[np.float64]
    xyz_lines: NDArray[np.float64]
    theta0: NDArray[np.float64]
    n_i: int
    n_j: int

    @property
    def wrap_per_span_deg(self) -> NDArray[np.float64]:
        """Wrap angle per span in degrees."""
        return np.degrees(self.wrap_per_span)

    @property
    def theta0_deg(self) -> NDArray[np.float64]:
        """Initial theta per span in degrees."""
        return np.degrees(self.theta0)


def compute_conformal_mapping(
    r_grid: NDArray[np.float64],
    z_grid: NDArray[np.float64],
    phi_grid: NDArray[np.float64],
    theta0_per_span: Optional[NDArray[np.float64]] = None,
) -> ConformalMappingResult:
    """
    Compute 3D mean-line curves from meridional grid and blade angles.

    This is the main computation function implementing the conformal mapping:
    1. For each segment, solve for dtheta using solve_theta3_array
    2. Cumulative sum to get theta[i,j] = theta0[j] + sum(dtheta[0:i,j])
    3. Convert to Cartesian: x = r*cos(theta), y = r*sin(theta), z = z

    Args:
        r_grid: Radial coordinates, shape (n_i, n_j)
        z_grid: Axial coordinates, shape (n_i, n_j)
        phi_grid: Blade angles in radians, shape (n_i-1, n_j)
        theta0_per_span: Initial theta angle per span in radians, shape (n_j,)
                        If None, defaults to zeros

    Returns:
        ConformalMappingResult containing theta_grid, xyz_lines, wrap angles, etc.

    Raises:
        ValueError: If grid shapes are inconsistent
    """
    n_i, n_j = r_grid.shape

    if z_grid.shape != (n_i, n_j):
        raise ValueError(f"z_grid shape {z_grid.shape} doesn't match r_grid shape {r_grid.shape}")

    if phi_grid.shape != (n_i - 1, n_j):
        raise ValueError(f"phi_grid shape {phi_grid.shape} should be ({n_i - 1}, {n_j})")

    if theta0_per_span is None:
        theta0_per_span = np.zeros(n_j, dtype=np.float64)
    elif len(theta0_per_span) != n_j:
        raise ValueError(f"theta0_per_span length {len(theta0_per_span)} should be {n_j}")

    theta0_per_span = np.asarray(theta0_per_span, dtype=np.float64)

    # Compute dtheta for each segment
    r1 = r_grid[:-1, :]  # (n_i-1, n_j)
    r2 = r_grid[1:, :]
    z1 = z_grid[:-1, :]
    z2 = z_grid[1:, :]

    dtheta_grid = solve_theta3_array(r1, r2, z1, z2, phi_grid)

    # Cumulative sum to get theta
    theta_grid = np.zeros((n_i, n_j), dtype=np.float64)
    theta_grid[0, :] = theta0_per_span

    for i in range(n_i - 1):
        theta_grid[i + 1, :] = theta_grid[i, :] + dtheta_grid[i, :]

    # Wrap angle per span
    wrap_per_span = theta_grid[-1, :] - theta0_per_span

    # Convert to Cartesian coordinates
    xyz_lines = np.zeros((n_j, n_i, 3), dtype=np.float64)
    for j in range(n_j):
        xyz_lines[j, :, 0] = r_grid[:, j] * np.cos(theta_grid[:, j])  # x
        xyz_lines[j, :, 1] = r_grid[:, j] * np.sin(theta_grid[:, j])  # y
        xyz_lines[j, :, 2] = z_grid[:, j]  # z

    return ConformalMappingResult(
        theta_grid=theta_grid,
        dtheta_grid=dtheta_grid,
        wrap_per_span=wrap_per_span,
        xyz_lines=xyz_lines,
        theta0=theta0_per_span.copy(),
        n_i=n_i,
        n_j=n_j,
    )


@dataclass
class CoupledAngleState:
    """
    State manager for coupled theta0/wrap angle editing.

    Implements the anchoring + scaling strategy for dependent coupled inputs:
    - wrap is fundamentally derived from dtheta sum
    - theta0 edits keep dtheta unchanged, wrap recalculates
    - wrap edits scale dtheta and adjust theta0 to keep theta_end constant

    Attributes:
        n_j: Number of spans
        theta0: Current theta0 per span (radians)
        wrap_raw: Raw (unscaled) wrap per span from phi_grid
        wrap_scale: Scale factor per span (default 1.0)
        theta_end_anchor: Persisted theta_end for anchoring (radians)
    """
    n_j: int
    theta0: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    wrap_raw: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    wrap_scale: NDArray[np.float64] = field(default_factory=lambda: np.array([]))
    theta_end_anchor: NDArray[np.float64] = field(default_factory=lambda: np.array([]))

    def __post_init__(self):
        """Initialize arrays if empty."""
        if len(self.theta0) == 0:
            self.theta0 = np.zeros(self.n_j, dtype=np.float64)
        if len(self.wrap_raw) == 0:
            self.wrap_raw = np.zeros(self.n_j, dtype=np.float64)
        if len(self.wrap_scale) == 0:
            self.wrap_scale = np.ones(self.n_j, dtype=np.float64)
        if len(self.theta_end_anchor) == 0:
            self.theta_end_anchor = np.zeros(self.n_j, dtype=np.float64)

    @property
    def wrap_current(self) -> NDArray[np.float64]:
        """Current (possibly scaled) wrap angle per span."""
        return self.wrap_raw * self.wrap_scale

    @property
    def theta0_deg(self) -> NDArray[np.float64]:
        """Theta0 in degrees."""
        return np.degrees(self.theta0)

    @property
    def wrap_current_deg(self) -> NDArray[np.float64]:
        """Current wrap angle in degrees."""
        return np.degrees(self.wrap_current)

    @property
    def theta_end(self) -> NDArray[np.float64]:
        """Current theta_end per span."""
        return self.theta0 + self.wrap_current

    def update_from_result(self, result: ConformalMappingResult, reset_scaling: bool = True):
        """
        Update state from a fresh computation result.

        Args:
            result: Conformal mapping computation result
            reset_scaling: If True, reset scale factors to 1.0 (default on upstream change)
        """
        if result.n_j != self.n_j:
            # Resize if span count changed
            self.n_j = result.n_j
            self.theta0 = result.theta0.copy()
            self.wrap_raw = result.wrap_per_span.copy()
            self.wrap_scale = np.ones(self.n_j, dtype=np.float64)
            self.theta_end_anchor = self.theta0 + self.wrap_raw
        else:
            self.wrap_raw = result.wrap_per_span.copy()
            if reset_scaling:
                self.wrap_scale = np.ones(self.n_j, dtype=np.float64)
                self.theta_end_anchor = self.theta0 + self.wrap_raw

    def edit_theta0(self, j: int, theta0_new_rad: float):
        """
        Handle user edit of theta0[j].

        Rule A: Keep dtheta unchanged, wrap stays same, theta_end changes.

        Args:
            j: Span index
            theta0_new_rad: New theta0 value in radians
        """
        if 0 <= j < self.n_j:
            self.theta0[j] = theta0_new_rad
            # Update anchor to new theta_end
            self.theta_end_anchor[j] = theta0_new_rad + self.wrap_current[j]

    def edit_wrap(self, j: int, wrap_new_rad: float):
        """
        Handle user edit of wrap[j].

        Rule B: Scale dtheta to achieve new wrap, adjust theta0 to keep anchor.

        Args:
            j: Span index
            wrap_new_rad: New wrap angle in radians
        """
        if 0 <= j < self.n_j:
            wrap_raw_j = self.wrap_raw[j]

            # Compute new scale factor (handle near-zero safely)
            if abs(wrap_raw_j) > 1e-9:
                self.wrap_scale[j] = wrap_new_rad / wrap_raw_j
            else:
                self.wrap_scale[j] = 1.0

            # Adjust theta0 to keep theta_end_anchor constant
            self.theta0[j] = self.theta_end_anchor[j] - wrap_new_rad

    def get_scaled_dtheta(self, dtheta_grid: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Apply wrap scaling to dtheta grid.

        Args:
            dtheta_grid: Unscaled dtheta, shape (n_i-1, n_j)

        Returns:
            Scaled dtheta grid
        """
        return dtheta_grid * self.wrap_scale[np.newaxis, :]

    def reset_span(self, j: int):
        """Reset scaling for a specific span."""
        if 0 <= j < self.n_j:
            self.wrap_scale[j] = 1.0
            self.theta_end_anchor[j] = self.theta0[j] + self.wrap_raw[j]


def compute_conformal_mapping_with_state(
    r_grid: NDArray[np.float64],
    z_grid: NDArray[np.float64],
    phi_grid: NDArray[np.float64],
    state: CoupledAngleState,
) -> ConformalMappingResult:
    """
    Compute conformal mapping using coupled angle state for theta0 and scaling.

    This variant uses the CoupledAngleState to apply user-specified theta0 and
    wrap scaling factors.

    Args:
        r_grid: Radial coordinates, shape (n_i, n_j)
        z_grid: Axial coordinates, shape (n_i, n_j)
        phi_grid: Blade angles in radians, shape (n_i-1, n_j)
        state: Coupled angle state with theta0 and scale factors

    Returns:
        ConformalMappingResult with scaled theta and wrap values
    """
    n_i, n_j = r_grid.shape

    # First compute unscaled dtheta
    r1 = r_grid[:-1, :]
    r2 = r_grid[1:, :]
    z1 = z_grid[:-1, :]
    z2 = z_grid[1:, :]

    dtheta_raw = solve_theta3_array(r1, r2, z1, z2, phi_grid)

    # Apply scaling from state
    dtheta_scaled = state.get_scaled_dtheta(dtheta_raw)

    # Cumulative sum with user theta0
    theta_grid = np.zeros((n_i, n_j), dtype=np.float64)
    theta_grid[0, :] = state.theta0

    for i in range(n_i - 1):
        theta_grid[i + 1, :] = theta_grid[i, :] + dtheta_scaled[i, :]

    # Wrap angle per span
    wrap_per_span = theta_grid[-1, :] - state.theta0

    # Convert to Cartesian
    xyz_lines = np.zeros((n_j, n_i, 3), dtype=np.float64)
    for j in range(n_j):
        xyz_lines[j, :, 0] = r_grid[:, j] * np.cos(theta_grid[:, j])
        xyz_lines[j, :, 1] = r_grid[:, j] * np.sin(theta_grid[:, j])
        xyz_lines[j, :, 2] = z_grid[:, j]

    return ConformalMappingResult(
        theta_grid=theta_grid,
        dtheta_grid=dtheta_scaled,
        wrap_per_span=wrap_per_span,
        xyz_lines=xyz_lines,
        theta0=state.theta0.copy(),
        n_i=n_i,
        n_j=n_j,
    )


def normalize_angle_deg(angle_deg: float, mode: str = "symmetric") -> float:
    """
    Normalize angle to a standard range.

    Args:
        angle_deg: Angle in degrees
        mode: "symmetric" for (-180, 180], "positive" for [0, 360)

    Returns:
        Normalized angle in degrees
    """
    if mode == "symmetric":
        # (-180, 180]
        while angle_deg > 180:
            angle_deg -= 360
        while angle_deg <= -180:
            angle_deg += 360
    else:
        # [0, 360)
        while angle_deg >= 360:
            angle_deg -= 360
        while angle_deg < 0:
            angle_deg += 360

    return angle_deg
