"""
Blade Analysis Plots Widget - Analysis plots for blade properties tab.

Provides:
1. Beta distribution along span (inlet/outlet)
2. Slip angle vs span
3. Incidence angle vs span (if applicable)
4. Flow vs Blocked vs Blade beta comparison
"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QPushButton,
    QSizePolicy
)
from PySide6.QtCore import Signal, QTimer

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


class BladeAnalysisPlotWidget(QWidget):
    """
    Widget for displaying various blade property analysis plots.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = {}
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(75)
        self._update_timer.timeout.connect(self._redraw_from_state)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Control bar
        control_layout = QHBoxLayout()
        control_layout.setSpacing(6)

        # Plot selector
        plot_label = QLabel("Plot type:")
        plot_label.setStyleSheet("color: #cdd6f4; font-size: 10px;")
        control_layout.addWidget(plot_label)

        self.plot_selector = QComboBox()
        self.plot_selector.addItems([
            "Beta Distribution (Inlet/Outlet)",
            "Slip Angle vs Span",
            "Incidence Angle vs Span",
            "Flow vs Blocked vs Blade Beta"
        ])
        self.plot_selector.setMaximumWidth(250)
        self.plot_selector.setStyleSheet("""
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                padding: 4px;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }
        """)
        self.plot_selector.currentTextChanged.connect(self._on_plot_type_changed)
        control_layout.addWidget(self.plot_selector)

        # Fit button
        self.fit_button = QPushButton("Fit")
        self.fit_button.setMaximumWidth(60)
        self.fit_button.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #89b4fa;
                border: 1px solid #45475a;
                padding: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """)
        self.fit_button.clicked.connect(self._on_fit_clicked)
        control_layout.addWidget(self.fit_button)

        control_layout.addStretch()
        layout.addLayout(control_layout)

        # Plot canvas
        self.figure = Figure(figsize=(8, 5), dpi=100, facecolor='#181825')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background-color: #181825;")
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_facecolor('#1e1e2e')
        self.ax.tick_params(colors='#cdd6f4', labelsize=9)
        self.ax.spines['bottom'].set_color('#45475a')
        self.ax.spines['top'].set_color('#45475a')
        self.ax.spines['left'].set_color('#45475a')
        self.ax.spines['right'].set_color('#45475a')

        layout.addWidget(self.canvas)

        # Initial plot
        self._plot_beta_distribution()

    def _on_plot_type_changed(self, plot_type):
        """Handle plot type change."""
        self._schedule_update()

    def _on_fit_clicked(self):
        """Fit plot to data."""
        self.ax.relim()
        self.ax.autoscale_view()
        self.canvas.draw()

    def update_data(self, data: dict):
        """
        Update plot data.

        Expected data dict:
        {
            'spans': [0.0, 0.5, 1.0],  # Normalized span positions (0=hub, 1=tip)
            'beta_inlet': [25, 27, 30],  # Inlet beta angles
            'beta_outlet': [55, 57, 60],  # Outlet beta angles
            'beta_blade_inlet': [30, 32, 35],  # Blade angles inlet
            'beta_blade_outlet': [60, 62, 65],  # Blade angles outlet
            'beta_blocked_inlet': [26, 28, 31],  # Blocked beta inlet
            'beta_blocked_outlet': [56, 58, 61],  # Blocked beta outlet
            'slip_angles': [5, 5, 5],  # Slip angles
            'incidence_angles': [4, 4, 5],  # Incidence angles
        }
        """
        self._data = data
        self._schedule_update()

    def _schedule_update(self):
        """Throttle plot redraws to avoid excessive recomputation."""
        if self._update_timer.isActive():
            self._update_timer.stop()
        self._update_timer.start()

    def _redraw_from_state(self):
        """Redraw based on the current plot selector."""
        plot_type = self.plot_selector.currentText()
        if plot_type == "Beta Distribution (Inlet/Outlet)":
            self._plot_beta_distribution()
        elif plot_type == "Slip Angle vs Span":
            self._plot_slip_vs_span()
        elif plot_type == "Incidence Angle vs Span":
            self._plot_incidence_vs_span()
        elif plot_type == "Flow vs Blocked vs Blade Beta":
            self._plot_beta_comparison()

    def _plot_beta_distribution(self):
        """Plot beta distribution along span for inlet and outlet."""
        self.ax.clear()

        if not self._data or 'spans' not in self._data:
            # Sample data
            spans = np.array([0.0, 0.5, 1.0])
            beta_inlet = np.array([25, 27, 30])
            beta_outlet = np.array([55, 57, 60])
        else:
            spans = np.array(self._data['spans'])
            beta_inlet = np.array(self._data.get('beta_inlet', []))
            beta_outlet = np.array(self._data.get('beta_outlet', []))

        if len(beta_inlet) > 0:
            self.ax.plot(spans, beta_inlet, 'o-', color='#89b4fa', linewidth=2,
                        markersize=6, label='β Inlet')

        if len(beta_outlet) > 0:
            self.ax.plot(spans, beta_outlet, 's-', color='#f9e2af', linewidth=2,
                        markersize=6, label='β Outlet')

        self.ax.set_xlabel('Normalized Span (0=Hub, 1=Tip)', color='#cdd6f4', fontsize=10)
        self.ax.set_ylabel('Beta Angle [°]', color='#cdd6f4', fontsize=10)
        self.ax.set_title('Beta Distribution Along Span', color='#cdd6f4', fontsize=11, fontweight='bold')
        self.ax.legend(facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4', fontsize=9)
        self.ax.grid(True, alpha=0.2, color='#45475a')

        self.canvas.draw()

    def _plot_slip_vs_span(self):
        """Plot slip angle vs span."""
        self.ax.clear()

        if not self._data or 'spans' not in self._data:
            # Sample data
            spans = np.array([0.0, 0.5, 1.0])
            slip_angles = np.array([5.0, 5.0, 5.0])
        else:
            spans = np.array(self._data['spans'])
            slip_angles = np.array(self._data.get('slip_angles', []))

        if len(slip_angles) > 0:
            self.ax.plot(spans, slip_angles, 'o-', color='#a6e3a1', linewidth=2,
                        markersize=6, label='Slip angle δ')

        self.ax.set_xlabel('Normalized Span (0=Hub, 1=Tip)', color='#cdd6f4', fontsize=10)
        self.ax.set_ylabel('Slip Angle δ [°]', color='#cdd6f4', fontsize=10)
        self.ax.set_title('Slip Angle vs Span', color='#cdd6f4', fontsize=11, fontweight='bold')
        self.ax.legend(facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4', fontsize=9)
        self.ax.grid(True, alpha=0.2, color='#45475a')

        self.canvas.draw()

    def _plot_incidence_vs_span(self):
        """Plot incidence angle vs span."""
        self.ax.clear()

        if not self._data or 'spans' not in self._data:
            # Sample data
            spans = np.array([0.0, 0.5, 1.0])
            incidence_angles = np.array([0.0, 0.0, 0.0])
        else:
            spans = np.array(self._data['spans'])
            incidence_angles = np.array(self._data.get('incidence_angles', []))

        if len(incidence_angles) > 0:
            self.ax.plot(spans, incidence_angles, 'o-', color='#f38ba8', linewidth=2,
                        markersize=6, label='Incidence i')

        self.ax.axhline(y=0, color='#45475a', linestyle='--', linewidth=1)

        self.ax.set_xlabel('Normalized Span (0=Hub, 1=Tip)', color='#cdd6f4', fontsize=10)
        self.ax.set_ylabel('Incidence Angle i [°]', color='#cdd6f4', fontsize=10)
        self.ax.set_title('Incidence Angle vs Span', color='#cdd6f4', fontsize=11, fontweight='bold')
        self.ax.legend(facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4', fontsize=9)
        self.ax.grid(True, alpha=0.2, color='#45475a')

        self.canvas.draw()

    def _plot_beta_comparison(self):
        """Plot flow vs blocked vs blade beta comparison."""
        self.ax.clear()

        if not self._data or 'spans' not in self._data:
            # Sample data
            spans = np.array([0.0, 1.0])
            beta_flow_in = np.array([25, 30])
            beta_blocked_in = np.array([26, 31])
            beta_blade_in = np.array([30, 35])
            beta_flow_out = np.array([55, 60])
            beta_blocked_out = np.array([56, 61])
            beta_blade_out = np.array([60, 65])
        else:
            spans = np.array(self._data['spans'])
            beta_flow_in = np.array(self._data.get('beta_inlet', []))
            beta_blocked_in = np.array(self._data.get('beta_blocked_inlet', []))
            beta_blade_in = np.array(self._data.get('beta_blade_inlet', []))
            beta_flow_out = np.array(self._data.get('beta_outlet', []))
            beta_blocked_out = np.array(self._data.get('beta_blocked_outlet', []))
            beta_blade_out = np.array(self._data.get('beta_blade_outlet', []))

        # Inlet curves
        if len(beta_flow_in) > 0:
            self.ax.plot(spans, beta_flow_in, '-', color='#89b4fa', linewidth=1.5,
                        alpha=0.7, label='Flow β (Inlet)')
        if len(beta_blocked_in) > 0:
            self.ax.plot(spans, beta_blocked_in, '--', color='#89b4fa', linewidth=1.5,
                        alpha=0.9, label='Blocked β (Inlet)')
        if len(beta_blade_in) > 0:
            self.ax.plot(spans, beta_blade_in, '-', color='#89b4fa', linewidth=2.5,
                        alpha=1.0, label='Blade β_B (Inlet)')

        # Outlet curves
        if len(beta_flow_out) > 0:
            self.ax.plot(spans, beta_flow_out, '-', color='#f9e2af', linewidth=1.5,
                        alpha=0.7, label='Flow β (Outlet)')
        if len(beta_blocked_out) > 0:
            self.ax.plot(spans, beta_blocked_out, '--', color='#f9e2af', linewidth=1.5,
                        alpha=0.9, label='Blocked β (Outlet)')
        if len(beta_blade_out) > 0:
            self.ax.plot(spans, beta_blade_out, '-', color='#f9e2af', linewidth=2.5,
                        alpha=1.0, label='Blade β_B (Outlet)')

        self.ax.set_xlabel('Normalized Span (0=Hub, 1=Tip)', color='#cdd6f4', fontsize=10)
        self.ax.set_ylabel('Beta Angle [°]', color='#cdd6f4', fontsize=10)
        self.ax.set_title('Flow vs Blocked vs Blade Beta', color='#cdd6f4', fontsize=11, fontweight='bold')
        self.ax.legend(facecolor='#313244', edgecolor='#45475a', labelcolor='#cdd6f4',
                      fontsize=8, ncol=2)
        self.ax.grid(True, alpha=0.2, color='#45475a')

        self.canvas.draw()
