"""
Blade Properties Widgets - Components for the Blade Properties tab.

Includes:
- StyledSpinBox: Custom spinbox with +/- buttons (from Design tab pattern)
- BladeThicknessMatrixWidget: 2×2 table for blade thickness input
- BladeInputsWidget: Blade count, incidence, and slip mode controls
- SlipCalculationWidget: Slip calculation results display
- TriangleDetailsWidget: Detailed velocity triangle information
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QSpinBox,
    QDoubleSpinBox, QComboBox, QFrame, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QPushButton, QSizePolicy, QToolButton, QAbstractSpinBox, QGridLayout
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from pumpforge3d_core.analysis.blade_properties import (
    BladeThicknessMatrix, SlipCalculationResult, calculate_slip
)


class StyledSpinBox(QWidget):
    """
    Custom spinbox without native arrows, with +/- buttons.
    Pattern from Design tab for consistent UX.
    """

    valueChanged = Signal(float)
    editingFinished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Minus button
        self.minus_btn = QToolButton()
        self.minus_btn.setText("−")
        self.minus_btn.setFixedSize(20, 24)
        self.minus_btn.setAutoRepeat(True)
        self.minus_btn.clicked.connect(self._decrement)
        layout.addWidget(self.minus_btn)

        # Spinbox without arrows
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spinbox.setFixedWidth(80)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)
        self.spinbox.editingFinished.connect(self.editingFinished.emit)
        layout.addWidget(self.spinbox)

        # Plus button
        self.plus_btn = QToolButton()
        self.plus_btn.setText("+")
        self.plus_btn.setFixedSize(20, 24)
        self.plus_btn.setAutoRepeat(True)
        self.plus_btn.clicked.connect(self._increment)
        layout.addWidget(self.plus_btn)

    def _increment(self):
        self.spinbox.stepUp()

    def _decrement(self):
        self.spinbox.stepDown()

    # Delegate methods to inner spinbox
    def value(self) -> float:
        return self.spinbox.value()

    def setValue(self, val: float):
        self.spinbox.setValue(val)

    def setRange(self, min_val: float, max_val: float):
        self.spinbox.setRange(min_val, max_val)

    def setDecimals(self, decimals: int):
        self.spinbox.setDecimals(decimals)

    def setSuffix(self, suffix: str):
        self.spinbox.setSuffix(suffix)

    def setSingleStep(self, step: float):
        self.spinbox.setSingleStep(step)

    def blockSignals(self, block: bool) -> bool:
        return self.spinbox.blockSignals(block)


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

        # Table with editable cells (no spinboxes)
        self.table = QTableWidget(2, 2)
        self.table.setHorizontalHeaderLabels(['Inlet', 'Outlet'])
        self.table.setVerticalHeaderLabels(['Hub', 'Tip'])

        # Disable scrollbars
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Fixed column and row sizes
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 70)
        self.table.setRowHeight(0, 28)
        self.table.setRowHeight(1, 28)

        # Calculate proper size to fit content without scrollbars
        # Header widths + column widths + borders + margins
        v_header_width = self.table.verticalHeader().width()
        h_header_height = self.table.horizontalHeader().height()
        total_width = v_header_width + 70 + 70 + 4  # 4 for borders/margins
        total_height = h_header_height + 28 + 28 + 4  # 4 for borders/margins

        self.table.setFixedSize(total_width, total_height)
        self.table.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

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
                text-align: center;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 4px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 9px;
            }
        """)

        # Populate with editable text items
        for row in range(2):
            for col in range(2):
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

        # Set initial values
        self.table.item(0, 0).setText(f"{self._thickness.hub_inlet:.2f}")
        self.table.item(0, 1).setText(f"{self._thickness.hub_outlet:.2f}")
        self.table.item(1, 0).setText(f"{self._thickness.tip_inlet:.2f}")
        self.table.item(1, 1).setText(f"{self._thickness.tip_outlet:.2f}")

        layout.addWidget(self.table)

    def _connect_signals(self):
        """Connect table itemChanged signal."""
        self.table.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        """Handle cell edit and emit signal."""
        try:
            value = float(item.text())
            # Clamp to reasonable range
            value = max(0.1, min(value, 100.0))

            # Update internal thickness matrix
            row = item.row()
            col = item.column()

            if row == 0 and col == 0:
                self._thickness.hub_inlet = value
            elif row == 0 and col == 1:
                self._thickness.hub_outlet = value
            elif row == 1 and col == 0:
                self._thickness.tip_inlet = value
            elif row == 1 and col == 1:
                self._thickness.tip_outlet = value

            # Update display with formatted value
            self.table.blockSignals(True)
            item.setText(f"{value:.2f}")
            self.table.blockSignals(False)

            # Emit change signal
            self.thicknessChanged.emit(self._thickness)

        except ValueError:
            # Invalid input, revert to previous value
            self.table.blockSignals(True)
            if item.row() == 0 and item.column() == 0:
                item.setText(f"{self._thickness.hub_inlet:.2f}")
            elif item.row() == 0 and item.column() == 1:
                item.setText(f"{self._thickness.hub_outlet:.2f}")
            elif item.row() == 1 and item.column() == 0:
                item.setText(f"{self._thickness.tip_inlet:.2f}")
            elif item.row() == 1 and item.column() == 1:
                item.setText(f"{self._thickness.tip_outlet:.2f}")
            self.table.blockSignals(False)

    def get_thickness(self) -> BladeThicknessMatrix:
        """Get current thickness matrix."""
        return self._thickness

    def set_thickness(self, thickness: BladeThicknessMatrix):
        """Set thickness matrix values."""
        self._thickness = thickness
        self.table.blockSignals(True)

        self.table.item(0, 0).setText(f"{thickness.hub_inlet:.2f}")
        self.table.item(0, 1).setText(f"{thickness.hub_outlet:.2f}")
        self.table.item(1, 0).setText(f"{thickness.tip_inlet:.2f}")
        self.table.item(1, 1).setText(f"{thickness.tip_outlet:.2f}")

        self.table.blockSignals(False)


class BladeInputsWidget(QWidget):
    """
    Blade parameters input widget using StyledSpinBox pattern from Design tab.
    QFormLayout for clean alignment.
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
        layout.setSpacing(8)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)

        # Helper to create styled labels (9px, right-aligned)
        def create_label(text):
            label = QLabel(text)
            label.setStyleSheet("color: #cdd6f4; font-size: 9px;")
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return label

        # Blade count z (integer)
        blade_count_spin = StyledSpinBox()
        blade_count_spin.setRange(1, 20)
        blade_count_spin.setDecimals(0)
        blade_count_spin.setSingleStep(1)
        blade_count_spin.setValue(self._blade_count)
        self.blade_count_spin = blade_count_spin
        layout.addRow(create_label("Blade count z:"), blade_count_spin)

        # Incidence i (degrees)
        incidence_spin = StyledSpinBox()
        incidence_spin.setRange(-20.0, 20.0)
        incidence_spin.setDecimals(1)
        incidence_spin.setSingleStep(0.5)
        incidence_spin.setSuffix("°")
        incidence_spin.setValue(self._incidence)
        self.incidence_spin = incidence_spin
        layout.addRow(create_label("Incidence i:"), incidence_spin)

        # Slip mode (combobox)
        slip_mode_combo = QComboBox()
        slip_mode_combo.addItems(["Mock", "Wiesner", "Gülich"])
        slip_mode_combo.setCurrentText(self._slip_mode)
        slip_mode_combo.setFixedWidth(122)  # Match StyledSpinBox total width
        slip_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 3px;
                font-size: 10px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        self.slip_mode_combo = slip_mode_combo
        layout.addRow(create_label("Slip mode:"), slip_mode_combo)

        # Mock slip δ (degrees, conditional)
        mock_slip_spin = StyledSpinBox()
        mock_slip_spin.setRange(-30.0, 30.0)
        mock_slip_spin.setDecimals(1)
        mock_slip_spin.setSingleStep(0.5)
        mock_slip_spin.setSuffix("°")
        mock_slip_spin.setValue(self._mock_slip)
        self.mock_slip_spin = mock_slip_spin
        self.mock_slip_label = create_label("Mock slip δ:")
        layout.addRow(self.mock_slip_label, mock_slip_spin)

        self._update_mock_slip_visibility()

    def _connect_signals(self):
        self.blade_count_spin.valueChanged.connect(self._on_blade_count_changed)
        self.incidence_spin.valueChanged.connect(self._on_incidence_changed)
        self.slip_mode_combo.currentTextChanged.connect(self._on_slip_mode_changed)
        self.mock_slip_spin.valueChanged.connect(self._on_mock_slip_changed)

    def _on_blade_count_changed(self, value):
        self._blade_count = int(value)
        self.bladeCountChanged.emit(self._blade_count)

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
        self.mock_slip_label.setVisible(is_mock)

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
    Widget displaying slip calculation results with method selector and data table.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slip_result = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Method selector (ComboBox)
        method_layout = QHBoxLayout()
        method_layout.setSpacing(6)

        method_label = QLabel("Method:")
        method_label.setStyleSheet("color: #cdd6f4; font-size: 9px;")
        method_layout.addWidget(method_label)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["Mock"])  # Şimdilik tek eleman
        self.method_combo.setFixedWidth(100)
        self.method_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 3px;
                font-size: 10px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()

        layout.addLayout(method_layout)

        # Results data table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(['Parameter', 'Value'])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.results_table.setColumnWidth(1, 80)
        self.results_table.setMaximumHeight(180)
        self.results_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #45475a;
                border: 1px solid #45475a;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 3px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 4px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 9px;
            }
        """)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        layout.addWidget(self.results_table)

        # Formula collapsible section
        self.formula_button = QPushButton("▸ Show Formula/Assumptions")
        self.formula_button.setCheckable(True)
        self.formula_button.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #89b4fa;
                border: 1px solid #45475a;
                padding: 4px;
                text-align: left;
                font-size: 10px;
            }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:checked { background-color: #45475a; }
        """)
        self.formula_button.clicked.connect(self._toggle_formula)
        layout.addWidget(self.formula_button)

        self.formula_text = QTextEdit()
        self.formula_text.setReadOnly(True)
        self.formula_text.setMaximumHeight(180)
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
        arrow = "▾" if checked else "▸"
        text = "Hide Formula/Assumptions" if checked else "Show Formula/Assumptions"
        self.formula_button.setText(f"{arrow} {text}")

    def update_slip_result(self, slip_result: SlipCalculationResult, u2: float = None, cu2_inf: float = None):
        """Update displayed slip calculation results."""
        self._slip_result = slip_result

        if slip_result is None:
            self.results_table.setRowCount(1)
            self.results_table.setItem(0, 0, QTableWidgetItem("No data"))
            self.results_table.setItem(0, 1, QTableWidgetItem("-"))
            return

        # Prepare data rows with hierarchy
        data_rows = []

        # Main results
        data_rows.append(("Method", slip_result.method))
        data_rows.append(("  γ (slip coeff.)", f"{slip_result.gamma:.4f}"))
        data_rows.append(("  δ (slip angle)", f"{slip_result.slip_angle_deg:.2f}°"))

        # Correction factors (sub-items)
        data_rows.append(("Correction factors:", ""))
        data_rows.append(("  f_i", f"{slip_result.f_i:.4f}"))
        data_rows.append(("  k_w", f"{slip_result.k_w:.4f}"))

        # Velocity results if available
        if u2 is not None and cu2_inf is not None:
            from pumpforge3d_core.analysis.blade_properties import calculate_cu_slipped
            cu2 = calculate_cu_slipped(u2, cu2_inf, slip_result.gamma)
            data_rows.append(("Velocities:", ""))
            data_rows.append(("  cu2∞ (theor.)", f"{cu2_inf:.2f} m/s"))
            data_rows.append(("  cu2 (slipped)", f"{cu2:.2f} m/s"))

        # Populate table
        self.results_table.setRowCount(len(data_rows))
        for i, (param, value) in enumerate(data_rows):
            param_item = QTableWidgetItem(param)
            value_item = QTableWidgetItem(value)

            # Style header rows differently
            if param.endswith(":"):
                param_item.setForeground(Qt.GlobalColor.cyan)
                font = param_item.font()
                font.setBold(True)
                param_item.setFont(font)

            self.results_table.setItem(i, 0, param_item)
            self.results_table.setItem(i, 1, value_item)

        # Adjust row heights
        for i in range(self.results_table.rowCount()):
            self.results_table.setRowHeight(i, 22)


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
        title.setStyleSheet("font-weight: bold; color: #cdd6f4; font-size: 11px;")
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
                font-size: 9px;
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
