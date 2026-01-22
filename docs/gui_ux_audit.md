# PumpForge3D GUI/UX Audit & Refactor Plan

## Executive summary (top 5 critical UX issues)
1. **No persistent UI state (window geometry, splitter ratios, last project)** — users lose their layout and session context every launch, making iterative design work less efficient.
2. **High-frequency redraws on value changes and hover events** — diagram and analysis plots update on every spinbox tick/mouse move, risking UI sluggishness during parameter tuning.
3. **Inconsistent layout resilience in splitters** — multiple splitters can collapse to zero or behave unpredictably during resizing, causing “lost” panels.
4. **UI thread coupling for heavy computations** — geometry updates, Matplotlib redraws, and 3D updates occur synchronously on the main thread, leading to stutters under heavy edits.
5. **Project I/O UX gaps** — no recent projects list, missing-file recovery, or persistent last-opened path makes re-opening designs cumbersome.

## GUI structure map (current)
- **Entrypoint / app shell**: `apps/PumpForge3D/__main__.py` → `MainWindow` (`apps/PumpForge3D/main_window.py`).
- **Main window layout**: horizontal splitter with **Tab widget** on the left and **3D viewer + object list** on the right.
- **Tabs / pages**:
  - **Design**: `apps/PumpForge3D/tabs/design_tab.py` (diagram editor + controls + analysis plots).
  - **Blade properties**: `apps/PumpForge3D/tabs/blade_properties_tab.py` (velocity triangles + analysis panels + inputs).
  - **Export**: `apps/PumpForge3D/tabs/export_tab.py` wrapping `apps/PumpForge3D/steps/step_e_export.py`.
- **Shared UI infrastructure**:
  - **Meridional diagram**: `apps/PumpForge3D/widgets/diagram_widget.py` (Matplotlib embedded via QtAgg).
  - **3D viewer**: `apps/PumpForge3D/widgets/viewer_3d.py` (PyVistaQt; fallback placeholder).
  - **Analysis plots**: `apps/PumpForge3D/widgets/analysis_plot.py`, `apps/PumpForge3D/widgets/blade_analysis_plots.py`.
  - **Undo/redo**: `apps/PumpForge3D/undo_commands.py` and QUndoStack in main window.

## Assumptions & audit notes
- The audit is based on static code review (no live GUI run).
- Performance issues are inferred from update frequency and UI thread usage.
- Line ranges below are approximate and should be verified after changes.

## Findings table
| ID | Symptom (user-facing) | Root cause (technical) | Where (file + class/function; lines) | Severity | Fix proposal | Verification steps |
|---|---|---|---|---|---|---|
| F-01 | Layout resets each launch; users lose panel sizes | No persistence for window geometry/splitter sizes; no QSettings usage | `MainWindow.__init__` and `_setup_ui` in `apps/PumpForge3D/main_window.py` (lines 244–341) | P1 | Add QSettings to save/restore geometry, splitter sizes, and last-opened project | Relaunch app; verify window and splitters restore previous sizes |
| F-02 | UI becomes sluggish when editing dimensions | `valueChanged` triggers full geometry + plot refresh every tick | `DesignTab._connect_signals` & `_apply_dimensions` in `apps/PumpForge3D/tabs/design_tab.py` (lines 425–526) | P1 | Debounce edits, use `editingFinished` and/or QTimer throttle before redraw | Drag a spinbox rapidly; ensure plot updates only after pause |
| F-03 | Panels can collapse or resize unpredictably | Splitters allow collapsing to size 0; inconsistent min sizes | Splitters in `MainWindow._setup_ui` (lines 277–334), `DesignTab._setup_ui` (lines 175–223), `BladePropertiesTab._create_right_panel` (lines 331–362) | P1 | Set `setChildrenCollapsible(False)`; apply minimum sizes and consistent stretch factors | Resize window; ensure panels remain visible and proportions stable |
| F-04 | 3D view refreshes even when hidden | 3D update called on every geometry change regardless of visibility | `MainWindow._on_geometry_changed` / `_on_dimensions_changed` (lines 449–467) | P2 | Skip updates when 3D pane hidden; refresh on re-show | Switch to blade properties; change values; return and see updated 3D |
| F-05 | Diagram hover and drag can stutter | `update_plot()` called on every mouse move for hover + drag | `DiagramWidget._on_mouse_move` + `update_plot` in `apps/PumpForge3D/widgets/diagram_widget.py` (lines 206–279, 439–519) | P1 | Throttle hover updates (e.g., 30–60ms) and avoid full redraw when only coords change | Move mouse quickly; CPU remains stable and hover still responsive |
| F-06 | No recent projects or recoverability | File menu lacks recent list; import flow has no recovery guidance | `MainWindow._setup_menu` (lines 376–405) and `StepEExport._import_design` (lines 177–205) | P1 | Add recent files list + missing-file recovery dialog; store last dir in settings | Open recent project; missing file shows recovery prompt |
| F-07 | Styling inconsistencies across tabs | Dual stylesheets (global in `__main__` and per window in `main_window`) conflict | `apps/PumpForge3D/__main__.py` `get_stylesheet` (lines 50–200) and `apps/PumpForge3D/main_window.py` `STYLE_SHEET` (lines 28–226) | P2 | Consolidate stylesheet in one place; avoid duplicate selectors | Compare tab styles for consistency across pages |
| F-08 | Heavy updates occur on UI thread | Geometry + plot + 3D updates all in main thread | `DesignTab._on_dimensions_applied` (lines 518–526) and `Viewer3DWidget.update_geometry` in `apps/PumpForge3D/widgets/viewer_3d.py` (lines 150–259) | P1 | Move heavy computations to worker threads and update UI on completion | Apply large edits; UI remains responsive |
| F-09 | Validation feedback is easy to miss | Validation output is static text with no inline field hints | `DesignTab._update_validation` (lines 660–672), `StepEExport._run_validation` (lines 207–226) | P2 | Add inline indicators near fields + a unified validation panel | Trigger validation; see inline highlights |
| F-10 | Dialog flow is inconsistent | Non-modal parameter window lacks state persistence; no standard OK/Cancel patterns | `BladePropertiesTab._toggle_params_window` (lines 415–420) | P2 | Use a standard dialog with persistent settings and explicit apply/reset | Open/close params; settings persist across sessions |

## Recommendations aligned with CFturbo-inspired principles
- **Step-based workflow clarity**: consider a top-level “workflow status” panel showing current step, next action, and warnings.
- **Consistent dialog controls**: adopt OK/Cancel/Apply behavior across parameter windows and validation tools.
- **Commit on Enter/focus-out**: for numeric fields, use `editingFinished` to commit changes to align with industrial CAD/CFD tools.
- **Persistent window state**: store splitter ratios, last project, and last export path in settings.
- **Meridional focus**: ensure the diagram is always visible during meridional edits and that side panels don’t collapse on resize.

## Refactor / Fix plan (PR-sized chunks)
### PR-1: Layout stabilization
- **Files**: `main_window.py`, `design_tab.py`, `blade_properties_tab.py`, `diagram_widget.py`
- **Steps**:
  1. Make splitters non-collapsible; set consistent handle widths and minimum sizes.
  2. Remove stray Matplotlib imports to avoid implicit figure creation.
  3. Avoid 3D updates when hidden; refresh on re-show.
- **Risks/edge cases**: Hard minimum sizes could reduce flexibility on small screens.
- **Minimal test plan**: `pytest -k "project_save_load_smoke or core_logic_runs_headless"`.

#### PR-1 applied status (current branch)
- Splitters made non-collapsible; minimum sizes added for the right panel and 3D list; handle widths unified.
- 3D refresh now deferred while hidden and re-applied on re-show.
- Diagram widget Matplotlib import simplified to avoid unused pyplot usage.

### PR-2: Interaction consistency
- **Files**: `design_tab.py`, `diagram_widget.py`, `step_e_export.py`
- **Steps**:
  1. Debounce spinbox updates and hover redraws.
  2. Standardize dialog patterns (OK/Cancel/Apply).
  3. Add tooltips/status hints in key widgets.
- **Risks/edge cases**: Potential loss of “live” feedback; ensure a manual refresh still exists.
- **Minimal test plan**: manual UI smoke test; ensure no regressions in existing pytest suite.

### PR-3: Performance
- **Files**: `viewer_3d.py`, `analysis_plot.py`, `blade_analysis_plots.py`
- **Steps**:
  1. Move heavy plot computations to worker threads.
  2. Add throttling for frequent plot redraws.
  3. Cache rendered data where feasible.
- **Risks/edge cases**: Thread safety with Qt; ensure UI updates happen on main thread.
- **Minimal test plan**: manual performance pass + `pytest`.

### PR-4: UX workflow foundations
- **Files**: `main_window.py`, new `workflow_state.py`, `undo_commands.py`
- **Steps**:
  1. Add wizard-like progression state + completion gating.
  2. Introduce undo/redo for key interactions beyond dimensions.
  3. Add recent projects list + recovery dialog.
- **Risks/edge cases**: Requires careful coordination with core design logic.
- **Minimal test plan**: unit tests for workflow state + manual UI verification.

## Visual verification checklist
- App launches without layout glitches.
- No floating/undocked Matplotlib windows.
- Main window resizing keeps diagram and plots visible.
- Heavy operations do not freeze the UI or clearly indicate progress.
- Export/import flows present clear error messages and persist last-used paths.
