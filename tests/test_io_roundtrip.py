"""
Tests for IO roundtrip (export/import).
"""

import pytest
import json
from pathlib import Path
import tempfile
import os

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.geometry.meridional import MainDimensions
from pumpforge3d_core.io.export import export_json, export_csv_samples
from pumpforge3d_core.io.import_handler import import_json, import_polyline
from pumpforge3d_core.io.schema import SCHEMA_VERSION


class TestExportImportRoundtrip:
    """Test that export/import preserves design data."""
    
    @pytest.fixture
    def design(self):
        """Create a test design with custom values."""
        design = InducerDesign.create_default(name="Test Inducer")
        design.main_dims = MainDimensions(
            r_h_in=25, r_t_in=55, r_h_out=35, r_t_out=50, L=100
        )
        design.contour.update_from_dimensions(design.main_dims)
        return design
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)
    
    def test_json_roundtrip(self, design, temp_dir):
        """Export to JSON and import should preserve design."""
        export_path = temp_dir / "test_design.json"
        
        # Export
        export_json(design, export_path)
        assert export_path.exists()
        
        # Import
        restored, warnings = import_json(export_path)
        
        # Check main dimensions preserved
        assert restored.main_dims.r_h_in == design.main_dims.r_h_in
        assert restored.main_dims.r_t_in == design.main_dims.r_t_in
        assert restored.main_dims.L == design.main_dims.L
        
        # Check name preserved
        assert restored.name == "Test Inducer"
    
    def test_json_contains_required_fields(self, design, temp_dir):
        """Exported JSON should contain all required fields."""
        export_path = temp_dir / "test_design.json"
        export_json(design, export_path)
        
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert "schema_version" in data
        assert "app_version" in data
        assert "design" in data
        assert "sampled_geometry" in data
        
        assert data["schema_version"] == SCHEMA_VERSION
    
    def test_json_control_points_preserved(self, design, temp_dir):
        """Control point positions should be preserved exactly."""
        # Move a control point to a specific position
        design.contour.hub_curve.set_point(2, 55.5, 28.3)
        
        export_path = temp_dir / "test_design.json"
        export_json(design, export_path)
        
        restored, _ = import_json(export_path)
        
        # Check the specific point
        orig_pt = design.contour.hub_curve.control_points[2]
        rest_pt = restored.contour.hub_curve.control_points[2]
        
        assert abs(orig_pt.z - rest_pt.z) < 1e-6
        assert abs(orig_pt.r - rest_pt.r) < 1e-6
    
    def test_csv_export_creates_files(self, design, temp_dir):
        """CSV export should create multiple files."""
        base_path = temp_dir / "test_export"
        export_csv_samples(design, base_path)
        
        expected_files = [
            temp_dir / "test_export_hub.csv",
            temp_dir / "test_export_tip.csv",
            temp_dir / "test_export_leading.csv",
            temp_dir / "test_export_trailing.csv",
        ]
        
        for file_path in expected_files:
            assert file_path.exists(), f"Missing: {file_path}"
    
    def test_csv_content_valid(self, design, temp_dir):
        """CSV content should be valid coordinate data."""
        base_path = temp_dir / "test_export"
        export_csv_samples(design, base_path, n_samples=50)
        
        hub_csv = temp_dir / "test_export_hub.csv"
        
        with open(hub_csv, 'r') as f:
            lines = f.readlines()
        
        # Check header
        assert lines[0].strip() == "z,r"
        
        # Check data rows
        assert len(lines) == 51  # Header + 50 samples
        
        # Check values are numeric
        parts = lines[1].strip().split(',')
        z = float(parts[0])
        r = float(parts[1])
        assert isinstance(z, float)
        assert isinstance(r, float)


class TestImportPolyline:
    """Test polyline import for reference curves."""
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yield Path(tmp)
    
    def test_csv_format(self, temp_dir):
        """Import comma-separated values."""
        file_path = temp_dir / "polyline.csv"
        file_path.write_text("0.0,10.0\n20.0,15.0\n40.0,12.0\n")
        
        points = import_polyline(file_path)
        
        assert len(points) == 3
        assert points[0] == (0.0, 10.0)
        assert points[2] == (40.0, 12.0)
    
    def test_with_header(self, temp_dir):
        """Import should skip header line."""
        file_path = temp_dir / "polyline.csv"
        file_path.write_text("z,r\n0.0,10.0\n20.0,15.0\n")
        
        points = import_polyline(file_path)
        
        assert len(points) == 2
    
    def test_space_separated(self, temp_dir):
        """Import space-separated values."""
        file_path = temp_dir / "polyline.txt"
        file_path.write_text("0.0 10.0\n20.0 15.0\n")
        
        points = import_polyline(file_path)
        
        assert len(points) == 2
    
    def test_skip_comments(self, temp_dir):
        """Import should skip comment lines."""
        file_path = temp_dir / "polyline.txt"
        file_path.write_text("# Header comment\n0.0,10.0\n# Another comment\n20.0,15.0\n")
        
        points = import_polyline(file_path)
        
        assert len(points) == 2
