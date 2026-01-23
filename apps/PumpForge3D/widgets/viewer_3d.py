"""
3D Viewer widget for PumpForge3D.

Provides a persistent 3D view of the inducer geometry using PyVistaQt.
The viewer displays:
- Inlet/outlet circles (both hub and tip radii)
- Hub and tip meridional curves (in z-r plane)
- Leading and trailing edge curves
- Perspective toggle
"""

from typing import Dict, Optional
import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QFrame
)
from PySide6.QtCore import Qt

from pumpforge3d_core.geometry.inducer import InducerDesign

# Try to import pyvista - graceful fallback if not available
try:
    import pyvista as pv
    from pyvistaqt import QtInteractor
    PYVISTA_AVAILABLE = True
except ImportError:
    PYVISTA_AVAILABLE = False


class Viewer3DWidget(QWidget):
    """
    3D viewer for inducer geometry visualization.

    Uses PyVistaQt for interactive 3D rendering.
    Falls back to placeholder if pyvista is not installed.
    """

    # Colors for mean lines (jet-like colormap)
    MEAN_LINE_COLORS = [
        '#89b4fa',  # Blue (hub)
        '#74c7ec',  # Sapphire
        '#94e2d5',  # Teal
        '#a6e3a1',  # Green
        '#f9e2af',  # Yellow
        '#fab387',  # Peach
        '#f38ba8',  # Red (tip)
        '#cba6f7',  # Mauve
        '#b4befe',  # Lavender
        '#eba0ac',  # Maroon
    ]

    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._perspective_on = True  # Default: perspective projection
        self._visibility: Dict[str, bool] = {
            'hub': True,
            'tip': True,
            'leading_edge': True,
            'trailing_edge': True,
            'inlet_hub_circle': True,
            'inlet_tip_circle': True,
            'outlet_hub_circle': True,
            'outlet_tip_circle': True,
            'reference': True,
            'mean_lines': True,
        }
        self._actors: Dict[str, object] = {}
        self._mean_line_actors: Dict[str, object] = {}
        self._mean_lines_data: Optional[np.ndarray] = None  # Shape (n_j, n_i, 3)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar for viewer controls
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame { background: #181825; border-bottom: 1px solid #313244; }
            QToolButton { 
                background: transparent; 
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 4px 8px;
                color: #cdd6f4;
            }
            QToolButton:hover { background: #313244; }
            QToolButton:checked { background: #45475a; border-color: #89b4fa; }
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(4)
        
        # Perspective toggle
        self.perspective_btn = QToolButton()
        self.perspective_btn.setText("👁 Perspective")
        self.perspective_btn.setCheckable(True)
        self.perspective_btn.setChecked(True)
        self.perspective_btn.setToolTip("Toggle perspective projection (display-only)")
        self.perspective_btn.toggled.connect(self._toggle_perspective)
        toolbar_layout.addWidget(self.perspective_btn)
        
        # Reset camera button
        reset_btn = QToolButton()
        reset_btn.setText("🎥 Reset View")
        reset_btn.setToolTip("Reset camera to isometric view")
        reset_btn.clicked.connect(self.reset_camera)
        toolbar_layout.addWidget(reset_btn)
        
        toolbar_layout.addStretch()
        
        # Label for 3D viewer
        title = QLabel("3D Viewer")
        title.setStyleSheet("color: #89b4fa; font-weight: bold; padding: 0 8px;")
        toolbar_layout.addWidget(title)
        
        layout.addWidget(toolbar)
        
        if PYVISTA_AVAILABLE:
            # Create PyVista Qt interactor
            self.plotter = QtInteractor(self)
            self.plotter.set_background('#1e1e2e')
            self.plotter.add_axes(color='#cdd6f4')
            layout.addWidget(self.plotter.interactor)
            
            # Initial render
            self.update_geometry(self.design)
        else:
            # Fallback placeholder
            self.plotter = None
            placeholder = QLabel("3D Viewer\n(Install pyvista & pyvistaqt for 3D view)")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                background: #1e1e2e;
                color: #a6adc8;
                font-size: 14px;
                border-radius: 8px;
                padding: 20px;
            """)
            layout.addWidget(placeholder)
    
    def _toggle_perspective(self, on: bool):
        """Toggle between perspective and parallel projection (display-only)."""
        self._perspective_on = on
        self.perspective_btn.setText("👁 Perspective" if on else "⬜ Parallel")
        
        if PYVISTA_AVAILABLE and self.plotter is not None:
            try:
                # Save current camera position
                camera = self.plotter.camera.copy()
                
                if on:
                    # Perspective mode (disable parallel)
                    self.plotter.disable_parallel_projection()
                else:
                    # Parallel mode
                    self.plotter.enable_parallel_projection()
                
                # Restore camera position
                self.plotter.camera = camera
            except Exception:
                pass  # Gracefully handle any API issues
    
    def update_geometry(self, design: InducerDesign):
        """Update the 3D view with current geometry."""
        self.design = design
        
        if not PYVISTA_AVAILABLE or self.plotter is None:
            return
        
        # Clear previous actors
        self.plotter.clear_actors()
        self._actors.clear()
        
        dims = design.main_dims
        contour = design.contour
        
        # Sample curves
        n_samples = 100
        
        # Hub curve (in z-r plane, y=0)
        if self._visibility.get('hub', True):
            hub_pts = contour.hub_curve.evaluate_many(n_samples)
            hub_3d = np.zeros((n_samples, 3))
            hub_3d[:, 0] = hub_pts[:, 1]  # r -> x
            hub_3d[:, 2] = hub_pts[:, 0]  # z -> z
            hub_line = pv.lines_from_points(hub_3d)
            actor = self.plotter.add_mesh(
                hub_line, color='#89b4fa', line_width=3,
                render_lines_as_tubes=True, name='hub'
            )
            self._actors['hub'] = actor
        
        # Tip curve
        if self._visibility.get('tip', True):
            tip_pts = contour.tip_curve.evaluate_many(n_samples)
            tip_3d = np.zeros((n_samples, 3))
            tip_3d[:, 0] = tip_pts[:, 1]  # r -> x
            tip_3d[:, 2] = tip_pts[:, 0]  # z -> z
            tip_line = pv.lines_from_points(tip_3d)
            actor = self.plotter.add_mesh(
                tip_line, color='#a6e3a1', line_width=3,
                render_lines_as_tubes=True, name='tip'
            )
            self._actors['tip'] = actor
        
        # Leading edge
        if self._visibility.get('leading_edge', True):
            le_pts = contour.leading_edge.evaluate_many(50)
            le_3d = np.zeros((50, 3))
            le_3d[:, 0] = le_pts[:, 1]  # r -> x
            le_3d[:, 2] = le_pts[:, 0]  # z -> z
            le_line = pv.lines_from_points(le_3d)
            actor = self.plotter.add_mesh(
                le_line, color='#fab387', line_width=2,
                render_lines_as_tubes=True, name='leading_edge'
            )
            self._actors['leading_edge'] = actor
        
        # Trailing edge
        if self._visibility.get('trailing_edge', True):
            te_pts = contour.trailing_edge.evaluate_many(50)
            te_3d = np.zeros((50, 3))
            te_3d[:, 0] = te_pts[:, 1]  # r -> x
            te_3d[:, 2] = te_pts[:, 0]  # z -> z
            te_line = pv.lines_from_points(te_3d)
            actor = self.plotter.add_mesh(
                te_line, color='#f5c2e7', line_width=2,
                render_lines_as_tubes=True, name='trailing_edge'
            )
            self._actors['trailing_edge'] = actor
        
        # Inlet hub circle (z=0, r=r_h_in)
        if self._visibility.get('inlet_hub_circle', True):
            inlet_hub = self._create_circle(dims.r_h_in, 0.0)
            actor = self.plotter.add_mesh(
                inlet_hub, color='#89b4fa', line_width=1,
                render_lines_as_tubes=True, name='inlet_hub_circle',
                opacity=0.7
            )
            self._actors['inlet_hub_circle'] = actor
        
        # Inlet tip circle (z=0, r=r_t_in)
        if self._visibility.get('inlet_tip_circle', True):
            inlet_tip = self._create_circle(dims.r_t_in, 0.0)
            actor = self.plotter.add_mesh(
                inlet_tip, color='#cba6f7', line_width=2,
                render_lines_as_tubes=True, name='inlet_tip_circle'
            )
            self._actors['inlet_tip_circle'] = actor
        
        # Outlet hub circle (z=L, r=r_h_out)
        if self._visibility.get('outlet_hub_circle', True):
            outlet_hub = self._create_circle(dims.r_h_out, dims.L)
            actor = self.plotter.add_mesh(
                outlet_hub, color='#89b4fa', line_width=1,
                render_lines_as_tubes=True, name='outlet_hub_circle',
                opacity=0.7
            )
            self._actors['outlet_hub_circle'] = actor
        
        # Outlet tip circle (z=L, r=r_t_out)
        if self._visibility.get('outlet_tip_circle', True):
            outlet_tip = self._create_circle(dims.r_t_out, dims.L)
            actor = self.plotter.add_mesh(
                outlet_tip, color='#94e2d5', line_width=2,
                render_lines_as_tubes=True, name='outlet_tip_circle'
            )
            self._actors['outlet_tip_circle'] = actor
        
        # Reset camera to fit
        self.plotter.reset_camera()
        self.plotter.view_isometric()
    
    def _create_circle(self, radius: float, z: float, n_points: int = 64) -> 'pv.PolyData':
        """Create a circle in the x-y plane at given z."""
        theta = np.linspace(0, 2 * np.pi, n_points)
        x = radius * np.cos(theta)
        y = radius * np.sin(theta)
        z_arr = np.full(n_points, z)
        
        points = np.column_stack([x, y, z_arr])
        return pv.lines_from_points(points, close=True)
    
    def set_object_visibility(self, name: str, visible: bool):
        """
        Set visibility of a specific object (display-only, NOT undoable).
        
        Args:
            name: Object name ('hub', 'tip', 'leading_edge', 'trailing_edge', 
                   'inlet_hub_circle', 'inlet_tip_circle', 'outlet_hub_circle',
                   'outlet_tip_circle', 'reference')
            visible: Whether to show the object
        """
        self._visibility[name] = visible
        
        if PYVISTA_AVAILABLE and self.plotter is not None:
            # Re-render with updated visibility
            self.update_geometry(self.design)
    
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh."""
        self.design = design
        self.update_geometry(design)
    
    def reset_camera(self):
        """Reset camera to fit all geometry."""
        if PYVISTA_AVAILABLE and self.plotter is not None:
            self.plotter.reset_camera()
            self.plotter.view_isometric()
    
    def get_visible_objects(self) -> Dict[str, bool]:
        """Get current visibility state."""
        return self._visibility.copy()

    def update_mean_lines(self, xyz_lines: Optional[np.ndarray]):
        """
        Update 3D mean-line visualization.

        Args:
            xyz_lines: Mean-line coordinates, shape (n_j, n_i, 3) where
                      n_j = number of spans, n_i = meridional points.
                      Set to None to clear mean lines.
        """
        if not PYVISTA_AVAILABLE or self.plotter is None:
            return

        # Clear existing mean line actors
        for name, actor in list(self._mean_line_actors.items()):
            try:
                self.plotter.remove_actor(actor)
            except Exception:
                pass
        self._mean_line_actors.clear()

        self._mean_lines_data = xyz_lines

        if xyz_lines is None or not self._visibility.get('mean_lines', True):
            return

        n_j = xyz_lines.shape[0]

        for j in range(n_j):
            line_pts = xyz_lines[j]  # Shape (n_i, 3)

            # Skip if empty
            if line_pts.shape[0] < 2:
                continue

            # Create polyline
            line = pv.lines_from_points(line_pts)

            # Select color from colormap
            color = self.MEAN_LINE_COLORS[j % len(self.MEAN_LINE_COLORS)]

            # Line width: thicker for hub/tip
            is_hub = (j == 0)
            is_tip = (j == n_j - 1)
            line_width = 3 if (is_hub or is_tip) else 2

            actor_name = f'mean_line_{j}'
            actor = self.plotter.add_mesh(
                line,
                color=color,
                line_width=line_width,
                render_lines_as_tubes=True,
                name=actor_name,
            )
            self._mean_line_actors[actor_name] = actor

    def clear_mean_lines(self):
        """Remove all mean line visualizations."""
        self.update_mean_lines(None)

    def set_mean_lines_visibility(self, visible: bool):
        """Toggle mean lines visibility."""
        self._visibility['mean_lines'] = visible
        if self._mean_lines_data is not None:
            self.update_mean_lines(self._mean_lines_data if visible else None)
