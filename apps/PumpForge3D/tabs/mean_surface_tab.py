"""
Mean Surface Tab for conformal mapping visualization.

Implements the "t,m Conformal mapping" workflow (CFturbo manual §7.3.2.1.1):
- Converts 2D meridional geometry + beta angle field into 3D mean-line curves
- No Apply button: auto-recomputes on editingFinished and upstream data changes
- Coupled theta0/wrap-angle fields with dependent edit behavior

Layout:
- LEFT: Input panel (scrollable) with status, coupling table
- RIGHT: Visualization area with beta plot (top) and 3D viewer (bottom)
"""

from typing import Optional, Callable
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QScrollArea,
    QGroupBox, QFormLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer

from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.geometry.beta_distribution import BetaDistributionModel
from pumpforge3d_core.analysis.conformal_mapping import (
    generate_meridional_grid,
    generate_mock_phi_grid,
    generate_phi_grid_from_beta,
    compute_conformal_mapping_with_state,
    CoupledAngleState,
    ConformalMappingResult,
)


class MeanSurfaceTab(QWidget):
    """
    Tab for conformal mapping and mean-line generation.

    Features:
    - Generates r_grid/z_grid by sampling hub/tip Bezier curves
    - Uses beta distribution (from Tab-2) or mock angles if unavailable
    - Computes 3D mean-line curves via conformal mapping
    - Coupled theta0/wrap editing with auto-recompute

    Signals:
        mean_lines_changed: Emitted when 3D mean lines are recomputed
    """

    mean_lines_changed = Signal(object)  # Emits ConformalMappingResult

    DEBOUNCE_MS = 200  # Debounce interval for recompute

    def __init__(
        self,
        design: InducerDesign,
        beta_model: Optional[BetaDistributionModel] = None,
        parent=None,
    ):
        super().__init__(parent)

        self._design = design
        self._beta_model = beta_model
        self._updating = False

        # Grid sampling parameters
        self._n_meridional = 50  # Points along meridional direction
        self._n_spans = 6  # Number of span stations (default matches beta model)

        # Grids (computed from design)
        self._r_grid: Optional[np.ndarray] = None
        self._z_grid: Optional[np.ndarray] = None
        self._phi_grid: Optional[np.ndarray] = None
        self._using_mock_angles = True

        # Coupled angle state
        self._angle_state: Optional[CoupledAngleState] = None

        # Latest result
        self._result: Optional[ConformalMappingResult] = None

        # Debounce timer
        self._recompute_timer = QTimer()
        self._recompute_timer.setSingleShot(True)
        self._recompute_timer.timeout.connect(self._do_recompute)

        self._setup_ui()
        self._connect_signals()

        # Initial computation
        QTimer.singleShot(100, self._initialize_data)

    def _setup_ui(self):
        """Create the main UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Main horizontal splitter: [Input Panel] | [Visualization]
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)

        # LEFT: Input panel (scrollable)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumWidth(280)
        scroll_area.setMaximumWidth(400)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        input_panel = QWidget()
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(4, 4, 4, 4)
        input_layout.setSpacing(8)

        # Status group
        status_group = QGroupBox("Data Status")
        status_layout = QFormLayout(status_group)
        status_layout.setSpacing(4)

        self.meridional_status = QLabel("OK")
        self.meridional_status.setStyleSheet("color: #a6e3a1;")
        status_layout.addRow("Meridional grid:", self.meridional_status)

        self.angle_status = QLabel("Mock active")
        self.angle_status.setStyleSheet("color: #f9e2af;")
        status_layout.addRow("Angle grid:", self.angle_status)

        self.shape_label = QLabel("--")
        status_layout.addRow("Grid shape:", self.shape_label)

        input_layout.addWidget(status_group)

        # Grid parameters
        params_group = QGroupBox("Grid Parameters")
        params_layout = QFormLayout(params_group)
        params_layout.setSpacing(4)

        self.n_meridional_spin = QSpinBox()
        self.n_meridional_spin.setRange(10, 200)
        self.n_meridional_spin.setValue(self._n_meridional)
        self.n_meridional_spin.setToolTip("Number of points along meridional direction")
        params_layout.addRow("Meridional points:", self.n_meridional_spin)

        self.n_spans_spin = QSpinBox()
        self.n_spans_spin.setRange(2, 20)
        self.n_spans_spin.setValue(self._n_spans)
        self.n_spans_spin.setToolTip("Number of span stations (hub to tip)")
        params_layout.addRow("Span count:", self.n_spans_spin)

        input_layout.addWidget(params_group)

        # Span Angle Coupling table
        coupling_group = QGroupBox("Span Angle Coupling")
        coupling_layout = QVBoxLayout(coupling_group)
        coupling_layout.setSpacing(4)

        self.coupling_table = QTableWidget()
        self.coupling_table.setColumnCount(4)
        self.coupling_table.setHorizontalHeaderLabels([
            "j", "theta0 (°)", "wrap (°)", "theta_end (°)"
        ])
        self.coupling_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.coupling_table.setMinimumHeight(180)
        self.coupling_table.setToolTip(
            "Edit theta0 or wrap angle per span.\n"
            "theta0: Initial angle (LE position)\n"
            "wrap: Total angular wrap (derived, but editable)\n"
            "theta_end: Final angle (TE position, read-only)"
        )
        coupling_layout.addWidget(self.coupling_table)

        input_layout.addWidget(coupling_group)

        # Stretch to push everything up
        input_layout.addStretch()

        scroll_area.setWidget(input_panel)
        self.main_splitter.addWidget(scroll_area)

        # RIGHT: Visualization area (vertical splitter)
        self.viz_splitter = QSplitter(Qt.Orientation.Vertical)
        self.viz_splitter.setChildrenCollapsible(False)

        # Top: Beta plot placeholder (will be replaced when integrated)
        self.beta_plot_placeholder = QLabel(
            "Beta Distribution Preview\n(Connect to beta editor)"
        )
        self.beta_plot_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beta_plot_placeholder.setMinimumHeight(150)
        self.beta_plot_placeholder.setStyleSheet(
            "background: #181825; color: #6c7086; "
            "border: 1px dashed #45475a; border-radius: 4px;"
        )
        self.viz_splitter.addWidget(self.beta_plot_placeholder)

        # Bottom: 3D viewer placeholder (will be replaced when integrated)
        self.viewer_placeholder = QLabel(
            "3D Mean Lines Preview\n(3D viewer will be embedded here)"
        )
        self.viewer_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.viewer_placeholder.setMinimumHeight(200)
        self.viewer_placeholder.setStyleSheet(
            "background: #181825; color: #6c7086; "
            "border: 1px dashed #45475a; border-radius: 4px;"
        )
        self.viz_splitter.addWidget(self.viewer_placeholder)

        # Set splitter proportions (40% plot, 60% 3D viewer)
        self.viz_splitter.setSizes([200, 300])

        self.main_splitter.addWidget(self.viz_splitter)

        # Set main splitter proportions (30% input, 70% viz)
        self.main_splitter.setSizes([300, 700])

        main_layout.addWidget(self.main_splitter)

    def _connect_signals(self):
        """Connect UI signals."""
        self.n_meridional_spin.editingFinished.connect(self._on_grid_params_changed)
        self.n_spans_spin.editingFinished.connect(self._on_grid_params_changed)
        self.coupling_table.cellChanged.connect(self._on_coupling_cell_changed)

    def _initialize_data(self):
        """Initialize grids and compute initial result."""
        self._generate_grids()
        self._update_status_display()
        self._schedule_recompute()

    def _generate_grids(self):
        """Generate meridional grids from design contour."""
        if self._design is None:
            self._r_grid = None
            self._z_grid = None
            return

        contour = self._design.contour

        # Sample hub and tip curves
        hub_points = contour.hub_curve.evaluate_many(self._n_meridional)
        tip_points = contour.tip_curve.evaluate_many(self._n_meridional)

        # Update span count from beta model if available
        if self._beta_model is not None:
            self._n_spans = self._beta_model.span_count
            self._updating = True
            self.n_spans_spin.setValue(self._n_spans)
            self._updating = False

        # Generate grid by interpolating between hub and tip
        self._r_grid, self._z_grid = generate_meridional_grid(
            hub_points, tip_points, self._n_spans
        )

        # Generate phi grid
        self._generate_phi_grid()

        # Initialize angle state if needed
        if self._angle_state is None or self._angle_state.n_j != self._n_spans:
            self._angle_state = CoupledAngleState(n_j=self._n_spans)

    def _generate_phi_grid(self):
        """Generate phi grid from beta model or mock data."""
        n_i = self._n_meridional
        n_j = self._n_spans

        if self._beta_model is not None:
            # Sample beta curves to get angles at each meridional station
            phi_grid = np.zeros((n_i - 1, n_j), dtype=np.float64)

            for j in range(n_j):
                # Sample the beta curve for this span
                theta_star, beta = self._beta_model.sample_span_curve(j, n_i)

                # Compute beta at segment midpoints
                beta_mid = 0.5 * (beta[:-1] + beta[1:])

                # Convert beta (degrees) to phi (radians)
                phi_grid[:, j] = np.radians(beta_mid)

            self._phi_grid = phi_grid
            self._using_mock_angles = False
        else:
            # Use mock phi grid
            self._phi_grid = generate_mock_phi_grid(n_i, n_j)
            self._using_mock_angles = True

    def _update_status_display(self):
        """Update status labels."""
        if self._r_grid is not None and self._z_grid is not None:
            n_i, n_j = self._r_grid.shape
            self.meridional_status.setText("OK")
            self.meridional_status.setStyleSheet("color: #a6e3a1;")
            self.shape_label.setText(f"n_i={n_i}, n_j={n_j}")
        else:
            self.meridional_status.setText("Missing")
            self.meridional_status.setStyleSheet("color: #f38ba8;")
            self.shape_label.setText("--")

        if self._using_mock_angles:
            self.angle_status.setText("Mock active")
            self.angle_status.setStyleSheet("color: #f9e2af;")
        else:
            self.angle_status.setText("OK")
            self.angle_status.setStyleSheet("color: #a6e3a1;")

    def _update_coupling_table(self):
        """Update the coupling table from current state."""
        if self._angle_state is None or self._result is None:
            return

        self._updating = True

        n_j = self._angle_state.n_j
        self.coupling_table.setRowCount(n_j)

        for j in range(n_j):
            # j column (read-only)
            j_item = QTableWidgetItem(str(j))
            j_item.setFlags(j_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            j_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if j == 0:
                j_item.setToolTip("Hub")
            elif j == n_j - 1:
                j_item.setToolTip("Tip")
            self.coupling_table.setItem(j, 0, j_item)

            # theta0 column (editable)
            theta0_deg = self._angle_state.theta0_deg[j]
            theta0_item = QTableWidgetItem(f"{theta0_deg:.1f}")
            theta0_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.coupling_table.setItem(j, 1, theta0_item)

            # wrap column (editable, dependent)
            wrap_deg = self._angle_state.wrap_current_deg[j]
            wrap_item = QTableWidgetItem(f"{wrap_deg:.1f}")
            wrap_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.coupling_table.setItem(j, 2, wrap_item)

            # theta_end column (read-only)
            theta_end_deg = np.degrees(self._angle_state.theta_end[j])
            theta_end_item = QTableWidgetItem(f"{theta_end_deg:.1f}")
            theta_end_item.setFlags(theta_end_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            theta_end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            theta_end_item.setBackground(Qt.GlobalColor.darkGray)
            self.coupling_table.setItem(j, 3, theta_end_item)

        self._updating = False

    def _on_grid_params_changed(self):
        """Handle grid parameter changes."""
        if self._updating:
            return

        new_n_meridional = self.n_meridional_spin.value()
        new_n_spans = self.n_spans_spin.value()

        if new_n_meridional != self._n_meridional or new_n_spans != self._n_spans:
            self._n_meridional = new_n_meridional
            self._n_spans = new_n_spans
            self._generate_grids()
            self._update_status_display()
            self._schedule_recompute()

    def _on_coupling_cell_changed(self, row: int, col: int):
        """Handle coupling table cell edit."""
        if self._updating or self._angle_state is None:
            return

        item = self.coupling_table.item(row, col)
        if item is None:
            return

        try:
            value = float(item.text())
        except ValueError:
            # Revert to current value
            self._update_coupling_table()
            return

        if col == 1:  # theta0 edit
            self._angle_state.edit_theta0(row, np.radians(value))
        elif col == 2:  # wrap edit
            self._angle_state.edit_wrap(row, np.radians(value))
        else:
            return  # Other columns are read-only

        self._schedule_recompute()

    def _schedule_recompute(self):
        """Schedule a debounced recompute."""
        self._recompute_timer.start(self.DEBOUNCE_MS)

    def _do_recompute(self):
        """Perform the actual recomputation."""
        if self._r_grid is None or self._z_grid is None or self._phi_grid is None:
            return

        if self._angle_state is None:
            self._angle_state = CoupledAngleState(n_j=self._n_spans)

        # Compute with current state
        self._result = compute_conformal_mapping_with_state(
            self._r_grid,
            self._z_grid,
            self._phi_grid,
            self._angle_state,
        )

        # Update state from result (preserves scaling if not reset)
        self._angle_state.update_from_result(self._result, reset_scaling=False)

        # Update UI
        self._update_coupling_table()

        # Emit signal for 3D viewer update
        self.mean_lines_changed.emit(self._result)

    # Public API

    def set_design(self, design: InducerDesign):
        """Set a new design and regenerate grids."""
        self._design = design
        self._generate_grids()
        self._update_status_display()

        # Reset angle state (upstream change)
        self._angle_state = CoupledAngleState(n_j=self._n_spans)
        self._schedule_recompute()

    def set_beta_model(self, model: BetaDistributionModel):
        """Set the beta distribution model and regenerate phi grid."""
        self._beta_model = model

        # Update span count
        if model.span_count != self._n_spans:
            self._n_spans = model.span_count
            self._updating = True
            self.n_spans_spin.setValue(self._n_spans)
            self._updating = False
            self._generate_grids()
        else:
            self._generate_phi_grid()

        self._update_status_display()

        # Reset angle state (upstream change)
        self._angle_state = CoupledAngleState(n_j=self._n_spans)
        self._schedule_recompute()

    def get_result(self) -> Optional[ConformalMappingResult]:
        """Get the latest computation result."""
        return self._result

    def get_mean_lines(self) -> Optional[np.ndarray]:
        """Get the 3D mean-line coordinates, shape (n_j, n_i, 3)."""
        if self._result is not None:
            return self._result.xyz_lines
        return None

    def embed_beta_widget(self, widget: QWidget):
        """Embed a beta editor widget in the visualization area."""
        # Replace placeholder with actual widget
        old_widget = self.viz_splitter.widget(0)
        if old_widget is not None:
            old_widget.setParent(None)

        self.viz_splitter.insertWidget(0, widget)
        self.beta_plot_placeholder = widget

    def embed_viewer_widget(self, widget: QWidget):
        """Embed a 3D viewer widget in the visualization area."""
        # Replace placeholder with actual widget
        old_widget = self.viz_splitter.widget(1)
        if old_widget is not None:
            old_widget.setParent(None)

        self.viz_splitter.insertWidget(1, widget)
        self.viewer_placeholder = widget
