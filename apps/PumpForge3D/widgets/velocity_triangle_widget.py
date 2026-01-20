"""
Velocity Triangle Widget - 2×2 Subplots with unified axis limits.

All 4 subplots have the same xlim and ylim based on maximum vector sizes.
"""

import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import Arc
from matplotlib.lines import Line2D

from pumpforge3d_core.analysis.velocity_triangle import (
    TriangleData, compute_triangle
)


class VelocityTriangleWidget(QWidget):
    """2×2 subplot velocity triangle widget with unified axis limits."""
    
    inputsChanged = Signal()
    
    # Colors
    COLOR_U = '#f9e2af'      # Blade speed - yellow
    COLOR_C = '#89b4fa'      # Absolute velocity - blue
    COLOR_W = '#a6e3a1'      # Relative velocity - green
    
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
        
        self._beta_in_hub = 25.0
        self._beta_in_tip = 30.0
        self._beta_out_hub = 55.0
        self._beta_out_tip = 60.0
        
        self._beta_blade_in_hub = 30.0
        self._beta_blade_in_tip = 35.0
        self._beta_blade_out_hub = 60.0
        self._beta_blade_out_tip = 65.0
        
        self._k_blockage = 1.10
        
        self._setup_ui()
        self._connect_signals()
        self._update_all()
    
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(6)
        
        # Left: Input panel
        input_panel = QFrame()
        input_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        input_panel.setMaximumWidth(180)
        input_layout = QVBoxLayout(input_panel)
        input_layout.setContentsMargins(6, 6, 6, 6)
        input_layout.setSpacing(6)
        
        # Machine
        machine_group = QGroupBox("Machine")
        machine_form = QFormLayout(machine_group)
        machine_form.setSpacing(3)
        self.rpm_spin = self._spin(100, 50000, self._rpm, " rpm")
        machine_form.addRow("n:", self.rpm_spin)
        self.alpha1_spin = self._spin(0, 180, self._alpha1, "°")
        machine_form.addRow("α₁:", self.alpha1_spin)
        input_layout.addWidget(machine_group)
        
        # Velocities
        vel_group = QGroupBox("cm (m/s)")
        vel_form = QFormLayout(vel_group)
        vel_form.setSpacing(3)
        self.cm1_spin = self._spin(0.1, 100, self._cm1)
        vel_form.addRow("cm₁:", self.cm1_spin)
        self.cm2_spin = self._spin(0.1, 100, self._cm2)
        vel_form.addRow("cm₂:", self.cm2_spin)
        input_layout.addWidget(vel_group)
        
        # Radii
        radii_group = QGroupBox("Radii (m)")
        radii_form = QFormLayout(radii_group)
        radii_form.setSpacing(3)
        self._r1_hub_spin = self._spin(0.001, 10, self._r1_hub, decimals=3)
        radii_form.addRow("r₁h:", self._r1_hub_spin)
        self._r1_tip_spin = self._spin(0.001, 10, self._r1_tip, decimals=3)
        radii_form.addRow("r₁t:", self._r1_tip_spin)
        self._r2_hub_spin = self._spin(0.001, 10, self._r2_hub, decimals=3)
        radii_form.addRow("r₂h:", self._r2_hub_spin)
        self._r2_tip_spin = self._spin(0.001, 10, self._r2_tip, decimals=3)
        radii_form.addRow("r₂t:", self._r2_tip_spin)
        input_layout.addWidget(radii_group)
        
        # Flow angles
        beta_group = QGroupBox("β flow (°)")
        beta_form = QFormLayout(beta_group)
        beta_form.setSpacing(3)
        self._beta_in_hub_spin = self._spin(5, 85, self._beta_in_hub, "°")
        beta_form.addRow("β₁h:", self._beta_in_hub_spin)
        self._beta_in_tip_spin = self._spin(5, 85, self._beta_in_tip, "°")
        beta_form.addRow("β₁t:", self._beta_in_tip_spin)
        self._beta_out_hub_spin = self._spin(5, 85, self._beta_out_hub, "°")
        beta_form.addRow("β₂h:", self._beta_out_hub_spin)
        self._beta_out_tip_spin = self._spin(5, 85, self._beta_out_tip, "°")
        beta_form.addRow("β₂t:", self._beta_out_tip_spin)
        input_layout.addWidget(beta_group)
        
        # Blade angles
        blade_group = QGroupBox("βB blade (°)")
        blade_form = QFormLayout(blade_group)
        blade_form.setSpacing(3)
        self._beta_blade_in_hub_spin = self._spin(5, 85, self._beta_blade_in_hub, "°")
        blade_form.addRow("βB₁h:", self._beta_blade_in_hub_spin)
        self._beta_blade_in_tip_spin = self._spin(5, 85, self._beta_blade_in_tip, "°")
        blade_form.addRow("βB₁t:", self._beta_blade_in_tip_spin)
        self._beta_blade_out_hub_spin = self._spin(5, 85, self._beta_blade_out_hub, "°")
        blade_form.addRow("βB₂h:", self._beta_blade_out_hub_spin)
        self._beta_blade_out_tip_spin = self._spin(5, 85, self._beta_blade_out_tip, "°")
        blade_form.addRow("βB₂t:", self._beta_blade_out_tip_spin)
        input_layout.addWidget(blade_group)
        
        # Blockage
        block_group = QGroupBox("Blockage")
        block_form = QFormLayout(block_group)
        block_form.setSpacing(3)
        self.k_blockage_spin = self._spin(1.0, 1.5, self._k_blockage, decimals=2)
        block_form.addRow("K:", self.k_blockage_spin)
        input_layout.addWidget(block_group)
        
        input_layout.addStretch()
        main_layout.addWidget(input_panel)
        
        # Right: Single figure with 2×2 subplots
        self.main_fig = Figure(figsize=(10, 8), dpi=100, facecolor='#181825')
        self.main_canvas = FigureCanvas(self.main_fig)
        self.main_canvas.setStyleSheet("background-color: #181825;")
        self.main_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.main_canvas, 1)
    
    def _spin(self, min_v, max_v, val, suffix="", decimals=1):
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setDecimals(decimals)
        s.setValue(val)
        if suffix:
            s.setSuffix(suffix)
        return s
    
    def _connect_signals(self):
        for s in [self.rpm_spin, self.alpha1_spin, self.cm1_spin, self.cm2_spin,
                  self._r1_hub_spin, self._r1_tip_spin, self._r2_hub_spin, self._r2_tip_spin,
                  self._beta_in_hub_spin, self._beta_in_tip_spin, self._beta_out_hub_spin, self._beta_out_tip_spin,
                  self._beta_blade_in_hub_spin, self._beta_blade_in_tip_spin, 
                  self._beta_blade_out_hub_spin, self._beta_blade_out_tip_spin,
                  self.k_blockage_spin]:
            s.valueChanged.connect(self._on_change)
    
    def _on_change(self):
        self._rpm = self.rpm_spin.value()
        self._alpha1 = self.alpha1_spin.value()
        self._cm1 = self.cm1_spin.value()
        self._cm2 = self.cm2_spin.value()
        self._r1_hub = self._r1_hub_spin.value()
        self._r1_tip = self._r1_tip_spin.value()
        self._r2_hub = self._r2_hub_spin.value()
        self._r2_tip = self._r2_tip_spin.value()
        self._beta_in_hub = self._beta_in_hub_spin.value()
        self._beta_in_tip = self._beta_in_tip_spin.value()
        self._beta_out_hub = self._beta_out_hub_spin.value()
        self._beta_out_tip = self._beta_out_tip_spin.value()
        self._beta_blade_in_hub = self._beta_blade_in_hub_spin.value()
        self._beta_blade_in_tip = self._beta_blade_in_tip_spin.value()
        self._beta_blade_out_hub = self._beta_blade_out_hub_spin.value()
        self._beta_blade_out_tip = self._beta_blade_out_tip_spin.value()
        self._k_blockage = self.k_blockage_spin.value()
        self._update_all()
        self.inputsChanged.emit()
    
    def _update_all(self):
        # Compute all 4 triangles
        inlet_hub = compute_triangle(self._beta_in_hub, self._r1_hub, self._rpm, self._cm1, self._alpha1, use_beta=False)
        inlet_tip = compute_triangle(self._beta_in_tip, self._r1_tip, self._rpm, self._cm1, self._alpha1, use_beta=False)
        outlet_hub = compute_triangle(self._beta_out_hub, self._r2_hub, self._rpm, self._cm2, 90.0, use_beta=True)
        outlet_tip = compute_triangle(self._beta_out_tip, self._r2_tip, self._rpm, self._cm2, 90.0, use_beta=True)
        
        all_tris = [inlet_hub, inlet_tip, outlet_hub, outlet_tip]
        
        # Calculate per-column xlim (Hub column, Tip column)
        # Column 0 (Hub): inlet_hub, outlet_hub
        hub_tris = [inlet_hub, outlet_hub]
        hub_xmax = max(t.u for t in hub_tris)
        hub_xmin = min(0, min(t.wu for t in hub_tris))
        
        # Column 1 (Tip): inlet_tip, outlet_tip
        tip_tris = [inlet_tip, outlet_tip]
        tip_xmax = max(t.u for t in tip_tris)
        tip_xmin = min(0, min(t.wu for t in tip_tris))
        
        # Calculate per-row ylim (Inlet row, Outlet row)
        # Row 0 (Inlet): inlet_hub, inlet_tip
        inlet_tris = [inlet_hub, inlet_tip]
        inlet_ymax = max(t.cm * self._k_blockage * 1.15 for t in inlet_tris)
        
        # Row 1 (Outlet): outlet_hub, outlet_tip
        outlet_tris = [outlet_hub, outlet_tip]
        outlet_ymax = max(t.cm * self._k_blockage * 1.15 for t in outlet_tris)
        
        margin = 1.5
        
        # Create 2×2 subplots with sharex per column, sharey per row
        self.main_fig.clear()
        axes = self.main_fig.subplots(2, 2, sharex='col', sharey='row')
        
        titles = [("Inlet Hub", inlet_hub, self._beta_blade_in_hub),
                  ("Inlet Tip", inlet_tip, self._beta_blade_in_tip),
                  ("Outlet Hub", outlet_hub, self._beta_blade_out_hub),
                  ("Outlet Tip", outlet_tip, self._beta_blade_out_tip)]
        
        for idx, (title, tri, beta_blade) in enumerate(titles):
            row, col = idx // 2, idx % 2
            ax = axes[row, col]
            self._draw_tri(ax, tri, beta_blade, self._k_blockage, title)
        
        # Apply per-column xlim
        axes[0, 0].set_xlim(hub_xmin - margin, hub_xmax + margin)
        axes[1, 0].set_xlim(hub_xmin - margin, hub_xmax + margin)
        axes[0, 1].set_xlim(tip_xmin - margin, tip_xmax + margin)
        axes[1, 1].set_xlim(tip_xmin - margin, tip_xmax + margin)
        
        # Apply per-row ylim
        axes[0, 0].set_ylim(-margin - 2, inlet_ymax + margin)
        axes[0, 1].set_ylim(-margin - 2, inlet_ymax + margin)
        axes[1, 0].set_ylim(-margin - 2, outlet_ymax + margin)
        axes[1, 1].set_ylim(-margin - 2, outlet_ymax + margin)
        
        self.main_fig.tight_layout()
        self.main_canvas.draw()
    
    def _draw_tri(self, ax, tri, beta_blade, k, title):
        """Draw triangle on given axes."""
        ax.set_facecolor('#1e1e2e')
        ax.set_title(title, color='#cdd6f4', fontsize=9, fontweight='bold')
        for sp in ax.spines.values():
            sp.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=7)
        
        # Geometry
        o = np.array([0, 0])
        u = np.array([tri.u, 0])
        apex = np.array([tri.wu, tri.cm])
        
        # Blocked geometry
        cm_b = tri.cm * k
        apex_b = np.array([tri.wu, cm_b])
        
        # Blade line
        beta_rad = math.radians(beta_blade)
        blade_y = cm_b * 1.1
        blade_x = blade_y / math.tan(beta_rad) if abs(math.tan(beta_rad)) > 0.01 else 0
        blade_end = np.array([blade_x, blade_y])
        
        # u baseline
        ax.annotate('', xy=u, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_U, lw=1.2))
        ax.text(tri.u/2, 0, 'u', fontsize=9, color=self.COLOR_U, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.1', facecolor='#1e1e2e', edgecolor='none', alpha=0.9))
        
        # w (flow) - green solid
        ax.annotate('', xy=apex, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_W, lw=1.0))
        
        # c (flow) - blue solid
        ax.annotate('', xy=apex, xytext=u, arrowprops=dict(arrowstyle='->', color=self.COLOR_C, lw=1.0))
        
        # w' c' (blocked) - dashed
        if k > 1.001:
            ax.annotate('', xy=apex_b, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_W, lw=0.8, ls='--'))
            ax.annotate('', xy=apex_b, xytext=u, arrowprops=dict(arrowstyle='->', color=self.COLOR_C, lw=0.8, ls='--'))
        
        # Blade line - thick transparent
        ax.plot([o[0], blade_end[0]], [o[1], blade_end[1]], color=self.COLOR_W, lw=3.5, alpha=0.35)
        
        # Labels on vectors
        w_mid = apex / 2
        ax.text(w_mid[0], w_mid[1], 'w', fontsize=9, color=self.COLOR_W, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.1', facecolor='#1e1e2e', edgecolor='none', alpha=0.9))
        
        c_mid = (u + apex) / 2
        ax.text(c_mid[0], c_mid[1], 'c', fontsize=9, color=self.COLOR_C, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.1', facecolor='#1e1e2e', edgecolor='none', alpha=0.9))
        
        # Component spans (wu and cu) below baseline
        span_y = -1.5
        label_y = -2.5
        
        # wu span: from 0 to wu
        if abs(tri.wu) > 0.1:
            ax.annotate('', xy=(tri.wu, span_y), xytext=(0, span_y),
                       arrowprops=dict(arrowstyle='<->', color='#6c7086', lw=0.8))
            ax.text(tri.wu/2, label_y, 'wu', fontsize=8, color=self.COLOR_W, ha='center')
        
        # cu span: from wu to u
        cu_val = tri.u - tri.wu
        if abs(cu_val) > 0.1:
            ax.annotate('', xy=(tri.u, span_y), xytext=(tri.wu, span_y),
                       arrowprops=dict(arrowstyle='<->', color='#6c7086', lw=0.8))
            ax.text((tri.wu + tri.u)/2, label_y, 'cu', fontsize=8, color=self.COLOR_C, ha='center')
        
        # Angle arcs
        arc_r = min(tri.u, tri.cm) * 0.2
        if arc_r < 1.5:
            arc_r = 1.5
        
        # β arc (flow)
        beta_flow = math.degrees(math.atan2(tri.cm, tri.wu)) if abs(tri.wu) > 0.01 else 90
        ax.add_patch(Arc(o, arc_r*2, arc_r*2, angle=0, theta1=0, theta2=beta_flow, color=self.COLOR_W, lw=1.0))
        
        # β arc (blade) - thick transparent
        ax.add_patch(Arc(o, arc_r*2.4, arc_r*2.4, angle=0, theta1=0, theta2=beta_blade, color=self.COLOR_W, lw=2.5, alpha=0.35))
        
        # β label
        mid_b = math.radians(beta_flow / 2)
        ax.text(arc_r * 1.4 * math.cos(mid_b), arc_r * 1.4 * math.sin(mid_b), 
               'β', fontsize=9, color=self.COLOR_W, fontweight='bold')
        
        # α arc - between u baseline and c vector
        c_vec = apex - u
        alpha_deg = math.degrees(math.atan2(c_vec[1], -c_vec[0]))
        if alpha_deg < 0:
            alpha_deg += 180
        ax.add_patch(Arc(u, arc_r*2, arc_r*2, angle=0, theta1=180-alpha_deg, theta2=180, color=self.COLOR_C, lw=1.0))
        alpha_mid = math.radians(180 - alpha_deg/2)
        ax.text(u[0] + arc_r * 1.3 * math.cos(alpha_mid), arc_r * 1.3 * math.sin(alpha_mid), 
               'α', fontsize=9, color=self.COLOR_C, fontweight='bold')
        
        # Baseline
        ax.axhline(0, color='#45475a', lw=0.3, alpha=0.5)
        ax.set_aspect('equal')
        
        # Legend (only once per axes - will duplicate but that's fine)
        legend_elements = [
            Line2D([0], [0], color=self.COLOR_C, lw=1.0, label='c'),
            Line2D([0], [0], color=self.COLOR_W, lw=1.0, label='w'),
            Line2D([0], [0], color=self.COLOR_W, lw=3.5, alpha=0.35, label='Blade'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=6, 
                 facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4')


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 11px; }
        QGroupBox { border: 1px solid #45475a; border-radius: 4px; margin-top: 6px; padding-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 6px; padding: 0 2px; }
        QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 3px; }
        QFrame { background-color: #181825; border-radius: 4px; }
    """)
    
    w = QMainWindow()
    w.setWindowTitle("Velocity Triangles - Unified Limits")
    w.resize(1100, 700)
    w.setCentralWidget(VelocityTriangleWidget())
    w.show()
    sys.exit(app.exec())
