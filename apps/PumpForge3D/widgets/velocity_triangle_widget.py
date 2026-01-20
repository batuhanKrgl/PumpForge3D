"""
Velocity Triangle Widget - 2×2 Subplots with unified axis limits.

All 4 subplots have the same xlim and ylim based on maximum vector sizes.
"""

import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
    QDoubleSpinBox, QFrame, QSizePolicy, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QTabWidget
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
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

        # Right: Plot area with toolbar and status
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(2)

        # Figure with 2×2 subplots
        self.main_fig = Figure(figsize=(10, 8), dpi=100, facecolor='#181825')
        self.main_canvas = FigureCanvas(self.main_fig)
        self.main_canvas.setStyleSheet("background-color: #181825;")
        self.main_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Matplotlib toolbar
        self.toolbar = NavigationToolbar(self.main_canvas, self)
        self.toolbar.setStyleSheet("""
            QToolBar { background-color: #313244; border: 1px solid #45475a; spacing: 2px; padding: 2px; }
            QToolButton { background-color: #313244; color: #cdd6f4; border: none; padding: 3px; }
            QToolButton:hover { background-color: #45475a; }
        """)

        # Status label for warnings and debug info
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #313244;
                color: #f9e2af;
                padding: 4px 8px;
                border: 1px solid #45475a;
                border-radius: 3px;
                font-size: 9px;
            }
        """)
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Data viewer table
        self.data_viewer = QTableWidget()
        self.data_viewer.setColumnCount(5)
        self.data_viewer.setHorizontalHeaderLabels(['Parameter', 'Inlet Hub', 'Inlet Tip', 'Outlet Hub', 'Outlet Tip'])
        self.data_viewer.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_viewer.setMaximumHeight(300)
        self.data_viewer.setStyleSheet("""
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
                padding: 6px;
                border: 1px solid #45475a;
                font-weight: bold;
                font-size: 10px;
            }
        """)

        right_layout.addWidget(self.toolbar)
        right_layout.addWidget(self.main_canvas, 1)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.data_viewer)

        # Hide data viewer by default (can be shown via set_data_viewer_visible)
        self.data_viewer.setVisible(False)

        main_layout.addWidget(right_widget, 1)
    
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

        # Collect warnings and validate data
        warnings = []
        for idx, tri in enumerate(all_tris):
            labels = ["Inlet Hub", "Inlet Tip", "Outlet Hub", "Outlet Tip"]
            # Check for warnings from compute_triangle
            if tri.warning:
                warnings.append(f"{labels[idx]}: {tri.warning}")

            # Validate finite values
            if not all(np.isfinite([tri.u, tri.cm, tri.cu, tri.wu, tri.c, tri.w, tri.alpha, tri.beta])):
                warnings.append(f"{labels[idx]}: NaN/Inf detected in triangle data")
                # Sanitize: replace NaN/Inf with safe fallback
                if not np.isfinite(tri.u):
                    tri.u = 0.0
                if not np.isfinite(tri.cm):
                    tri.cm = 0.0
                if not np.isfinite(tri.cu):
                    tri.cu = 0.0
                if not np.isfinite(tri.wu):
                    tri.wu = 0.0
                if not np.isfinite(tri.c):
                    tri.c = 0.0
                if not np.isfinite(tri.w):
                    tri.w = 0.0
                if not np.isfinite(tri.alpha):
                    tri.alpha = 90.0
                if not np.isfinite(tri.beta):
                    tri.beta = 90.0

        # Update status label
        if warnings:
            self.status_label.setText("⚠ " + " | ".join(warnings))
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #313244;
                    color: #f38ba8;
                    padding: 4px 8px;
                    border: 1px solid #f38ba8;
                    border-radius: 3px;
                    font-size: 9px;
                }
            """)
        else:
            # Show key computed values for debugging/validation
            status_parts = [
                f"Inlet Hub: α={inlet_hub.alpha:.1f}° β={inlet_hub.beta:.1f}° u={inlet_hub.u:.2f} cu={inlet_hub.cu:.2f} wu={inlet_hub.wu:.2f}",
                f"Outlet Hub: α={outlet_hub.alpha:.1f}° β={outlet_hub.beta:.1f}° u={outlet_hub.u:.2f} cu={outlet_hub.cu:.2f} wu={outlet_hub.wu:.2f}"
            ]
            self.status_label.setText(" | ".join(status_parts))
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #313244;
                    color: #a6e3a1;
                    padding: 4px 8px;
                    border: 1px solid #45475a;
                    border-radius: 3px;
                    font-size: 9px;
                }
            """)
        
        # Create 2×2 subplots with independent axes (no syncing)
        self.main_fig.clear()
        axes = self.main_fig.subplots(2, 2)

        triangles_data = [
            ("Inlet Hub", inlet_hub, self._beta_blade_in_hub),
            ("Inlet Tip", inlet_tip, self._beta_blade_in_tip),
            ("Outlet Hub", outlet_hub, self._beta_blade_out_hub),
            ("Outlet Tip", outlet_tip, self._beta_blade_out_tip)
        ]

        # Draw each triangle with independent axis limits
        for idx, (title, tri, beta_blade) in enumerate(triangles_data):
            row, col = idx // 2, idx % 2
            ax = axes[row, col]
            self._draw_tri(ax, tri, beta_blade, self._k_blockage, title)

            # Calculate independent axis limits for this triangle
            margin = 1.5
            xmax = tri.u + margin
            xmin = min(0, tri.wu) - margin
            ymax = tri.cm * self._k_blockage * 1.15 + margin

            ax.set_xlim(xmin, xmax)
            ax.set_ylim(-margin - 2, ymax)

        # Populate data viewer table
        self._update_data_viewer(inlet_hub, inlet_tip, outlet_hub, outlet_tip)
        
        self.main_fig.tight_layout()
        self.main_canvas.draw()

    def _update_data_viewer(self, inlet_hub, inlet_tip, outlet_hub, outlet_tip):
        """Populate data viewer table with comprehensive triangle data."""
        # Parameters to display
        params = [
            ("Radius (m)", lambda t: f"{t.radius:.4f}"),
            ("RPM", lambda t: f"{t.rpm:.1f}"),
            ("", lambda t: ""),  # Separator
            ("u (m/s)", lambda t: f"{t.u:.2f}"),
            ("cm (m/s)", lambda t: f"{t.cm:.2f}"),
            ("cu (m/s)", lambda t: f"{t.cu:.2f}"),
            ("wu (m/s)", lambda t: f"{t.wu:.2f}"),
            ("", lambda t: ""),  # Separator
            ("c (m/s)", lambda t: f"{t.c:.2f}"),
            ("w (m/s)", lambda t: f"{t.w:.2f}"),
            ("", lambda t: ""),  # Separator
            ("α (deg)", lambda t: f"{t.alpha:.2f}"),
            ("β (deg)", lambda t: f"{t.beta:.2f}"),
            ("", lambda t: ""),  # Separator
            ("c/u ratio", lambda t: f"{t.c/t.u:.3f}" if t.u > 0.01 else "N/A"),
            ("w/u ratio", lambda t: f"{t.w/t.u:.3f}" if t.u > 0.01 else "N/A"),
        ]

        triangles = [inlet_hub, inlet_tip, outlet_hub, outlet_tip]

        self.data_viewer.setRowCount(len(params))

        for row_idx, (param_name, value_func) in enumerate(params):
            # Parameter name
            name_item = QTableWidgetItem(param_name)
            if param_name == "":  # Separator row
                name_item.setBackground(Qt.GlobalColor.darkGray)
            else:
                font = QFont()
                font.setBold(True)
                name_item.setFont(font)
            self.data_viewer.setItem(row_idx, 0, name_item)

            # Values for each triangle
            for col_idx, tri in enumerate(triangles):
                value_item = QTableWidgetItem(value_func(tri))
                if param_name == "":  # Separator row
                    value_item.setBackground(Qt.GlobalColor.darkGray)
                else:
                    value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.data_viewer.setItem(row_idx, col_idx + 1, value_item)

    def _draw_tri(self, ax, tri, beta_blade, k, title):
        """Draw triangle on given axes with improved readability and stability."""
        ax.set_facecolor('#1e1e2e')
        ax.set_title(title, color='#cdd6f4', fontsize=10, fontweight='bold')
        for sp in ax.spines.values():
            sp.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=8)
        
        # Geometry
        o = np.array([0, 0])
        u = np.array([tri.u, 0])
        apex = np.array([tri.wu, tri.cm])
        
        # Blocked geometry
        cm_b = tri.cm * k
        apex_b = np.array([tri.wu, cm_b])

        # Blade line - FIXED: properly handle singularities at beta=0° and beta=90°
        # tan(beta) is near zero when beta is near 0° (horizontal) or 180°
        # tan(beta) is infinite when beta is near 90° (vertical)
        blade_y = cm_b * 1.1
        # Avoid singularities: check if beta_blade is near 0°, 90°, or 180°
        if abs(beta_blade) < 2.0 or abs(beta_blade - 180) < 2.0:
            # Near horizontal blade (beta ≈ 0° or 180°)
            blade_x = blade_y * 100 if beta_blade > 0 else -blade_y * 100  # Very large x
        elif abs(beta_blade - 90) < 2.0:
            # Near vertical blade (beta ≈ 90°)
            blade_x = 0.0  # Vertical line
        else:
            # Normal case: blade_x = blade_y / tan(beta)
            beta_rad = math.radians(beta_blade)
            tan_beta = math.tan(beta_rad)
            blade_x = blade_y / tan_beta
        blade_end = np.array([blade_x, blade_y])
        
        # u baseline
        ax.annotate('', xy=u, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_U, lw=1.5))
        ax.text(tri.u/2, 0, 'u', fontsize=10, color=self.COLOR_U, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.15', facecolor='#1e1e2e', edgecolor='none', alpha=0.9))

        # w (flow) - green solid
        ax.annotate('', xy=apex, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_W, lw=1.3))

        # c (flow) - blue solid
        ax.annotate('', xy=apex, xytext=u, arrowprops=dict(arrowstyle='->', color=self.COLOR_C, lw=1.3))

        # w' c' (blocked) - dashed
        if k > 1.001:
            ax.annotate('', xy=apex_b, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_W, lw=1.0, ls='--'))
            ax.annotate('', xy=apex_b, xytext=u, arrowprops=dict(arrowstyle='->', color=self.COLOR_C, lw=1.0, ls='--'))

        # Blade line - thick transparent
        ax.plot([o[0], blade_end[0]], [o[1], blade_end[1]], color=self.COLOR_W, lw=4.0, alpha=0.35)

        # Labels on vectors
        w_mid = apex / 2
        ax.text(w_mid[0], w_mid[1], 'w', fontsize=10, color=self.COLOR_W, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.15', facecolor='#1e1e2e', edgecolor='none', alpha=0.9))

        c_mid = (u + apex) / 2
        ax.text(c_mid[0], c_mid[1], 'c', fontsize=10, color=self.COLOR_C, ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.15', facecolor='#1e1e2e', edgecolor='none', alpha=0.9))
        
        # Component spans (wu and cu) below baseline with values
        span_y = -1.5
        label_y = -2.8

        # wu span: from 0 to wu
        if abs(tri.wu) > 0.1:
            ax.annotate('', xy=(tri.wu, span_y), xytext=(0, span_y),
                       arrowprops=dict(arrowstyle='<->', color='#6c7086', lw=0.9))
            ax.text(tri.wu/2, label_y, f'wu={tri.wu:.1f}', fontsize=9, color=self.COLOR_W, ha='center',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='#1e1e2e', edgecolor='none', alpha=0.85))

        # cu span: from wu to u
        cu_val = tri.cu  # Use tri.cu directly for accuracy
        if abs(cu_val) > 0.1:
            ax.annotate('', xy=(tri.u, span_y), xytext=(tri.wu, span_y),
                       arrowprops=dict(arrowstyle='<->', color='#6c7086', lw=0.9))
            ax.text((tri.wu + tri.u)/2, label_y, f'cu={cu_val:.1f}', fontsize=9, color=self.COLOR_C, ha='center',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='#1e1e2e', edgecolor='none', alpha=0.85))
        
        # Angle arcs with improved sizing and labels
        arc_r = min(tri.u, tri.cm) * 0.2
        if arc_r < 1.8:
            arc_r = 1.8

        # β arc (flow) - angle from horizontal axis to w vector
        # beta_flow should always be measured from positive x-axis counter-clockwise
        beta_flow = math.degrees(math.atan2(tri.cm, tri.wu)) if abs(tri.wu) > 0.01 else 90.0
        # Ensure beta_flow is in [0, 180] range
        if beta_flow < 0:
            beta_flow += 180
        ax.add_patch(Arc(o, arc_r*2, arc_r*2, angle=0, theta1=0, theta2=beta_flow, color=self.COLOR_W, lw=1.2))

        # β arc (blade) - thick transparent
        ax.add_patch(Arc(o, arc_r*2.5, arc_r*2.5, angle=0, theta1=0, theta2=beta_blade, color=self.COLOR_W, lw=2.8, alpha=0.35))

        # β label - positioned at midpoint of flow angle arc
        mid_b = math.radians(beta_flow / 2)
        ax.text(arc_r * 1.5 * math.cos(mid_b), arc_r * 1.5 * math.sin(mid_b),
               'β', fontsize=11, color=self.COLOR_W, fontweight='bold', ha='center', va='center')

        # α arc - angle from u baseline (negative x from u) to c vector
        # This measures the absolute flow angle at the impeller tip
        c_vec = apex - u  # c vector components
        alpha_deg = math.degrees(math.atan2(c_vec[1], -c_vec[0]))  # Angle from -x axis
        if alpha_deg < 0:
            alpha_deg += 180
        # Guard against edge cases
        if alpha_deg > 0.1 and alpha_deg < 179.9:
            ax.add_patch(Arc(u, arc_r*2, arc_r*2, angle=0, theta1=180-alpha_deg, theta2=180, color=self.COLOR_C, lw=1.2))
            alpha_mid = math.radians(180 - alpha_deg/2)
            ax.text(u[0] + arc_r * 1.4 * math.cos(alpha_mid), arc_r * 1.4 * math.sin(alpha_mid),
                   'α', fontsize=11, color=self.COLOR_C, fontweight='bold', ha='center', va='center')
        
        # Baseline
        ax.axhline(0, color='#45475a', lw=0.3, alpha=0.5)
        ax.set_aspect('equal')

        # Legend - positioned at lower right to avoid overlapping with vectors
        legend_elements = [
            Line2D([0], [0], color=self.COLOR_C, lw=1.3, label='c (abs)'),
            Line2D([0], [0], color=self.COLOR_W, lw=1.3, label='w (rel)'),
            Line2D([0], [0], color=self.COLOR_W, lw=4.0, alpha=0.35, label='Blade'),
        ]
        ax.legend(handles=legend_elements, loc='lower right', fontsize=8,
                 facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4',
                 framealpha=0.9)

    def set_data_viewer_visible(self, visible: bool):
        """Show or hide the data viewer table."""
        self.data_viewer.setVisible(visible)


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
