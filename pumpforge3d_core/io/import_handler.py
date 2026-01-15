"""
Import functionality for inducer designs.

Handles loading from JSON with version validation and migration.
"""

import json
from pathlib import Path
from typing import Tuple, Optional
import warnings

from .schema import check_version_compatibility, validate_schema, VersionCompatibility
from ..geometry.inducer import InducerDesign


class ImportError(Exception):
    """Raised when import fails due to validation errors."""
    pass


class ImportWarning(UserWarning):
    """Warning issued when import has non-fatal issues."""
    pass


def import_json(path: Path, strict: bool = False) -> Tuple[InducerDesign, list[str]]:
    """
    Import an inducer design from JSON format.
    
    Validates schema version and structure before loading.
    
    Args:
        path: Path to JSON file
        strict: If True, raise on any validation warning
    
    Returns:
        Tuple of (InducerDesign, list of warning messages)
    
    Raises:
        ImportError: If file cannot be loaded or has invalid schema
        FileNotFoundError: If file does not exist
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    warnings_list = []
    
    # Load JSON
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ImportError(f"Invalid JSON format: {e}")
    
    # Validate schema structure
    is_valid, errors = validate_schema(data)
    if not is_valid:
        raise ImportError(f"Schema validation failed: {'; '.join(errors)}")
    
    # Check version compatibility
    compat, version_msg = check_version_compatibility(data["schema_version"])
    
    if compat == VersionCompatibility.REJECT_MAJOR:
        raise ImportError(version_msg)
    elif compat == VersionCompatibility.WARN_NEWER_MINOR:
        warnings_list.append(version_msg)
        if strict:
            raise ImportError(version_msg)
        warnings.warn(version_msg, ImportWarning)
    
    # Load design
    try:
        design_data = data["design"]
        design = InducerDesign.from_dict(design_data)
    except (KeyError, TypeError, ValueError) as e:
        raise ImportError(f"Failed to parse design data: {e}")
    
    # Restore metadata if present
    if "metadata" in design_data:
        design.metadata.update(design_data["metadata"])
    
    # Add import metadata
    design.metadata["imported_from"] = str(path)
    design.metadata["original_schema_version"] = data["schema_version"]
    design.metadata["original_app_version"] = data.get("app_version", "unknown")
    
    return design, warnings_list


def import_polyline(path: Path) -> list[Tuple[float, float]]:
    """
    Import a polyline from a text file (x,y pairs).
    
    Used for reference curve overlays in the diagram view.
    
    Supported formats:
    - CSV with z,r columns (with or without header)
    - Space or tab separated values
    
    Args:
        path: Path to polyline file
    
    Returns:
        List of (z, r) coordinate tuples
    """
    path = Path(path)
    points = []
    
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Try different separators
        for sep in [',', '\t', ' ']:
            parts = [p.strip() for p in line.split(sep) if p.strip()]
            if len(parts) >= 2:
                try:
                    z = float(parts[0])
                    r = float(parts[1])
                    points.append((z, r))
                    break
                except ValueError:
                    # Skip header lines or invalid data
                    continue
    
    return points
