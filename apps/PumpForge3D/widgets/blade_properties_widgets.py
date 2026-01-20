"""
Blade Properties Widgets - Components for the Blade Properties tab.

Includes:
- BladeThicknessMatrixWidget: 2×2 table for blade thickness input
- BladeInputsWidget: Blade count, incidence, and slip mode controls
- SlipCalculationWidget: Slip calculation results display
- TriangleDetailsWidget: Detailed velocity triangle information
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QFrame, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from pumpforge3d_core.analysis.blade_properties import (
    BladeThicknessMatrix, SlipCalculationResult, calculate_slip
)


class BladeThicknessMatrixWidget(QWidget):
    """
    Compact 2×2 table for blade thickness input (hub/tip × inlet/outlet).

    Units: mm
    """

    thicknessChanged = Signal(BladeThicknessMatrix)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thickness = BladeThicknessMatrix()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title
        title = QLabel("Blade Thickness (mm)")
        title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget(2, 2)
        self.table.setHorizontalHeaderLabels(['Inlet', 'Outlet'])
        self.table.setVerticalHeaderLabels(['Hub', 'Tip'])
        self.table.setMaximumHeight(100)
        self.table.setMaximumWidth(200)

        # Style
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #45475a;
                border: 1px solid #45475a;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 4px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 10px;
            }
        """)

        # Fixed column widths
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 80)

        # Populate with spinboxes
        self._hub_inlet_spin = self._create_spinbox(self._thickness.hub_inlet)
        self._hub_outlet_spin = self._create_spinbox(self._thickness.hub_outlet)
        self._tip_inlet_spin = self._create_spinbox(self._thickness.tip_inlet)
        self._tip_outlet_spin = self._create_spinbox(self._thickness.tip_outlet)

        self.table.setCellWidget(0, 0, self._hub_inlet_spin)
        self.table.setCellWidget(0, 1, self._hub_outlet_spin)
        self.table.setCellWidget(1, 0, self._tip_inlet_spin)
        self.table.setCellWidget(1, 1, self._tip_outlet_spin)

        layout.addWidget(self.table)

    def _create_spinbox(self, value):
        """Create a compact spinbox for thickness values."""
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 100.0)
        spin.setDecimals(2)
        spin.setValue(value)
        spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 2px;
            }
        """)
        return spin

    def _connect_signals(self):
        """Connect spinbox signals to update thickness matrix."""
        for spin in [self._hub_inlet_spin, self._hub_outlet_spin,
                     self._tip_inlet_spin, self._tip_outlet_spin]:
            spin.valueChanged.connect(self._on_thickness_changed)

    def _on_thickness_changed(self):
        """Update thickness matrix and emit signal."""
        self._thickness.hub_inlet = self._hub_inlet_spin.value()
        self._thickness.hub_outlet = self._hub_outlet_spin.value()
        self._thickness.tip_inlet = self._tip_inlet_spin.value()
        self._thickness.tip_outlet = self._tip_outlet_spin.value()
        self.thicknessChanged.emit(self._thickness)

    def get_thickness(self) -> BladeThicknessMatrix:
        """Get current thickness matrix."""
        return self._thickness

    def set_thickness(self, thickness: BladeThicknessMatrix):
        """Set thickness matrix values."""
        self._thickness = thickness
        self._hub_inlet_spin.blockSignals(True)
        self._hub_outlet_spin.blockSignals(True)
        self._tip_inlet_spin.blockSignals(True)
        self._tip_outlet_spin.blockSignals(True)

        self._hub_inlet_spin.setValue(thickness.hub_inlet)
        self._hub_outlet_spin.setValue(thickness.hub_outlet)
        self._tip_inlet_spin.setValue(thickness.tip_inlet)
        self._tip_outlet_spin.setValue(thickness.tip_outlet)

        self._hub_inlet_spin.blockSignals(False)
        self._hub_outlet_spin.blockSignals(False)
        self._tip_inlet_spin.blockSignals(False)
        self._tip_outlet_spin.blockSignals(False)


class BladeInputsWidget(QWidget):
    """
    Compact widget for blade count, incidence, and slip mode inputs.
    """

    bladeCountChanged = Signal(int)
    incidenceChanged = Signal(float)
    slipModeChanged = Signal(str)
    mockSlipChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blade_count = 3
        self._incidence = 0.0
        self._slip_mode = "Mock"
        self._mock_slip = 5.0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        # Blade count
        self.blade_count_spin = QSpinBox()
        self.blade_count_spin.setRange(1, 20)
        self.blade_count_spin.setValue(self._blade_count)
        self.blade_count_spin.setMaximumWidth(80)
        self.blade_count_spin.setStyleSheet("""
            QSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 3px;
            }
        """)
        layout.addRow("Blade count z:", self.blade_count_spin)

        # Incidence
        self.incidence_spin = QDoubleSpinBox()
        self.incidence_spin.setRange(-20.0, 20.0)
        self.incidence_spin.setDecimals(1)
        self.incidence_spin.setValue(self._incidence)
        self.incidence_spin.setSuffix("°")
        self.incidence_spin.setMaximumWidth(80)
        self.incidence_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 3px;
            }
        """)
        layout.addRow("Incidence i:", self.incidence_spin)

        # Slip mode
        self.slip_mode_combo = QComboBox()
        self.slip_mode_combo.addItems(["Mock", "Wiesner", "Gülich"])
        self.slip_mode_combo.setCurrentText(self._slip_mode)
        self.slip_mode_combo.setMaximumWidth(120)
        self.slip_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        layout.addRow("Slip mode:", self.slip_mode_combo)

        # Mock slip (only shown when slip_mode = "Mock")
        self.mock_slip_spin = QDoubleSpinBox()
        self.mock_slip_spin.setRange(-30.0, 30.0)
        self.mock_slip_spin.setDecimals(1)
        self.mock_slip_spin.setValue(self._mock_slip)
        self.mock_slip_spin.setSuffix("°")
        self.mock_slip_spin.setMaximumWidth(80)
        self.mock_slip_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 3px;
            }
        """)
        layout.addRow("Mock slip δ:", self.mock_slip_spin)
        self._update_mock_slip_visibility()

    def _connect_signals(self):
        self.blade_count_spin.valueChanged.connect(self._on_blade_count_changed)
        self.incidence_spin.valueChanged.connect(self._on_incidence_changed)
        self.slip_mode_combo.currentTextChanged.connect(self._on_slip_mode_changed)
        self.mock_slip_spin.valueChanged.connect(self._on_mock_slip_changed)

    def _on_blade_count_changed(self, value):
        self._blade_count = value
        self.bladeCountChanged.emit(value)

    def _on_incidence_changed(self, value):
        self._incidence = value
        self.incidenceChanged.emit(value)

    def _on_slip_mode_changed(self, mode):
        self._slip_mode = mode
        self._update_mock_slip_visibility()
        self.slipModeChanged.emit(mode)

    def _on_mock_slip_changed(self, value):
        self._mock_slip = value
        self.mockSlipChanged.emit(value)

    def _update_mock_slip_visibility(self):
        """Show/hide mock slip input based on slip mode."""
        is_mock = self._slip_mode == "Mock"
        self.mock_slip_spin.setVisible(is_mock)
        # Find the label
        form_layout = self.layout()
        for i in range(form_layout.rowCount()):
            label = form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if label and label.widget() and label.widget().text() == "Mock slip δ:":
                label.widget().setVisible(is_mock)

    def get_blade_count(self) -> int:
        return self._blade_count

    def get_incidence(self) -> float:
        return self._incidence

    def get_slip_mode(self) -> str:
        return self._slip_mode

    def get_mock_slip(self) -> float:
        return self._mock_slip


class SlipCalculationWidget(QWidget):
    """
    Widget displaying slip calculation results (γ, δ, f_i, k_w, cu_slipped).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slip_result = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title
        title = QLabel("Slip Calculation (Outlet)")
        title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        layout.addWidget(title)

        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 6px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.results_text)

        # Formula collapsible section (simple button toggle)
        self.formula_button = QPushButton("Show Formula/Assumptions")
        self.formula_button.setCheckable(True)
        self.formula_button.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #89b4fa;
                border: 1px solid #45475a;
                padding: 4px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
            QPushButton:checked {
                background-color: #45475a;
            }
        """)
        self.formula_button.clicked.connect(self._toggle_formula)
        layout.addWidget(self.formula_button)

        self.formula_text = QTextEdit()
        self.formula_text.setReadOnly(True)
        self.formula_text.setMaximumHeight(200)
        self.formula_text.setVisible(False)
        self.formula_text.setStyleSheet("""
            QTextEdit {
                background-color: #181825;
                color: #a6adc8;
                border: 1px solid #45475a;
                padding: 6px;
                font-family: 'Courier New', monospace;
                font-size: 9px;
            }
        """)
        self.formula_text.setHtml("""
            <b>Slip Coefficient Formulas (CFturbo 7.3.1.4.2.1)</b><br>
            <br>
            <b>Definition:</b><br>
            γ = 1 - (cu2∞ - cu2) / u2<br>
            <br>
            <b>Wiesner formula:</b><br>
            γ = 1 - √(sin β₂B) / z^0.7<br>
            <br>
            <b>Gülich modification:</b><br>
            γ = f_i * (1 - √(sin β₂B) / z^0.7) * k_w<br>
            <br>
            <b>Correction factors:</b><br>
            f_i = 0.98 (radial)<br>
            f_i = max(0.98, 1.02 + 1.2×10⁻³(r_q - 50)) (mixed-flow)<br>
            <br>
            k_w requires d_inlet_hub, d_inlet_shroud, d_outlet:<br>
            d_im = √(0.5*(d_shroud² + d_hub²))<br>
            ε_Lim = exp(-8.16 sin β₂B / z)<br>
            k_w = 1 if d_im/d_2 ≤ ε_Lim<br>
            k_w = 1 - (d_im/d_2 - ε_Lim)/(1 - ε_Lim) otherwise<br>
            <br>
            <b>Slipped cu:</b><br>
            cu2 = cu2∞ - (1 - γ) * u2
        """)
        layout.addWidget(self.formula_text)

    def _toggle_formula(self, checked):
        self.formula_text.setVisible(checked)
        self.formula_button.setText("Hide Formula/Assumptions" if checked else "Show Formula/Assumptions")

    def update_slip_result(self, slip_result: SlipCalculationResult, u2: float = None, cu2_inf: float = None):
        """Update displayed slip calculation results."""
        self._slip_result = slip_result

        if slip_result is None:
            self.results_text.setPlainText("No slip calculation available.")
            return

        # Format results
        text = f"Method: {slip_result.method}\n"
        text += f"γ (slip coefficient): {slip_result.gamma:.4f}\n"
        text += f"δ (slip angle): {slip_result.slip_angle_deg:.2f}°\n"
        text += f"f_i: {slip_result.f_i:.4f}\n"
        text += f"k_w: {slip_result.k_w:.4f}\n"

        if u2 is not None and cu2_inf is not None:
            from pumpforge3d_core.analysis.blade_properties import calculate_cu_slipped
            cu2 = calculate_cu_slipped(u2, cu2_inf, slip_result.gamma)
            text += f"\ncu2∞ (theoretical): {cu2_inf:.2f} m/s\n"
            text += f"cu2 (slipped): {cu2:.2f} m/s\n"

        if slip_result.warning:
            text += f"\nWarning: {slip_result.warning}"

        self.results_text.setPlainText(text)


class TriangleDetailsWidget(QWidget):
    """
    Detailed velocity triangle information with collapsible groups for each station.

    Shows:
    - u, cu, cm, c, w, alpha, beta
    - blocked values (cm_blocked, beta_blocked, etc.)
    - blade angles, incidence, slip
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Title
        title = QLabel("Triangle Details")
        title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        layout.addWidget(title)

        # Tree widget for collapsible groups
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Parameter', 'Value', 'Unit'])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 50)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                font-size: 10px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #45475a;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 4px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 10px;
            }
        """)

        # Create groups
        self.inlet_hub_group = QTreeWidgetItem(self.tree, ['Inlet Hub'])
        self.inlet_tip_group = QTreeWidgetItem(self.tree, ['Inlet Tip'])
        self.outlet_hub_group = QTreeWidgetItem(self.tree, ['Outlet Hub'])
        self.outlet_tip_group = QTreeWidgetItem(self.tree, ['Outlet Tip'])

        # Expand all by default
        self.tree.expandAll()

        layout.addWidget(self.tree)

    def update_details(self, triangle_data_dict: dict):
        """
        Update triangle details display.

        Args:
            triangle_data_dict: Dict with keys 'inlet_hub', 'inlet_tip', 'outlet_hub', 'outlet_tip'
                                Each value is a dict with triangle parameters
        """
        # Clear existing items
        for group in [self.inlet_hub_group, self.inlet_tip_group,
                      self.outlet_hub_group, self.outlet_tip_group]:
            group.takeChildren()

        # Populate each group
        self._populate_group(self.inlet_hub_group, triangle_data_dict.get('inlet_hub', {}))
        self._populate_group(self.inlet_tip_group, triangle_data_dict.get('inlet_tip', {}))
        self._populate_group(self.outlet_hub_group, triangle_data_dict.get('outlet_hub', {}))
        self._populate_group(self.outlet_tip_group, triangle_data_dict.get('outlet_tip', {}))

    def _populate_group(self, parent_item: QTreeWidgetItem, data: dict):
        """Populate a group with triangle data."""
        if not data:
            QTreeWidgetItem(parent_item, ['No data', '-', '-'])
            return

        # Define parameter order and formatting
        params = [
            ('u', 'Blade speed u', 'm/s', 2),
            ('cu', 'Circumferential cu', 'm/s', 2),
            ('cm', 'Meridional cm', 'm/s', 2),
            ('c', 'Absolute velocity c', 'm/s', 2),
            ('w', 'Relative velocity w', 'm/s', 2),
            ('alpha', 'Absolute angle α', '°', 1),
            ('beta', 'Relative angle β', '°', 1),
            ('cm_blocked', 'Blocked cm', 'm/s', 2),
            ('beta_blocked', 'Blocked β', '°', 1),
            ('beta_blade', 'Blade angle β_B', '°', 1),
            ('incidence', 'Incidence i', '°', 1),
            ('slip', 'Slip δ', '°', 1),
            ('cu_slipped', 'Slipped cu', 'm/s', 2),
        ]

        for key, label, unit, decimals in params:
            if key in data:
                value = data[key]
                if isinstance(value, (int, float)):
                    value_str = f"{value:.{decimals}f}"
                else:
                    value_str = str(value)
                QTreeWidgetItem(parent_item, [label, value_str, unit])
