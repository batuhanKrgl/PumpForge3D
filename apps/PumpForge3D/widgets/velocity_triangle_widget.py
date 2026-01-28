"""Velocity Triangle Widget - 1×4 subplots with shared y limits."""

import math
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QPixmap, QPainter, QPen, QColor

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.patches import Arc
from matplotlib import rcParams

from core.velocity_triangles import InletTriangle, OutletTriangle
from ..app.state.app_state import AppState


from ..utils.matplotlib_layout import apply_layout_to_figure


class VelocityTriangleWidget(QWidget):
    """1×4 subplot velocity triangle widget with shared y limits."""
    
    inputsChanged = Signal()
    
    # Colors
    COLOR_U = '#fab387'      # Blade speed - orange
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

        # Figure with 1×4 subplots
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

        self.legend_widget = self._build_legend_widget()
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)
        top_layout.addWidget(self.toolbar)
        top_layout.addWidget(self.legend_widget, 1)

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

        main_layout.addWidget(top_bar)
        main_layout.addWidget(self.main_canvas, 1)
        main_layout.addWidget(self.data_viewer)

        # Hide data viewer by default (can be shown via set_data_viewer_visible)
        self.data_viewer.setVisible(False)
    
    def _connect_signals(self):
        """No longer needed - parameters set via public methods."""
        pass

    def _build_legend_widget(self) -> QWidget:
        legend = QWidget()
        legend.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        legend.setFixedHeight(28)
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(8, 2, 8, 2)
        legend_layout.setSpacing(10)

        legend_items = [
            ("Blue: c (absolute)", self.COLOR_C, 2, Qt.PenStyle.SolidLine),
            ("Green: w (relative)", self.COLOR_W, 2, Qt.PenStyle.SolidLine),
            ("Orange: u (blade speed)", self.COLOR_U, 2, Qt.PenStyle.SolidLine),
            ("Dashed: blocked flow", "#cdd6f4", 2, Qt.PenStyle.DashLine),
            ("Thick: blade angle", "#cdd6f4", 4, Qt.PenStyle.SolidLine),
            ("Solid: velocity vectors", "#cdd6f4", 2, Qt.PenStyle.SolidLine),
        ]

        for text, color, width, style in legend_items:
            legend_layout.addWidget(self._legend_item(text, color, width, style))

        legend_layout.addStretch()
        return legend

    def _legend_item(self, text: str, color: str, width: int, style: Qt.PenStyle) -> QWidget:
        item = QWidget()
        item_layout = QHBoxLayout(item)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(6)

        sample = QLabel()
        sample.setPixmap(self._line_pixmap(color, width, style))
        label = QLabel(text)
        label.setStyleSheet("color: #cdd6f4; font-size: 9px;")

        item_layout.addWidget(sample)
        item_layout.addWidget(label)
        return item

    def _line_pixmap(self, color: str, width: int, style: Qt.PenStyle) -> QPixmap:
        pixmap = QPixmap(36, 8)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        pen = QPen()
        pen.setColor(QColor(color))
        pen.setWidth(width)
        pen.setStyle(style)
        painter.setPen(pen)
        painter.drawLine(2, pixmap.height() // 2, pixmap.width() - 2, pixmap.height() // 2)
        painter.end()
        return pixmap

    def _draw_angle_arc(
        self,
        ax,
        origin: np.ndarray,
        v1_end: np.ndarray,
        v2_end: np.ndarray,
        radius: float,
        label: str,
        color: str,
    ) -> None:
        theta1 = math.degrees(math.atan2(v1_end[1] - origin[1], v1_end[0] - origin[0]))
        theta2 = math.degrees(math.atan2(v2_end[1] - origin[1], v2_end[0] - origin[0]))
        theta1 %= 360
        theta2 %= 360
        delta = (theta2 - theta1) % 360
        if delta > 180:
            theta1, theta2 = theta2, theta1
            delta = 360 - delta
        if delta < 1.0:
            return
        ax.add_patch(Arc(origin, radius * 2, radius * 2, angle=0, theta1=theta1, theta2=theta1 + delta, color=color, lw=1.2))
        mid_angle = math.radians(theta1 + delta / 2)
        label_x = origin[0] + radius * 1.2 * math.cos(mid_angle)
        label_y = origin[1] + radius * 1.2 * math.sin(mid_angle)
        ax.text(label_x, label_y, label, fontsize=11, color=color, fontweight='bold', ha='center', va='center')
    
    def _update_all(self):
        inlet_hub, inlet_tip, outlet_hub, outlet_tip = self._get_triangles()

        # Create 1×4 subplots with independent axes (no syncing)
        self.main_fig.clear()
        axes = self.main_fig.subplots(1, 4)

        triangles_data = [
            ("Hub @ Leading Edge", inlet_hub, inlet_hub.beta_blade_effective),
            ("Hub @ Trailing Edge", outlet_hub, outlet_hub.beta_blade),
            ("Shroud @ Leading Edge", inlet_tip, inlet_tip.beta_blade_effective),
            ("Shroud @ Trailing Edge", outlet_tip, outlet_tip.beta_blade),
        ]

        global_y = self._collect_global_ylim(triangles_data)
        global_x = self._collect_global_xlim(triangles_data, global_y)

        # Populate data viewer table
        self._update_data_viewer(inlet_hub, inlet_tip, outlet_hub, outlet_tip)

        for ax, (title, tri, beta_blade) in zip(axes, triangles_data):
            self._draw_tri(ax, tri, beta_blade, title, global_y, global_x)

        self._apply_layout()
        self.main_canvas.draw()

    def _apply_layout(self) -> None:
        apply_layout_to_figure(self.main_fig)
        self.main_fig.subplots_adjust(top=0.96, bottom=0.10, left=0.06, right=0.98, wspace=0.35)

    def _collect_global_ylim(self, triangles_data) -> tuple[float, float]:
        y_points = []
        for _, tri, beta_blade in triangles_data:
            points = self._triangle_points(tri, beta_blade)
            y_points.extend(points[:, 1].tolist())
        y_min = min(y_points)
        y_max = max(y_points)
        y_span = max(y_max - y_min, 1.0)
        margin = 0.10 * y_span
        return y_min - margin, y_max + margin

    def _collect_global_xlim(self, triangles_data, global_y) -> tuple[float, float]:
        max_c_m = max(tri.c_m for _, tri, _ in triangles_data)
        y_span = max(global_y[1] - global_y[0], 1.0)
        margin = 0.10 * y_span
        x_span = y_span
        x_min = min(0.0, max_c_m + margin - x_span)
        x_max = x_min + x_span
        if x_max < max_c_m + margin:
            x_max = max_c_m + margin
            x_min = x_max - x_span
        return x_min, x_max

    def _triangle_points(self, tri, beta_blade) -> np.ndarray:
        o = np.array([0.0, 0.0])
        u = np.array([0.0, tri.u])
        apex = np.array([tri.c_m, tri.wu])
        cm_b = tri.cm_blocked
        apex_b = np.array([cm_b, tri.wu])

        blade_x = cm_b * 1.1
        beta_blade_deg = math.degrees(beta_blade)
        if abs(beta_blade_deg) < 2.0 or abs(beta_blade_deg - 180) < 2.0:
            blade_y = blade_x * 100 if beta_blade_deg > 0 else -blade_x * 100
        elif abs(beta_blade_deg - 90) < 2.0:
            blade_y = 0.0
        else:
            tan_beta = math.tan(beta_blade)
            blade_y = blade_x / tan_beta
        blade_end = np.array([blade_x, blade_y])
        return np.vstack([o, u, apex, apex_b, blade_end])

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

    def _draw_tri(self, ax, tri, beta_blade, title, global_y, global_x):
        """Draw triangle on given axes with improved readability and stability."""
        ax.set_facecolor('#1e1e2e')
        ax.set_title(title, color='#cdd6f4', fontsize=10, fontweight='bold')
        for sp in ax.spines.values():
            sp.set_color('#45475a')
        ax.tick_params(colors='#a6adc8', labelsize=8)
        
        # Geometry
        o = np.array([0.0, 0.0])
        u = np.array([0.0, tri.u])
        apex = np.array([tri.c_m, tri.wu])

        # Blocked geometry
        cm_b = tri.cm_blocked
        apex_b = np.array([cm_b, tri.wu])

        # Blade line - properly handle singularities at beta=0° and beta=90°
        blade_x = cm_b * 1.1
        beta_blade_deg = math.degrees(beta_blade)
        if abs(beta_blade_deg) < 2.0 or abs(beta_blade_deg - 180) < 2.0:
            blade_y = blade_x * 100 if beta_blade_deg > 0 else -blade_x * 100
        elif abs(beta_blade_deg - 90) < 2.0:
            blade_y = 0.0
        else:
            tan_beta = math.tan(beta_blade)
            blade_y = blade_x / tan_beta
        blade_end = np.array([blade_x, blade_y])

        ax.set_xlim(*global_x)
        ax.set_ylim(*global_y)
        
        # u baseline
        ax.annotate('', xy=u, xytext=o, arrowprops=dict(arrowstyle='->', color=self.COLOR_U, lw=1.5))
        bbox_style = dict(boxstyle="round,pad=0.2", facecolor="#1e1e2e", edgecolor="none", alpha=0.85)
        ax.text(0, tri.u / 2, 'u', fontsize=10, color=self.COLOR_U, ha='center', va='center', bbox=bbox_style)

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
        ax.text(w_mid[0], w_mid[1], 'w', fontsize=10, color=self.COLOR_W, ha='center', va='center', bbox=bbox_style)

        c_mid = (u + apex) / 2
        ax.text(c_mid[0], c_mid[1], 'c', fontsize=10, color=self.COLOR_C, ha='center', va='center', bbox=bbox_style)
        
        # Component spans (wu and cu)
        x_span = global_x[1] - global_x[0]
        y_span = global_y[1] - global_y[0]
        span_x = global_x[0] + 0.08 * x_span
        span_x_cu = global_x[0] + 0.12 * x_span

        # wu span: from 0 to wu
        if abs(tri.wu) > 0.1:
            ax.annotate('', xy=(span_x, tri.wu), xytext=(span_x, 0),
                        arrowprops=dict(arrowstyle='<->', color='#6c7086', lw=0.9))
            label_y = (tri.wu + 0.0) / 2
            ax.text(span_x, label_y, 'wu', fontsize=9, color=self.COLOR_W, ha='center', bbox=bbox_style)

        # cu span: from wu to u
        cu_val = tri.cu  # Use tri.cu directly for accuracy
        if abs(cu_val) > 0.1:
            ax.annotate('', xy=(span_x_cu, tri.u), xytext=(span_x_cu, tri.wu),
                        arrowprops=dict(arrowstyle='<->', color='#6c7086', lw=0.9))
            label_y = (tri.wu + tri.u) / 2
            ax.text(span_x_cu, label_y, 'cu', fontsize=9, color=self.COLOR_C, ha='center', bbox=bbox_style)

        # Angle arcs between u and c / u and w
        arc_r = 0.15 * min(x_span, y_span)
        u_dir = u
        w_dir = apex
        c_dir = apex
        self._draw_angle_arc(ax, o, u_dir, w_dir, arc_r, "β", self.COLOR_W)
        u_reverse = o
        self._draw_angle_arc(ax, u, u_reverse, c_dir, arc_r * 1.1, "α", self.COLOR_C)
        
        # Baseline
        ax.axhline(0, color='#45475a', lw=0.3, alpha=0.5)
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel("c_m", color='#a6adc8', fontsize=9)
        ax.set_ylabel("u", color='#a6adc8', fontsize=9)

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
