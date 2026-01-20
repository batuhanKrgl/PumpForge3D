"""
Combined Beta Editor + Velocity Triangle Widget.

This module combines the Beta Distribution Editor with the Velocity Triangle
visualization as a single standalone widget.

Layout:
- Left: Beta table + controls
- Right (vertical split):
  - Top: β-θ plot
  - Bottom: 2×2 velocity triangles
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox
)
from PySide6.QtCore import Qt

from apps.PumpForge3D.widgets.beta_editor_widget import BetaDistributionEditorWidget
from apps.PumpForge3D.widgets.velocity_triangle_widget import VelocityTriangleWidget


class BetaTriangleEditorWidget(QWidget):
    """
    Combined widget with:
    - Left: Beta Table + controls
    - Right: β-θ plot (top) + 2×2 Velocity Triangles (bottom)
    
    Changes to beta values automatically update velocity triangles.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._setup_ui()
        self._connect_signals()
        self._sync_beta_to_triangles()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Left: Beta editor (table only, we'll use its signals)
        self.beta_widget = BetaDistributionEditorWidget()
        layout.addWidget(self.beta_widget, 0)  # Don't stretch
        
        # Right: Vertical splitter with β-θ plot and triangles
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Note: We can't easily extract the plot from beta_widget.
        # Instead, we'll put the triangle widget in the right panel
        # and let the beta_widget be its own thing on the left
        
        # 2×2 Velocity triangles (takes full right panel)
        triangle_group = QGroupBox("Velocity Triangles")
        triangle_layout = QVBoxLayout(triangle_group)
        triangle_layout.setContentsMargins(2, 8, 2, 2)
        self.triangle_widget = VelocityTriangleWidget()
        self.triangle_widget.setMinimumHeight(400)
        triangle_layout.addWidget(self.triangle_widget)
        
        layout.addWidget(triangle_group, 1)  # Stretch to fill
    
    def _connect_signals(self):
        """Connect signals between widgets."""
        # When beta model changes, update triangles
        self.beta_widget.modelChanged.connect(self._sync_beta_to_triangles)
    
    def _sync_beta_to_triangles(self):
        """Sync beta values from table to velocity triangles."""
        model = self.beta_widget.get_model()
        
        # Hub = row 0, Tip = row N-1
        beta_in_hub = model.beta_in[0]
        beta_in_tip = model.beta_in[-1]
        beta_out_hub = model.beta_out[0]
        beta_out_tip = model.beta_out[-1]
        
        self.triangle_widget.set_beta_values(
            beta_in_hub, beta_in_tip,
            beta_out_hub, beta_out_tip
        )
    
    # Public API
    def get_beta_widget(self) -> BetaDistributionEditorWidget:
        """Get the beta editor widget."""
        return self.beta_widget
    
    def get_triangle_widget(self) -> VelocityTriangleWidget:
        """Get the velocity triangle widget."""
        return self.triangle_widget


# Standalone demo
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background-color: #1e1e2e; color: #cdd6f4; font-family: 'Segoe UI'; font-size: 11px; }
        QGroupBox { border: 1px solid #45475a; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
        QTableWidget { background-color: #181825; gridline-color: #313244; border: 1px solid #313244; }
        QHeaderView::section { background-color: #313244; color: #cdd6f4; padding: 4px; border: none; }
        QSpinBox, QDoubleSpinBox { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; padding: 2px 4px; }
        QToolButton { background-color: #313244; border: 1px solid #45475a; border-radius: 4px; }
        QToolButton:hover { background-color: #45475a; }
        QSplitter::handle { background-color: #45475a; height: 3px; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Beta + Velocity Triangle Editor")
    window.resize(1100, 800)
    
    widget = BetaTriangleEditorWidget()
    window.setCentralWidget(widget)
    
    window.show()
    sys.exit(app.exec())
