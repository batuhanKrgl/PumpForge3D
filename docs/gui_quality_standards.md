# PumpForge3D GUI Quality Standards

This document describes the GUI standards enforced across the PySide6/Qt6 application.

## Commit Policy (Excel-like)
- Edits commit on **Enter** or focus-out (`editingFinished`) only.
- **Esc** reverts to the last valid value for widgets that support it.
- No continuous live updates during typing; changes are applied on commit.
- Sliders (if used) throttle preview updates and commit only on `sliderReleased`.

## Accessibility Requirements
- Every interactive widget must have:
  - A visible label (or explicit `setBuddy` when using `QLabel`).
  - `setAccessibleName` and `setAccessibleDescription`.
- Tab/Shift+Tab navigation is verified for the primary input flow.

## Validation UX
- Invalid input never updates state.
- Errors include:
  - Field highlight (`error=true` property for stylesheet).
  - Tooltip with the error reason.
  - Inline message label with an icon (e.g., ⚠).
- Detailed diagnostics are logged to the UI logger.

## Settings Persistence Keys
- `main_window/geometry`
- `main_window/splitter_sizes`
- `main_window/right_splitter_sizes`
- `design_tab/splitter_sizes`
- `blade_properties_tab/splitter_sizes`

## Running Tests
```bash
pytest -q
```
