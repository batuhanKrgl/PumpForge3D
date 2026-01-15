"""
JSON schema versioning and validation.

Implements semantic versioning for export format compatibility.
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import Enum


# Current schema version
SCHEMA_VERSION = "0.1.0"


class VersionCompatibility(Enum):
    """Compatibility status between versions."""
    COMPATIBLE = "compatible"
    WARN_NEWER_MINOR = "warn_newer_minor"
    REJECT_MAJOR = "reject_major"


@dataclass
class VersionInfo:
    """Parsed semantic version."""
    major: int
    minor: int
    patch: int
    
    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @classmethod
    def parse(cls, version_str: str) -> "VersionInfo":
        """Parse a semver string."""
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version_str)
        if not match:
            raise ValueError(f"Invalid version format: {version_str}")
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
        )


def check_version_compatibility(
    file_version: str,
    current_version: str = SCHEMA_VERSION
) -> Tuple[VersionCompatibility, str]:
    """
    Check compatibility between file schema version and current version.
    
    Rules:
    - Same major version: compatible
    - Newer minor version: warn but allow
    - Different major version: reject
    
    Args:
        file_version: Version string from imported file
        current_version: Current schema version
    
    Returns:
        Tuple of (compatibility status, message)
    """
    try:
        file_v = VersionInfo.parse(file_version)
        current_v = VersionInfo.parse(current_version)
    except ValueError as e:
        return VersionCompatibility.REJECT_MAJOR, str(e)
    
    if file_v.major != current_v.major:
        return (
            VersionCompatibility.REJECT_MAJOR,
            f"Incompatible major version: file is {file_v.major}.x.x, app supports {current_v.major}.x.x"
        )
    
    if file_v.minor > current_v.minor:
        return (
            VersionCompatibility.WARN_NEWER_MINOR,
            f"File is from newer version ({file_version}), some features may not load correctly"
        )
    
    return VersionCompatibility.COMPATIBLE, "Version compatible"


def validate_schema(data: dict) -> Tuple[bool, list[str]]:
    """
    Validate exported JSON data against the schema.
    
    Args:
        data: Dictionary loaded from JSON
    
    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    
    # Check required top-level fields
    required_fields = ["schema_version", "app_version", "design"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors
    
    # Check version compatibility
    compat, msg = check_version_compatibility(data["schema_version"])
    if compat == VersionCompatibility.REJECT_MAJOR:
        errors.append(msg)
        return False, errors
    
    # Validate design structure
    design = data.get("design", {})
    
    # Check main dimensions
    if "main_dimensions" not in design:
        errors.append("Missing main_dimensions in design")
    else:
        dims = design["main_dimensions"]
        dim_fields = ["r_h_in", "r_t_in", "r_h_out", "r_t_out", "L"]
        for field in dim_fields:
            if field not in dims:
                errors.append(f"Missing dimension field: {field}")
            elif not isinstance(dims[field], (int, float)):
                errors.append(f"Invalid type for {field}: expected number")
    
    # Check contour
    if "contour" not in design:
        errors.append("Missing contour in design")
    else:
        contour = design["contour"]
        for curve_name in ["hub_curve", "tip_curve"]:
            if curve_name not in contour:
                errors.append(f"Missing {curve_name} in contour")
            else:
                curve = contour[curve_name]
                if "control_points" not in curve:
                    errors.append(f"Missing control_points in {curve_name}")
                elif len(curve["control_points"]) != 5:
                    errors.append(f"{curve_name} must have exactly 5 control points")
    
    return len(errors) == 0, errors


COORDINATE_SYSTEM = {
    "description": "Axisymmetric meridional plane",
    "z_axis": "axial direction (inlet at z=0)",
    "r_axis": "radial direction (hub to tip)",
    "origin": "centerline at inlet plane",
}
