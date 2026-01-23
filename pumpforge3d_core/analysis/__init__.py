"""Analysis module for PumpForge3D."""

from .velocity_triangle import (
    TriangleData,
    InletTriangleResult,
    OutletTriangleResult,
    compute_triangle,
    compute_inlet_triangle,
    compute_outlet_triangle,
    calculate_euler_head,
    calculate_flow_area,
)
from .turbomachinery_calc import (
    TurbomachineryCalculator,
    OperatingConditions,
    InfoTableData,
    PerformanceResult,
)

__all__ = [
    "TriangleData",
    "InletTriangleResult",
    "OutletTriangleResult",
    "compute_triangle",
    "compute_inlet_triangle",
    "compute_outlet_triangle",
    "calculate_euler_head",
    "calculate_flow_area",
    "TurbomachineryCalculator",
    "OperatingConditions",
    "InfoTableData",
    "PerformanceResult",
]
