"""Smoke tests for project IO flows."""

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.io.export import export_json
from pumpforge3d_core.io.import_handler import import_json


def test_project_save_load_smoke(tmp_path):
    """Saving and loading a design should not crash."""
    design = InducerDesign.create_default(name="Smoke Test")
    export_path = tmp_path / "smoke_design.json"

    export_json(design, export_path)
    restored, warnings = import_json(export_path)

    assert restored.name == "Smoke Test"
    assert warnings is not None
