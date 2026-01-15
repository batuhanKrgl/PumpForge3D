"""
Step D: Additional Views / Analysis panel.

Shows curvature progression and area section plots.
CFturbo-inspired: togglable helper views for design validation.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QGroupBox, QCheckBox, QPushButton,
    QFrame, QScrollArea, QTabWidget
)
from PySide6.QtCore import Qt, Signal

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from pumpforge3d_core.geometry.inducer import InducerDesign


class AnalysisPlotWidget(QWidget):
    """A single analysis plot (curvature or area)."""
    
    def __init__(self, title: str, xlabel: str, ylabel: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the plot widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(6, 4), dpi=100, facecolor='#181825')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #181825;")
        layout.addWidget(self.canvas)
        
        self.ax = self.figure.add_subplot(111)
        self._style_axes()
    
    def _style_axes(self):
        """Apply dark theme styling to axes."""
        self.ax.set_facecolor('#1e1e2e')
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')
        self.ax.tick_params(colors='#a6adc8', labelsize=8)
        self.ax.xaxis.label.set_color('#cdd6f4')
        self.ax.yaxis.label.set_color('#cdd6f4')
        self.ax.set_title(self.title, color='#cdd6f4', fontsize=10)
        self.ax.set_xlabel(self.xlabel, fontsize=9)
        self.ax.set_ylabel(self.ylabel, fontsize=9)
        self.ax.grid(True, color='#313244', linestyle='-', linewidth=0.5, alpha=0.5)
    
    def plot_data(self, data_list: list, labels: list, colors: list):
        """
        Plot multiple data series.
        
        Args:
            data_list: List of (x, y) arrays
            labels: List of labels for legend
            colors: List of colors for each series
        """
        self.ax.clear()
        self._style_axes()
        
        for (x, y), label, color in zip(data_list, labels, colors):
            self.ax.plot(x, y, '-', color=color, linewidth=1.5, label=label)
        
        if len(data_list) > 1:
            self.ax.legend(loc='best', fontsize=8,
                          facecolor='#313244', edgecolor='#45475a',
                          labelcolor='#cdd6f4')
        
        self.figure.tight_layout()
        self.canvas.draw()


class StepDViews(QWidget):
    """
    Step D: Additional Views / Analysis.
    
    Provides curvature progression and area section plots.
    """
    
    def __init__(self, design: InducerDesign, parent=None):
        super().__init__(parent)
        self.design = design
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # Header
        header = QLabel("Step D: Analysis Views")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(header)
        
        description = QLabel(
            "View curvature progression and cross-sectional area along the meridional axis. "
            "These plots help validate the design quality."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #a6adc8; margin-bottom: 8px;")
        layout.addWidget(description)
        
        # Controls
        controls = QHBoxLayout()
        
        self.curv_check = QCheckBox("Show Curvature Progression")
        self.curv_check.setChecked(True)
        self.curv_check.toggled.connect(self._on_visibility_changed)
        controls.addWidget(self.curv_check)
        
        self.area_check = QCheckBox("Show Area Section")
        self.area_check.setChecked(True)
        self.area_check.toggled.connect(self._on_visibility_changed)
        controls.addWidget(self.area_check)
        
        controls.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(refresh_btn)
        
        layout.addLayout(controls)
        
        # Plot tabs
        self.tab_widget = QTabWidget()
        
        # Curvature plot
        self.curvature_plot = AnalysisPlotWidget(
            "Curvature Progression",
            "Parameter t",
            "Curvature κ [1/mm]"
        )
        self.tab_widget.addTab(self.curvature_plot, "Curvature")
        
        # Area plot
        self.area_plot = AnalysisPlotWidget(
            "Cross-Sectional Area Progression",
            "Axial Position Z [mm]",
            "Area [mm²]"
        )
        self.tab_widget.addTab(self.area_plot, "Area Section")
        
        layout.addWidget(self.tab_widget, 1)
        
        # Initial update
        self.refresh()
    
    def _on_visibility_changed(self):
        """Handle visibility toggle."""
        self.tab_widget.setTabVisible(0, self.curv_check.isChecked())
        self.tab_widget.setTabVisible(1, self.area_check.isChecked())
    
    def refresh(self):
        """Refresh all plots with current design data."""
        self._update_curvature_plot()
        self._update_area_plot()
    
    def _update_curvature_plot(self):
        """Update the curvature progression plot."""
        hub_curv = self.design.contour.hub_curve.compute_curvature_progression(100)
        tip_curv = self.design.contour.tip_curve.compute_curvature_progression(100)
        
        self.curvature_plot.plot_data(
            data_list=[
                (hub_curv[:, 0], hub_curv[:, 1]),
                (tip_curv[:, 0], tip_curv[:, 1]),
            ],
            labels=["Hub", "Tip"],
            colors=["#89b4fa", "#a6e3a1"]
        )
    
    def _update_area_plot(self):
        """Update the area section plot."""
        area_data = self.design.contour.compute_area_progression(50)
        
        self.area_plot.plot_data(
            data_list=[(area_data[:, 0], area_data[:, 1])],
            labels=["Cross-section"],
            colors=["#f5c2e7"]
        )
    
    def set_design(self, design: InducerDesign):
        """Set a new design and refresh."""
        self.design = design
        self.refresh()
