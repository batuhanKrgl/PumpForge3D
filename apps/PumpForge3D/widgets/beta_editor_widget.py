"""
Beta Distribution Editor Widget.

Interactive widget for editing blade beta angle distribution with:
- Beta table (N x 2: beta_in, beta_out) with linear hub→tip distribution mode
- Interactive β–θ Bezier curve plot with 6 draggable handles
- 3 coupled lines connecting hub and tip CPs
- Angle lock controls for hub/tip CP1 and CP3
"""

from typing import Optional, Tuple, List
import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolButton, QLabel, QCheckBox, QSpinBox,
    QSizePolicy, QGroupBox, QFormLayout, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from pumpforge3d_core.geometry.beta_distribution import BetaDistributionModel


class BetaDistributionEditorWidget(QWidget):
    """
    Widget for editing beta angle distribution.
    
    Left: Table with beta_in/beta_out per span + linear mode toggles
    Right: Interactive β–θ plot with 6 draggable handles
    
    Signals:
        modelChanged: Emitted when model is modified
    """
    
    modelChanged = Signal(object)
    
    PICK_TOLERANCE = 10
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._model = BetaDistributionModel()
        self._updating = False
        
        # Drag state: ('hub'|'tip', j) or None
        self._dragging = None
        self._pan_start = None
        
        self._setup_ui()
        self._setup_plot()
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
        self.span_spin.setRange(2, 20)
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
        
        # Angle lock controls
        angle_group = QGroupBox("Angle Locks")
        angle_layout = QFormLayout(angle_group)
        angle_layout.setSpacing(4)
        
        # Hub CP1 and CP3
        hub_row1 = QHBoxLayout()
        self.hub_cp1_lock = QCheckBox()
        self.hub_cp1_angle = QDoubleSpinBox()
        self.hub_cp1_angle.setRange(-180, 180)
        self.hub_cp1_angle.setValue(45)
        self.hub_cp1_angle.setSuffix("°")
        hub_row1.addWidget(self.hub_cp1_lock)
        hub_row1.addWidget(self.hub_cp1_angle)
        angle_layout.addRow("Hub CP1:", hub_row1)
        
        hub_row3 = QHBoxLayout()
        self.hub_cp3_lock = QCheckBox()
        self.hub_cp3_angle = QDoubleSpinBox()
        self.hub_cp3_angle.setRange(-180, 180)
        self.hub_cp3_angle.setValue(45)
        self.hub_cp3_angle.setSuffix("°")
        hub_row3.addWidget(self.hub_cp3_lock)
        hub_row3.addWidget(self.hub_cp3_angle)
        angle_layout.addRow("Hub CP3:", hub_row3)
        
        # Tip CP1 and CP3
        tip_row1 = QHBoxLayout()
        self.tip_cp1_lock = QCheckBox()
        self.tip_cp1_angle = QDoubleSpinBox()
        self.tip_cp1_angle.setRange(-180, 180)
        self.tip_cp1_angle.setValue(45)
        self.tip_cp1_angle.setSuffix("°")
        tip_row1.addWidget(self.tip_cp1_lock)
        tip_row1.addWidget(self.tip_cp1_angle)
        angle_layout.addRow("Tip CP1:", tip_row1)
        
        tip_row3 = QHBoxLayout()
        self.tip_cp3_lock = QCheckBox()
        self.tip_cp3_angle = QDoubleSpinBox()
        self.tip_cp3_angle.setRange(-180, 180)
        self.tip_cp3_angle.setValue(45)
        self.tip_cp3_angle.setSuffix("°")
        tip_row3.addWidget(self.tip_cp3_lock)
        tip_row3.addWidget(self.tip_cp3_angle)
        angle_layout.addRow("Tip CP3:", tip_row3)
        
        left_layout.addWidget(angle_group)
        layout.addWidget(left_panel)
        
        # Right panel: Plot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(4)
        
        fit_btn = QToolButton()
        fit_btn.setText("⤢")
        fit_btn.setToolTip("Fit View")
        fit_btn.setFixedSize(28, 24)
        fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(fit_btn)
        
        toolbar.addStretch()
        
        self.show_lines_check = QCheckBox("Coupled lines")
        self.show_lines_check.setChecked(True)
        toolbar.addWidget(self.show_lines_check)
        
        right_layout.addLayout(toolbar)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(6, 4), dpi=100, facecolor='#181825')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #181825;")
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.canvas, 1)
        
        layout.addWidget(right_panel, 1)
    
    def _setup_plot(self):
        """Initialize the matplotlib plot."""
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#1e1e2e')
        
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')
        self.ax.tick_params(colors='#a6adc8', labelsize=8)
        self.ax.set_xlabel('θ* (normalized)', fontsize=9, color='#cdd6f4')
        self.ax.set_ylabel('β (degrees)', fontsize=9, color='#cdd6f4')
        
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
    
    def _connect_signals(self):
        """Connect UI signals."""
        self.span_spin.valueChanged.connect(self._on_span_count_changed)
        self.table.cellChanged.connect(self._on_table_cell_changed)
        self.show_lines_check.toggled.connect(lambda _: self._update_plot())
        
        # Linear mode toggles
        self.linear_inlet_check.toggled.connect(self._on_linear_inlet_toggled)
        self.linear_outlet_check.toggled.connect(self._on_linear_outlet_toggled)
        
        # Angle lock toggles
        self.hub_cp1_lock.toggled.connect(lambda v: self._on_angle_lock_changed('hub', 1, v))
        self.hub_cp3_lock.toggled.connect(lambda v: self._on_angle_lock_changed('hub', 3, v))
        self.tip_cp1_lock.toggled.connect(lambda v: self._on_angle_lock_changed('tip', 1, v))
        self.tip_cp3_lock.toggled.connect(lambda v: self._on_angle_lock_changed('tip', 3, v))
        
        # Angle value changes
        self.hub_cp1_angle.valueChanged.connect(lambda v: self._on_angle_value_changed('hub', 1, v))
        self.hub_cp3_angle.valueChanged.connect(lambda v: self._on_angle_value_changed('hub', 3, v))
        self.tip_cp1_angle.valueChanged.connect(lambda v: self._on_angle_value_changed('tip', 1, v))
        self.tip_cp3_angle.valueChanged.connect(lambda v: self._on_angle_value_changed('tip', 3, v))
    
    def _load_from_model(self):
        """Load table and plot from model."""
        self._updating = True
        
        # Linear mode toggles
        self.linear_inlet_check.setChecked(self._model.linear_inlet)
        self.linear_outlet_check.setChecked(self._model.linear_outlet)
        
        # Angle locks
        self.hub_cp1_lock.setChecked(self._model.hub_angle_lock[0])
        self.hub_cp1_angle.setValue(self._model.hub_angle_value[0])
        self.hub_cp3_lock.setChecked(self._model.hub_angle_lock[1])
        self.hub_cp3_angle.setValue(self._model.hub_angle_value[1])
        self.tip_cp1_lock.setChecked(self._model.tip_angle_lock[0])
        self.tip_cp1_angle.setValue(self._model.tip_angle_value[0])
        self.tip_cp3_lock.setChecked(self._model.tip_angle_lock[1])
        self.tip_cp3_angle.setValue(self._model.tip_angle_value[1])
        
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
        self._update_plot()
    
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
    
    def _update_plot(self):
        """Redraw the β–θ plot."""
        self.ax.clear()
        
        # Style
        self.ax.set_facecolor('#1e1e2e')
        for spine in self.ax.spines.values():
            spine.set_color('#45475a')
        self.ax.tick_params(colors='#a6adc8', labelsize=8)
        self.ax.set_xlabel('θ* (normalized)', fontsize=9, color='#cdd6f4')
        self.ax.set_ylabel('β (degrees)', fontsize=9, color='#cdd6f4')
        
        # Draw 3 coupled lines
        if self.show_lines_check.isChecked():
            for line in self._model.get_coupled_lines():
                xs = [pt[0] for pt in line]
                ys = [pt[1] for pt in line]
                self.ax.plot(xs, ys, '--', color='#f9e2af', linewidth=1.5, alpha=0.7)
        
        # Draw reference lines for locked CPs
        self._draw_reference_lines()
        
        # Colors
        colors = ['#89b4fa', '#a6e3a1', '#f5c2e7', '#cba6f7', '#94e2d5',
                  '#fab387', '#74c7ec', '#b4befe', '#f38ba8', '#eba0ac']
        
        # Draw all span curves
        for i in range(self._model.span_count):
            theta, beta = self._model.sample_span_curve(i, 100)
            color = colors[i % len(colors)]
            
            is_hub = (i == 0)
            is_tip = (i == self._model.span_count - 1)
            
            linewidth = 2.0 if (is_hub or is_tip) else 0.8
            alpha = 1.0 if (is_hub or is_tip) else 0.4
            
            label = "Hub" if is_hub else ("Tip" if is_tip else None)
            self.ax.plot(theta, beta, '-', color=color, linewidth=linewidth, alpha=alpha, label=label)
        
        # Draw 6 draggable handles
        hub_color = colors[0]
        tip_color = colors[min(self._model.span_count - 1, len(colors) - 1)]
        
        for j in range(3):
            hx, hy = self._model.hub_theta[j], self._model.hub_beta[j]
            self.ax.plot(hx, hy, 'o', color=hub_color, markersize=12,
                        markeredgecolor='white', markeredgewidth=2, zorder=10)
            
            tx, ty = self._model.tip_theta[j], self._model.tip_beta[j]
            self.ax.plot(tx, ty, 'o', color=tip_color, markersize=12,
                        markeredgecolor='white', markeredgewidth=2, zorder=10)
        
        # Draw endpoints (squares)
        for i in range(self._model.span_count):
            cps = self._model.get_span_cps(i)
            color = colors[i % len(colors)]
            alpha = 1.0 if i in [0, self._model.span_count - 1] else 0.3
            self.ax.plot(cps[0][0], cps[0][1], 's', color=color, markersize=6, alpha=alpha)
            self.ax.plot(cps[4][0], cps[4][1], 's', color=color, markersize=6, alpha=alpha)
        
        self.ax.grid(True, alpha=0.2, color='#45475a')
        self.ax.legend(loc='upper right', fontsize=8,
                      facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4')
        
        self.ax.set_xlim(-0.05, 1.05)
        self.figure.tight_layout(pad=0.5)
        self.canvas.draw()
    
    def _draw_reference_lines(self):
        """Draw reference lines for angle-locked CPs."""
        for which in ['hub', 'tip']:
            for j in [1, 3]:
                lock_idx = 0 if j == 1 else 1
                
                if which == 'hub':
                    is_locked = self._model.hub_angle_lock[lock_idx]
                else:
                    is_locked = self._model.tip_angle_lock[lock_idx]
                
                if is_locked:
                    ref = self._model.get_reference_line(which, j)
                    if ref:
                        start, end = ref
                        color = '#89b4fa' if which == 'hub' else '#a6e3a1'
                        self.ax.plot([start[0], end[0]], [start[1], end[1]], 
                                   ':', color=color, linewidth=2, alpha=0.7)
    
    def _fit_view(self):
        """Auto-scale axes."""
        all_beta = np.concatenate([self._model.beta_in, self._model.beta_out,
                                   self._model.hub_beta, self._model.tip_beta])
        if len(all_beta) > 0:
            margin = (all_beta.max() - all_beta.min()) * 0.15
            self.ax.set_ylim(all_beta.min() - margin, all_beta.max() + margin)
        self.ax.set_xlim(-0.05, 1.05)
        self.canvas.draw()
    
    def _on_span_count_changed(self, value: int):
        """Handle span count change."""
        self._model.set_span_count(value)
        self._model.apply_linear_mode()
        self._load_from_model()
        self.modelChanged.emit(self._model)
    
    def _on_linear_inlet_toggled(self, checked: bool):
        """Handle linear inlet mode toggle."""
        if self._updating:
            return
        self._model.linear_inlet = checked
        if checked:
            self._model.apply_linear_mode()
        self._load_from_model()
        self.modelChanged.emit(self._model)
    
    def _on_linear_outlet_toggled(self, checked: bool):
        """Handle linear outlet mode toggle."""
        if self._updating:
            return
        self._model.linear_outlet = checked
        if checked:
            self._model.apply_linear_mode()
        self._load_from_model()
        self.modelChanged.emit(self._model)
    
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
    
    def _on_angle_lock_changed(self, which: str, j: int, locked: bool):
        """Handle angle lock toggle."""
        if self._updating:
            return
        
        lock_idx = 0 if j == 1 else 1
        idx = j - 1  # Array index
        
        if which == 'hub':
            self._model.hub_angle_lock[lock_idx] = locked
            if locked:
                # Snap CP to reference line
                old_theta = self._model.hub_theta[idx]
                old_beta = self._model.hub_beta[idx]
                new_theta, new_beta = self._model.apply_angle_constraint(
                    'hub', j, old_theta, old_beta
                )
                self._model.hub_theta[idx] = new_theta
                self._model.hub_beta[idx] = new_beta
        else:
            self._model.tip_angle_lock[lock_idx] = locked
            if locked:
                # Snap CP to reference line
                old_theta = self._model.tip_theta[idx]
                old_beta = self._model.tip_beta[idx]
                new_theta, new_beta = self._model.apply_angle_constraint(
                    'tip', j, old_theta, old_beta
                )
                self._model.tip_theta[idx] = new_theta
                self._model.tip_beta[idx] = new_beta
        
        self._update_plot()
        self.modelChanged.emit(self._model)
    
    def _on_angle_value_changed(self, which: str, j: int, value: float):
        """Handle angle value change."""
        if self._updating:
            return
        
        lock_idx = 0 if j == 1 else 1
        if which == 'hub':
            self._model.hub_angle_value[lock_idx] = value
            if self._model.hub_angle_lock[lock_idx]:
                # Apply constraint to move CP
                idx = j - 1
                old_theta = self._model.hub_theta[idx]
                old_beta = self._model.hub_beta[idx]
                new_theta, new_beta = self._model.apply_angle_constraint(
                    'hub', j, old_theta, old_beta
                )
                self._model.hub_theta[idx] = new_theta
                self._model.hub_beta[idx] = new_beta
        else:
            self._model.tip_angle_value[lock_idx] = value
            if self._model.tip_angle_lock[lock_idx]:
                idx = j - 1
                old_theta = self._model.tip_theta[idx]
                old_beta = self._model.tip_beta[idx]
                new_theta, new_beta = self._model.apply_angle_constraint(
                    'tip', j, old_theta, old_beta
                )
                self._model.tip_theta[idx] = new_theta
                self._model.tip_beta[idx] = new_beta
        
        self._update_plot()
        self.modelChanged.emit(self._model)
    
    def _on_mouse_press(self, event):
        """Handle mouse press."""
        if event.inaxes != self.ax:
            return
        
        if event.button == 2:
            self._pan_start = (event.xdata, event.ydata)
            self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        
        if event.button == 1:
            handle = self._pick_handle(event.xdata, event.ydata)
            if handle:
                self._dragging = handle
    
    def _on_mouse_release(self, event):
        """Handle mouse release."""
        if self._pan_start:
            self._pan_start = None
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
            return
        
        if self._dragging:
            self._dragging = None
            self.modelChanged.emit(self._model)
    
    def _on_mouse_move(self, event):
        """Handle mouse move."""
        if event.inaxes != self.ax:
            return
        
        if self._pan_start:
            dx = self._pan_start[0] - event.xdata
            dy = self._pan_start[1] - event.ydata
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
            self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
            self.canvas.draw()
            return
        
        if self._dragging:
            which, j = self._dragging
            new_theta = max(0.01, min(0.99, event.xdata))
            new_beta = event.ydata
            
            # Apply angle constraint if locked
            new_theta, new_beta = self._model.apply_angle_constraint(which, j, new_theta, new_beta)
            
            if which == 'hub':
                self._model.set_hub_cp(j, new_theta, new_beta)
            else:
                self._model.set_tip_cp(j, new_theta, new_beta)
            
            self._update_plot()
    
    def _on_scroll(self, event):
        """Handle scroll zoom."""
        if event.inaxes != self.ax:
            return
        
        scale = 1.2 if event.button == 'down' else 1/1.2
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        
        self.ax.set_xlim(
            xdata - (xdata - xlim[0]) * scale,
            xdata + (xlim[1] - xdata) * scale
        )
        self.ax.set_ylim(
            ydata - (ydata - ylim[0]) * scale,
            ydata + (ylim[1] - ydata) * scale
        )
        self.canvas.draw()
    
    def _pick_handle(self, x: float, y: float) -> Optional[Tuple[str, int]]:
        """Pick a draggable handle."""
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        bbox = self.ax.get_window_extent()
        
        px_to_data_x = (xlim[1] - xlim[0]) / bbox.width
        px_to_data_y = (ylim[1] - ylim[0]) / bbox.height
        tol_x = self.PICK_TOLERANCE * px_to_data_x
        tol_y = self.PICK_TOLERANCE * px_to_data_y
        
        for j in range(3):
            hx, hy = self._model.hub_theta[j], self._model.hub_beta[j]
            if abs(x - hx) < tol_x and abs(y - hy) < tol_y:
                return ('hub', j + 1)
            
            tx, ty = self._model.tip_theta[j], self._model.tip_beta[j]
            if abs(x - tx) < tol_x and abs(y - ty) < tol_y:
                return ('tip', j + 1)
        
        return None
    
    # Public API
    def set_model(self, model: BetaDistributionModel):
        """Set a new model."""
        self._model = model
        self.span_spin.blockSignals(True)
        self.span_spin.setValue(model.span_count)
        self.span_spin.blockSignals(False)
        self._load_from_model()
    
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
