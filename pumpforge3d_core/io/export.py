"""
Export functionality for inducer designs.

Exports to versioned JSON format and optional CSV for sampled points.
"""

import json
from pathlib import Path
from typing import Optional
import csv

from .schema import SCHEMA_VERSION, COORDINATE_SYSTEM
from ..geometry.inducer import InducerDesign
from .. import __version__ as CORE_VERSION


def export_json(
    design: InducerDesign,
    path: Path,
    app_version: Optional[str] = None,
    indent: int = 2
) -> None:
    """
    Export an inducer design to JSON format.
    
    The exported JSON includes:
    - Schema version for compatibility checking
    - App version for traceability
    - Units and coordinate system definition
    - All design data (dimensions, curves, constraints)
    - Sampled geometry points
    
    Args:
        design: The InducerDesign to export
        path: Output file path
        app_version: Optional app version string (defaults to core version)
        indent: JSON indentation level
    """
    if app_version is None:
        app_version = CORE_VERSION
    
    # Sample points for convenience
    sample_points = design.contour.get_all_sample_points(n=200)
    
    export_data = {
        "schema_version": SCHEMA_VERSION,
        "app_version": app_version,
        "coordinate_system": COORDINATE_SYSTEM,
        "design": design.to_dict(),
        "sampled_geometry": {
            "sample_count": 200,
            "hub": sample_points["hub"].tolist(),
            "tip": sample_points["tip"].tolist(),
            "leading_edge": sample_points["leading"].tolist(),
            "trailing_edge": sample_points["trailing"].tolist(),
        }
    }
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=indent)


def export_csv_samples(
    design: InducerDesign,
    path: Path,
    n_samples: int = 200
) -> None:
    """
    Export sampled geometry points to CSV format.
    
    Creates separate CSV files for each curve:
    - {name}_hub.csv
    - {name}_tip.csv
    - {name}_leading.csv
    - {name}_trailing.csv
    
    Args:
        design: The InducerDesign to export
        path: Base output path (without extension)
        n_samples: Number of sample points per curve
    """
    path = Path(path)
    base_name = path.stem
    output_dir = path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    sample_points = design.contour.get_all_sample_points(n=n_samples)
    
    for curve_name, points in sample_points.items():
        csv_path = output_dir / f"{base_name}_{curve_name}.csv"
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["z", "r"])
            for z, r in points:
                writer.writerow([f"{z:.6f}", f"{r:.6f}"])


def export_summary(design: InducerDesign, path: Path) -> None:
    """
    Export a human-readable summary of the design.
    
    Args:
        design: The InducerDesign to export
        path: Output file path (typically .txt)
    """
    summary = design.get_summary()
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        f"Inducer Design Summary",
        f"=" * 40,
        f"",
        f"Name: {summary['name']}",
        f"Units: {summary['units']}",
        f"",
        f"Main Dimensions:",
        f"  Axial Length (L): {summary['axial_length']:.2f} {summary['units']}",
        f"  Inlet Hub Radius: {summary['inlet_hub_radius']:.2f} {summary['units']}",
        f"  Inlet Tip Radius: {summary['inlet_tip_radius']:.2f} {summary['units']}",
        f"  Outlet Hub Radius: {summary['outlet_hub_radius']:.2f} {summary['units']}",
        f"  Outlet Tip Radius: {summary['outlet_tip_radius']:.2f} {summary['units']}",
        f"",
        f"Computed Properties:",
        f"  Hub Arc Length: {summary['hub_arc_length']:.2f} {summary['units']}",
        f"  Tip Arc Length: {summary['tip_arc_length']:.2f} {summary['units']}",
    ]
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
