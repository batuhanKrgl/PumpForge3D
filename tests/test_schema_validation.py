"""
Tests for schema validation.
"""

import pytest

from pumpforge3d_core.io.schema import (
    SCHEMA_VERSION, VersionInfo, VersionCompatibility,
    check_version_compatibility, validate_schema
)


class TestVersionInfo:
    """Test VersionInfo parsing."""
    
    def test_parse_valid(self):
        v = VersionInfo.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
    
    def test_parse_zero_version(self):
        v = VersionInfo.parse("0.1.0")
        assert v.major == 0
        assert v.minor == 1
        assert v.patch == 0
    
    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            VersionInfo.parse("invalid")
    
    def test_str(self):
        v = VersionInfo(1, 2, 3)
        assert str(v) == "1.2.3"


class TestVersionCompatibility:
    """Test version compatibility checking."""
    
    def test_same_version_compatible(self):
        compat, msg = check_version_compatibility(SCHEMA_VERSION, SCHEMA_VERSION)
        assert compat == VersionCompatibility.COMPATIBLE
    
    def test_older_minor_compatible(self):
        # File version 0.0.5, current 0.1.0 - older file should work
        compat, _ = check_version_compatibility("0.0.5", "0.1.0")
        assert compat == VersionCompatibility.COMPATIBLE
    
    def test_newer_minor_warns(self):
        # File version 0.2.0, current 0.1.0 - newer file should warn
        compat, _ = check_version_compatibility("0.2.0", "0.1.0")
        assert compat == VersionCompatibility.WARN_NEWER_MINOR
    
    def test_different_major_rejects(self):
        # File version 1.0.0, current 0.1.0 - different major rejected
        compat, _ = check_version_compatibility("1.0.0", "0.1.0")
        assert compat == VersionCompatibility.REJECT_MAJOR
    
    def test_invalid_version_rejects(self):
        compat, _ = check_version_compatibility("invalid", "0.1.0")
        assert compat == VersionCompatibility.REJECT_MAJOR


class TestSchemaValidation:
    """Test schema structure validation."""
    
    def test_valid_minimal(self):
        """Minimal valid schema should pass."""
        data = {
            "schema_version": "0.1.0",
            "app_version": "0.1.0",
            "design": {
                "main_dimensions": {
                    "r_h_in": 20,
                    "r_t_in": 50,
                    "r_h_out": 30,
                    "r_t_out": 45,
                    "L": 80
                },
                "contour": {
                    "hub_curve": {
                        "control_points": [
                            {"z": 0, "r": 20},
                            {"z": 20, "r": 22},
                            {"z": 40, "r": 25},
                            {"z": 60, "r": 28},
                            {"z": 80, "r": 30},
                        ]
                    },
                    "tip_curve": {
                        "control_points": [
                            {"z": 0, "r": 50},
                            {"z": 20, "r": 48},
                            {"z": 40, "r": 47},
                            {"z": 60, "r": 46},
                            {"z": 80, "r": 45},
                        ]
                    },
                    "leading_edge": {"mode": "straight"},
                    "trailing_edge": {"mode": "straight"}
                }
            }
        }
        
        is_valid, errors = validate_schema(data)
        assert is_valid, f"Unexpected errors: {errors}"
    
    def test_missing_schema_version(self):
        """Missing schema_version should fail."""
        data = {
            "app_version": "0.1.0",
            "design": {}
        }
        
        is_valid, errors = validate_schema(data)
        assert not is_valid
        assert any("schema_version" in e for e in errors)
    
    def test_missing_design(self):
        """Missing design should fail."""
        data = {
            "schema_version": "0.1.0",
            "app_version": "0.1.0"
        }
        
        is_valid, errors = validate_schema(data)
        assert not is_valid
        assert any("design" in e for e in errors)
    
    def test_missing_main_dimensions(self):
        """Missing main_dimensions should fail."""
        data = {
            "schema_version": "0.1.0",
            "app_version": "0.1.0",
            "design": {
                "contour": {}
            }
        }
        
        is_valid, errors = validate_schema(data)
        assert not is_valid
        assert any("main_dimensions" in e for e in errors)
    
    def test_wrong_control_point_count(self):
        """Wrong number of control points should fail."""
        data = {
            "schema_version": "0.1.0",
            "app_version": "0.1.0",
            "design": {
                "main_dimensions": {
                    "r_h_in": 20, "r_t_in": 50, "r_h_out": 30, "r_t_out": 45, "L": 80
                },
                "contour": {
                    "hub_curve": {
                        "control_points": [{"z": 0, "r": 20}]  # Only 1 point
                    },
                    "tip_curve": {
                        "control_points": [
                            {"z": 0, "r": 50},
                            {"z": 20, "r": 48},
                            {"z": 40, "r": 47},
                            {"z": 60, "r": 46},
                            {"z": 80, "r": 45},
                        ]
                    }
                }
            }
        }
        
        is_valid, errors = validate_schema(data)
        assert not is_valid
        assert any("5 control points" in e for e in errors)
    
    def test_incompatible_major_version(self):
        """Incompatible major version should fail."""
        data = {
            "schema_version": "99.0.0",  # Far future version
            "app_version": "0.1.0",
            "design": {"main_dimensions": {}, "contour": {}}
        }
        
        is_valid, errors = validate_schema(data)
        assert not is_valid
