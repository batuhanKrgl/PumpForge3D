"""
Inducer domain model.

The InducerDesign class is the top-level container for all inducer geometry data.
It wraps MainDimensions and MeridionalContour with additional metadata and constraints.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime

from .meridional import MainDimensions, MeridionalContour


@dataclass
class ConstraintFlags:
    """Flags controlling curve behavior constraints."""
    
    # Hub curve P1/P3 angle constraints
    hub_p1_angle_locked: bool = False
    hub_p3_angle_locked: bool = False
    
    # Tip curve P1/P3 angle constraints
    tip_p1_angle_locked: bool = False
    tip_p3_angle_locked: bool = False
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "hub_p1_angle_locked": self.hub_p1_angle_locked,
            "hub_p3_angle_locked": self.hub_p3_angle_locked,
            "tip_p1_angle_locked": self.tip_p1_angle_locked,
            "tip_p3_angle_locked": self.tip_p3_angle_locked,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConstraintFlags":
        """Deserialize from dictionary."""
        return cls(
            hub_p1_angle_locked=data.get("hub_p1_angle_locked", False),
            hub_p3_angle_locked=data.get("hub_p3_angle_locked", False),
            tip_p1_angle_locked=data.get("tip_p1_angle_locked", False),
            tip_p3_angle_locked=data.get("tip_p3_angle_locked", False),
        )


@dataclass
class InducerDesign:
    """
    Complete inducer meridional design.
    
    This is the top-level container that holds all geometry data,
    constraints, and metadata for a single inducer design.
    
    Attributes:
        name: Design name/identifier
        main_dims: Main dimensions defining geometry bounds
        contour: Meridional contour with all curves
        constraints: Constraint flags for curve behavior
        metadata: Additional design metadata
    """
    name: str = "Untitled Inducer"
    main_dims: MainDimensions = field(default_factory=MainDimensions)
    contour: MeridionalContour = field(default_factory=MeridionalContour)
    constraints: ConstraintFlags = field(default_factory=ConstraintFlags)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize contour if needed."""
        if self.contour is None:
            self.contour = MeridionalContour.create_from_dimensions(self.main_dims)
        self._apply_constraints()
    
    def _apply_constraints(self):
        """Apply constraint flags to curves."""
        # Apply angle lock constraints to hub curve
        if len(self.contour.hub_curve.control_points) >= 5:
            self.contour.hub_curve.control_points[1].angle_locked = self.constraints.hub_p1_angle_locked
            self.contour.hub_curve.control_points[3].angle_locked = self.constraints.hub_p3_angle_locked
        
        # Apply angle lock constraints to tip curve
        if len(self.contour.tip_curve.control_points) >= 5:
            self.contour.tip_curve.control_points[1].angle_locked = self.constraints.tip_p1_angle_locked
            self.contour.tip_curve.control_points[3].angle_locked = self.constraints.tip_p3_angle_locked
    
    @classmethod
    def create_default(cls, name: str = "New Inducer") -> "InducerDesign":
        """
        Create a new inducer design with default dimensions and curves.
        
        Args:
            name: Design name
        
        Returns:
            InducerDesign with default geometry
        """
        dims = MainDimensions()
        contour = MeridionalContour.create_from_dimensions(dims)
        
        return cls(
            name=name,
            main_dims=dims,
            contour=contour,
            metadata={
                "created": datetime.now().isoformat(),
                "author": "",
                "notes": "",
            }
        )
    
    def set_main_dimensions(self, dims: MainDimensions):
        """
        Update main dimensions and propagate to contour.
        
        This updates curve endpoints while preserving internal shape.
        """
        self.main_dims = dims
        self.contour.update_from_dimensions(dims)
    
    def set_constraint(self, name: str, value: bool):
        """
        Set a constraint flag by name.
        
        Args:
            name: Constraint name (e.g., "hub_p1_angle_locked")
            value: True to enable, False to disable
        """
        if hasattr(self.constraints, name):
            setattr(self.constraints, name, value)
            self._apply_constraints()
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate the design geometry.
        
        Returns:
            Tuple of (is_valid, list of warning/error messages)
        """
        messages = []
        is_valid = True
        
        # Check for self-intersections (basic check)
        hub_points = self.contour.hub_curve.evaluate_many(50)
        tip_points = self.contour.tip_curve.evaluate_many(50)
        
        # Check that tip is always above hub
        for i in range(len(hub_points)):
            if hub_points[i, 1] >= tip_points[i, 1]:
                messages.append(f"Warning: Hub and tip curves may intersect near z={hub_points[i, 0]:.1f}")
                is_valid = False
                break
        
        # Check for negative radii
        if any(pt.r < 0 for pt in self.contour.hub_curve.control_points):
            messages.append("Error: Hub curve has negative radius values")
            is_valid = False
        
        if any(pt.r < 0 for pt in self.contour.tip_curve.control_points):
            messages.append("Error: Tip curve has negative radius values")
            is_valid = False
        
        # Check monotonicity in z (optional warning)
        hub_z = [pt.z for pt in self.contour.hub_curve.control_points]
        if hub_z != sorted(hub_z):
            messages.append("Info: Hub curve control points are not monotonic in z")
        
        return is_valid, messages
    
    def get_summary(self) -> dict:
        """Get a summary of the design for display."""
        hub_length = self.contour.hub_curve.compute_arc_length()
        tip_length = self.contour.tip_curve.compute_arc_length()
        
        return {
            "name": self.name,
            "axial_length": self.main_dims.L,
            "inlet_hub_radius": self.main_dims.r_h_in,
            "inlet_tip_radius": self.main_dims.r_t_in,
            "outlet_hub_radius": self.main_dims.r_h_out,
            "outlet_tip_radius": self.main_dims.r_t_out,
            "hub_arc_length": hub_length,
            "tip_arc_length": tip_length,
            "units": self.main_dims.units,
        }
    
    def to_dict(self) -> dict:
        """Serialize the complete design to dictionary."""
        return {
            "name": self.name,
            "main_dimensions": self.main_dims.to_dict(),
            "contour": self.contour.to_dict(),
            "constraints": self.constraints.to_dict(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InducerDesign":
        """Deserialize from dictionary."""
        design = cls(
            name=data.get("name", "Untitled"),
            main_dims=MainDimensions.from_dict(data["main_dimensions"]),
            contour=MeridionalContour.from_dict(data["contour"]),
            constraints=ConstraintFlags.from_dict(data.get("constraints", {})),
            metadata=data.get("metadata", {}),
        )
        design._apply_constraints()
        return design
