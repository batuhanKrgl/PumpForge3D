"""Headless core logic tests (no GUI dependency)."""

from pumpforge3d_core.analysis.velocity_triangle import compute_triangle
from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.io.export import export_json


def test_core_logic_runs_headless(tmp_path):
    """Core modules should run without importing GUI components."""
    design = InducerDesign.create_default(name="Headless Core")
    export_path = tmp_path / "headless_core.json"

    export_json(design, export_path)
    triangle = compute_triangle(beta_deg=30.0, radius=0.04, rpm=3000.0, cm=5.0, alpha1_deg=90.0)

    assert export_path.exists()
    assert triangle.u > 0
