"""
Blade Properties Tab - Central workspace for blade-related inputs and velocity triangles.

Based on CFturbo manual section 7.3.1.4 (Velocity Triangles) and 7.3.1.4.2.1 (Slip by Gülich/Wiesner).

Layout:
- Left panel: Inputs (thickness, blade count, incidence, slip)
- Center: Velocity triangle visualizations (2×2 subplots)
- Right panel: Analysis plots and detailed triangle info
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QGroupBox,
    QFormLayout, QScrollArea, QFrame, QLabel
)
from PySide6.QtCore import Qt, Signal

from ..widgets.velocity_triangle_widget import VelocityTriangleWidget
from ..widgets.blade_properties_widgets import (
    BladeThicknessMatrixWidget, BladeInputsWidget,
    SlipCalculationWidget, TriangleDetailsWidget
)
from ..widgets.blade_analysis_plots import BladeAnalysisPlotWidget

from pumpforge3d_core.analysis.blade_properties import (
    BladeProperties, calculate_slip, calculate_cu_slipped
)
from pumpforge3d_core.analysis.velocity_triangle import (
    compute_triangle, compute_derived_triangle
)


class BladePropertiesTab(QWidget):
    """
    Blade Properties Tab - main workspace for blade parameters and velocity triangles.
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

        self._setup_ui()
        self._connect_signals()
        self._update_all()

    def _setup_ui(self):
        """Setup the tab UI layout."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # Create main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT PANEL: Inputs ===
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)

        # === CENTER PANEL: Velocity Triangles ===
        self.triangle_widget = VelocityTriangleWidget()
        main_splitter.addWidget(self.triangle_widget)

        # === RIGHT PANEL: Analysis & Details ===
        right_panel = self._create_right_panel()
        main_splitter.addWidget(right_panel)

        # Set splitter proportions: 250px : flexible : 350px
        main_splitter.setStretchFactor(0, 0)  # Fixed width
        main_splitter.setStretchFactor(1, 1)  # Flexible
        main_splitter.setStretchFactor(2, 0)  # Fixed width

        main_layout.addWidget(main_splitter)

    def _create_left_panel(self) -> QWidget:
        """Create left input panel."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMaximumWidth(280)
        panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #45475a;
            }
        """)

        # Scroll area for inputs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #181825; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(12)

        # Title
        title = QLabel("Blade Properties")
        title.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 13px;
                font-weight: bold;
                padding: 4px;
            }
        """)
        scroll_layout.addWidget(title)

        # Blade thickness matrix
        thickness_group = QGroupBox("Blade Thickness")
        thickness_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                color: #89b4fa;
            }
        """)
        thickness_layout = QVBoxLayout(thickness_group)
        thickness_layout.setContentsMargins(6, 6, 6, 6)

        self.thickness_widget = BladeThicknessMatrixWidget()
        thickness_layout.addWidget(self.thickness_widget)
        scroll_layout.addWidget(thickness_group)

        # Blade inputs (count, incidence, slip mode)
        inputs_group = QGroupBox("Blade Parameters")
        inputs_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                color: #89b4fa;
            }
        """)
        inputs_layout = QVBoxLayout(inputs_group)
        inputs_layout.setContentsMargins(6, 6, 6, 6)

        self.blade_inputs_widget = BladeInputsWidget()
        inputs_layout.addWidget(self.blade_inputs_widget)
        scroll_layout.addWidget(inputs_group)

        # Slip calculation results
        slip_group = QGroupBox("Slip Calculation")
        slip_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                color: #89b4fa;
            }
        """)
        slip_layout = QVBoxLayout(slip_group)
        slip_layout.setContentsMargins(6, 6, 6, 6)

        self.slip_widget = SlipCalculationWidget()
        slip_layout.addWidget(self.slip_widget)
        scroll_layout.addWidget(slip_group)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addWidget(scroll)

        return panel

    def _create_right_panel(self) -> QWidget:
        """Create right panel with analysis plots and triangle details."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setMaximumWidth(400)
        panel.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #45475a;
            }
        """)

        # Vertical splitter for plots and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Analysis plots
        plots_group = QGroupBox("Analysis Plots")
        plots_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                color: #89b4fa;
            }
        """)
        plots_layout = QVBoxLayout(plots_group)
        plots_layout.setContentsMargins(4, 4, 4, 4)

        self.analysis_plots = BladeAnalysisPlotWidget()
        plots_layout.addWidget(self.analysis_plots)
        splitter.addWidget(plots_group)

        # Triangle details
        details_group = QGroupBox("Triangle Details")
        details_group.setStyleSheet("""
            QGroupBox {
                color: #cdd6f4;
                font-weight: bold;
                border: 1px solid #45475a;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 2px 6px;
                color: #89b4fa;
            }
        """)
        details_layout = QVBoxLayout(details_group)
        details_layout.setContentsMargins(4, 4, 4, 4)

        self.triangle_details = TriangleDetailsWidget()
        details_layout.addWidget(self.triangle_details)
        splitter.addWidget(details_group)

        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(6, 6, 6, 6)
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

        # Calculate slip
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

        # Update slip widget
        # Placeholder values for u2 and cu2_inf
        u2 = 30.0  # m/s - should calculate from rpm and radius
        cu2_inf = 25.0  # m/s - theoretical value

        self.slip_widget.update_slip_result(slip_result, u2, cu2_inf)

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
