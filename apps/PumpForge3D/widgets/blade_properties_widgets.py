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


def create_subscript_label(base: str, subscript: str) -> QLabel:
    """Create a label with subscript formatting like i<sub>1</sub>."""
    label = QLabel(f"{base}<sub>{subscript}</sub>")
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


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

        # Minus button - larger for better touch target
        self.minus_btn = QToolButton()
        self.minus_btn.setText("−")
        self.minus_btn.setFixedSize(26, 28)
        self.minus_btn.setAutoRepeat(True)
        self.minus_btn.setStyleSheet("""
            QToolButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QToolButton:hover { background-color: #45475a; }
            QToolButton:pressed { background-color: #585b70; }
        """)
        self.minus_btn.clicked.connect(self._decrement)
        layout.addWidget(self.minus_btn)

        # Spinbox without arrows
        self.spinbox = QDoubleSpinBox()
        self.spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spinbox.setFixedWidth(80)
        self.spinbox.valueChanged.connect(self.valueChanged.emit)
        self.spinbox.editingFinished.connect(self.editingFinished.emit)
        layout.addWidget(self.spinbox)

        # Plus button - larger for better touch target
        self.plus_btn = QToolButton()
        self.plus_btn.setText("+")
        self.plus_btn.setFixedSize(26, 28)
        self.plus_btn.setAutoRepeat(True)
        self.plus_btn.setStyleSheet("""
            QToolButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QToolButton:hover { background-color: #45475a; }
            QToolButton:pressed { background-color: #585b70; }
        """)
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

        # Stretch columns to fill width, fixed row heights
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.setRowHeight(0, 28)
        self.table.setRowHeight(1, 28)

        # No vertical size constraints - let it fit naturally
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Style with hover effects and better fonts
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #45475a;
                border: 1px solid #45475a;
                border-radius: 4px;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 6px;
                text-align: center;
            }
            QTableWidget::item:hover {
                background-color: #313244;
            }
            QTableWidget::item:selected {
                background-color: #45475a;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #cdd6f4;
                padding: 6px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 10px;
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


class SpanNumberInputWidget(QWidget):
    """
    Widget for selecting number of span positions (2-10).
    Used to configure dynamic flow angle table.
    """

    spanCountChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._span_count = 2  # Default: hub + tip
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Span count spinbox
        span_spin = StyledSpinBox()
        span_spin.setRange(2, 10)
        span_spin.setDecimals(0)
        span_spin.setSingleStep(1)
        span_spin.setValue(self._span_count)
        span_spin.setToolTip("Number of span positions for analysis (2=hub+tip, 3=hub+mid+tip, etc.)")
        span_spin.valueChanged.connect(self._on_span_count_changed)
        self.span_spin = span_spin

        layout.addRow("Spans:", span_spin)

    def _on_span_count_changed(self, value):
        self._span_count = int(value)
        self.spanCountChanged.emit(self._span_count)

    def get_span_count(self) -> int:
        return self._span_count

    def set_span_count(self, count: int):
        count = max(2, min(10, count))
        self._span_count = count
        self.span_spin.setValue(count)


class IncidenceInputWidget(QWidget):
    """
    Widget for hub + tip incidence angle input with linear interpolation.
    Used for inlet blade angle calculation.
    """

    incidenceChanged = Signal(dict)  # {'hub': float, 'tip': float}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._incidence_hub = 0.0
        self._incidence_tip = 0.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Hub incidence
        hub_spin = StyledSpinBox()
        hub_spin.setRange(-20.0, 20.0)
        hub_spin.setDecimals(1)
        hub_spin.setSingleStep(0.5)
        hub_spin.setSuffix("°")
        hub_spin.setValue(self._incidence_hub)
        hub_spin.setToolTip("Incidence angle at hub (βF - βB)")
        hub_spin.valueChanged.connect(lambda v: self._on_value_changed('hub', v))
        self.hub_spin = hub_spin
        layout.addRow(create_subscript_label("i", "hub"), hub_spin)

        # Tip incidence
        tip_spin = StyledSpinBox()
        tip_spin.setRange(-20.0, 20.0)
        tip_spin.setDecimals(1)
        tip_spin.setSingleStep(0.5)
        tip_spin.setSuffix("°")
        tip_spin.setValue(self._incidence_tip)
        tip_spin.setToolTip("Incidence angle at tip (βF - βB)")
        tip_spin.valueChanged.connect(lambda v: self._on_value_changed('tip', v))
        self.tip_spin = tip_spin
        layout.addRow(create_subscript_label("i", "tip"), tip_spin)

        # Info label
        info_label = QLabel("Intermediate spans: linear interpolation")
        info_label.setStyleSheet("color: #a6adc8; font-size: 9px; font-style: italic;")
        layout.addRow("", info_label)

    def _on_value_changed(self, position: str, value: float):
        if position == 'hub':
            self._incidence_hub = value
        else:
            self._incidence_tip = value

        self.incidenceChanged.emit({'hub': self._incidence_hub, 'tip': self._incidence_tip})

    def get_incidence(self) -> dict:
        return {'hub': self._incidence_hub, 'tip': self._incidence_tip}

    def set_incidence(self, hub: float, tip: float):
        self._incidence_hub = hub
        self._incidence_tip = tip
        self.hub_spin.setValue(hub)
        self.tip_spin.setValue(tip)


class SlipInputWidget(QWidget):
    """
    Widget for slip calculation settings (separate from incidence).
    """

    slipSettingsChanged = Signal(dict)  # {'mode': str, 'mock_slip': float}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slip_mode = "Mock"
        self._mock_slip = 5.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Slip mode
        slip_mode_combo = QComboBox()
        slip_mode_combo.addItems(["Mock", "Wiesner", "Gülich"])
        slip_mode_combo.setCurrentText(self._slip_mode)
        slip_mode_combo.setFixedWidth(134)
        slip_mode_combo.setToolTip("Slip calculation method:\n• Mock: Manual slip angle\n• Wiesner: Empirical formula\n• Gülich: CFturbo recommended")
        slip_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 4px 6px;
                font-size: 11px;
                border-radius: 4px;
            }
            QComboBox:hover { background-color: #45475a; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        slip_mode_combo.currentTextChanged.connect(self._on_slip_mode_changed)
        self.slip_mode_combo = slip_mode_combo
        layout.addRow("Mode:", slip_mode_combo)

        # Mock slip
        mock_slip_spin = StyledSpinBox()
        mock_slip_spin.setRange(-30.0, 30.0)
        mock_slip_spin.setDecimals(1)
        mock_slip_spin.setSingleStep(0.5)
        mock_slip_spin.setSuffix("°")
        mock_slip_spin.setValue(self._mock_slip)
        mock_slip_spin.setToolTip("Manual slip angle (δ)")
        mock_slip_spin.valueChanged.connect(self._on_mock_slip_changed)
        self.mock_slip_spin = mock_slip_spin
        self.mock_slip_label = create_subscript_label("δ", "2")
        layout.addRow(self.mock_slip_label, mock_slip_spin)

        self._update_mock_slip_visibility()

    def _on_slip_mode_changed(self, mode: str):
        self._slip_mode = mode
        self._update_mock_slip_visibility()
        self._emit_changed()

    def _on_mock_slip_changed(self, value: float):
        self._mock_slip = value
        self._emit_changed()

    def _update_mock_slip_visibility(self):
        is_mock = self._slip_mode == "Mock"
        self.mock_slip_spin.setVisible(is_mock)
        self.mock_slip_label.setVisible(is_mock)

    def _emit_changed(self):
        self.slipSettingsChanged.emit({
            'mode': self._slip_mode,
            'mock_slip': self._mock_slip
        })

    def get_settings(self) -> dict:
        return {'mode': self._slip_mode, 'mock_slip': self._mock_slip}

    def set_settings(self, mode: str, mock_slip: float):
        self._slip_mode = mode
        self._mock_slip = mock_slip
        self.slip_mode_combo.setCurrentText(mode)
        self.mock_slip_spin.setValue(mock_slip)
        self._update_mock_slip_visibility()


class BetaAngleTableWidget(QWidget):
    """
    Dynamic editable table for beta flow angles.
    Rows = span positions (hub to tip), Columns = inlet/outlet.
    Table resizes based on span count (2-10).
    Units: degrees
    """

    betaAnglesChanged = Signal(dict)  # {'spans': [...], 'inlet': [...], 'outlet': [...]}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._span_count = 2  # Default: hub + tip only
        self._inlet_angles = [25.0, 30.0]  # Hub, Tip
        self._outlet_angles = [55.0, 60.0]  # Hub, Tip
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Table with editable cells
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['β Inlet', 'β Outlet'])

        # Disable scrollbars
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Stretch columns to fill width, fixed row heights
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        # No vertical size constraints - let it fit naturally
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Style (same as thickness table)
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

        layout.addWidget(self.table)

        # Build table with current span count
        self._rebuild_table()

    def _rebuild_table(self):
        """Rebuild table with current span count."""
        self.table.blockSignals(True)

        # Set row count based on span count
        self.table.setRowCount(self._span_count)

        # Update row labels
        row_labels = []
        if self._span_count == 2:
            row_labels = ['Hub', 'Tip']
        else:
            row_labels = ['Hub']
            for i in range(1, self._span_count - 1):
                span_pct = int((i / (self._span_count - 1)) * 100)
                row_labels.append(f'{span_pct}%')
            row_labels.append('Tip')

        self.table.setVerticalHeaderLabels(row_labels)

        # Resize angle arrays if needed
        if len(self._inlet_angles) != self._span_count:
            self._resize_angle_arrays()

        # Populate cells
        for row in range(self._span_count):
            for col in range(2):
                # Get or create item
                item = self.table.item(row, col)
                if item is None:
                    item = QTableWidgetItem()
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, col, item)

                # Set value
                if col == 0:  # Inlet
                    item.setText(f"{self._inlet_angles[row]:.1f}")
                else:  # Outlet
                    item.setText(f"{self._outlet_angles[row]:.1f}")

            # Set row height
            self.table.setRowHeight(row, 28)

        self.table.blockSignals(False)

    def _resize_angle_arrays(self):
        """Resize inlet/outlet angle arrays and interpolate intermediate values."""
        old_count = len(self._inlet_angles)
        new_count = self._span_count

        if new_count < old_count:
            # Reduce: keep hub and tip, discard middle
            self._inlet_angles = [self._inlet_angles[0], self._inlet_angles[-1]]
            self._outlet_angles = [self._outlet_angles[0], self._outlet_angles[-1]]

        if new_count > len(self._inlet_angles):
            # Expand: interpolate between hub and tip
            hub_inlet = self._inlet_angles[0]
            tip_inlet = self._inlet_angles[-1]
            hub_outlet = self._outlet_angles[0]
            tip_outlet = self._outlet_angles[-1]

            self._inlet_angles = [
                hub_inlet + (i / (new_count - 1)) * (tip_inlet - hub_inlet)
                for i in range(new_count)
            ]
            self._outlet_angles = [
                hub_outlet + (i / (new_count - 1)) * (tip_outlet - hub_outlet)
                for i in range(new_count)
            ]

    def _connect_signals(self):
        """Connect table itemChanged signal."""
        self.table.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        """Handle cell edit and emit signal."""
        try:
            value = float(item.text())
            # Clamp to reasonable range
            value = max(0.0, min(value, 90.0))

            # Update internal angles array
            row = item.row()
            col = item.column()

            if col == 0:  # Inlet
                self._inlet_angles[row] = value
            else:  # Outlet
                self._outlet_angles[row] = value

            # Update display with formatted value
            self.table.blockSignals(True)
            item.setText(f"{value:.1f}")
            self.table.blockSignals(False)

            # Emit change signal
            self._emit_angles_changed()

        except ValueError:
            # Invalid input, revert to previous value
            self.table.blockSignals(True)
            if col == 0:
                item.setText(f"{self._inlet_angles[row]:.1f}")
            else:
                item.setText(f"{self._outlet_angles[row]:.1f}")
            self.table.blockSignals(False)

    def _emit_angles_changed(self):
        """Emit signal with current angles data."""
        spans = [i / (self._span_count - 1) for i in range(self._span_count)]
        self.betaAnglesChanged.emit({
            'spans': spans,
            'inlet': self._inlet_angles.copy(),
            'outlet': self._outlet_angles.copy()
        })

    def set_span_count(self, count: int):
        """Set number of span positions and rebuild table."""
        count = max(2, min(10, count))
        if count != self._span_count:
            self._span_count = count
            self._rebuild_table()
            self._emit_angles_changed()

    def get_angles(self) -> dict:
        """Get current beta angles."""
        spans = [i / (self._span_count - 1) for i in range(self._span_count)]
        return {
            'spans': spans,
            'inlet': self._inlet_angles.copy(),
            'outlet': self._outlet_angles.copy()
        }

    def set_angles(self, inlet_angles: list, outlet_angles: list):
        """Set beta angles values."""
        if len(inlet_angles) != len(outlet_angles):
            return

        self._span_count = len(inlet_angles)
        self._inlet_angles = inlet_angles.copy()
        self._outlet_angles = outlet_angles.copy()
        self._rebuild_table()


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
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Blade count z (integer)
        blade_count_spin = StyledSpinBox()
        blade_count_spin.setRange(1, 20)
        blade_count_spin.setDecimals(0)
        blade_count_spin.setSingleStep(1)
        blade_count_spin.setValue(self._blade_count)
        blade_count_spin.setToolTip("Number of blades (typically 5-7 for pumps)")
        self.blade_count_spin = blade_count_spin
        layout.addRow("z:", blade_count_spin)

        # Incidence i (degrees) - with subscript
        incidence_spin = StyledSpinBox()
        incidence_spin.setRange(-20.0, 20.0)
        incidence_spin.setDecimals(1)
        incidence_spin.setSingleStep(0.5)
        incidence_spin.setSuffix("°")
        incidence_spin.setValue(self._incidence)
        incidence_spin.setToolTip("Incidence angle: β₁ - βB₁ (flow angle - blade angle)")
        self.incidence_spin = incidence_spin
        layout.addRow(create_subscript_label("i", "1"), incidence_spin)

        # Slip mode (combobox)
        slip_mode_combo = QComboBox()
        slip_mode_combo.addItems(["Mock", "Wiesner", "Gülich"])
        slip_mode_combo.setCurrentText(self._slip_mode)
        slip_mode_combo.setFixedWidth(134)  # Match StyledSpinBox total width
        slip_mode_combo.setToolTip("Slip calculation method:\n• Mock: Manual slip angle\n• Wiesner: Empirical formula\n• Gülich: CFturbo recommended")
        slip_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 4px 6px;
                font-size: 11px;
                border-radius: 4px;
            }
            QComboBox:hover { background-color: #45475a; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        self.slip_mode_combo = slip_mode_combo
        layout.addRow("Slip:", slip_mode_combo)

        # Mock slip δ (degrees, conditional)
        mock_slip_spin = StyledSpinBox()
        mock_slip_spin.setRange(-30.0, 30.0)
        mock_slip_spin.setDecimals(1)
        mock_slip_spin.setSingleStep(0.5)
        mock_slip_spin.setSuffix("°")
        mock_slip_spin.setValue(self._mock_slip)
        mock_slip_spin.setToolTip("Manual slip angle (δ): deviation from blade angle at outlet")
        self.mock_slip_spin = mock_slip_spin
        self.mock_slip_label = QLabel("δ:")
        self.mock_slip_label.setToolTip("Slip angle (manual value)")
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
    Detailed velocity triangle information in table format.
    Single table with Hub (left) | Separator | Tip (right) layout.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Single unified table: [Param] [Hub Inlet] [Hub Outlet] | [Tip Inlet] [Tip Outlet]
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['', 'Leading edge\n@Hub', 'Trailing edge\n@Hub',
                                               'Leading edge\n@Shroud', 'Trailing edge\n@Shroud'])

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Column widths
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 80)  # Parameter name column

        # No horizontal scrollbar
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

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
                padding: 6px 4px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 9px;
            }
        """)

        layout.addWidget(self.table)

    def update_details(self, triangle_data_dict: dict):
        """
        Update triangle details display.

        Args:
            triangle_data_dict: Dict with keys 'inlet_hub', 'inlet_tip', 'outlet_hub', 'outlet_tip'
                                Each value is a dict with triangle parameters
        """
        inlet_hub = triangle_data_dict.get('inlet_hub', {})
        inlet_tip = triangle_data_dict.get('inlet_tip', {})
        outlet_hub = triangle_data_dict.get('outlet_hub', {})
        outlet_tip = triangle_data_dict.get('outlet_tip', {})

        # Define parameter rows with merge info: (key, label, merge_hub_cols)
        # merge_hub_cols: True if hub has single value (merge cols 1-2)
        params = [
            ('z', 'z', True),             # Blade count - merged for hub
            ('r', 'r', False),            # Radius - different inlet/outlet
            ('d', 'd', False),            # Diameter
            ('alpha', 'αF', False),       # Flow angle
            ('beta', 'βF', False),        # Relative flow angle
            ('u', 'u', False),            # Blade speed
            ('cm', 'cm', False),          # Meridional velocity
            ('cu', 'cu', False),          # Circumferential velocity
            ('cr', 'cr', False),          # Radial velocity
            ('cz', 'cz', False),          # Axial velocity
            ('c', 'c', False),            # Absolute velocity
            ('wu', 'wu', False),          # Relative tangential velocity
            ('w', 'w', False),            # Relative velocity
            ('cu_r', 'cu·r', False),      # Angular momentum
            ('tau', 'τ', True),           # Obstruction - merged
            ('i_1delta', 'i|δ', False),   # Incidence/deviation
            ('w2_w1', 'w2/w1', True),     # Velocity ratio - merged
            ('c2_c1', 'c2/c1', True),     # Velocity ratio - merged
            ('delta_alpha', 'ΔαF', True), # Deflection angle - merged
            ('delta_beta', 'ΔβF', True),  # Deflection angle - merged
            ('phi', 'φ=ΔβB', True),       # Blade camber - merged
            ('gamma', 'γ', True),         # Slip coefficient - merged
            ('delta_cu_r', 'Δ(cu·r)', True), # Swirl difference - merged
            ('T', 'T', True),             # Torque - merged
            ('H', 'H', True),             # Head - merged
        ]

        self.table.setRowCount(len(params))

        for row, (key, label, merge_hub) in enumerate(params):
            # Parameter name (col 0)
            param_item = QTableWidgetItem(label)
            param_item.setFont(QFont("", -1, QFont.Weight.Bold))
            self.table.setItem(row, 0, param_item)

            if merge_hub:
                # Single value for hub - merge columns 1-2
                hub_value = inlet_hub.get(key, outlet_hub.get(key, ''))
                if isinstance(hub_value, (int, float)):
                    hub_str = f"{hub_value:.2f}"
                else:
                    hub_str = str(hub_value) if hub_value else '-'

                hub_item = QTableWidgetItem(hub_str)
                hub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, hub_item)
                self.table.setSpan(row, 1, 1, 2)  # Merge columns 1-2

                # Same for tip - merge columns 3-4
                tip_value = inlet_tip.get(key, outlet_tip.get(key, ''))
                if isinstance(tip_value, (int, float)):
                    tip_str = f"{tip_value:.2f}"
                else:
                    tip_str = str(tip_value) if tip_value else '-'

                tip_item = QTableWidgetItem(tip_str)
                tip_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, tip_item)
                self.table.setSpan(row, 3, 1, 2)  # Merge columns 3-4
            else:
                # Different values for inlet/outlet
                # Hub inlet (col 1)
                hub_inlet_val = inlet_hub.get(key, '')
                if isinstance(hub_inlet_val, (int, float)):
                    hub_inlet_str = f"{hub_inlet_val:.2f}"
                else:
                    hub_inlet_str = str(hub_inlet_val) if hub_inlet_val else '-'
                hub_inlet_item = QTableWidgetItem(hub_inlet_str)
                hub_inlet_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, hub_inlet_item)

                # Hub outlet (col 2)
                hub_outlet_val = outlet_hub.get(key, '')
                if isinstance(hub_outlet_val, (int, float)):
                    hub_outlet_str = f"{hub_outlet_val:.2f}"
                else:
                    hub_outlet_str = str(hub_outlet_val) if hub_outlet_val else '-'
                hub_outlet_item = QTableWidgetItem(hub_outlet_str)
                hub_outlet_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 2, hub_outlet_item)

                # Tip inlet (col 3)
                tip_inlet_val = inlet_tip.get(key, '')
                if isinstance(tip_inlet_val, (int, float)):
                    tip_inlet_str = f"{tip_inlet_val:.2f}"
                else:
                    tip_inlet_str = str(tip_inlet_val) if tip_inlet_val else '-'
                tip_inlet_item = QTableWidgetItem(tip_inlet_str)
                tip_inlet_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, tip_inlet_item)

                # Tip outlet (col 4)
                tip_outlet_val = outlet_tip.get(key, '')
                if isinstance(tip_outlet_val, (int, float)):
                    tip_outlet_str = f"{tip_outlet_val:.2f}"
                else:
                    tip_outlet_str = str(tip_outlet_val) if tip_outlet_val else '-'
                tip_outlet_item = QTableWidgetItem(tip_outlet_str)
                tip_outlet_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, tip_outlet_item)

            # Set row height
            self.table.setRowHeight(row, 22)
