"""
Velocity Triangle Widget - Improved.

Shows inlet and outlet velocity triangles for hub and tip endpoints.
- Alpha input (default 90° = no preswirl)
- Hub/tip offset for readability
- Angle arcs for α and β
- Minimum aspect ratio
- Thinner lines
"""

from typing import Optional, Tuple
import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QCheckBox, QToolButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import Arc

from pumpforge3d_core.analysis.velocity_triangle import (
    TriangleData, compute_triangle
)


class VelocityTriangleWidget(QWidget):
    """
    Widget showing velocity triangles for inlet and outlet.
    
    Signals:
        inputsChanged: Emitted when mock inputs change
    """
    
    inputsChanged = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Mock inputs
        self._rpm = 3000.0
        self._cm1 = 5.0
        self._cm2 = 4.0
        self._r1_hub = 0.03
        self._r1_tip = 0.05
        self._r2_hub = 0.04
        self._r2_tip = 0.06
        self._alpha1 = 90.0  # Inlet flow angle (90° = no preswirl)
        
        # Beta values from table
        self._beta_in_hub = 20.0
        self._beta_in_tip = 25.0
        self._beta_out_hub = 50.0
        self._beta_out_tip = 55.0
        
        # Display options
        self._show_components = True
        self._show_angles = True
        
        self._setup_ui()
        self._connect_signals()
        self._update_triangles()
    
    def _setup_ui(self):
        """Create the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        
        # Top: Mock inputs panel
        inputs_group = QGroupBox("Triangle Inputs")
        inputs_layout = QHBoxLayout(inputs_group)
        inputs_layout.setSpacing(8)
        
        # RPM
        rpm_layout = QFormLayout()
        self.rpm_spin = QDoubleSpinBox()
        self.rpm_spin.setRange(100, 50000)
        self.rpm_spin.setValue(self._rpm)
        self.rpm_spin.setSuffix(" rpm")
        rpm_layout.addRow("n:", self.rpm_spin)
        inputs_layout.addLayout(rpm_layout)
        
        # Alpha1 (inlet flow angle)
        alpha_layout = QFormLayout()
        self.alpha1_spin = QDoubleSpinBox()
        self.alpha1_spin.setRange(0, 180)
        self.alpha1_spin.setValue(90)
        self.alpha1_spin.setSuffix("°")
        self.alpha1_spin.setToolTip("Inlet flow angle (90° = no preswirl)")
        alpha_layout.addRow("α₁:", self.alpha1_spin)
        inputs_layout.addLayout(alpha_layout)
        
        # Meridional velocities
        cm_layout = QFormLayout()
        self.cm1_spin = QDoubleSpinBox()
        self.cm1_spin.setRange(0.1, 100)
        self.cm1_spin.setValue(self._cm1)
        self.cm1_spin.setSuffix(" m/s")
        cm_layout.addRow("cm₁:", self.cm1_spin)
        
        self.cm2_spin = QDoubleSpinBox()
        self.cm2_spin.setRange(0.1, 100)
        self.cm2_spin.setValue(self._cm2)
        self.cm2_spin.setSuffix(" m/s")
        cm_layout.addRow("cm₂:", self.cm2_spin)
        inputs_layout.addLayout(cm_layout)
        
        # Inlet radii
        r1_layout = QFormLayout()
        self.r1_hub_spin = QDoubleSpinBox()
        self.r1_hub_spin.setRange(0.001, 10)
        self.r1_hub_spin.setDecimals(3)
        self.r1_hub_spin.setValue(self._r1_hub)
        self.r1_hub_spin.setSuffix(" m")
        r1_layout.addRow("r₁h:", self.r1_hub_spin)
        
        self.r1_tip_spin = QDoubleSpinBox()
        self.r1_tip_spin.setRange(0.001, 10)
        self.r1_tip_spin.setDecimals(3)
        self.r1_tip_spin.setValue(self._r1_tip)
        self.r1_tip_spin.setSuffix(" m")
        r1_layout.addRow("r₁t:", self.r1_tip_spin)
        inputs_layout.addLayout(r1_layout)
        
        # Outlet radii
        r2_layout = QFormLayout()
        self.r2_hub_spin = QDoubleSpinBox()
        self.r2_hub_spin.setRange(0.001, 10)
        self.r2_hub_spin.setDecimals(3)
        self.r2_hub_spin.setValue(self._r2_hub)
        self.r2_hub_spin.setSuffix(" m")
        r2_layout.addRow("r₂h:", self.r2_hub_spin)
        
        self.r2_tip_spin = QDoubleSpinBox()
        self.r2_tip_spin.setRange(0.001, 10)
        self.r2_tip_spin.setDecimals(3)
        self.r2_tip_spin.setValue(self._r2_tip)
        self.r2_tip_spin.setSuffix(" m")
        r2_layout.addRow("r₂t:", self.r2_tip_spin)
        inputs_layout.addLayout(r2_layout)
        
        main_layout.addWidget(inputs_group)
        
        # Options bar
        options_layout = QHBoxLayout()
        
        self.show_comp_check = QCheckBox("Components")
        self.show_comp_check.setChecked(True)
        options_layout.addWidget(self.show_comp_check)
        
        self.show_angles_check = QCheckBox("Angles")
        self.show_angles_check.setChecked(True)
        options_layout.addWidget(self.show_angles_check)
        
        options_layout.addStretch()
        
        fit_btn = QToolButton()
        fit_btn.setText("⤢ Fit")
        fit_btn.clicked.connect(self._fit_view)
        options_layout.addWidget(fit_btn)
        
        main_layout.addLayout(options_layout)
        
        # Triangle panels
        triangles_layout = QHBoxLayout()
        triangles_layout.setSpacing(8)
        
        # Inlet
        inlet_group = QGroupBox("Inlet Triangle (1)")
        inlet_layout = QVBoxLayout(inlet_group)
        inlet_layout.setContentsMargins(2, 2, 2, 2)
        self.inlet_figure = Figure(figsize=(4, 3), dpi=100, facecolor='#181825')
        self.inlet_canvas = FigureCanvas(self.inlet_figure)
        self.inlet_canvas.setStyleSheet("background-color: #181825;")
        inlet_layout.addWidget(self.inlet_canvas)
        triangles_layout.addWidget(inlet_group)
        
        # Outlet
        outlet_group = QGroupBox("Outlet Triangle (2)")
        outlet_layout = QVBoxLayout(outlet_group)
        outlet_layout.setContentsMargins(2, 2, 2, 2)
        self.outlet_figure = Figure(figsize=(4, 3), dpi=100, facecolor='#181825')
        self.outlet_canvas = FigureCanvas(self.outlet_figure)
        self.outlet_canvas.setStyleSheet("background-color: #181825;")
        outlet_layout.addWidget(self.outlet_canvas)
        triangles_layout.addWidget(outlet_group)
        
        main_layout.addLayout(triangles_layout, 1)
        
        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #a6adc8; font-size: 9px;")
        main_layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """Connect signals."""
        self.rpm_spin.valueChanged.connect(self._on_input_changed)
        self.alpha1_spin.valueChanged.connect(self._on_input_changed)
        self.cm1_spin.valueChanged.connect(self._on_input_changed)
        self.cm2_spin.valueChanged.connect(self._on_input_changed)
        self.r1_hub_spin.valueChanged.connect(self._on_input_changed)
        self.r1_tip_spin.valueChanged.connect(self._on_input_changed)
        self.r2_hub_spin.valueChanged.connect(self._on_input_changed)
        self.r2_tip_spin.valueChanged.connect(self._on_input_changed)
        
        self.show_comp_check.toggled.connect(lambda: self._update_triangles())
        self.show_angles_check.toggled.connect(lambda: self._update_triangles())
    
    def _on_input_changed(self):
        """Handle input changes."""
        self._rpm = self.rpm_spin.value()
        self._alpha1 = self.alpha1_spin.value()
        self._cm1 = self.cm1_spin.value()
        self._cm2 = self.cm2_spin.value()
        self._r1_hub = self.r1_hub_spin.value()
        self._r1_tip = self.r1_tip_spin.value()
        self._r2_hub = self.r2_hub_spin.value()
        self._r2_tip = self.r2_tip_spin.value()
        
        self._update_triangles()
        self.inputsChanged.emit()
    
    def set_beta_values(self, beta_in_hub: float, beta_in_tip: float,
                       beta_out_hub: float, beta_out_tip: float):
        """Set beta values from external source."""
        self._beta_in_hub = beta_in_hub
        self._beta_in_tip = beta_in_tip
        self._beta_out_hub = beta_out_hub
        self._beta_out_tip = beta_out_tip
        self._update_triangles()
    
    def _update_triangles(self):
        """Recompute and redraw triangles."""
        # Compute triangles
        inlet_hub = compute_triangle(self._beta_in_hub, self._r1_hub, self._rpm, self._cm1, self._alpha1)
        inlet_tip = compute_triangle(self._beta_in_tip, self._r1_tip, self._rpm, self._cm1, self._alpha1)
        outlet_hub = compute_triangle(self._beta_out_hub, self._r2_hub, self._rpm, self._cm2, 90.0)
        outlet_tip = compute_triangle(self._beta_out_tip, self._r2_tip, self._rpm, self._cm2, 90.0)
        
        # Draw
        self._draw_triangle_panel(self.inlet_figure, inlet_hub, inlet_tip, "Inlet")
        self._draw_triangle_panel(self.outlet_figure, outlet_hub, outlet_tip, "Outlet")
        
        self.inlet_canvas.draw()
        self.outlet_canvas.draw()
        
        # Update info
        self.info_label.setText(
            f"β: Hub in={self._beta_in_hub:.1f}° out={self._beta_out_hub:.1f}° | "
            f"Tip in={self._beta_in_tip:.1f}° out={self._beta_out_tip:.1f}°"
        )
    
    def _draw_triangle_panel(self, figure: Figure, hub: TriangleData, tip: TriangleData, title: str):
        """Draw a triangle panel."""
        figure.clear()
        ax = figure.add_subplot(111)
        ax.set_facecolor('#1e1e2e')
        
        for spine in ax.spines.values():
            spine.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=7)
        
        hub_color = '#89b4fa'
        tip_color = '#a6e3a1'
        
        # Offset tip triangle slightly for readability
        hub_offset = np.array([0, 0])
        tip_offset = np.array([0, hub.cm * 0.15])  # Offset tip upward
        
        # Draw hub (solid)
        self._draw_single_triangle(ax, hub, hub_offset, hub_color, '-', 'Hub')
        
        # Draw tip (dashed, offset)
        self._draw_single_triangle(ax, tip, tip_offset, tip_color, '--', 'Tip')
        
        # Legend
        ax.plot([], [], '-', color=hub_color, linewidth=1.5, label='Hub')
        ax.plot([], [], '--', color=tip_color, linewidth=1.5, label='Tip')
        ax.legend(loc='upper right', fontsize=7, facecolor='#313244', 
                 edgecolor='#45475a', labelcolor='#cdd6f4')
        
        # Set aspect with minimum ratio
        ax.set_aspect('equal')
        
        # Ensure minimum plot area
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        
        # Ensure y_range is at least 0.4 * x_range (avoid flat triangles)
        min_y_ratio = 0.4
        if y_range < x_range * min_y_ratio:
            center_y = (ylim[0] + ylim[1]) / 2
            new_y_range = x_range * min_y_ratio
            ax.set_ylim(center_y - new_y_range/2, center_y + new_y_range/2)
        
        ax.grid(True, alpha=0.15, color='#45475a', linewidth=0.5)
        ax.set_xlabel('Circumferential [m/s]', fontsize=7, color='#a6adc8')
        ax.set_ylabel('Meridional [m/s]', fontsize=7, color='#a6adc8')
        
        figure.tight_layout(pad=0.3)
    
    def _draw_single_triangle(self, ax, tri: TriangleData, offset: np.ndarray,
                             color: str, linestyle: str, label: str):
        """Draw a single velocity triangle."""
        origin = offset.copy()
        
        # u: blade speed (horizontal)
        u_end = origin + np.array([tri.u, 0])
        
        # c: absolute velocity from origin
        c_end = origin + np.array([tri.cu, tri.cm])
        
        # w: relative velocity (from u_end to c_end)
        # w = c - u vectorially
        
        # Draw main vectors (thin lines)
        lw = 1.0 if linestyle == '-' else 0.8
        
        # u vector
        self._draw_vector(ax, origin, u_end, color, linestyle, lw, 'u', label)
        
        # c vector
        self._draw_vector(ax, origin, c_end, color, linestyle, lw, 'c', label)
        
        # w vector (from u_end)
        self._draw_vector(ax, u_end, c_end, color, linestyle, lw, 'w', label)
        
        # Components
        show_comp = self.show_comp_check.isChecked()
        if show_comp:
            # cu component (only if non-zero)
            if abs(tri.cu) > 0.1:
                cu_end = origin + np.array([tri.cu, 0])
                ax.plot([origin[0], cu_end[0]], [origin[1], cu_end[1]], 
                       ':', color=color, linewidth=0.5, alpha=0.6)
                ax.text(cu_end[0] - 0.5, cu_end[1] - 0.3, 'cu', fontsize=6, 
                       color=color, alpha=0.7)
            
            # cm component
            cm_start = origin + np.array([tri.cu, 0])
            ax.plot([cm_start[0], c_end[0]], [cm_start[1], c_end[1]], 
                   ':', color=color, linewidth=0.5, alpha=0.6)
            
            # wu component (only if visible)
            if abs(tri.wu) > 0.1:
                wu_end = u_end + np.array([tri.cu - tri.u, 0])
                ax.plot([u_end[0], wu_end[0]], [u_end[1], wu_end[1]], 
                       ':', color=color, linewidth=0.5, alpha=0.6)
        
        # Angle arcs
        show_angles = self.show_angles_check.isChecked()
        if show_angles:
            arc_radius = min(tri.c, tri.w, tri.u) * 0.15
            
            # Alpha arc (at origin, between u-direction and c)
            if abs(tri.cu) > 0.1 and tri.alpha < 89:
                alpha_arc = Arc(origin, arc_radius*2, arc_radius*2,
                              angle=0, theta1=0, theta2=tri.alpha,
                              color=color, linewidth=0.5, linestyle=linestyle)
                ax.add_patch(alpha_arc)
                ax.text(origin[0] + arc_radius*1.5, origin[1] + arc_radius*0.5, 
                       f'α={tri.alpha:.0f}°', fontsize=5, color=color, alpha=0.8)
            
            # Beta arc (at u_end, angle of w from horizontal)
            beta_angle = math.degrees(math.atan2(tri.cm, tri.cu - tri.u))
            if beta_angle < 0:
                beta_angle += 180
            beta_arc = Arc(u_end, arc_radius*2, arc_radius*2,
                          angle=0, theta1=0, theta2=beta_angle,
                          color=color, linewidth=0.5, linestyle=linestyle)
            ax.add_patch(beta_arc)
            ax.text(u_end[0] - arc_radius*2, u_end[1] + arc_radius*0.5, 
                   f'β={tri.beta:.0f}°', fontsize=5, color=color, alpha=0.8)
    
    def _draw_vector(self, ax, start: np.ndarray, end: np.ndarray, 
                    color: str, linestyle: str, linewidth: float, 
                    name: str, triangle_label: str):
        """Draw a vector with arrowhead and label."""
        # Line
        ax.plot([start[0], end[0]], [start[1], end[1]], 
               linestyle=linestyle, color=color, linewidth=linewidth)
        
        # Arrowhead
        direction = end - start
        length = np.linalg.norm(direction)
        if length > 0.1:
            direction = direction / length
            arrow_size = length * 0.08
            perp = np.array([-direction[1], direction[0]])
            arrow_pos = end - direction * arrow_size
            ax.plot([end[0], arrow_pos[0] + perp[0]*arrow_size*0.4],
                   [end[1], arrow_pos[1] + perp[1]*arrow_size*0.4],
                   linestyle='-', color=color, linewidth=linewidth)
            ax.plot([end[0], arrow_pos[0] - perp[0]*arrow_size*0.4],
                   [end[1], arrow_pos[1] - perp[1]*arrow_size*0.4],
                   linestyle='-', color=color, linewidth=linewidth)
        
        # Label at midpoint
        mid = (start + end) / 2
        # Offset perpendicular to vector
        if length > 0.1:
            perp = np.array([-direction[1], direction[0]])
            label_pos = mid + perp * length * 0.1
            ax.text(label_pos[0], label_pos[1], name, fontsize=7, 
                   color=color, ha='center', va='center', fontweight='bold')
    
    def _fit_view(self):
        """Auto-fit views."""
        self._update_triangles()


# Standalone demo
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 11px; }
        QGroupBox { border: 1px solid #45475a; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 2px; }
        QToolButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 4px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Velocity Triangles - Improved")
    window.resize(900, 450)
    
    widget = VelocityTriangleWidget()
    window.setCentralWidget(widget)
    
    window.show()
    sys.exit(app.exec())
