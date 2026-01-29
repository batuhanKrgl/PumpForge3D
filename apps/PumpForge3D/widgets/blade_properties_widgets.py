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
from PySide6.QtCore import Signal, Qt, QEvent
from PySide6.QtGui import QFont

import logging

from ..styles import (
    apply_combobox_style,
    apply_form_label_style,
    apply_groupbox_style,
    apply_numeric_spinbox_style,
)
from ..utils.editor_commit_filter import attach_commit_filter

from pumpforge3d_core.analysis.blade_properties import (
    BladeThicknessMatrix, SlipCalculationResult, calculate_slip
)

logger = logging.getLogger(__name__)


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
        self.minus_btn.setAccessibleName("Decrease value")
        self.minus_btn.setAccessibleDescription("Decrease the value.")
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
        self.spinbox.editingFinished.connect(self._on_editing_finished)
        apply_numeric_spinbox_style(self.spinbox)
        layout.addWidget(self.spinbox)

        # Plus button - larger for better touch target
        self.plus_btn = QToolButton()
        self.plus_btn.setText("+")
        self.plus_btn.setFixedSize(26, 28)
        self.plus_btn.setAutoRepeat(True)
        self.plus_btn.setAccessibleName("Increase value")
        self.plus_btn.setAccessibleDescription("Increase the value.")
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
        self.valueChanged.emit(self.spinbox.value())

    def _decrement(self):
        self.spinbox.stepDown()
        self.valueChanged.emit(self.spinbox.value())

    def _on_editing_finished(self):
        self.editingFinished.emit()
        self.valueChanged.emit(self.spinbox.value())

    # Delegate methods to inner spinbox
    def value(self) -> float:
        return self.spinbox.value()

    def setValue(self, val: float):
        self.spinbox.setValue(val)
        self._set_last_valid_value(val)

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

    def setReadOnly(self, read_only: bool) -> None:
        self.spinbox.setReadOnly(read_only)

    def setButtonsEnabled(self, enabled: bool) -> None:
        self.minus_btn.setEnabled(enabled)
        self.plus_btn.setEnabled(enabled)

    def _set_last_valid_value(self, value: float) -> None:
        self.spinbox.setProperty("last_valid_value", value)

    def revert_to_last_valid(self) -> None:
        last_valid = self.spinbox.property("last_valid_value")
        if last_valid is not None:
            self.spinbox.setValue(float(last_valid))


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
        self.table.setAccessibleName("Blade thickness table")
        self.table.setAccessibleDescription("Blade thickness inputs for hub and tip at inlet and outlet.")

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

        for row in range(2):
            for col in range(2):
                item = self.table.item(row, col)
                item.setData(Qt.ItemDataRole.UserRole, float(item.text()))

        layout.addWidget(self.table)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #f38ba8; font-size: 10px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

    def _connect_signals(self):
        """Connect table itemChanged signal."""
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.installEventFilter(self)

    def eventFilter(self, watched, event):  # noqa: N802 - Qt naming
        if watched is self.table and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                current = self.table.currentItem()
                if current is not None:
                    last_valid = current.data(Qt.ItemDataRole.UserRole)
                    if last_valid is not None:
                        self.table.blockSignals(True)
                        current.setText(f"{float(last_valid):.2f}")
                        self.table.blockSignals(False)
                        return True
        return super().eventFilter(watched, event)

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
            item.setData(Qt.ItemDataRole.UserRole, value)
            self.table.blockSignals(False)

            self._clear_error_state()

            # Emit change signal
            self.thicknessChanged.emit(self._thickness)

        except ValueError:
            # Invalid input, revert to previous value
            self.table.blockSignals(True)
            last_valid = item.data(Qt.ItemDataRole.UserRole)
            if last_valid is None:
                last_valid = self._thickness.hub_inlet
            item.setText(f"{float(last_valid):.2f}")
            self.table.blockSignals(False)
            self._set_error_state("Blade thickness must be a number between 0.1 and 100.0 mm.")
            logger.warning("Invalid blade thickness input at row %s col %s.", item.row(), item.column())

    def _set_error_state(self, message: str) -> None:
        self.table.setProperty("error", True)
        self.table.setToolTip(message)
        self.table.style().unpolish(self.table)
        self.table.style().polish(self.table)
        self.error_label.setText(f"⚠ {message}")
        self.error_label.setVisible(True)

    def _clear_error_state(self) -> None:
        self.table.setProperty("error", False)
        self.table.setToolTip("")
        self.table.style().unpolish(self.table)
        self.table.style().polish(self.table)
        self.error_label.setText("")
        self.error_label.setVisible(False)

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

        for row in range(2):
            for col in range(2):
                item = self.table.item(row, col)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, float(item.text()))

        self.table.blockSignals(False)
        self._clear_error_state()


class BladeInputsWidget(QWidget):
    """
    Blade parameters input widget using StyledSpinBox pattern from Design tab.
    QFormLayout for clean alignment.
    """

    bladeCountChanged = Signal(int)
    incidenceChanged = Signal(float, float)
    slipModeChanged = Signal(str)
    mockSlipChanged = Signal(float, float)
    inputsCommitted = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blade_count = 3
        self._incidence_hub = 0.0
        self._incidence_tip = 0.0
        self._slip_mode = "Mock"
        self._mock_slip_hub = 5.0
        self._mock_slip_tip = 5.0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(8)
        self.setMinimumWidth(340)

        # Blade count z (integer)
        blade_count_spin = StyledSpinBox()
        blade_count_spin.setRange(1, 20)
        blade_count_spin.setDecimals(0)
        blade_count_spin.setSingleStep(1)
        blade_count_spin.setValue(self._blade_count)
        blade_count_spin.setToolTip("Number of blades (typically 5-7 for pumps)")
        self.blade_count_spin = blade_count_spin
        top_form = QFormLayout()
        top_form.setSpacing(8)
        top_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
        top_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        blade_count_label = QLabel("z:")
        apply_form_label_style(blade_count_label)
        blade_count_label.setBuddy(blade_count_spin.spinbox)
        top_form.addRow(blade_count_label, blade_count_spin)

        # Incidence i (degrees) - with subscript
        incidence_hub_spin = StyledSpinBox()
        incidence_hub_spin.setRange(-20.0, 20.0)
        incidence_hub_spin.setDecimals(1)
        incidence_hub_spin.setSingleStep(0.5)
        incidence_hub_spin.setSuffix("°")
        incidence_hub_spin.setValue(self._incidence_hub)
        incidence_hub_spin.setToolTip("Hub incidence angle: β₁ - βB₁ (flow angle - blade angle)")
        self.incidence_hub_spin = incidence_hub_spin
        hub_form = QFormLayout()
        hub_form.setSpacing(6)
        hub_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        hub_header = QLabel("Hub")
        apply_form_label_style(hub_header)

        incidence_tip_spin = StyledSpinBox()
        incidence_tip_spin.setRange(-20.0, 20.0)
        incidence_tip_spin.setDecimals(1)
        incidence_tip_spin.setSingleStep(0.5)
        incidence_tip_spin.setSuffix("°")
        incidence_tip_spin.setValue(self._incidence_tip)
        incidence_tip_spin.setToolTip("Tip incidence angle: β₁ - βB₁ (flow angle - blade angle)")
        self.incidence_tip_spin = incidence_tip_spin
        tip_form = QFormLayout()
        tip_form.setSpacing(6)
        tip_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        tip_header = QLabel("Tip/Shroud")
        apply_form_label_style(tip_header)

        # Slip mode (combobox)
        slip_mode_combo = QComboBox()
        slip_mode_combo.addItems(["Mock", "Wiesner", "Gülich"])
        slip_mode_combo.setCurrentText(self._slip_mode)
        slip_mode_combo.setFixedWidth(134)  # Match StyledSpinBox total width
        slip_mode_combo.setToolTip("Slip calculation method:\n• Mock: Manual slip angle\n• Wiesner: Empirical formula\n• Gülich: CFturbo recommended")
        apply_combobox_style(slip_mode_combo)
        self.slip_mode_combo = slip_mode_combo
        slip_label = QLabel("Slip:")
        apply_form_label_style(slip_label)
        slip_label.setBuddy(slip_mode_combo)
        top_form.addRow(slip_label, slip_mode_combo)

        incidence_hub_label = create_subscript_label("i", "1,hub")
        apply_form_label_style(incidence_hub_label)
        incidence_hub_label.setBuddy(incidence_hub_spin.spinbox)
        hub_form.addRow(incidence_hub_label, incidence_hub_spin)

        incidence_tip_label = create_subscript_label("i", "1,tip")
        apply_form_label_style(incidence_tip_label)
        incidence_tip_label.setBuddy(incidence_tip_spin.spinbox)
        tip_form.addRow(incidence_tip_label, incidence_tip_spin)

        # Mock slip δ (degrees, conditional)
        mock_slip_hub_spin = StyledSpinBox()
        mock_slip_hub_spin.setRange(-30.0, 30.0)
        mock_slip_hub_spin.setDecimals(1)
        mock_slip_hub_spin.setSingleStep(0.5)
        mock_slip_hub_spin.setSuffix("°")
        mock_slip_hub_spin.setValue(self._mock_slip_hub)
        mock_slip_hub_spin.setToolTip("Hub slip angle (δ): deviation from blade angle at outlet")
        self.mock_slip_hub_spin = mock_slip_hub_spin
        self.mock_slip_hub_label = QLabel("δ hub:")
        apply_form_label_style(self.mock_slip_hub_label)
        self.mock_slip_hub_label.setToolTip("Slip angle (hub)")
        self.mock_slip_hub_label.setBuddy(mock_slip_hub_spin.spinbox)
        hub_form.addRow(self.mock_slip_hub_label, mock_slip_hub_spin)

        mock_slip_tip_spin = StyledSpinBox()
        mock_slip_tip_spin.setRange(-30.0, 30.0)
        mock_slip_tip_spin.setDecimals(1)
        mock_slip_tip_spin.setSingleStep(0.5)
        mock_slip_tip_spin.setSuffix("°")
        mock_slip_tip_spin.setValue(self._mock_slip_tip)
        mock_slip_tip_spin.setToolTip("Tip slip angle (δ): deviation from blade angle at outlet")
        self.mock_slip_tip_spin = mock_slip_tip_spin
        self.mock_slip_tip_label = QLabel("δ tip:")
        apply_form_label_style(self.mock_slip_tip_label)
        self.mock_slip_tip_label.setToolTip("Slip angle (tip)")
        self.mock_slip_tip_label.setBuddy(mock_slip_tip_spin.spinbox)
        tip_form.addRow(self.mock_slip_tip_label, mock_slip_tip_spin)

        layout.addLayout(top_form, 0, 0, 1, 2)

        hub_column = QVBoxLayout()
        hub_column.setSpacing(4)
        hub_column.addWidget(hub_header)
        hub_column.addLayout(hub_form)
        layout.addLayout(hub_column, 1, 0)

        tip_column = QVBoxLayout()
        tip_column.setSpacing(4)
        tip_column.addWidget(tip_header)
        tip_column.addLayout(tip_form)
        layout.addLayout(tip_column, 1, 1)

        self._update_mock_slip_visibility()

        blade_count_spin.spinbox.setAccessibleName("Blade count")
        blade_count_spin.spinbox.setAccessibleDescription("Number of blades.")
        incidence_hub_spin.spinbox.setAccessibleName("Hub incidence")
        incidence_hub_spin.spinbox.setAccessibleDescription("Hub incidence angle in degrees.")
        incidence_tip_spin.spinbox.setAccessibleName("Tip incidence")
        incidence_tip_spin.spinbox.setAccessibleDescription("Tip incidence angle in degrees.")
        slip_mode_combo.setAccessibleName("Slip mode")
        slip_mode_combo.setAccessibleDescription("Select the slip calculation mode.")
        mock_slip_hub_spin.spinbox.setAccessibleName("Hub slip angle")
        mock_slip_hub_spin.spinbox.setAccessibleDescription("Hub slip angle in degrees.")
        mock_slip_tip_spin.spinbox.setAccessibleName("Tip slip angle")
        mock_slip_tip_spin.spinbox.setAccessibleDescription("Tip slip angle in degrees.")

    def _connect_signals(self):
        self.blade_count_spin.editingFinished.connect(self._on_blade_count_changed)
        self.incidence_hub_spin.editingFinished.connect(self._on_incidence_changed)
        self.incidence_tip_spin.editingFinished.connect(self._on_incidence_changed)
        self.slip_mode_combo.currentTextChanged.connect(self._on_slip_mode_changed)
        self.mock_slip_hub_spin.editingFinished.connect(self._on_mock_slip_changed)
        self.mock_slip_tip_spin.editingFinished.connect(self._on_mock_slip_changed)
        self.blade_count_spin.editingFinished.connect(self.inputsCommitted.emit)
        self.incidence_hub_spin.editingFinished.connect(self.inputsCommitted.emit)
        self.incidence_tip_spin.editingFinished.connect(self.inputsCommitted.emit)
        self.mock_slip_hub_spin.editingFinished.connect(self.inputsCommitted.emit)
        self.mock_slip_tip_spin.editingFinished.connect(self.inputsCommitted.emit)
        self.slip_mode_combo.currentTextChanged.connect(self.inputsCommitted.emit)

        for spin in [
            self.blade_count_spin,
            self.incidence_hub_spin,
            self.incidence_tip_spin,
            self.mock_slip_hub_spin,
            self.mock_slip_tip_spin,
        ]:
            attach_commit_filter(spin.spinbox)

    def _on_blade_count_changed(self, _value=None):
        self._blade_count = int(self.blade_count_spin.value())
        self.bladeCountChanged.emit(self._blade_count)

    def _on_incidence_changed(self, _value=None):
        self._incidence_hub = self.incidence_hub_spin.value()
        self._incidence_tip = self.incidence_tip_spin.value()
        self.incidenceChanged.emit(self._incidence_hub, self._incidence_tip)

    def _on_slip_mode_changed(self, mode):
        self._slip_mode = mode
        self._update_mock_slip_visibility()
        self.slipModeChanged.emit(mode)

    def _on_mock_slip_changed(self, _value=None):
        self._mock_slip_hub = self.mock_slip_hub_spin.value()
        self._mock_slip_tip = self.mock_slip_tip_spin.value()
        self.mockSlipChanged.emit(self._mock_slip_hub, self._mock_slip_tip)

    def _update_mock_slip_visibility(self):
        """Show/hide mock slip input based on slip mode."""
        is_mock = self._slip_mode == "Mock"
        self.mock_slip_hub_spin.setVisible(is_mock)
        self.mock_slip_hub_label.setVisible(is_mock)
        self.mock_slip_tip_spin.setVisible(is_mock)
        self.mock_slip_tip_label.setVisible(is_mock)

    def get_blade_count(self) -> int:
        return self._blade_count

    def get_incidence_hub(self) -> float:
        return self._incidence_hub

    def get_incidence_tip(self) -> float:
        return self._incidence_tip

    def get_slip_mode(self) -> str:
        return self._slip_mode

    def get_mock_slip_hub(self) -> float:
        return self._mock_slip_hub

    def get_mock_slip_tip(self) -> float:
        return self._mock_slip_tip


class StyledGroupBox(QGroupBox):
    """Group box using shared Design tab styling helpers."""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        apply_groupbox_style(self)


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
    Two-panel layout showing Leading edge (Hub/Tip) and Trailing edge (Hub/Tip).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Left table: Leading edge (@Hub and @Shroud/Tip)
        self.leading_table = QTableWidget()
        self.leading_table.setColumnCount(3)
        self.leading_table.setHorizontalHeaderLabels(['', 'Leading edge\n@Hub', 'Leading edge\n@Shroud'])
        self._configure_table(self.leading_table)
        layout.addWidget(self.leading_table)

        # Right table: Trailing edge (@Hub and @Shroud/Tip)
        self.trailing_table = QTableWidget()
        self.trailing_table.setColumnCount(3)
        self.trailing_table.setHorizontalHeaderLabels(['', 'Trailing edge\n@Hub', 'Trailing edge\n@Shroud'])
        self._configure_table(self.trailing_table)
        layout.addWidget(self.trailing_table)

    def _configure_table(self, table):
        """Configure common table properties."""
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Stretch columns
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 80)  # Parameter name column

        # No scrollbars
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #45475a;
                border: 1px solid #45475a;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 4px;
                border-right: 1px solid #45475a;
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

        # Define parameter rows
        params = [
            ('z', 'z', '', 0),  # Blade count
            ('r', 'r', 'mm', 2),  # Radius
            ('d', 'd', 'mm', 2),  # Diameter
            ('alpha', 'αF', '°', 1),  # Flow angle
            ('beta', 'βF', '°', 1),  # Relative flow angle
            ('u', 'u', 'm/s', 2),  # Blade speed
            ('cm', 'cm', 'm/s', 2),  # Meridional velocity
            ('cu', 'cu', 'm/s', 2),  # Circumferential velocity
            ('cr', 'cr', 'm/s', 2),  # Radial velocity
            ('cz', 'cz', 'm/s', 2),  # Axial velocity
            ('c', 'c', 'm/s', 2),  # Absolute velocity
            ('wu', 'wu', 'm/s', 2),  # Relative tangential velocity
            ('w', 'w', 'm/s', 2),  # Relative velocity
            ('cu_r', 'cu·r', 'm²/s', 3),  # Angular momentum
            ('i_1delta', 'i 1δ', '°', 1),  # Incidence
            ('beta_blade', 'β blade', '°', 1),  # Blade angle
        ]

        # Populate leading edge table (inlet)
        self._populate_table(self.leading_table, params, inlet_hub, inlet_tip)

        # Populate trailing edge table (outlet)
        self._populate_table(self.trailing_table, params, outlet_hub, outlet_tip)

    def _populate_table(self, table, params, hub_data, tip_data):
        """Populate a table with hub and tip data."""
        table.setRowCount(len(params))

        for row, (key, label, unit, decimals) in enumerate(params):
            # Parameter name
            param_item = QTableWidgetItem(label)
            param_item.setFont(QFont("", -1, QFont.Weight.Bold))
            table.setItem(row, 0, param_item)

            # Hub value
            hub_value = hub_data.get(key, '')
            if isinstance(hub_value, (int, float)):
                hub_str = f"{hub_value:.{decimals}f}"
            else:
                hub_str = str(hub_value) if hub_value else '-'
            hub_item = QTableWidgetItem(hub_str)
            hub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, hub_item)

            # Tip value
            tip_value = tip_data.get(key, '')
            if isinstance(tip_value, (int, float)):
                tip_str = f"{tip_value:.{decimals}f}"
            else:
                tip_str = str(tip_value) if tip_value else '-'
            tip_item = QTableWidgetItem(tip_str)
            tip_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, tip_item)

            # Set row height
            table.setRowHeight(row, 24)
