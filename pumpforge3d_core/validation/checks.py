"""
Geometry validation checks.

Provides detailed validation of inducer designs with
actionable feedback for users.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
from enum import Enum

from ..geometry.inducer import InducerDesign
from ..geometry.bezier import BezierCurve4


class Severity(Enum):
    """Validation message severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationMessage:
    """A single validation finding."""
    severity: Severity
    code: str
    message: str
    location: str = ""  # Optional location hint (e.g., "hub_curve.P2")
    
    def __str__(self) -> str:
        prefix = f"[{self.severity.value.upper()}]"
        loc = f" ({self.location})" if self.location else ""
        return f"{prefix}{loc} {self.message}"


@dataclass
class ValidationResult:
    """Complete validation result for a design."""
    is_valid: bool
    messages: List[ValidationMessage] = field(default_factory=list)
    
    @property
    def errors(self) -> List[ValidationMessage]:
        """Get only error-level messages."""
        return [m for m in self.messages if m.severity == Severity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationMessage]:
        """Get only warning-level messages."""
        return [m for m in self.messages if m.severity == Severity.WARNING]
    
    @property
    def info(self) -> List[ValidationMessage]:
        """Get only info-level messages."""
        return [m for m in self.messages if m.severity == Severity.INFO]
    
    def add(self, severity: Severity, code: str, message: str, location: str = ""):
        """Add a validation message."""
        self.messages.append(ValidationMessage(severity, code, message, location))
        if severity == Severity.ERROR:
            self.is_valid = False


def validate_design(design: InducerDesign) -> ValidationResult:
    """
    Perform comprehensive validation of an inducer design.
    
    Checks include:
    - Dimension sanity (positive values, hub < tip)
    - Curve endpoint constraints
    - Control point positions (no negative radii)
    - Hub/tip curve intersection detection
    - Curvature extrema warnings
    
    Args:
        design: The design to validate
    
    Returns:
        ValidationResult with all findings
    """
    result = ValidationResult(is_valid=True)
    
    # Validate dimensions
    _validate_dimensions(design, result)
    
    # Validate hub curve
    _validate_curve(design.contour.hub_curve, "hub", design.main_dims, result)
    
    # Validate tip curve
    _validate_curve(design.contour.tip_curve, "tip", design.main_dims, result)
    
    # Check for intersections
    _check_curve_intersections(design, result)
    
    # Check curvature
    _check_curvature(design, result)
    
    return result


def _validate_dimensions(design: InducerDesign, result: ValidationResult):
    """Validate main dimensions."""
    dims = design.main_dims
    
    if dims.L <= 0:
        result.add(Severity.ERROR, "DIM001", 
                   f"Axial length must be positive (got {dims.L})",
                   "main_dims.L")
    
    if dims.r_h_in < 0:
        result.add(Severity.ERROR, "DIM002",
                   f"Inlet hub radius cannot be negative (got {dims.r_h_in})",
                   "main_dims.r_h_in")
    
    if dims.r_t_in < 0:
        result.add(Severity.ERROR, "DIM003",
                   f"Inlet tip radius cannot be negative (got {dims.r_t_in})",
                   "main_dims.r_t_in")
    
    if dims.r_h_in >= dims.r_t_in:
        result.add(Severity.ERROR, "DIM004",
                   f"Inlet hub radius ({dims.r_h_in}) must be less than inlet tip radius ({dims.r_t_in})",
                   "main_dims")
    
    if dims.r_h_out >= dims.r_t_out:
        result.add(Severity.ERROR, "DIM005",
                   f"Outlet hub radius ({dims.r_h_out}) must be less than outlet tip radius ({dims.r_t_out})",
                   "main_dims")
    
    # Warnings for unusual configurations
    if dims.r_h_in > dims.r_h_out * 2:
        result.add(Severity.WARNING, "DIM010",
                   "Large hub contraction may cause flow separation",
                   "main_dims.r_h")


def _validate_curve(curve: BezierCurve4, name: str, dims, result: ValidationResult):
    """Validate a single Bezier curve."""
    
    for i, pt in enumerate(curve.control_points):
        # Check for negative radii
        if pt.r < 0:
            result.add(Severity.ERROR, "CURVE001",
                       f"Control point P{i} has negative radius ({pt.r})",
                       f"{name}_curve.P{i}")
        
        # Check for out-of-bounds z
        if pt.z < -dims.L * 0.1:
            result.add(Severity.WARNING, "CURVE002",
                       f"Control point P{i} extends significantly before inlet (z={pt.z})",
                       f"{name}_curve.P{i}")
        
        if pt.z > dims.L * 1.1:
            result.add(Severity.WARNING, "CURVE003",
                       f"Control point P{i} extends significantly beyond outlet (z={pt.z})",
                       f"{name}_curve.P{i}")


def _check_curve_intersections(design: InducerDesign, result: ValidationResult):
    """Check if hub and tip curves intersect."""
    hub_points = design.contour.hub_curve.evaluate_many(100)
    tip_points = design.contour.tip_curve.evaluate_many(100)
    
    for i in range(len(hub_points)):
        r_hub = hub_points[i, 1]
        r_tip = tip_points[i, 1]
        z = hub_points[i, 0]
        
        if r_hub >= r_tip:
            result.add(Severity.ERROR, "GEOM001",
                       f"Hub and tip curves intersect or cross near z={z:.1f}",
                       "contour")
            return  # Only report first intersection
        
        gap = r_tip - r_hub
        if gap < 1.0:  # Less than 1mm gap
            result.add(Severity.WARNING, "GEOM002",
                       f"Very small gap ({gap:.2f}mm) between hub and tip near z={z:.1f}",
                       "contour")


def _check_curvature(design: InducerDesign, result: ValidationResult):
    """Check for excessive curvature values."""
    
    for curve, name in [
        (design.contour.hub_curve, "hub"),
        (design.contour.tip_curve, "tip")
    ]:
        progression = curve.compute_curvature_progression(50)
        curvatures = progression[:, 1]
        
        max_curv = max(abs(curvatures))
        if max_curv > 0.1:  # High curvature threshold
            result.add(Severity.INFO, "CURV001",
                       f"{name.capitalize()} curve has high curvature region (max |κ|={max_curv:.3f})",
                       f"{name}_curve")
