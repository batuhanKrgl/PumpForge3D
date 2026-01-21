"""
Blade Properties Tab - Purpose-focused workspace for blade parameters and velocity triangles.

Reorganized layout (UI/UX fix):
- 3D viewer hidden when this tab is active (managed by main window)
- 3-column layout: [Inputs] | [Velocity Triangles] | [Analysis & Details]
- Collapsible input groups for space efficiency
- No horizontal stretching on numeric inputs
- Compact, readable, goal-oriented workspace

Based on CFturbo manual section 7.3.1.4 (Velocity Triangles) and 7.3.1.4.2.1 (Slip by Gülich/Wiesner).
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QGroupBox,
    QFormLayout, QScrollArea, QFrame, QLabel, QToolBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from ..widgets.velocity_triangle_widget import VelocityTriangleWidget
from ..widgets.blade_properties_widgets import (
    BladeThicknessMatrixWidget, BladeInputsWidget,
    TriangleDetailsWidget
)
from ..widgets.blade_analysis_plots import BladeAnalysisPlotWidget
from ..widgets.velocity_triangle_params_window import VelocityTriangleParamsWindow

from pumpforge3d_core.analysis.blade_properties import (
    BladeProperties, calculate_slip, calculate_cu_slipped
)
from pumpforge3d_core.analysis.velocity_triangle import (
    compute_triangle, compute_derived_triangle
)


class CollapsibleSection(QWidget):
    """A collapsible section with header and content."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._is_collapsed = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        # Header button
        self.header = QPushButton(f"▼ {self.title}")
        self.header.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                background: #313244;
                border: none;
                border-radius: 4px;
                color: #cdd6f4;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #45475a;
            }
        """)
        self.header.clicked.connect(self._toggle)
        layout.addWidget(self.header)

        # Content widget
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.content)

    def _toggle(self):
        self._is_collapsed = not self._is_collapsed
        self.content.setVisible(not self._is_collapsed)
        arrow = "▶" if self._is_collapsed else "▼"
        self.header.setText(f"{arrow} {self.title}")

    def addWidget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class BladePropertiesTab(QWidget):
    """
    Blade Properties Tab - reorganized for optimal UX.

    Layout: 3 columns
    - Left (23%): Inputs (collapsible groups, compact controls)
    - Center (52%): Velocity triangles (2×2 main visual)
    - Right (25%): Analysis & Details (plots + numeric data)
    """

    # Signals
    propertiesChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize blade properties
        self._blade_properties = BladeProperties(
            thickness=BladeThicknessMatrixWidget().get_thickness(),
            blade_count=3,
            incidence_deg=0.0,
            slip_mode="Mock",
            mock_slip_deg=5.0
        )

        # Create parameter window (non-modal, hidden by default)
        self.params_window = VelocityTriangleParamsWindow()
        self.params_window.hide()

        self._setup_ui()
        self._connect_signals()
        self._update_all()

    def _setup_ui(self):
        """Setup the 3-column tab layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Create main horizontal splitter with 3 panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(3)
        self.main_splitter.setChildrenCollapsible(False)  # Prevent collapsing to 0

        # === LEFT PANEL: Inputs (compact, collapsible) ===
        left_panel = self._create_left_panel()
        self.main_splitter.addWidget(left_panel)

        # === CENTER PANEL: Velocity Triangles (main visual area) ===
        center_panel = self._create_center_panel()
        self.main_splitter.addWidget(center_panel)

        # === RIGHT PANEL: Analysis & Details ===
        right_panel = self._create_right_panel()
        self.main_splitter.addWidget(right_panel)

        # Set initial proportions: 23% | 52% | 25% (for 1400px total = ~320 | 728 | 350)
        total_hint = 1400
        self.main_splitter.setSizes([int(total_hint * 0.23), int(total_hint * 0.52), int(total_hint * 0.25)])
        self.main_splitter.setStretchFactor(0, 23)  # Inputs: less stretch
        self.main_splitter.setStretchFactor(1, 52)  # Triangles: most stretch
        self.main_splitter.setStretchFactor(2, 25)  # Analysis: moderate stretch

        main_layout.addWidget(self.main_splitter)

    def _create_left_panel(self) -> QWidget:
        """Create left input panel with collapsible groups."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMinimumWidth(280)
        panel.setMaximumWidth(380)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #45475a;
            }
        """)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(4, 4, 4, 4)
        panel_layout.setSpacing(4)

        # Panel title
        title = QLabel("⚙ Blade Inputs")
        title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 4px;
                background-color: #1e1e2e;
                border-radius: 3px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        panel_layout.addWidget(title)

        # Scroll area for collapsible groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(6, 6, 6, 6)
        scroll_layout.setSpacing(8)

        # === 1. Blade Thickness Group (collapsible) ===
        thickness_group = CollapsibleSection("Blade Thickness")

        self.thickness_widget = BladeThicknessMatrixWidget()
        thickness_group.addWidget(self.thickness_widget)

        scroll_layout.addWidget(thickness_group)

        # === 2. Blade Parameters Group (collapsible) ===
        params_group = CollapsibleSection("Blade Parameters")

        self.blade_inputs_widget = BladeInputsWidget()
        params_group.addWidget(self.blade_inputs_widget)

        scroll_layout.addWidget(params_group)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        panel_layout.addWidget(scroll)

        return panel

    def _create_center_panel(self) -> QWidget:
        """Create center panel with velocity triangles (main visual area)."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #45475a;
            }
        """)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(4, 4, 4, 4)
        panel_layout.setSpacing(4)

        # Panel title with minimal toolbar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        title = QLabel("◈ Velocity Triangles")
        title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 4px;
            }
        """)
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Parameter window button
        from PySide6.QtWidgets import QPushButton
        params_btn = QPushButton("⚙ Parameters")
        params_btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #89b4fa;
                border: 1px solid #45475a;
                padding: 4px 8px;
                border-radius: 3px;
                font-size: 9px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            QPushButton:pressed {
                background-color: #89b4fa;
                color: #1e1e2e;
            }
        """)
        params_btn.clicked.connect(self._toggle_params_window)
        header_layout.addWidget(params_btn)

        # Mini info label (optional, shows current settings)
        self.triangle_info_label = QLabel("2×2 Subplots | Hub & Tip")
        self.triangle_info_label.setStyleSheet("""
            QLabel {
                color: #a6adc8;
                font-size: 9px;
                padding: 4px;
            }
        """)
        header_layout.addWidget(self.triangle_info_label)

        panel_layout.addLayout(header_layout)

        # Velocity triangle widget (existing, with built-in controls)
        self.triangle_widget = VelocityTriangleWidget()
        self.triangle_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel_layout.addWidget(self.triangle_widget)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create right panel with analysis plots and triangle details."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMinimumWidth(320)
        panel.setMaximumWidth(500)
        panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #45475a;
            }
        """)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(4, 4, 4, 4)
        panel_layout.setSpacing(4)

        # Panel title
        title = QLabel("📊 Analysis & Details")
        title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 12px;
                font-weight: bold;
                padding: 6px 4px;
                background-color: #1e1e2e;
                border-radius: 3px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        panel_layout.addWidget(title)

        # Vertical splitter for plots (top) and details (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(3)

        # === Analysis Plots (top) ===
        plots_widget = QWidget()
        plots_layout = QVBoxLayout(plots_widget)
        plots_layout.setContentsMargins(4, 4, 4, 4)
        plots_layout.setSpacing(4)

        plots_label = QLabel("Analysis Plots")
        plots_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 10px; padding: 4px;")
        plots_layout.addWidget(plots_label)

        self.analysis_plots = BladeAnalysisPlotWidget()
        plots_layout.addWidget(self.analysis_plots)

        splitter.addWidget(plots_widget)

        # === Triangle Details (bottom) ===
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(4, 4, 4, 4)
        details_layout.setSpacing(4)

        details_label = QLabel("Triangle Details")
        details_label.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 10px; padding: 4px;")
        details_layout.addWidget(details_label)

        self.triangle_details = TriangleDetailsWidget()
        details_layout.addWidget(self.triangle_details)

        splitter.addWidget(details_widget)

        # Set splitter proportions: 60% plots, 40% details
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)

        panel_layout.addWidget(splitter)

        return panel

    def _connect_signals(self):
        """Connect widget signals to update handlers."""
        self.thickness_widget.thicknessChanged.connect(self._on_thickness_changed)
        self.blade_inputs_widget.bladeCountChanged.connect(self._on_blade_count_changed)
        self.blade_inputs_widget.incidenceChanged.connect(self._on_incidence_changed)
        self.blade_inputs_widget.slipModeChanged.connect(self._on_slip_mode_changed)
        self.blade_inputs_widget.mockSlipChanged.connect(self._on_mock_slip_changed)
        self.triangle_widget.inputsChanged.connect(self._on_triangle_inputs_changed)
        self.params_window.parametersChanged.connect(self._on_params_changed)

    def _on_thickness_changed(self, thickness):
        """Handle thickness matrix change."""
        self._blade_properties.thickness = thickness
        self._update_all()

    def _on_blade_count_changed(self, count):
        """Handle blade count change."""
        self._blade_properties.blade_count = count
        self._update_slip_calculation()
        self._update_analysis_plots()

    def _on_incidence_changed(self, incidence):
        """Handle incidence change."""
        self._blade_properties.incidence_deg = incidence
        self._update_triangle_details()
        self._update_analysis_plots()

    def _on_slip_mode_changed(self, mode):
        """Handle slip mode change."""
        self._blade_properties.slip_mode = mode
        self._update_slip_calculation()

    def _on_mock_slip_changed(self, slip):
        """Handle mock slip value change."""
        self._blade_properties.mock_slip_deg = slip
        self._update_slip_calculation()

    def _on_triangle_inputs_changed(self):
        """Handle velocity triangle input changes."""
        self._update_triangle_details()
        self._update_analysis_plots()

    def _on_params_changed(self, params: dict):
        """Handle parameter window changes."""
        # params = {'n': RPM, 'Q': m³/s, 'alpha1': degrees}
        # Update triangle calculations with new parameters
        # For now, just trigger a refresh
        self._update_all()

    def _toggle_params_window(self):
        """Show/hide the parameter input window."""
        if self.params_window.isVisible():
            self.params_window.hide()
        else:
            self.params_window.show()
            self.params_window.raise_()
            self.params_window.activateWindow()

    def _update_all(self):
        """Update all displays."""
        self._update_slip_calculation()
        self._update_triangle_details()
        self._update_analysis_plots()

    def _update_slip_calculation(self):
        """Update slip calculation display."""
        # Get outlet blade angles from triangle widget
        # For simplicity, use average of hub and tip
        beta_blade_out_hub = 60.0  # Placeholder - should get from triangle widget
        beta_blade_out_tip = 65.0  # Placeholder

        beta_blade_avg = (beta_blade_out_hub + beta_blade_out_tip) / 2.0

        # Calculate slip (used internally for triangle calculations)
        slip_result = calculate_slip(
            beta_blade_deg=beta_blade_avg,
            blade_count=self._blade_properties.blade_count,
            slip_mode=self._blade_properties.slip_mode,
            mock_slip_deg=self._blade_properties.mock_slip_deg,
            r_q=self._blade_properties.r_q,
            d_inlet_hub_mm=self._blade_properties.d_inlet_hub_mm,
            d_inlet_shroud_mm=self._blade_properties.d_inlet_shroud_mm,
            d_outlet_mm=self._blade_properties.d_outlet_mm
        )
        # Slip calculation results are used in triangle details and analysis plots
        # No separate display widget needed - inputs are in Blade Parameters section

    def _update_triangle_details(self):
        """Update detailed triangle information display."""
        # Create sample triangle data dict
        # In full implementation, this would compute from actual triangle widget data
        triangle_data = {
            'inlet_hub': {
                'u': 15.7,
                'cu': 0.0,
                'cm': 5.0,
                'c': 5.0,
                'w': 16.5,
                'alpha': 90.0,
                'beta': 25.0,
                'cm_blocked': 5.5,
                'beta_blocked': 26.0,
                'beta_blade': 30.0,
                'incidence': self._blade_properties.incidence_deg,
            },
            'inlet_tip': {
                'u': 26.2,
                'cu': 0.0,
                'cm': 5.0,
                'c': 5.0,
                'w': 26.7,
                'alpha': 90.0,
                'beta': 30.0,
                'cm_blocked': 5.5,
                'beta_blocked': 31.0,
                'beta_blade': 35.0,
                'incidence': self._blade_properties.incidence_deg,
            },
            'outlet_hub': {
                'u': 20.9,
                'cu': 18.0,
                'cm': 4.0,
                'c': 18.4,
                'w': 4.3,
                'alpha': 12.5,
                'beta': 55.0,
                'cm_blocked': 4.4,
                'beta_blocked': 56.0,
                'beta_blade': 60.0,
                'slip': self._blade_properties.mock_slip_deg,
                'cu_slipped': 17.0,
            },
            'outlet_tip': {
                'u': 31.4,
                'cu': 27.0,
                'cm': 4.0,
                'c': 27.3,
                'w': 5.9,
                'alpha': 8.4,
                'beta': 60.0,
                'cm_blocked': 4.4,
                'beta_blocked': 61.0,
                'beta_blade': 65.0,
                'slip': self._blade_properties.mock_slip_deg,
                'cu_slipped': 26.0,
            },
        }

        self.triangle_details.update_details(triangle_data)

    def _update_analysis_plots(self):
        """Update analysis plots."""
        # Create sample plot data
        # In full implementation, this would compute from actual blade angle distributions
        plot_data = {
            'spans': [0.0, 1.0],  # Hub to tip
            'beta_inlet': [25.0, 30.0],
            'beta_outlet': [55.0, 60.0],
            'beta_blade_inlet': [30.0, 35.0],
            'beta_blade_outlet': [60.0, 65.0],
            'beta_blocked_inlet': [26.0, 31.0],
            'beta_blocked_outlet': [56.0, 61.0],
            'slip_angles': [
                self._blade_properties.mock_slip_deg,
                self._blade_properties.mock_slip_deg
            ],
            'incidence_angles': [
                self._blade_properties.incidence_deg,
                self._blade_properties.incidence_deg
            ],
        }

        self.analysis_plots.update_data(plot_data)

    def get_blade_properties(self) -> BladeProperties:
        """Get current blade properties."""
        return self._blade_properties

    def set_blade_properties(self, properties: BladeProperties):
        """Set blade properties."""
        self._blade_properties = properties
        self.thickness_widget.set_thickness(properties.thickness)
        # Update other widgets...
        self._update_all()
