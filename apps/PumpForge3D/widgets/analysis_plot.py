"""
Analysis Plot Widget for PumpForge3D.

Provides curvature and area progression plots using Matplotlib.
"""

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer

from pumpforge3d_core.geometry.inducer import InducerDesign


class AnalysisPlotWidget(QWidget):
    """
    Widget for displaying analysis plots (curvature, area).
    
    Updates dynamically when geometry changes.
    """
    
    PLOT_TYPES = ["Curvature Progression", "Cross-Section Area"]
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._current_plot = 0
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(75)
        self._update_timer.timeout.connect(self.update_plot)
        self._setup_ui()
        self.update_plot()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Plot type selector
        selector_row = QHBoxLayout()
        selector_row.addWidget(QLabel("Plot:"))
        self.plot_selector = QComboBox()
        self.plot_selector.addItems(self.PLOT_TYPES)
        self.plot_selector.currentIndexChanged.connect(self._on_plot_type_changed)
        selector_row.addWidget(self.plot_selector)
        selector_row.addStretch()
        layout.addLayout(selector_row)
        
        # Matplotlib figure
        self.figure = Figure(figsize=(4, 3), facecolor='#1e1e2e')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(200)
        layout.addWidget(self.canvas)
        
        # Create axes
        self.ax = self.figure.add_subplot(111)
        self._style_axes()
    
    def _style_axes(self):
        """Apply dark theme styling to axes."""
        self.ax.set_facecolor('#1e1e2e')
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')
        self.ax.tick_params(colors='#cdd6f4', labelsize=8)
        self.ax.xaxis.label.set_color('#cdd6f4')
        self.ax.yaxis.label.set_color('#cdd6f4')
        self.ax.title.set_color('#cdd6f4')
        self.ax.grid(True, color='#313244', linestyle='-', linewidth=0.5, alpha=0.5)
    
    def _on_plot_type_changed(self, index: int):
        """Handle plot type selection change."""
        self._current_plot = index
        self.request_update()

    def request_update(self):
        """Throttle plot redraws to avoid excessive recomputation."""
        if self._update_timer.isActive():
            self._update_timer.stop()
        self._update_timer.start()
    
    def update_plot(self):
        """Update the current plot with latest geometry."""
        self.ax.clear()
        self._style_axes()
        
        if self._current_plot == 0:
            self._plot_curvature()
        else:
            self._plot_area()
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def _plot_curvature(self):
        """Plot curvature progression for hub and tip curves."""
        contour = self.design.contour
        n = 100
        
        # Hub curvature
        hub_curv = contour.hub_curve.compute_curvature_progression(n)
        self.ax.plot(hub_curv[:, 0], hub_curv[:, 1], 
                     color='#89b4fa', linewidth=2, label='Hub')
        
        # Tip curvature
        tip_curv = contour.tip_curve.compute_curvature_progression(n)
        self.ax.plot(tip_curv[:, 0], tip_curv[:, 1], 
                     color='#a6e3a1', linewidth=2, label='Tip')
        
        self.ax.set_xlabel('Parameter t', fontsize=9, color='#cdd6f4')
        self.ax.set_ylabel('Curvature (1/mm)', fontsize=9, color='#cdd6f4')
        self.ax.set_title('Curvature Progression', fontsize=10, color='#cdd6f4')
        self.ax.legend(loc='best', facecolor='#313244', edgecolor='#45475a',
                       labelcolor='#cdd6f4', fontsize=8)
    
    def _plot_area(self):
        """Plot cross-sectional area progression."""
        contour = self.design.contour
        n = 50
        
        area_data = contour.compute_area_progression(n)
        self.ax.plot(area_data[:, 0], area_data[:, 1] / 1000,  # Convert to cm²
                     color='#f9e2af', linewidth=2)
        
        self.ax.set_xlabel('Axial position z (mm)', fontsize=9, color='#cdd6f4')
        self.ax.set_ylabel('Area (cm²)', fontsize=9, color='#cdd6f4')
        self.ax.set_title('Cross-Section Area', fontsize=10, color='#cdd6f4')
        self.ax.fill_between(area_data[:, 0], 0, area_data[:, 1] / 1000,
                             alpha=0.3, color='#f9e2af')
    
    def set_design(self, design: InducerDesign):
        """Update with new design."""
        self.design = design
        self.request_update()
