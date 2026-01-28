"""
Beta Distribution Editor Widget.

Interactive widget for editing blade beta angle distribution with:
- Beta table (N x 2: beta_in, beta_out) with linear hub→tip distribution mode
"""

from typing import List
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QCheckBox, QSpinBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from pumpforge3d_core.geometry.beta_distribution import BetaDistributionModel


class BetaDistributionEditorWidget(QWidget):
    """
    Widget for editing beta angle distribution.
    
    Left: Table with beta_in/beta_out per span + linear mode toggles
    
    Signals:
        modelChanged: Emitted when model is modified
        betaCellEdited: Emitted when a beta table cell is edited (row, col, value)
        spanCountChanged: Emitted when span count changes
        linearModeChanged: Emitted when linear inlet/outlet toggles change
    """
    
    modelChanged = Signal(object)
    betaCellEdited = Signal(int, int, float)
    spanCountChanged = Signal(int)
    linearModeChanged = Signal(bool, bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self._model = BetaDistributionModel()
        self._updating = False
        
        self._setup_ui()
        self._connect_signals()
        self._load_from_model()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # Left panel: Table + controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        # Span count
        span_row = QHBoxLayout()
        span_row.addWidget(QLabel("Spans:"))
        self.span_spin = QSpinBox()
        self.span_spin.setRange(3, 25)
        self.span_spin.setValue(self._model.span_count)
        span_row.addWidget(self.span_spin)
        span_row.addStretch()
        left_layout.addLayout(span_row)
        
        # Linear mode toggles
        linear_row = QHBoxLayout()
        self.linear_inlet_check = QCheckBox("Linear Inlet")
        self.linear_inlet_check.setToolTip("Hub/Tip only editable, others interpolated")
        linear_row.addWidget(self.linear_inlet_check)
        self.linear_outlet_check = QCheckBox("Linear Outlet")
        self.linear_outlet_check.setToolTip("Hub/Tip only editable, others interpolated")
        linear_row.addWidget(self.linear_outlet_check)
        left_layout.addLayout(linear_row)
        
        # Beta table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["β_in (°)", "β_out (°)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumWidth(180)
        self.table.setMaximumWidth(250)
        left_layout.addWidget(self.table, 1)
        
        layout.addWidget(left_panel)
        
    
    def _connect_signals(self):
        """Connect UI signals."""
        self.span_spin.valueChanged.connect(self._on_span_count_changed)
        self.table.cellChanged.connect(self._on_table_cell_changed)
        # Linear mode toggles
        self.linear_inlet_check.toggled.connect(self._on_linear_inlet_toggled)
        self.linear_outlet_check.toggled.connect(self._on_linear_outlet_toggled)
    
    def _load_from_model(self):
        """Load table and plot from model."""
        self._updating = True
        
        # Linear mode toggles
        self.linear_inlet_check.setChecked(self._model.linear_inlet)
        self.linear_outlet_check.setChecked(self._model.linear_outlet)
        
        # Table
        self.table.setRowCount(self._model.span_count)
        for i in range(self._model.span_count):
            # Beta in
            item_in = QTableWidgetItem(f"{self._model.beta_in[i]:.1f}")
            item_in.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, item_in)
            
            # Beta out
            item_out = QTableWidgetItem(f"{self._model.beta_out[i]:.1f}")
            item_out.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, item_out)
            
            # Row header
            label = "Hub" if i == 0 else ("Tip" if i == self._model.span_count - 1 else f"S{i}")
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(label))
        
        # Update cell enabled state based on linear mode
        self._update_table_cell_states()
        
        self._updating = False
    
    def _update_table_cell_states(self):
        """Enable/disable table cells based on linear mode."""
        for i in range(self._model.span_count):
            is_hub_or_tip = (i == 0 or i == self._model.span_count - 1)
            
            # Inlet column
            item_in = self.table.item(i, 0)
            if item_in:
                if self._model.linear_inlet and not is_hub_or_tip:
                    item_in.setFlags(item_in.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item_in.setBackground(QColor('#313244'))
                else:
                    item_in.setFlags(item_in.flags() | Qt.ItemFlag.ItemIsEditable)
                    item_in.setBackground(QColor('#1e1e2e'))
            
            # Outlet column
            item_out = self.table.item(i, 1)
            if item_out:
                if self._model.linear_outlet and not is_hub_or_tip:
                    item_out.setFlags(item_out.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item_out.setBackground(QColor('#313244'))
                else:
                    item_out.setFlags(item_out.flags() | Qt.ItemFlag.ItemIsEditable)
                    item_out.setBackground(QColor('#1e1e2e'))
    
    def _on_span_count_changed(self, value: int):
        """Handle span count change."""
        self._model.set_span_count(value)
        self._model.apply_linear_mode()
        self._load_from_model()
        self.modelChanged.emit(self._model)
        self.spanCountChanged.emit(value)
    
    def _on_linear_inlet_toggled(self, checked: bool):
        """Handle linear inlet mode toggle."""
        if self._updating:
            return
        self._model.linear_inlet = checked
        if checked:
            self._model.apply_linear_mode()
        self._load_from_model()
        self.modelChanged.emit(self._model)
        self.linearModeChanged.emit(self._model.linear_inlet, self._model.linear_outlet)
    
    def _on_linear_outlet_toggled(self, checked: bool):
        """Handle linear outlet mode toggle."""
        if self._updating:
            return
        self._model.linear_outlet = checked
        if checked:
            self._model.apply_linear_mode()
        self._load_from_model()
        self.modelChanged.emit(self._model)
        self.linearModeChanged.emit(self._model.linear_inlet, self._model.linear_outlet)
    
    def _on_table_cell_changed(self, row: int, col: int):
        """Handle table cell edit."""
        if self._updating:
            return
        
        item = self.table.item(row, col)
        if not item:
            return
        
        try:
            value = float(item.text())
        except ValueError:
            self._load_from_model()
            return
        
        self._updating = True
        if col == 0:
            self._model.set_beta_in(row, value)
            if self._model.linear_inlet:
                self._model.apply_linear_mode()
        else:
            self._model.set_beta_out(row, value)
            if self._model.linear_outlet:
                self._model.apply_linear_mode()
        self._updating = False
        
        self._load_from_model()
        self.modelChanged.emit(self._model)
        self.betaCellEdited.emit(row, col, value)
    
    
    # Public API
    def set_model(self, model: BetaDistributionModel):
        """Set a new model."""
        self._model = model
        self.span_spin.blockSignals(True)
        self.span_spin.setValue(model.span_count)
        self.span_spin.blockSignals(False)
        self._load_from_model()

    def set_beta_distribution(
        self,
        *,
        span_count: int,
        beta_in: List[float],
        beta_out: List[float],
        linear_inlet: bool,
        linear_outlet: bool,
    ) -> None:
        """Update model values without re-triggering edits."""
        self._updating = True
        self._model.span_count = span_count
        self._model.span_fractions = np.linspace(0, 1, span_count)
        self._model.beta_in = np.array(beta_in, dtype=float)
        self._model.beta_out = np.array(beta_out, dtype=float)
        self._model.linear_inlet = linear_inlet
        self._model.linear_outlet = linear_outlet
        self.span_spin.blockSignals(True)
        self.span_spin.setValue(span_count)
        self.span_spin.blockSignals(False)
        self._load_from_model()
        self._updating = False
    
    def get_model(self) -> BetaDistributionModel:
        """Get the current model."""
        return self._model


# Standalone demo
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 11px; }
        QTableWidget { background-color: #181825; gridline-color: #313244; border: 1px solid #313244; }
        QHeaderView::section { background-color: #313244; color: #cdd6f4; padding: 4px; border: none; }
        QSpinBox, QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 2px 4px; }
        QToolButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; }
        QToolButton:hover { background-color: #45475a; }
        QGroupBox { border: 1px solid #45475a; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Beta Editor - Linear Mode + Angle Lock")
    window.resize(1000, 550)
    
    editor = BetaDistributionEditorWidget()
    window.setCentralWidget(editor)
    
    window.show()
    sys.exit(app.exec())
