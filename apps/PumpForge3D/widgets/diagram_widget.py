"""
Interactive 2D diagram widget for meridional contour visualization.

CFturbo-inspired features:
- Auto-fit/scaling with Fit View button
- Right-click popup menu on empty diagram area
- Hover highlighting for curves and control points
- Drag-and-drop control point editing
- Right-click on control points for numeric input
- Reference curve overlay (import polyline)
- Measure distance tool
"""

import numpy as np
from typing import Optional, Tuple, List, Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QMenu, QFileDialog, QMessageBox, QLabel
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QCursor

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

from pumpforge3d_core.geometry.bezier import BezierCurve4
from pumpforge3d_core.geometry.inducer import InducerDesign
from pumpforge3d_core.io.import_handler import import_polyline

from .numeric_input_dialog import NumericInputDialog


class DiagramWidget(QWidget):
    """
    Interactive 2D diagram for meridional contour editing.
    
    Signals:
        geometry_changed: Emitted when control points are modified
        point_selected: Emitted when a point is clicked (curve_name, point_index)
    """
    
    geometry_changed = Signal()
    point_selected = Signal(str, int)
    
    # Constants
    POINT_RADIUS = 8  # Control point display radius in pixels
    PICK_TOLERANCE = 10  # Pixel tolerance for picking points
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        
        self.design = design
        self.reference_curves: List[np.ndarray] = []
        
        # State
        self._selected_curve: Optional[str] = None
        self._selected_point: Optional[int] = None
        self._dragging = False
        self._dragging_anchor: Optional[str] = None  # 'le_hub', 'le_tip', 'te_hub', 'te_tip'
        self._measuring = False
        self._measure_start: Optional[Tuple[float, float]] = None
        self._hover_curve: Optional[str] = None
        self._hover_point: Optional[int] = None
        self._pending_hover_curve: Optional[str] = None
        self._pending_hover_point: Optional[int] = None
        
        # Display options
        self.show_grid = True
        self.show_control_points = True
        self.show_control_polygon = True
        self.show_edge_anchors = True  # Show edge attachment points on hub/tip
        
        # Mode options
        self.pan_mode = False  # When True, mouse drag pans, CP drag disabled
        self._pan_start = None  # (x, y) for pan start
        
        # Constraint options
        self.use_bounding_box = False  # If True, constrain CP movement to bounding box
        self.bbox_margin = 0.9  # CP stays within 90% of current bbox
        
        self._setup_ui()
        self._setup_plot()
        self._connect_events()
        self._setup_hover_throttle()

    def _setup_hover_throttle(self):
        """Setup a throttle to limit hover redraw frequency."""
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(33)
        self._hover_timer.timeout.connect(self._apply_hover_state)
    
    def _setup_ui(self):
        """Create the widget UI."""
        from PySide6.QtWidgets import QSizePolicy, QToolButton
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar with controls
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 2)
        toolbar.setSpacing(4)
        
        # Fit View
        fit_btn = QToolButton()
        fit_btn.setText("⤢")
        fit_btn.setToolTip("Fit View")
        fit_btn.setFixedSize(28, 24)
        fit_btn.clicked.connect(self.fit_view)
        toolbar.addWidget(fit_btn)
        
        # Note: Pan via middle mouse button (matplotlib style)
        
        toolbar.addWidget(QLabel(" | "))
        
        # Grid toggle
        self.grid_btn = QToolButton()
        self.grid_btn.setText("☐")
        self.grid_btn.setToolTip("Toggle Grid")
        self.grid_btn.setCheckable(True)
        self.grid_btn.setChecked(True)
        self.grid_btn.setFixedSize(28, 24)
        self.grid_btn.toggled.connect(lambda c: setattr(self, 'show_grid', c) or self.update_plot())
        toolbar.addWidget(self.grid_btn)
        
        # Control points toggle
        self.cp_btn = QToolButton()
        self.cp_btn.setText("◉")
        self.cp_btn.setToolTip("Toggle Control Points")
        self.cp_btn.setCheckable(True)
        self.cp_btn.setChecked(True)
        self.cp_btn.setFixedSize(28, 24)
        self.cp_btn.toggled.connect(lambda c: setattr(self, 'show_control_points', c) or self.update_plot())
        toolbar.addWidget(self.cp_btn)
        
        # Control polygon toggle
        self.polygon_btn = QToolButton()
        self.polygon_btn.setText("🔗")
        self.polygon_btn.setToolTip("Toggle Control Polygon")
        self.polygon_btn.setCheckable(True)
        self.polygon_btn.setChecked(True)
        self.polygon_btn.setFixedSize(28, 24)
        self.polygon_btn.toggled.connect(lambda c: setattr(self, 'show_control_polygon', c) or self.update_plot())
        toolbar.addWidget(self.polygon_btn)
        
        toolbar.addStretch()
        
        # Coordinate display
        self.coords_label = QLabel("Z: --, R: --")
        self.coords_label.setStyleSheet("color: #a6adc8; font-size: 10px; padding-right: 8px;")
        toolbar.addWidget(self.coords_label)
        
        layout.addLayout(toolbar)
        
        # Matplotlib figure - maximize size
        self.figure = Figure(figsize=(8, 6), dpi=100, facecolor='#181825')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #181825;")
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.canvas, 1)  # stretch factor 1
        
    def _setup_plot(self):
        """Initialize the matplotlib plot."""
        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#1e1e2e')
        
        # Style the axes
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')
        self.ax.tick_params(colors='#a6adc8', labelsize=8)
        self.ax.xaxis.label.set_color('#cdd6f4')
        self.ax.yaxis.label.set_color('#cdd6f4')
        
        self.ax.set_xlabel('Z (axial) [mm]', fontsize=9)
        self.ax.set_ylabel('R (radial) [mm]', fontsize=9)
        self.ax.set_aspect('equal')
        
        # Grid
        self.ax.grid(True, color='#313244', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # Plot elements (will be populated in update_plot)
        self._hub_line = None
        self._tip_line = None
        self._le_line = None
        self._te_line = None
        self._control_points = {}
        self._control_polygons = {}
        self._reference_lines = []
        self._measure_line = None
        self._measure_text = None
        
        self.update_plot()
    
    def _connect_events(self):
        """Connect matplotlib events."""
        self.canvas.mpl_connect('button_press_event', self._on_mouse_press)
        self.canvas.mpl_connect('button_release_event', self._on_mouse_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self._on_scroll)
    
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh the plot."""
        self.design = design
        self.update_plot()
    
    def update_plot(self):
        """Redraw all curves and control points."""
        self.ax.clear()
        
        # Re-apply styling
        self.ax.set_facecolor('#1e1e2e')
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')
        self.ax.tick_params(colors='#a6adc8', labelsize=8)
        self.ax.set_xlabel('Z (axial) [mm]', fontsize=9)
        self.ax.set_ylabel('R (radial) [mm]', fontsize=9)
        
        if self.show_grid:
            self.ax.grid(True, color='#313244', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # Get sampled curves
        samples = self.design.contour.get_all_sample_points(200)
        
        # Draw reference curves first (background)
        for ref_curve in self.reference_curves:
            self.ax.plot(ref_curve[:, 0], ref_curve[:, 1], 
                        '--', color='#fab387', linewidth=1, alpha=0.7,
                        label='Reference')
        
        # Draw curves
        curve_configs = [
            ('hub', samples['hub'], '#89b4fa', 'Hub'),
            ('tip', samples['tip'], '#a6e3a1', 'Tip'),
            ('leading', samples['leading'], '#f5c2e7', 'LE'),
            ('trailing', samples['trailing'], '#cba6f7', 'TE'),
        ]
        
        for name, points, color, label in curve_configs:
            # Highlight if hovered
            width = 2.5 if name == self._hover_curve else 2
            self.ax.plot(points[:, 0], points[:, 1], 
                        '-', color=color, linewidth=width, label=label)
        
        # Draw control polygons and points
        if self.show_control_points:
            self._draw_control_points('hub', self.design.contour.hub_curve, '#89b4fa')
            self._draw_control_points('tip', self.design.contour.tip_curve, '#a6e3a1')
            
            # Edge curves (if Bezier mode)
            if self.design.contour.leading_edge.bezier_curve:
                self._draw_control_points('leading', 
                    self.design.contour.leading_edge.bezier_curve, '#f5c2e7')
            if self.design.contour.trailing_edge.bezier_curve:
                self._draw_control_points('trailing',
                    self.design.contour.trailing_edge.bezier_curve, '#cba6f7')
        
        # Draw edge anchor markers (on hub/tip curves)
        if self.show_edge_anchors:
            self._draw_edge_anchors()
        
        # Draw measure line if active
        if self._measure_line:
            self.ax.plot(*zip(*self._measure_line), 'r--', linewidth=1)
        
        # Legend
        self.ax.legend(loc='upper right', fontsize=8, 
                      facecolor='#313244', edgecolor='#45475a',
                      labelcolor='#cdd6f4')
        
        # Equal aspect ratio but fill space by adjusting axis limits (CAD-style)
        # This extends the axis limits to match widget aspect ratio
        self.ax.set_aspect('equal', adjustable='datalim')
        
        # Force the figure to fill available space
        self.figure.tight_layout(pad=0.5)
        self.figure.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.1)
        self.canvas.draw()
    
    def _draw_control_points(self, curve_name: str, curve: BezierCurve4, color: str):
        """Draw control points and polygon for a Bezier curve."""
        points = curve.get_control_array()
        
        # Control polygon
        if self.show_control_polygon:
            self.ax.plot(points[:, 0], points[:, 1],
                        '--', color=color, linewidth=0.8, alpha=0.4)
        
        # Control points
        for i, pt in enumerate(curve.control_points):
            # Determine point appearance
            is_hovered = (curve_name == self._hover_curve and i == self._hover_point)
            is_selected = (curve_name == self._selected_curve and i == self._selected_point)
            is_locked = pt.is_locked
            
            if is_locked:
                marker = 's'  # Square for locked
                size = 8 if is_hovered else 6
            else:
                marker = 'o'  # Circle for movable
                size = 10 if is_hovered else 7
            
            edge_color = '#f38ba8' if is_selected else ('#ffffff' if is_hovered else color)
            face_color = color if not is_locked else '#45475a'
            
            self.ax.plot(pt.z, pt.r, marker, 
                        markersize=size,
                        markerfacecolor=face_color,
                        markeredgecolor=edge_color,
                        markeredgewidth=2 if is_selected or is_hovered else 1,
                        picker=True)
    
    def _draw_edge_anchors(self):
        """Draw draggable anchor markers where edges attach to hub/tip."""
        contour = self.design.contour
        
        # Leading edge anchors
        le_hub_pt = contour.hub_curve.evaluate(contour.leading_edge.hub_t)
        le_tip_pt = contour.tip_curve.evaluate(contour.leading_edge.tip_t)
        
        # Trailing edge anchors  
        te_hub_pt = contour.hub_curve.evaluate(contour.trailing_edge.hub_t)
        te_tip_pt = contour.tip_curve.evaluate(contour.trailing_edge.tip_t)
        
        # Draw anchor markers (diamonds)
        anchors = [
            ('le_hub', le_hub_pt, '#f5c2e7'),
            ('le_tip', le_tip_pt, '#f5c2e7'),
            ('te_hub', te_hub_pt, '#cba6f7'),
            ('te_tip', te_tip_pt, '#cba6f7'),
        ]
        
        for name, (z, r), color in anchors:
            is_hovered = (self._hover_curve == name)
            size = 10 if is_hovered else 7
            self.ax.plot(z, r, 'D',  # Diamond marker
                        markersize=size,
                        markerfacecolor=color,
                        markeredgecolor='#ffffff' if is_hovered else color,
                        markeredgewidth=2 if is_hovered else 1,
                        alpha=0.8)
    
    def fit_view(self):
        """Fit the view to show all geometry."""
        samples = self.design.contour.get_all_sample_points(50)
        
        all_points = np.vstack([
            samples['hub'], samples['tip'],
            samples['leading'], samples['trailing']
        ])
        
        z_min, z_max = all_points[:, 0].min(), all_points[:, 0].max()
        r_min, r_max = all_points[:, 1].min(), all_points[:, 1].max()
        
        # Add margin
        z_margin = (z_max - z_min) * 0.1
        r_margin = (r_max - r_min) * 0.1
        
        self.ax.set_xlim(z_min - z_margin, z_max + z_margin)
        self.ax.set_ylim(r_min - r_margin, r_max + r_margin)
        
        self.canvas.draw()
    
    def _toggle_pan_mode(self, enabled: bool):
        """Toggle pan mode on/off."""
        self.pan_mode = enabled
        self._pan_start = None
        # Visual feedback
        if enabled:
            self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
    
    def _on_mouse_press(self, event):
        """Handle mouse press event."""
        if event.inaxes != self.ax:
            return
        
        if event.button == 2:  # Middle click = pan
            self._pan_start = (event.xdata, event.ydata)
            self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        
        if event.button == 1:  # Left click
            if self._measuring:
                self._measure_start = (event.xdata, event.ydata)
                return
            
            # Try to pick a control point or edge anchor
            curve, idx = self._pick_control_point(event.xdata, event.ydata)
            anchor_name = self._pick_edge_anchor(event.xdata, event.ydata)
            
            if curve and idx is not None:
                # Dragging a control point
                self._selected_curve = curve
                self._selected_point = idx
                self._dragging = True
                self._dragging_anchor = None
                self.point_selected.emit(curve, idx)
                self.update_plot()
            elif anchor_name:
                # Dragging an edge anchor
                self._dragging_anchor = anchor_name
                self._dragging = True
                self._selected_curve = None
                self._selected_point = None
        
        elif event.button == 3:  # Right click
            self._show_context_menu(event)
    
    def _on_mouse_release(self, event):
        """Handle mouse release event."""
        if self._pan_start:
            self._pan_start = None
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
            return
        
        if self._dragging:
            self._dragging = False
            self._dragging_anchor = None
            self.geometry_changed.emit()
        
        if self._measuring and self._measure_start and event.inaxes == self.ax:
            end = (event.xdata, event.ydata)
            distance = np.sqrt(
                (end[0] - self._measure_start[0])**2 + 
                (end[1] - self._measure_start[1])**2
            )
            QMessageBox.information(
                self, "Measure Distance",
                f"Distance: {distance:.3f} mm"
            )
            self._measuring = False
            self._measure_start = None
            self._measure_line = None
            self.update_plot()
    
    def _on_mouse_move(self, event):
        """Handle mouse move event."""
        if event.inaxes != self.ax:
            self.coords_label.setText("Z: --, R: --")
            return
        
        # Update coordinate display
        self.coords_label.setText(f"Z: {event.xdata:.2f}, R: {event.ydata:.2f}")
        
        # Pan - move view (middle button drag)
        if self._pan_start:
            dx = self._pan_start[0] - event.xdata
            dy = self._pan_start[1] - event.ydata
            
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            self.ax.set_xlim(xlim[0] + dx, xlim[1] + dx)
            self.ax.set_ylim(ylim[0] + dy, ylim[1] + dy)
            
            self.canvas.draw()
            return
        
        if self._dragging and self._selected_curve and self._selected_point is not None:
            # Update control point position with constraints
            curve = self._get_curve(self._selected_curve)
            if curve and not curve.control_points[self._selected_point].is_locked:
                new_z, new_r = event.xdata, event.ydata
                
                # Apply bounding box constraint
                if self.use_bounding_box:
                    new_z, new_r = self._apply_bbox_constraint(new_z, new_r)
                
                # Apply angle lock constraint
                pt = curve.control_points[self._selected_point]
                if pt.angle_locked and self._selected_point in [1, 3]:
                    new_z, new_r = self._apply_angle_constraint(
                        curve, self._selected_point, new_z, new_r
                    )
                
                curve.set_point(self._selected_point, new_z, new_r)
                
                # Recompute edge curves when hub/tip changes
                if self._selected_curve in ['hub', 'tip']:
                    contour = self.design.contour
                    contour.leading_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
                    contour.trailing_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
                
                # Constrain LE/TE endpoints (P0, P2) to stay on hub/tip curves
                if self._selected_curve in ['leading', 'trailing'] and self._selected_point in [0, 2]:
                    contour = self.design.contour
                    # P0 = hub endpoint, P2 = tip endpoint
                    target_curve = contour.hub_curve if self._selected_point == 0 else contour.tip_curve
                    
                    # Find closest t on curve
                    best_t = 0.0
                    min_dist = float('inf')
                    for t in np.linspace(0, 1, 100):
                        pos = target_curve.evaluate(t)
                        dist = (pos[0] - new_z)**2 + (pos[1] - new_r)**2
                        if dist < min_dist:
                            min_dist = dist
                            best_t = t
                    
                    # Snap endpoint to curve
                    snapped = target_curve.evaluate(best_t)
                    curve.set_point(self._selected_point, snapped[0], snapped[1])
                    
                    # Update the edge anchor t value
                    edge = contour.leading_edge if self._selected_curve == 'leading' else contour.trailing_edge
                    if self._selected_point == 0:
                        edge.hub_t = best_t
                    else:
                        edge.tip_t = best_t
                
                self.update_plot()
        
        elif self._dragging and self._dragging_anchor:
            # Drag edge anchor along hub/tip curve
            self._update_edge_anchor(self._dragging_anchor, event.xdata, event.ydata)
            self.update_plot()
        
        elif self._measuring and self._measure_start:
            # Update measure line
            self._measure_line = [self._measure_start, (event.xdata, event.ydata)]
            self.update_plot()
        
        else:
            # Hover detection
            curve, idx = self._pick_control_point(event.xdata, event.ydata)
            if (curve, idx) != (self._hover_curve, self._hover_point):
                self._pending_hover_curve = curve
                self._pending_hover_point = idx
                if not self._hover_timer.isActive():
                    self._hover_timer.start()

    def _apply_hover_state(self):
        """Apply pending hover state and redraw at a throttled rate."""
        if (self._pending_hover_curve, self._pending_hover_point) != (
            self._hover_curve, self._hover_point
        ):
            self._hover_curve = self._pending_hover_curve
            self._hover_point = self._pending_hover_point
            self.update_plot()
    
    def _on_scroll(self, event):
        """Handle scroll event for zooming."""
        if event.inaxes != self.ax:
            return
        
        scale_factor = 1.2 if event.button == 'down' else 1/1.2
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Zoom centered on cursor position
        xdata, ydata = event.xdata, event.ydata
        
        new_xlim = [
            xdata - (xdata - xlim[0]) * scale_factor,
            xdata + (xlim[1] - xdata) * scale_factor
        ]
        new_ylim = [
            ydata - (ydata - ylim[0]) * scale_factor,
            ydata + (ylim[1] - ydata) * scale_factor
        ]
        
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw()
    
    def _pick_control_point(
        self, x: float, y: float
    ) -> Tuple[Optional[str], Optional[int]]:
        """
        Find the control point nearest to the given coordinates.
        
        Returns (curve_name, point_index) or (None, None) if nothing found.
        """
        # Convert tolerance from pixels to data coordinates
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Approximate pixel-to-data conversion
        bbox = self.ax.get_window_extent()
        px_to_data_x = (xlim[1] - xlim[0]) / bbox.width
        px_to_data_y = (ylim[1] - ylim[0]) / bbox.height
        tol = self.PICK_TOLERANCE * max(px_to_data_x, px_to_data_y)
        
        curves = [
            ('hub', self.design.contour.hub_curve),
            ('tip', self.design.contour.tip_curve),
        ]
        
        if self.design.contour.leading_edge.bezier_curve:
            curves.append(('leading', self.design.contour.leading_edge.bezier_curve))
        if self.design.contour.trailing_edge.bezier_curve:
            curves.append(('trailing', self.design.contour.trailing_edge.bezier_curve))
        
        min_dist = float('inf')
        best_curve = None
        best_idx = None
        
        for curve_name, curve in curves:
            for i, pt in enumerate(curve.control_points):
                # Skip hub/tip endpoints (P0, P4) - they conflict with edge anchors
                if curve_name in ['hub', 'tip'] and i in [0, len(curve.control_points) - 1]:
                    continue
                    
                dist = np.sqrt((x - pt.z)**2 + (y - pt.r)**2)
                if dist < min_dist and dist < tol:
                    min_dist = dist
                    best_curve = curve_name
                    best_idx = i
        
        return best_curve, best_idx
    
    def _get_curve(self, curve_name: str) -> Optional[BezierCurve4]:
        """Get Bezier curve by name."""
        if curve_name == 'hub':
            return self.design.contour.hub_curve
        elif curve_name == 'tip':
            return self.design.contour.tip_curve
        elif curve_name == 'leading':
            return self.design.contour.leading_edge.bezier_curve
        elif curve_name == 'trailing':
            return self.design.contour.trailing_edge.bezier_curve
        return None
    
    def _pick_edge_anchor(self, x: float, y: float) -> Optional[str]:
        """
        Find the edge anchor nearest to the given coordinates.
        
        Returns anchor name ('le_hub', 'le_tip', 'te_hub', 'te_tip') or None.
        """
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        bbox = self.ax.get_window_extent()
        px_to_data_x = (xlim[1] - xlim[0]) / bbox.width
        px_to_data_y = (ylim[1] - ylim[0]) / bbox.height
        tol = self.PICK_TOLERANCE * max(px_to_data_x, px_to_data_y)
        
        contour = self.design.contour
        
        # Get edge anchor positions
        anchors = [
            ('le_hub', contour.hub_curve.evaluate(contour.leading_edge.hub_t)),
            ('le_tip', contour.tip_curve.evaluate(contour.leading_edge.tip_t)),
            ('te_hub', contour.hub_curve.evaluate(contour.trailing_edge.hub_t)),
            ('te_tip', contour.tip_curve.evaluate(contour.trailing_edge.tip_t)),
        ]
        
        min_dist = float('inf')
        best_anchor = None
        
        for name, (z, r) in anchors:
            dist = np.sqrt((x - z)**2 + (y - r)**2)
            if dist < min_dist and dist < tol:
                min_dist = dist
                best_anchor = name
        
        return best_anchor
    
    def _update_edge_anchor(self, anchor_name: str, x: float, y: float):
        """
        Update edge anchor position by finding closest t on curve.
        
        anchor_name: 'le_hub', 'le_tip', 'te_hub', 'te_tip'
        """
        contour = self.design.contour
        
        # Determine which curve and edge
        if 'hub' in anchor_name:
            curve = contour.hub_curve
        else:
            curve = contour.tip_curve
        
        # Find closest t parameter
        best_t = 0.0
        min_dist = float('inf')
        
        for t in np.linspace(0, 1, 100):
            pt = curve.evaluate(t)
            dist = (pt[0] - x)**2 + (pt[1] - y)**2
            if dist < min_dist:
                min_dist = dist
                best_t = t
        
        # Clamp t to valid range (e.g. 0.05 to 0.95)
        best_t = max(0.05, min(0.95, best_t))
        
        # Update the appropriate edge anchor
        if anchor_name == 'le_hub':
            contour.leading_edge.hub_t = best_t
        elif anchor_name == 'le_tip':
            contour.leading_edge.tip_t = best_t
        elif anchor_name == 'te_hub':
            contour.trailing_edge.hub_t = best_t
        elif anchor_name == 'te_tip':
            contour.trailing_edge.tip_t = best_t
        
        # Recompute edge curves
        contour.leading_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
        contour.trailing_edge.update_from_meridional(contour.hub_curve, contour.tip_curve)
    
    def _apply_bbox_constraint(self, z: float, r: float) -> Tuple[float, float]:
        """Constrain point to bounding box derived from hub/tip endpoints."""
        contour = self.design.contour
        
        # Get hub/tip curve endpoints for dynamic limits
        hub_pts = contour.hub_curve.get_control_array()
        tip_pts = contour.tip_curve.get_control_array()
        
        # Z limits from curve endpoints (P0 and P4)
        z_min = min(hub_pts[0, 0], hub_pts[-1, 0], tip_pts[0, 0], tip_pts[-1, 0])
        z_max = max(hub_pts[0, 0], hub_pts[-1, 0], tip_pts[0, 0], tip_pts[-1, 0])
        
        # R limits from curve endpoints
        r_min = min(hub_pts[0, 1], hub_pts[-1, 1])  # Hub radii
        r_max = max(tip_pts[0, 1], tip_pts[-1, 1])  # Tip radii
        
        # Apply margin (allow slight expansion)
        m = self.bbox_margin
        z_pad = (z_max - z_min) * (1 - m) / 2
        r_pad = (r_max - r_min) * (1 - m) / 2
        
        # Clamp with margin
        z = max(z_min + z_pad, min(z, z_max - z_pad))
        r = max(r_min + r_pad, min(r, r_max - r_pad))
        
        return z, r
    
    def _apply_angle_constraint(
        self, curve: BezierCurve4, idx: int, z: float, r: float
    ) -> Tuple[float, float]:
        """
        Constrain point movement to preserve tangent angle.
        
        For P1: move along line from P0 at locked angle
        For P3: move along line from P4 at locked angle
        """
        points = curve.get_control_array()
        pt = curve.control_points[idx]
        
        if idx == 1:
            anchor = points[0]  # P0
        elif idx == 3:
            anchor = points[4]  # P4
        else:
            return z, r
        
        # Use locked_angle if set, otherwise use current direction
        locked_angle = getattr(pt, 'locked_angle', None)
        if locked_angle is not None and locked_angle != 0.0:
            # Convert angle (degrees) to direction vector
            import math
            angle_rad = math.radians(locked_angle)
            dir_z = math.cos(angle_rad)
            dir_r = math.sin(angle_rad)
        else:
            # Use current point direction
            orig_dz = pt.z - anchor[0]
            orig_dr = pt.r - anchor[1]
            
            orig_len = np.sqrt(orig_dz**2 + orig_dr**2)
            if orig_len < 1e-9:
                return z, r
            
            dir_z = orig_dz / orig_len
            dir_r = orig_dr / orig_len
        
        # Direction from anchor to target
        dz = z - anchor[0]
        dr = r - anchor[1]
        
        # Project new position onto the line
        projection = dz * dir_z + dr * dir_r
        
        new_z = anchor[0] + projection * dir_z
        new_r = anchor[1] + projection * dir_r
        
        return new_z, new_r
    
    def _show_context_menu(self, event):
        """Show context menu based on click location."""
        # Check if clicking on a control point
        curve, idx = self._pick_control_point(event.xdata, event.ydata)
        
        if curve and idx is not None:
            self._show_point_context_menu(curve, idx, event)
        else:
            self._show_diagram_context_menu(event)
    
    def _show_diagram_context_menu(self, event):
        """Show context menu for empty diagram area."""
        menu = QMenu(self)
        
        # Zoom/View actions
        fit_action = menu.addAction("Fit View")
        fit_action.triggered.connect(self.fit_view)
        
        menu.addSeparator()
        
        # Measure tool
        measure_action = menu.addAction("Measure Distance")
        measure_action.triggered.connect(lambda: setattr(self, '_measuring', True))
        
        menu.addSeparator()
        
        # Import polyline
        import_action = menu.addAction("Import Reference Polyline...")
        import_action.triggered.connect(self._import_polyline)
        
        if self.reference_curves:
            clear_ref_action = menu.addAction("Clear Reference Curves")
            clear_ref_action.triggered.connect(self._clear_reference_curves)
        
        menu.addSeparator()
        
        # Save image
        save_action = menu.addAction("Save Image...")
        save_action.triggered.connect(self._save_image)
        
        menu.addSeparator()
        
        # Display options
        grid_action = menu.addAction("Show Grid")
        grid_action.setCheckable(True)
        grid_action.setChecked(self.show_grid)
        grid_action.triggered.connect(lambda c: self._toggle_grid(c))
        
        cp_action = menu.addAction("Show Control Points")
        cp_action.setCheckable(True)
        cp_action.setChecked(self.show_control_points)
        cp_action.triggered.connect(lambda c: self._toggle_control_points(c))
        
        # Show at cursor
        menu.exec(QCursor.pos())
    
    def _show_point_context_menu(self, curve_name: str, point_idx: int, event):
        """Show context menu for a control point."""
        curve = self._get_curve(curve_name)
        if not curve:
            return
        
        pt = curve.control_points[point_idx]
        
        menu = QMenu(self)
        
        # Point info header
        header = menu.addAction(f"P{point_idx} ({curve_name.capitalize()})")
        header.setEnabled(False)
        
        menu.addSeparator()
        
        # Edit coordinates
        edit_action = menu.addAction("Edit Coordinates...")
        edit_action.triggered.connect(
            lambda: self._edit_point_coordinates(curve_name, point_idx)
        )
        
        if pt.is_locked:
            locked_info = menu.addAction("⚠ Point is locked (endpoint)")
            locked_info.setEnabled(False)
        
        menu.addSeparator()
        
        # Angle lock toggle (for P1 and P3)
        if point_idx in [1, 3] and not pt.is_locked:
            angle_action = menu.addAction("Lock Tangent Angle")
            angle_action.setCheckable(True)
            angle_action.setChecked(pt.angle_locked)
            angle_action.triggered.connect(
                lambda c: self._toggle_angle_lock(curve_name, point_idx, c)
            )
        
        menu.exec(QCursor.pos())
    
    def _edit_point_coordinates(self, curve_name: str, point_idx: int):
        """Open numeric input dialog for a control point."""
        curve = self._get_curve(curve_name)
        if not curve:
            return
        
        pt = curve.control_points[point_idx]
        
        if pt.is_locked:
            QMessageBox.information(
                self, "Locked Point",
                "This point is locked and cannot be edited directly.\n"
                "Change the main dimensions to move this endpoint."
            )
            return
        
        # Calculate current angle for P1/P3 from tangent direction
        import math
        current_angle = getattr(pt, 'locked_angle', 0.0)
        if point_idx in [1, 3] and current_angle == 0.0:
            # Calculate from current direction
            points = curve.get_control_array()
            if point_idx == 1:
                anchor = points[0]  # P0
            else:
                anchor = points[4]  # P4
            dz = pt.z - anchor[0]
            dr = pt.r - anchor[1]
            if abs(dz) > 1e-9 or abs(dr) > 1e-9:
                current_angle = math.degrees(math.atan2(dr, dz))
        
        # Use new popup API with angle lock support
        accepted, new_z, new_r, angle_locked, angle_value = NumericInputDialog.get_coordinates(
            pt.z, pt.r,
            f"{curve_name.capitalize()} P{point_idx}",
            self,
            curve_name=curve_name,
            point_index=point_idx,
            angle_locked=pt.angle_locked,
            angle_value=current_angle
        )
        
        if accepted:
            # Apply angle lock and value if changed
            if point_idx in [1, 3]:
                pt.angle_locked = angle_locked
                pt.locked_angle = angle_value
                
                # If angle lock is enabled, move point to the specified angle
                if angle_locked:
                    import math
                    points = curve.get_control_array()
                    if point_idx == 1:
                        anchor = points[0]  # P0
                    else:
                        anchor = points[4]  # P4
                    
                    # Calculate current distance from anchor
                    dist = math.sqrt((pt.z - anchor[0])**2 + (pt.r - anchor[1])**2)
                    
                    # Move point to new angle at same distance
                    angle_rad = math.radians(angle_value)
                    new_z = anchor[0] + dist * math.cos(angle_rad)
                    new_r = anchor[1] + dist * math.sin(angle_rad)
            
            curve.set_point(point_idx, new_z, new_r)
            self.update_plot()
            self.geometry_changed.emit()
    
    def _toggle_angle_lock(self, curve_name: str, point_idx: int, locked: bool):
        """Toggle angle lock for a control point."""
        curve = self._get_curve(curve_name)
        if curve:
            curve.control_points[point_idx].angle_locked = locked
            self.update_plot()
    
    def _toggle_grid(self, show: bool):
        """Toggle grid display."""
        self.show_grid = show
        self.update_plot()
    
    def _toggle_control_points(self, show: bool):
        """Toggle control points display."""
        self.show_control_points = show
        self.update_plot()
    
    def _import_polyline(self):
        """Import a reference polyline from file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Reference Polyline",
            "", "CSV/Text files (*.csv *.txt);;All files (*.*)"
        )
        
        if path:
            try:
                points = import_polyline(Path(path))
                if points:
                    self.reference_curves.append(np.array(points))
                    self.update_plot()
                else:
                    QMessageBox.warning(self, "Import Error", 
                                       "No valid points found in file.")
            except Exception as e:
                QMessageBox.warning(self, "Import Error", str(e))
    
    def _clear_reference_curves(self):
        """Clear all reference curves."""
        self.reference_curves.clear()
        self.update_plot()
    
    def _save_image(self):
        """Save the diagram as an image."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Diagram Image",
            "meridional_diagram.png",
            "PNG Image (*.png);;SVG Vector (*.svg);;PDF Document (*.pdf)"
        )
        
        if path:
            self.figure.savefig(
                path, 
                facecolor=self.figure.get_facecolor(),
                edgecolor='none',
                dpi=150
            )
