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
from matplotlib import rcParams

from core.velocity_triangles import InletTriangle, OutletTriangle
from ..app.state.app_state import AppState


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
        self._blade_number = 3
        self._incidence_in = 0.0
        self._slip_out = 5.0
        
        self._beta_in_hub = 25.0
        self._beta_in_tip = 30.0
        self._beta_out_hub = 55.0
        self._beta_out_tip = 60.0
        
        self._beta_blade_in_hub = 30.0
        self._beta_blade_in_tip = 35.0
        self._beta_blade_out_hub = 60.0
        self._beta_blade_out_tip = 65.0
        
        self._k_blockage = 1.10
        self._triangles = None
        self._state = None
        
        self._setup_ui()
        self._connect_signals()
        self._update_all()
    
    def _setup_ui(self):
        rcParams["font.family"] = "DejaVu Sans"
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

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

        main_layout.addWidget(self.toolbar)
        main_layout.addWidget(self.main_canvas, 1)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.data_viewer)

        # Hide data viewer by default (can be shown via set_data_viewer_visible)
        self.data_viewer.setVisible(False)
    
    def _connect_signals(self):
        """No longer needed - parameters set via public methods."""
        pass
    
    def _update_all(self):
        inlet_hub, inlet_tip, outlet_hub, outlet_tip = self._get_triangles()

        all_tris = [inlet_hub, inlet_tip, outlet_hub, outlet_tip]

        # Collect warnings and validate data
        warnings = []
        for idx, tri in enumerate(all_tris):
            labels = ["Inlet Hub", "Inlet Tip", "Outlet Hub", "Outlet Tip"]
            # Check for warnings from compute_triangle
            # Validate finite values
            if not all(np.isfinite([tri.u, tri.c_m, tri.cu, tri.wu, tri.c, tri.w, tri.alpha, tri.beta])):
                warnings.append(f"{labels[idx]}: NaN/Inf detected in triangle data")

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
                f"Inlet Hub: α={math.degrees(inlet_hub.alpha):.1f}° β={math.degrees(inlet_hub.beta):.1f}° u={inlet_hub.u:.2f} cu={inlet_hub.cu:.2f} wu={inlet_hub.wu:.2f}",
                f"Outlet Hub: α={math.degrees(outlet_hub.alpha):.1f}° β={math.degrees(outlet_hub.beta):.1f}° u={outlet_hub.u:.2f} cu={outlet_hub.cu:.2f} wu={outlet_hub.wu:.2f}"
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
            ("Inlet Hub", inlet_hub, inlet_hub.beta_blade_effective),      # row 0, col 0
            ("Inlet Tip", inlet_tip, inlet_tip.beta_blade_effective),      # row 0, col 1
            ("Outlet Hub", outlet_hub, outlet_hub.beta_blade),   # row 1, col 0
            ("Outlet Tip", outlet_tip, outlet_tip.beta_blade)    # row 1, col 1
        ]

        # Calculate axis limits per row (xlim) and per column (ylim)
        margin = 1.5

        # Calculate xlim for each row
        row0_xmax = max(inlet_hub.u + margin, inlet_tip.u + margin)
        row0_xmin = min(min(0, inlet_hub.wu) - margin, min(0, inlet_tip.wu) - margin)
        row1_xmax = max(outlet_hub.u + margin, outlet_tip.u + margin)
        row1_xmin = min(min(0, outlet_hub.wu) - margin, min(0, outlet_tip.wu) - margin)

        # Calculate ylim for each column
        col0_ymax = max(inlet_hub.cm_blocked * 1.15 + margin,
                        outlet_hub.cm_blocked * 1.15 + margin)
        col1_ymax = max(inlet_tip.cm_blocked * 1.15 + margin,
                        outlet_tip.cm_blocked * 1.15 + margin)
        unified_ymin = -margin - 2

        # Map row/col to their limits
        row_xlims = {
            0: (row0_xmin, row0_xmax),  # Inlet row
            1: (row1_xmin, row1_xmax)   # Outlet row
        }
        col_ylims = {
            0: (unified_ymin, col0_ymax),  # Hub column
            1: (unified_ymin, col1_ymax)   # Tip column
        }

        # Draw each triangle with row-wise xlim and column-wise ylim
        for idx, (title, tri, beta_blade) in enumerate(triangles_data):
            row, col = idx // 2, idx % 2
            ax = axes[row, col]
            self._draw_tri(ax, tri, beta_blade, title)

            # Apply row-specific xlim and column-specific ylim
            ax.set_xlim(*row_xlims[row])
            ax.set_ylim(*col_ylims[col])

        # Populate data viewer table
        self._update_data_viewer(inlet_hub, inlet_tip, outlet_hub, outlet_tip)
        
        self.main_fig.tight_layout()
        self.main_canvas.draw()

    def _get_triangles(self) -> tuple[InletTriangle, InletTriangle, OutletTriangle, OutletTriangle]:
        if self._triangles is not None:
            return self._triangles
        return self._build_triangles_from_inputs()

    def set_state(self, state: AppState) -> None:
        """Connect the widget to AppState for triangle updates."""
        if self._state is not None:
            try:
                self._state.triangles_changed.disconnect(self._on_triangles_changed)
            except TypeError:
                pass
        self._state = state
        self._state.triangles_changed.connect(self._on_triangles_changed)
        inducer = self._state.get_inducer()
        inlet_hub, outlet_hub = inducer.build_triangles_pair("hub")
        inlet_tip, outlet_tip = inducer.build_triangles_pair("shroud")
        self.set_triangles(inlet_hub, inlet_tip, outlet_hub, outlet_tip)

    def _on_triangles_changed(self, payload: dict) -> None:
        inlet_hub = payload.get("inlet_hub")
        inlet_tip = payload.get("inlet_tip")
        outlet_hub = payload.get("outlet_hub")
        outlet_tip = payload.get("outlet_tip")
        if not all([inlet_hub, inlet_tip, outlet_hub, outlet_tip]):
            return
        self.set_triangles(inlet_hub, inlet_tip, outlet_hub, outlet_tip)

    def _build_triangles_from_inputs(
        self,
    ) -> tuple[InletTriangle, InletTriangle, OutletTriangle, OutletTriangle]:
        omega = self._rpm * 2.0 * math.pi / 60.0
        alpha_rad = math.radians(self._alpha1)

        inlet_hub = InletTriangle(
            r=self._r1_hub,
            omega=omega,
            c_m=self._cm1,
            alpha=alpha_rad,
            blade_number=self._blade_number,
            blockage=self._k_blockage,
            incidence=math.radians(self._incidence_in),
            beta_blade=math.radians(self._beta_blade_in_hub),
        )
        inlet_tip = InletTriangle(
            r=self._r1_tip,
            omega=omega,
            c_m=self._cm1,
            alpha=alpha_rad,
            blade_number=self._blade_number,
            blockage=self._k_blockage,
            incidence=math.radians(self._incidence_in),
            beta_blade=math.radians(self._beta_blade_in_tip),
        )

        slip_hub = math.radians(self._beta_blade_out_hub - self._beta_out_hub)
        slip_tip = math.radians(self._beta_blade_out_tip - self._beta_out_tip)
        outlet_hub = OutletTriangle(
            r=self._r2_hub,
            omega=omega,
            c_m=self._cm2,
            beta_blade=math.radians(self._beta_blade_out_hub),
            blade_number=self._blade_number,
            blockage=self._k_blockage,
            slip=slip_hub,
        )
        outlet_tip = OutletTriangle(
            r=self._r2_tip,
            omega=omega,
            c_m=self._cm2,
            beta_blade=math.radians(self._beta_blade_out_tip),
            blade_number=self._blade_number,
            blockage=self._k_blockage,
            slip=slip_tip,
        )
        return inlet_hub, inlet_tip, outlet_hub, outlet_tip

    def _update_data_viewer(self, inlet_hub, inlet_tip, outlet_hub, outlet_tip):
        """Populate data viewer table with comprehensive triangle data."""
        def _rpm(omega: float) -> float:
            return omega * 60.0 / (2.0 * math.pi)

        # Parameters to display
        params = [
            ("Radius (m)", lambda t: f"{t.r:.4f}"),
            ("RPM", lambda t: f"{_rpm(t.omega):.1f}"),
            ("", lambda t: ""),  # Separator
            ("u (m/s)", lambda t: f"{t.u:.2f}"),
            ("cm (m/s)", lambda t: f"{t.c_m:.2f}"),
            ("cu (m/s)", lambda t: f"{t.cu:.2f}"),
            ("wu (m/s)", lambda t: f"{t.wu:.2f}"),
            ("", lambda t: ""),  # Separator
            ("c (m/s)", lambda t: f"{t.c:.2f}"),
            ("w (m/s)", lambda t: f"{t.w:.2f}"),
            ("", lambda t: ""),  # Separator
            ("α (deg)", lambda t: f"{math.degrees(t.alpha):.2f}"),
            ("β (deg)", lambda t: f"{math.degrees(t.beta):.2f}"),
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

    def _draw_tri(self, ax, tri, beta_blade, title):
        """Draw triangle on given axes with improved readability and stability."""
        ax.set_facecolor('#1e1e2e')
        ax.set_title(title, color='#cdd6f4', fontsize=10, fontweight='bold')
        for sp in ax.spines.values():
            sp.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=8)
        
        # Geometry
        o = np.array([0, 0])
        u = np.array([tri.u, 0])
        apex = np.array([tri.wu, tri.c_m])
        
        # Blocked geometry
        cm_b = tri.cm_blocked
        apex_b = np.array([tri.wu, cm_b])

        # Blade line - FIXED: properly handle singularities at beta=0° and beta=90°
        # tan(beta) is near zero when beta is near 0° (horizontal) or 180°
        # tan(beta) is infinite when beta is near 90° (vertical)
        blade_y = cm_b * 1.1
        # Avoid singularities: check if beta_blade is near 0°, 90°, or 180°
        beta_blade_deg = math.degrees(beta_blade)
        if abs(beta_blade_deg) < 2.0 or abs(beta_blade_deg - 180) < 2.0:
            # Near horizontal blade (beta ≈ 0° or 180°)
            blade_x = blade_y * 100 if beta_blade_deg > 0 else -blade_y * 100  # Very large x
        elif abs(beta_blade_deg - 90) < 2.0:
            # Near vertical blade (beta ≈ 90°)
            blade_x = 0.0  # Vertical line
        else:
            # Normal case: blade_x = blade_y / tan(beta)
            tan_beta = math.tan(beta_blade)
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
        if tri.blockage > 1.001:
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
        arc_r = min(tri.u, tri.c_m) * 0.2
        if arc_r < 1.8:
            arc_r = 1.8

        # β arc (flow) - angle from horizontal axis to w vector
        # beta_flow should always be measured from positive x-axis counter-clockwise
        beta_flow = math.degrees(math.atan2(tri.c_m, tri.wu)) if abs(tri.wu) > 0.01 else 90.0
        # Ensure beta_flow is in [0, 180] range
        if beta_flow < 0:
            beta_flow += 180
        ax.add_patch(Arc(o, arc_r*2, arc_r*2, angle=0, theta1=0, theta2=beta_flow, color=self.COLOR_W, lw=1.2))

        # β arc (blade) - thick transparent
        ax.add_patch(Arc(o, arc_r*2.5, arc_r*2.5, angle=0, theta1=0, theta2=beta_blade_deg, color=self.COLOR_W, lw=2.8, alpha=0.35))

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

    def set_triangles(
        self,
        inlet_hub: InletTriangle,
        inlet_tip: InletTriangle,
        outlet_hub: OutletTriangle,
        outlet_tip: OutletTriangle,
    ) -> None:
        """Set triangles directly from core models."""
        self._triangles = (inlet_hub, inlet_tip, outlet_hub, outlet_tip)
        self._update_all()

    # Public setters for external parameter control
    def set_rpm(self, rpm: float):
        """Set rotational speed (RPM)."""
        self._rpm = rpm
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_velocities(self, cm1: float, cm2: float):
        """Set meridional velocities (m/s)."""
        self._cm1 = cm1
        self._cm2 = cm2
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_radii(self, r1_hub: float, r1_tip: float, r2_hub: float, r2_tip: float):
        """Set radii (m)."""
        self._r1_hub = r1_hub
        self._r1_tip = r1_tip
        self._r2_hub = r2_hub
        self._r2_tip = r2_tip
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_flow_angles(self, beta_in_hub: float, beta_in_tip: float,
                        beta_out_hub: float, beta_out_tip: float):
        """Set flow angles β (degrees)."""
        self._beta_in_hub = beta_in_hub
        self._beta_in_tip = beta_in_tip
        self._beta_out_hub = beta_out_hub
        self._beta_out_tip = beta_out_tip
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_blade_angles(self, beta_blade_in_hub: float, beta_blade_in_tip: float,
                         beta_blade_out_hub: float, beta_blade_out_tip: float):
        """Set blade angles βB (degrees)."""
        self._beta_blade_in_hub = beta_blade_in_hub
        self._beta_blade_in_tip = beta_blade_in_tip
        self._beta_blade_out_hub = beta_blade_out_hub
        self._beta_blade_out_tip = beta_blade_out_tip
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_blockage_factor(self, k_blockage: float):
        """Set blockage factor K."""
        self._k_blockage = k_blockage
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_alpha1(self, alpha1: float):
        """Set inlet flow angle α₁ (degrees)."""
        self._alpha1 = alpha1
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_all_parameters(self, rpm: float, cm1: float, cm2: float, alpha1: float,
                          r1_hub: float, r1_tip: float, r2_hub: float, r2_tip: float,
                          beta_in_hub: float, beta_in_tip: float,
                          beta_out_hub: float, beta_out_tip: float,
                          beta_blade_in_hub: float, beta_blade_in_tip: float,
                          beta_blade_out_hub: float, beta_blade_out_tip: float,
                          k_blockage: float):
        """Set all parameters at once and update."""
        self._rpm = rpm
        self._cm1 = cm1
        self._cm2 = cm2
        self._alpha1 = alpha1
        self._r1_hub = r1_hub
        self._r1_tip = r1_tip
        self._r2_hub = r2_hub
        self._r2_tip = r2_tip
        self._beta_in_hub = beta_in_hub
        self._beta_in_tip = beta_in_tip
        self._beta_out_hub = beta_out_hub
        self._beta_out_tip = beta_out_tip
        self._beta_blade_in_hub = beta_blade_in_hub
        self._beta_blade_in_tip = beta_blade_in_tip
        self._beta_blade_out_hub = beta_blade_out_hub
        self._beta_blade_out_tip = beta_blade_out_tip
        self._k_blockage = k_blockage
        self._triangles = None
        self._update_all()
        self.inputsChanged.emit()

    def set_beta_values(self, beta_in_hub: float, beta_in_tip: float,
                        beta_out_hub: float, beta_out_tip: float) -> None:
        """Backward-compatible alias for updating flow angles."""
        self.set_flow_angles(beta_in_hub, beta_in_tip, beta_out_hub, beta_out_tip)


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
