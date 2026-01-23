"""Analysis module for PumpForge3D."""

from .conformal_mapping import (
    solve_theta3_array,
    generate_meridional_grid,
    generate_mock_phi_grid,
    generate_phi_grid_from_beta,
    compute_conformal_mapping,
    compute_conformal_mapping_with_state,
    CoupledAngleState,
    ConformalMappingResult,
    normalize_angle_deg,
)

__all__ = [
    "solve_theta3_array",
    "generate_meridional_grid",
    "generate_mock_phi_grid",
    "generate_phi_grid_from_beta",
    "compute_conformal_mapping",
    "compute_conformal_mapping_with_state",
    "CoupledAngleState",
    "ConformalMappingResult",
    "normalize_angle_deg",
]
