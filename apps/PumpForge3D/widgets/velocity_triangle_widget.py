"""
Velocity Triangle Widget - CFturbo 2×2 Layout with input panel.

Layout:
- Left: Vertical input panel (rpm, cm, radii, alpha, beta)
- Right: 2×2 velocity triangles (Inlet Hub/Tip, Outlet Hub/Tip)
"""

from typing import Optional
import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QLabel, QFrame, QSizePolicy
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
    2×2 velocity triangle widget with vertical input panel.
    
    Layout:
    +--------+-------------------+-------------------+
    | Inputs |   Inlet (Hub)     |   Inlet (Tip)     |
    |        +-------------------+-------------------+
    |        |   Outlet (Hub)    |   Outlet (Tip)    |
    +--------+-------------------+-------------------+
    """
    
    inputsChanged = Signal()
    
    # Colors
    COLOR_U = '#f9e2af'      # Blade speed - yellow
    COLOR_C = '#89b4fa'      # Absolute velocity - blue
    COLOR_W = '#a6e3a1'      # Relative velocity - green
    COLOR_DASHED = '#6c7086' # Dashed constructions - gray
    COLOR_ARC = '#cba6f7'    # Angle arcs - purple
    COLOR_PRIME = '#f38ba8'  # Prime/slip vectors - pink
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Inputs
        self._rpm = 3000.0
        self._cm1 = 5.0
        self._cm2 = 4.0
        self._r1_hub = 0.03
        self._r1_tip = 0.05
        self._r2_hub = 0.04
        self._r2_tip = 0.06
        self._alpha1 = 90.0
        
        # Beta values (flow angles)
        self._beta_in_hub = 25.0
        self._beta_in_tip = 30.0
        self._beta_out_hub = 55.0
        self._beta_out_tip = 60.0
        
        # Blade angles (for derivated triangles)
        self._beta_blade_in_hub = 20.0
        self._beta_blade_in_tip = 25.0
        self._beta_blade_out_hub = 50.0
        self._beta_blade_out_tip = 55.0
        
        self._setup_ui()
        self._connect_signals()
        self._update_all()
    
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)
        
        # Left: Vertical input panel
        input_panel = QFrame()
        input_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        input_panel.setMaximumWidth(200)
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)
        
        # Machine parameters
        machine_group = QGroupBox("Machine")
        machine_form = QFormLayout(machine_group)
        machine_form.setSpacing(4)
        
        self.rpm_spin = QDoubleSpinBox()
        self.rpm_spin.setRange(100, 50000)
        self.rpm_spin.setValue(self._rpm)
        self.rpm_spin.setSuffix(" rpm")
        machine_form.addRow("n:", self.rpm_spin)
        
        self.alpha1_spin = QDoubleSpinBox()
        self.alpha1_spin.setRange(0, 180)
        self.alpha1_spin.setValue(self._alpha1)
        self.alpha1_spin.setSuffix("°")
        machine_form.addRow("α₁:", self.alpha1_spin)
        
        input_layout.addWidget(machine_group)
        
        # Meridional velocities
        vel_group = QGroupBox("Velocities")
        vel_form = QFormLayout(vel_group)
        vel_form.setSpacing(4)
        
        self.cm1_spin = QDoubleSpinBox()
        self.cm1_spin.setRange(0.1, 100)
        self.cm1_spin.setValue(self._cm1)
        self.cm1_spin.setSuffix(" m/s")
        vel_form.addRow("cm₁:", self.cm1_spin)
        
        self.cm2_spin = QDoubleSpinBox()
        self.cm2_spin.setRange(0.1, 100)
        self.cm2_spin.setValue(self._cm2)
        self.cm2_spin.setSuffix(" m/s")
        vel_form.addRow("cm₂:", self.cm2_spin)
        
        input_layout.addWidget(vel_group)
        
        # Radii
        radii_group = QGroupBox("Radii (m)")
        radii_form = QFormLayout(radii_group)
        radii_form.setSpacing(4)
        
        for name, attr, default in [
            ("r₁h:", "_r1_hub", 0.03), ("r₁t:", "_r1_tip", 0.05),
            ("r₂h:", "_r2_hub", 0.04), ("r₂t:", "_r2_tip", 0.06)
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(0.001, 10)
            spin.setDecimals(3)
            spin.setValue(default)
            setattr(self, f"{attr}_spin", spin)
            radii_form.addRow(name, spin)
        
        input_layout.addWidget(radii_group)
        
        # Flow angles (beta)
        beta_group = QGroupBox("Flow Angles β")
        beta_form = QFormLayout(beta_group)
        beta_form.setSpacing(4)
        
        for name, attr in [
            ("β₁ hub:", "_beta_in_hub"), ("β₁ tip:", "_beta_in_tip"),
            ("β₂ hub:", "_beta_out_hub"), ("β₂ tip:", "_beta_out_tip")
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(0, 90)
            spin.setValue(getattr(self, attr))
            spin.setSuffix("°")
            setattr(self, f"{attr}_spin", spin)
            beta_form.addRow(name, spin)
        
        input_layout.addWidget(beta_group)
        
        # Blade angles (beta_B)
        blade_group = QGroupBox("Blade Angles βB")
        blade_form = QFormLayout(blade_group)
        blade_form.setSpacing(4)
        
        for name, attr in [
            ("βB₁ hub:", "_beta_blade_in_hub"), ("βB₁ tip:", "_beta_blade_in_tip"),
            ("βB₂ hub:", "_beta_blade_out_hub"), ("βB₂ tip:", "_beta_blade_out_tip")
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(0, 90)
            spin.setValue(getattr(self, attr))
            spin.setSuffix("°")
            setattr(self, f"{attr}_spin", spin)
            blade_form.addRow(name, spin)
        
        input_layout.addWidget(blade_group)
        
        input_layout.addStretch()
        main_layout.addWidget(input_panel)
        
        # Right: 2×2 grid of triangle panels
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(4)
        
        # Create 4 panels
        self.inlet_hub_fig = Figure(figsize=(5, 4), dpi=100, facecolor='#181825')
        self.inlet_hub_canvas = FigureCanvas(self.inlet_hub_fig)
        inlet_hub_group = self._create_panel("Inlet (Hub)", self.inlet_hub_canvas)
        grid_layout.addWidget(inlet_hub_group, 0, 0)
        
        self.inlet_tip_fig = Figure(figsize=(5, 4), dpi=100, facecolor='#181825')
        self.inlet_tip_canvas = FigureCanvas(self.inlet_tip_fig)
        inlet_tip_group = self._create_panel("Inlet (Tip)", self.inlet_tip_canvas)
        grid_layout.addWidget(inlet_tip_group, 0, 1)
        
        self.outlet_hub_fig = Figure(figsize=(5, 4), dpi=100, facecolor='#181825')
        self.outlet_hub_canvas = FigureCanvas(self.outlet_hub_fig)
        outlet_hub_group = self._create_panel("Outlet (Hub)", self.outlet_hub_canvas)
        grid_layout.addWidget(outlet_hub_group, 1, 0)
        
        self.outlet_tip_fig = Figure(figsize=(5, 4), dpi=100, facecolor='#181825')
        self.outlet_tip_canvas = FigureCanvas(self.outlet_tip_fig)
        outlet_tip_group = self._create_panel("Outlet (Tip)", self.outlet_tip_canvas)
        grid_layout.addWidget(outlet_tip_group, 1, 1)
        
        grid_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(grid_widget, 1)
    
    def _create_panel(self, title: str, canvas) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(2, 8, 2, 2)
        canvas.setStyleSheet("background-color: #181825;")
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(canvas)
        return group
    
    def _connect_signals(self):
        # Connect all spinboxes
        for spin in [self.rpm_spin, self.alpha1_spin, self.cm1_spin, self.cm2_spin]:
            spin.valueChanged.connect(self._on_input_changed)
        
        for attr in ["_r1_hub", "_r1_tip", "_r2_hub", "_r2_tip"]:
            getattr(self, f"{attr}_spin").valueChanged.connect(self._on_input_changed)
        
        for attr in ["_beta_in_hub", "_beta_in_tip", "_beta_out_hub", "_beta_out_tip",
                     "_beta_blade_in_hub", "_beta_blade_in_tip", "_beta_blade_out_hub", "_beta_blade_out_tip"]:
            getattr(self, f"{attr}_spin").valueChanged.connect(self._on_input_changed)
    
    def _on_input_changed(self):
        # Read all values
        self._rpm = self.rpm_spin.value()
        self._alpha1 = self.alpha1_spin.value()
        self._cm1 = self.cm1_spin.value()
        self._cm2 = self.cm2_spin.value()
        
        for attr in ["_r1_hub", "_r1_tip", "_r2_hub", "_r2_tip"]:
            setattr(self, attr, getattr(self, f"{attr}_spin").value())
        
        for attr in ["_beta_in_hub", "_beta_in_tip", "_beta_out_hub", "_beta_out_tip",
                     "_beta_blade_in_hub", "_beta_blade_in_tip", "_beta_blade_out_hub", "_beta_blade_out_tip"]:
            setattr(self, attr, getattr(self, f"{attr}_spin").value())
        
        self._update_all()
        self.inputsChanged.emit()
    
    def _update_all(self):
        # Compute all 4 triangles
        inlet_hub = compute_triangle(self._beta_in_hub, self._r1_hub, self._rpm, self._cm1, self._alpha1, use_beta=False)
        inlet_tip = compute_triangle(self._beta_in_tip, self._r1_tip, self._rpm, self._cm1, self._alpha1, use_beta=False)
        outlet_hub = compute_triangle(self._beta_out_hub, self._r2_hub, self._rpm, self._cm2, 90.0, use_beta=True)
        outlet_tip = compute_triangle(self._beta_out_tip, self._r2_tip, self._rpm, self._cm2, 90.0, use_beta=True)
        
        # Draw each panel with derivated triangles
        self._draw_inlet(self.inlet_hub_fig, inlet_hub, self._beta_blade_in_hub)
        self._draw_inlet(self.inlet_tip_fig, inlet_tip, self._beta_blade_in_tip)
        self._draw_outlet(self.outlet_hub_fig, outlet_hub, self._beta_blade_out_hub)
        self._draw_outlet(self.outlet_tip_fig, outlet_tip, self._beta_blade_out_tip)
        
        for canvas in [self.inlet_hub_canvas, self.inlet_tip_canvas, 
                       self.outlet_hub_canvas, self.outlet_tip_canvas]:
            canvas.draw()
    
    def _draw_inlet(self, fig: Figure, tri: TriangleData, beta_blade: float):
        """Draw inlet triangle with derivated elements (w', c', i')."""
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor('#1e1e2e')
        for spine in ax.spines.values():
            spine.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=7)
        
        # Base triangle layout
        wu = tri.wu
        origin = np.array([0, 0])
        u_end = np.array([tri.u, 0])
        apex = np.array([wu, tri.cm])
        
        # Draw baseline u₁
        self._draw_baseline(ax, origin, u_end, 'u₁', self.COLOR_U)
        
        # Draw main vectors (solid)
        self._draw_arrow(ax, origin, apex, self.COLOR_W, '-', 1.8)
        self._label_on_vector(ax, origin, apex, 'w₁', self.COLOR_W)
        
        self._draw_arrow(ax, u_end, apex, self.COLOR_C, '-', 1.8)
        self._label_on_vector(ax, u_end, apex, 'c₁', self.COLOR_C)
        
        # Derivated triangle: w₁' at blade angle β₁B
        beta_b_rad = math.radians(beta_blade)
        wu_prime = tri.cm / math.tan(beta_b_rad) if abs(math.tan(beta_b_rad)) > 0.01 else tri.cm * 100
        apex_prime = np.array([wu_prime, tri.cm])
        
        # Draw w₁' (dashed)
        self._draw_arrow(ax, origin, apex_prime, self.COLOR_PRIME, '--', 1.2)
        self._label_on_vector(ax, origin, apex_prime, "w₁'", self.COLOR_PRIME)
        
        # Draw c₁' (dashed) from u_end to apex_prime
        self._draw_arrow(ax, u_end, apex_prime, self.COLOR_PRIME, '--', 1.2)
        self._label_on_vector(ax, u_end, apex_prime, "c₁'", self.COLOR_PRIME)
        
        # Component spans
        if abs(wu) > 0.1:
            ax.annotate('', xy=(wu, -2), xytext=(0, -2),
                       arrowprops=dict(arrowstyle='<->', color=self.COLOR_DASHED, lw=0.8))
            ax.text(wu/2, -3.5, 'w₁u', fontsize=9, color=self.COLOR_W, ha='center')
        
        cu_val = tri.u - wu
        if abs(cu_val) > 0.1:
            ax.annotate('', xy=(tri.u, -2), xytext=(wu, -2),
                       arrowprops=dict(arrowstyle='<->', color=self.COLOR_DASHED, lw=0.8))
            ax.text((wu + tri.u)/2, -3.5, 'c₁u', fontsize=9, color=self.COLOR_C, ha='center')
        
        # cm span (vertical)
        ax.annotate('', xy=(tri.u + 2, tri.cm), xytext=(tri.u + 2, 0),
                   arrowprops=dict(arrowstyle='<->', color=self.COLOR_DASHED, lw=0.8))
        ax.text(tri.u + 3, tri.cm/2, 'c₁m', fontsize=9, color=self.COLOR_C, ha='left', va='center')
        
        # Vertical reference line
        ax.axvline(apex[0], color=self.COLOR_DASHED, ls='--', lw=0.5, alpha=0.5)
        
        # Angle arcs
        arc_r = min(tri.u, tri.cm) * 0.15
        if arc_r < 1:
            arc_r = 1
        
        # β₁: flow angle (solid) at origin
        beta_flow = math.degrees(math.atan2(tri.cm, wu)) if abs(wu) > 0.01 else 90
        arc = Arc(origin, arc_r*2, arc_r*2, angle=0, theta1=0, theta2=beta_flow,
                 color=self.COLOR_ARC, lw=1.0)
        ax.add_patch(arc)
        mid = math.radians(beta_flow/2)
        ax.text(arc_r*1.3*math.cos(mid), arc_r*1.3*math.sin(mid), 'β₁', 
               fontsize=10, color=self.COLOR_ARC, fontweight='bold')
        
        # β₁B: blade angle (dashed arc)
        beta_b_deg = beta_blade
        arc_b = Arc(origin, arc_r*2.5, arc_r*2.5, angle=0, theta1=0, theta2=beta_b_deg,
                   color=self.COLOR_PRIME, lw=1.0, ls='--')
        ax.add_patch(arc_b)
        mid_b = math.radians(beta_b_deg/2)
        ax.text(arc_r*2.8*math.cos(mid_b), arc_r*2.8*math.sin(mid_b), 'β₁B', 
               fontsize=9, color=self.COLOR_PRIME)
        
        # i₁': incidence angle (between β₁B and β₁)
        if abs(beta_flow - beta_b_deg) > 1:
            theta1, theta2 = min(beta_b_deg, beta_flow), max(beta_b_deg, beta_flow)
            arc_i = Arc(origin, arc_r*1.8, arc_r*1.8, angle=0, theta1=theta1, theta2=theta2,
                       color='#fab387', lw=1.5)
            ax.add_patch(arc_i)
            mid_i = math.radians((theta1 + theta2)/2)
            ax.text(arc_r*2*math.cos(mid_i), arc_r*2*math.sin(mid_i), "i₁'", 
                   fontsize=9, color='#fab387', fontweight='bold')
        
        self._finalize_ax(ax, origin, u_end, apex, apex_prime)
    
    def _draw_outlet(self, fig: Figure, tri: TriangleData, beta_blade: float):
        """Draw outlet triangle with derivated elements (w', c', δ')."""
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_facecolor('#1e1e2e')
        for spine in ax.spines.values():
            spine.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=7)
        
        # Base triangle layout
        wu = tri.wu
        origin = np.array([0, 0])
        u_end = np.array([tri.u, 0])
        apex = np.array([wu, tri.cm])
        
        # Draw baseline u₂
        self._draw_baseline(ax, origin, u_end, 'u₂', self.COLOR_U)
        
        # Draw main vectors (solid)
        self._draw_arrow(ax, origin, apex, self.COLOR_W, '-', 1.8)
        self._label_on_vector(ax, origin, apex, 'w₂', self.COLOR_W)
        
        self._draw_arrow(ax, u_end, apex, self.COLOR_C, '-', 1.8)
        self._label_on_vector(ax, u_end, apex, 'c₂', self.COLOR_C)
        
        # Derivated triangle: w₂' at blade angle β₂B
        beta_b_rad = math.radians(beta_blade)
        wu_prime = tri.cm / math.tan(beta_b_rad) if abs(math.tan(beta_b_rad)) > 0.01 else tri.cm * 100
        apex_prime = np.array([wu_prime, tri.cm])
        
        # Draw w₂' (dashed)
        self._draw_arrow(ax, origin, apex_prime, self.COLOR_PRIME, '--', 1.2)
        self._label_on_vector(ax, origin, apex_prime, "w₂'", self.COLOR_PRIME)
        
        # Draw c₂' (dashed)
        self._draw_arrow(ax, u_end, apex_prime, self.COLOR_PRIME, '--', 1.2)
        self._label_on_vector(ax, u_end, apex_prime, "c₂'", self.COLOR_PRIME)
        
        # Component spans
        if abs(wu) > 0.1:
            ax.annotate('', xy=(wu, -2), xytext=(0, -2),
                       arrowprops=dict(arrowstyle='<->', color=self.COLOR_DASHED, lw=0.8))
            ax.text(wu/2, -3.5, 'w₂u', fontsize=9, color=self.COLOR_W, ha='center')
        
        cu_val = tri.u - wu
        if abs(cu_val) > 0.1:
            ax.annotate('', xy=(tri.u, -2), xytext=(wu, -2),
                       arrowprops=dict(arrowstyle='<->', color=self.COLOR_DASHED, lw=0.8))
            ax.text((wu + tri.u)/2, -3.5, 'c₂u', fontsize=9, color=self.COLOR_C, ha='center')
        
        # cm span
        ax.annotate('', xy=(tri.u + 2, tri.cm), xytext=(tri.u + 2, 0),
                   arrowprops=dict(arrowstyle='<->', color=self.COLOR_DASHED, lw=0.8))
        ax.text(tri.u + 3, tri.cm/2, 'c₂m', fontsize=9, color=self.COLOR_C, ha='left', va='center')
        
        # Vertical reference line
        ax.axvline(apex[0], color=self.COLOR_DASHED, ls='--', lw=0.5, alpha=0.5)
        
        # Angle arcs
        arc_r = min(tri.u, tri.cm) * 0.15
        if arc_r < 1:
            arc_r = 1
        
        # β₂: flow angle at origin
        beta_flow = math.degrees(math.atan2(tri.cm, wu)) if abs(wu) > 0.01 else 90
        arc = Arc(origin, arc_r*2, arc_r*2, angle=0, theta1=0, theta2=beta_flow,
                 color=self.COLOR_ARC, lw=1.0)
        ax.add_patch(arc)
        mid = math.radians(beta_flow/2)
        ax.text(arc_r*1.3*math.cos(mid), arc_r*1.3*math.sin(mid), 'β₂', 
               fontsize=10, color=self.COLOR_ARC, fontweight='bold')
        
        # β₂B: blade angle
        beta_b_deg = beta_blade
        arc_b = Arc(origin, arc_r*2.5, arc_r*2.5, angle=0, theta1=0, theta2=beta_b_deg,
                   color=self.COLOR_PRIME, lw=1.0, ls='--')
        ax.add_patch(arc_b)
        mid_b = math.radians(beta_b_deg/2)
        ax.text(arc_r*2.8*math.cos(mid_b), arc_r*2.8*math.sin(mid_b), 'β₂B', 
               fontsize=9, color=self.COLOR_PRIME)
        
        # δ': deviation/slip angle
        if abs(beta_flow - beta_b_deg) > 1:
            theta1, theta2 = min(beta_b_deg, beta_flow), max(beta_b_deg, beta_flow)
            arc_d = Arc(origin, arc_r*1.8, arc_r*1.8, angle=0, theta1=theta1, theta2=theta2,
                       color='#fab387', lw=1.5)
            ax.add_patch(arc_d)
            mid_d = math.radians((theta1 + theta2)/2)
            ax.text(arc_r*2*math.cos(mid_d), arc_r*2*math.sin(mid_d), "δ'", 
                   fontsize=9, color='#fab387', fontweight='bold')
        
        self._finalize_ax(ax, origin, u_end, apex, apex_prime)
    
    def _draw_baseline(self, ax, start, end, label, color):
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=color, lw=2.0, shrinkA=0, shrinkB=0))
        mid = (start + end) / 2
        ax.text(mid[0], mid[1], label, fontsize=11, color=color, 
               ha='center', va='center', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.1', facecolor='#1e1e2e', edgecolor='none', alpha=0.8))
    
    def _draw_arrow(self, ax, start, end, color, ls, lw):
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', color=color, lw=lw, linestyle=ls, shrinkA=0, shrinkB=0))
    
    def _label_on_vector(self, ax, start, end, label, color):
        mid = (start + end) / 2
        ax.text(mid[0], mid[1], label, fontsize=10, color=color, 
               ha='center', va='center', fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.1', facecolor='#1e1e2e', edgecolor='none', alpha=0.8))
    
    def _finalize_ax(self, ax, origin, u_end, apex, apex_prime=None):
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.15, color='#45475a', lw=0.3)
        ax.axhline(0, color='#45475a', lw=0.5)
        
        # Bounds from all points
        all_x = [origin[0], u_end[0], apex[0]]
        all_y = [origin[1], u_end[1], apex[1]]
        if apex_prime is not None:
            all_x.append(apex_prime[0])
            all_y.append(apex_prime[1])
        
        x_min, x_max = min(all_x), max(all_x)
        y_min, y_max = min(all_y), max(all_y)
        
        x_margin = (x_max - x_min) * 0.2 + 5
        y_margin = (y_max - y_min) * 0.2 + 2
        
        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin - 5, y_max + y_margin)


# Demo
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 11px; }
        QGroupBox { border: 1px solid #45475a; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 2px; }
        QFrame { background-color: #181825; border-radius: 4px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Velocity Triangles - Derivated (w', c', δ', i')")
    window.resize(1200, 700)
    
    widget = VelocityTriangleWidget()
    window.setCentralWidget(widget)
    
    window.show()
    sys.exit(app.exec())
