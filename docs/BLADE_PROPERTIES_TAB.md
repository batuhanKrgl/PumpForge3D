# Blade Properties Tab - Implementation Documentation

## Overview

The **Blade Properties** tab provides a comprehensive workspace for blade-related parameters and velocity triangle analysis. This implementation is based on CFturbo manual sections 7.3.1.4 (Velocity Triangles) and 7.3.1.4.2.1 (Slip coefficient by Gülich/Wiesner).

## Features

### 1. Blade Thickness Matrix (2×2)
- Compact table for hub/tip × inlet/outlet blade thickness values
- Units: mm
- Fixed column widths to prevent UI stretching
- Located in left panel

### 2. Blade Parameters
- **Blade count (z)**: Integer spinbox, range 1-20
- **Incidence angle (i)**: Float spinbox, range -20° to +20°
- **Slip mode**: ComboBox with three options:
  - **Mock**: Direct slip angle input (default 5°)
  - **Wiesner**: Empirical formula γ = 1 - √(sin β₂B) / z^0.7
  - **Gülich**: Modified formula with correction factors f_i and k_w

### 3. Slip Calculation Display
- Shows calculated slip coefficient (γ)
- Displays slip angle (δ)
- Shows correction factors (f_i, k_w)
- Calculates slipped cu₂ from theoretical cu₂∞
- Collapsible formula section explaining the calculations

### 4. Velocity Triangle Visualizations
- Integrated VelocityTriangleWidget (existing component)
- 2×2 subplot layout: Inlet Hub, Inlet Tip, Outlet Hub, Outlet Tip
- Vector diagrams showing u, c (absolute), w (relative) velocities
- Independent axis limits per subplot

### 5. Triangle Details Panel
- Collapsible tree widget with four groups:
  - Inlet Hub
  - Inlet Tip
  - Outlet Hub
  - Outlet Tip
- Each group shows:
  - Basic velocities: u, cu, cm, c, w
  - Flow angles: α (absolute), β (relative)
  - Blocked values: cm_blocked, β_blocked
  - Blade parameters: β_blade, incidence (inlet), slip (outlet)
  - Slipped values: cu_slipped (outlet)

### 6. Analysis Plots
Four plot types available via dropdown selector:

1. **Beta Distribution (Inlet/Outlet)**
   - Shows β angles along normalized span (0=hub, 1=tip)
   - Separate curves for inlet and outlet

2. **Slip Angle vs Span**
   - Displays slip deviation angle δ along span
   - Useful for understanding radial slip variation

3. **Incidence Angle vs Span**
   - Shows incidence angle i along span
   - Reference line at i=0

4. **Flow vs Blocked vs Blade Beta**
   - Compares three β curves for inlet and outlet:
     - Flow β (thin line)
     - Blocked β (dashed line)
     - Blade β_B (thick line)
   - Helps visualize the relationship between different beta definitions

## Layout

### Three-panel layout with QSplitter:

```
┌─────────────┬───────────────────────────┬─────────────────┐
│             │                           │                 │
│  Left Panel │    Center Panel           │  Right Panel    │
│  (250px)    │    (Flexible)             │  (350px)        │
│             │                           │                 │
│  • Blade    │  Velocity Triangle        │  • Analysis     │
│    Thickness│  Visualizations           │    Plots        │
│             │  (2×2 subplots)           │                 │
│  • Blade    │                           │  • Triangle     │
│    Count    │                           │    Details      │
│    Incidence│                           │    (Collapsible)│
│    Slip Mode│                           │                 │
│             │                           │                 │
│  • Slip     │                           │                 │
│    Results  │                           │                 │
│             │                           │                 │
└─────────────┴───────────────────────────┴─────────────────┘
```

## Theoretical Background

### Slip Coefficient Formulas (CFturbo 7.3.1.4.2.1)

**Basic Definition:**
```
γ = 1 - (cu2∞ - cu2) / u2
```

**Wiesner Formula:**
```
γ = 1 - √(sin β₂B) / z^0.7
```

**Gülich Modification:**
```
γ = f_i * (1 - √(sin β₂B) / z^0.7) * k_w
```

**Correction Factors:**

- **f_i**: Impeller type correction
  - 0.98 for radial impellers
  - max(0.98, 1.02 + 1.2×10⁻³(r_q - 50)) for mixed-flow impellers

- **k_w**: Blockage-related correction (requires inlet/outlet diameters)
  - d_im = √(0.5*(d_shroud² + d_hub²))
  - ε_Lim = exp(-8.16 sin β₂B / z)
  - k_w = 1 if d_im/d_2 ≤ ε_Lim
  - k_w = 1 - (d_im/d_2 - ε_Lim)/(1 - ε_Lim) otherwise

**Slipped Velocity:**
```
cu2 = cu2∞ - (1 - γ) * u2
```

**Average Slip (Hub + Shroud):**
```
γ = 0.5 * (γ_Hub + γ_Shroud)
```

## File Structure

```
pumpforge3d_core/
  analysis/
    blade_properties.py          # Data models and slip calculations
    velocity_triangle.py         # Existing triangle computations (reused)

apps/PumpForge3D/
  tabs/
    blade_properties_tab.py      # Main tab widget

  widgets/
    blade_properties_widgets.py  # Input/display widgets:
                                 # - BladeThicknessMatrixWidget
                                 # - BladeInputsWidget
                                 # - SlipCalculationWidget
                                 # - TriangleDetailsWidget

    blade_analysis_plots.py      # Analysis plot widget
    velocity_triangle_widget.py  # Existing widget (reused)

  main_window.py                 # Modified to add new tab
```

## Key Classes

### Data Models (`pumpforge3d_core/analysis/blade_properties.py`)

- **BladeThicknessMatrix**: 2×2 thickness values
- **BladeProperties**: Complete blade parameter set
- **SlipCalculationResult**: Slip coefficient and derived values
- **Functions**:
  - `calculate_wiesner_slip()`
  - `calculate_gulich_slip()`
  - `calculate_slip()` - dispatcher
  - `calculate_cu_slipped()`
  - `calculate_average_slip()`

### Widgets

- **BladeThicknessMatrixWidget**: 2×2 table with QDoubleSpinBox cells
- **BladeInputsWidget**: Blade count, incidence, slip mode controls
- **SlipCalculationWidget**: Results display with collapsible formula
- **TriangleDetailsWidget**: QTreeWidget with four collapsible groups
- **BladeAnalysisPlotWidget**: Matplotlib canvas with plot selector

### Main Tab (`BladePropertiesTab`)

- Orchestrates all widgets
- Manages signal connections
- Updates all displays when inputs change
- Provides get/set methods for blade properties

## UI/UX Design Principles

### Styling (Catppuccin Dark Theme)
- Background: #1e1e2e (main), #181825 (panels)
- Text: #cdd6f4 (primary), #a6adc8 (secondary)
- Accents: #89b4fa (blue), #f9e2af (yellow), #a6e3a1 (green)
- Borders: #45475a (hover), #313244 (normal)

### Layout Constraints
- **No horizontal stretching** for numeric inputs (fixed widths)
- **Compact tables** with fixed column widths
- **Collapsible sections** to minimize clutter
- **Responsive splitters** for user-adjustable layout
- **Consistent spacing**: 4-6px between elements

### Accessibility
- All inputs have clear labels
- Units displayed (°, mm, m/s)
- Tooltips on complex parameters (future enhancement)
- Color-blind friendly plot colors
- Readable font sizes (10-11px)

## Integration Points

### Signals
- `thicknessChanged` → updates calculations
- `bladeCountChanged` → recalculates slip
- `incidenceChanged` → updates triangle details
- `slipModeChanged` → switches calculation method
- `mockSlipChanged` → updates mock slip value
- `inputsChanged` → propagates triangle widget changes

### Data Flow
```
User Input → BladeInputsWidget
           → Update BladeProperties model
           → Calculate slip (calculate_slip)
           → Update SlipCalculationWidget
           → Update TriangleDetailsWidget
           → Update AnalysisPlots
```

## Future Enhancements

1. **Integration with Beta Distribution Editor**
   - Use existing BetaDistributionEditorWidget
   - Synchronize blade angles with span-wise distribution

2. **Live 3D Blade Visualization**
   - Show blade surfaces in 3D viewer
   - Highlight current span selection

3. **Export Capabilities**
   - Export blade properties to JSON/CSV
   - Generate reports with plots

4. **Advanced Slip Models**
   - Stodola slip factor
   - Busemann slip model
   - Custom empirical correlations

5. **Validation Warnings**
   - Flag unrealistic blade thickness values
   - Warn about high incidence angles
   - Suggest blade count based on specific speed

## Testing

### Manual Test Checklist

- [ ] Tab appears in main window
- [ ] All widgets render correctly
- [ ] Blade thickness inputs update
- [ ] Blade count changes trigger slip recalculation
- [ ] Incidence affects triangle details
- [ ] Slip mode switching works (Mock/Wiesner/Gülich)
- [ ] Mock slip input visible only in Mock mode
- [ ] Formula section toggles open/closed
- [ ] Analysis plots update on input change
- [ ] All four plot types render correctly
- [ ] Triangle details tree is collapsible
- [ ] Splitters resize correctly
- [ ] No UI glitches or excessive whitespace
- [ ] Dark theme consistent throughout

### Unit Test Coverage (Future)

```python
# tests/test_blade_properties.py
def test_wiesner_slip_calculation()
def test_gulich_slip_with_corrections()
def test_slip_mode_switching()
def test_cu_slipped_calculation()
def test_average_slip()

# tests/widgets/test_blade_widgets.py
def test_thickness_matrix_widget()
def test_blade_inputs_widget()
def test_slip_widget_display()
```

## Known Limitations

1. **Placeholder Triangle Data**: Current implementation uses sample data for triangle details. Full integration with actual triangle computations from velocity_triangle_widget requires connecting to its internal state.

2. **Beta Distribution Not Integrated**: The tab currently shows hub/tip only. Integration with BetaDistributionEditorWidget would provide span-wise blade angle distribution.

3. **No Diameter Inputs for k_w**: Full Gülich slip calculation requires inlet/outlet diameters. Currently uses k_w=1.0 as fallback.

4. **No Undo/Redo**: Blade property changes are not yet integrated with the main undo stack.

## References

- CFturbo Manual Section 7.3.1.4: Velocity Triangles
- CFturbo Manual Section 7.3.1.4.2.1: Slip coefficient by Gülich/Wiesner
- Wiesner, F.J.: "A Review of Slip Factors for Centrifugal Impellers"
- Gülich, J.F.: "Centrifugal Pumps", 3rd Edition

## Commit Information

This feature was implemented following CFturbo theory and best practices for turbomachinery design. All formulas and conventions are documented and traceable to the CFturbo manual.
