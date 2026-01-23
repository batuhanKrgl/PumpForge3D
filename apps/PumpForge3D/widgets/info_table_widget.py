"""
Info Table Widget - Redesigned velocity triangle information display.

Layout based on CFturbo-style info table:
- Left section: Hub (Leading edge | Trailing edge)
- Separator
- Right section: Shroud/Tip (Leading edge | Trailing edge)
- Merged cells for single-value parameters at bottom
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QSizePolicy, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from pumpforge3d_core.analysis.turbomachinery_calc import InfoTableData


class InfoTableWidget(QWidget):
    """
    Info table widget displaying velocity triangle data in CFturbo style.

    Layout:
    ┌──────────────────────────┬──────────────────────────┐
    │          @Hub            │        @Shroud           │
    ├────────────┬─────────────┼────────────┬─────────────┤
    │ Leading    │ Trailing    │ Leading    │ Trailing    │
    │ edge       │ edge        │ edge       │ edge        │
    ├────────────┼─────────────┼────────────┼─────────────┤
    │  values    │   values    │  values    │   values    │
    ├────────────┴─────────────┼────────────┴─────────────┤
    │    merged values         │     merged values        │
    └──────────────────────────┴──────────────────────────┘
    """

    dataChanged = Signal()

    # Row definitions: (key, label, decimals, is_merged)
    # is_merged=True means the value spans both inlet/outlet columns
    ROW_DEFS = [
        ('z', 'z', 2, False),           # Axial position
        ('r', 'r', 3, False),           # Radial coordinate
        ('d', 'd', 2, False),           # Diameter
        ('alpha', 'αF', 1, False),      # Absolute flow angle
        ('beta', 'βF', 1, False),       # Relative flow angle
        ('u', 'u', 1, False),           # Circumferential velocity
        ('cm', 'cm', 1, False),         # Meridional velocity
        ('cu', 'cu', 1, False),         # Circumferential component of c
        ('cr', 'cr', 1, False),         # Radial component of c
        ('cz', 'cz', 1, False),         # Axial component of c
        ('c', 'c', 1, False),           # Absolute velocity
        ('wu', 'wu', 1, False),         # Circumferential component of w
        ('w', 'w', 1, False),           # Relative velocity
        ('cur', 'cu·r', 3, False),      # Swirl (angular momentum)
        ('tau', 'τ', 3, False),         # Obstruction factor
        ('i_delta', 'i | δ', 1, False), # Incidence | Deviation
        # Merged rows (single value spanning inlet/outlet)
        ('w2_w1', 'w2/w1', 3, True),    # Deceleration ratio
        ('c2_c1', 'c2/c1', 3, True),    # Absolute velocity ratio
        ('delta_alpha', 'ΔαF', 1, True),  # Absolute deflection
        ('delta_beta', 'ΔβF', 1, True),   # Relative deflection
        ('camber', 'φ=ΔβB', 1, True),     # Blade camber angle
        ('gamma', 'γ', 3, True),          # Slip coefficient
        ('delta_cur', 'Δ(cu·r)', 3, True),  # Swirl difference
        ('torque', 'T', 2, True),         # Torque
        ('head', 'H', 2, True),           # Head
    ]

    # Colors
    COLOR_BG = QColor('#1e1e2e')
    COLOR_HEADER = QColor('#313244')
    COLOR_GRID = QColor('#45475a')
    COLOR_TEXT = QColor('#cdd6f4')
    COLOR_TEXT_DIM = QColor('#a6adc8')
    COLOR_SEPARATOR = QColor('#89b4fa')
    COLOR_MERGED_BG = QColor('#181825')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: Optional[InfoTableData] = None
        self._setup_ui()

    def _setup_ui(self):
        """Create the table layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main table
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Label + Hub(2) + Shroud(2)
        self.table.setRowCount(len(self.ROW_DEFS))

        # Headers
        self.table.setHorizontalHeaderLabels([
            '', 'Leading edge\n@Hub', 'Trailing edge\n@Hub',
            'Leading edge\n@Shroud', 'Trailing edge\n@Shroud'
        ])

        # Configure header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 60)  # Label column

        # Hide vertical header
        self.table.verticalHeader().setVisible(False)

        # Table properties
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setShowGrid(True)

        # Scrollbar policy
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Style
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.COLOR_BG.name()};
                color: {self.COLOR_TEXT.name()};
                gridline-color: {self.COLOR_GRID.name()};
                border: 1px solid {self.COLOR_GRID.name()};
                font-size: 10px;
                font-family: 'Segoe UI', sans-serif;
            }}
            QTableWidget::item {{
                padding: 2px 4px;
                border-right: 1px solid {self.COLOR_GRID.name()};
            }}
            QHeaderView::section {{
                background-color: {self.COLOR_HEADER.name()};
                color: {self.COLOR_TEXT.name()};
                padding: 4px;
                border: 1px solid {self.COLOR_GRID.name()};
                font-weight: bold;
                font-size: 9px;
            }}
        """)

        # Initialize rows
        self._init_rows()

        # Set size policy
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Calculate minimum height based on row count
        row_height = 22
        header_height = 40
        min_height = header_height + len(self.ROW_DEFS) * row_height + 4
        self.table.setMinimumHeight(min_height)

        layout.addWidget(self.table)

    def _init_rows(self):
        """Initialize table rows with labels and structure."""
        for row, (key, label, decimals, is_merged) in enumerate(self.ROW_DEFS):
            # Set row height
            self.table.setRowHeight(row, 22)

            # Label column (column 0)
            label_item = QTableWidgetItem(label)
            label_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            label_item.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
            label_item.setForeground(QBrush(self.COLOR_TEXT_DIM))
            self.table.setItem(row, 0, label_item)

            if is_merged:
                # Merged rows: span columns 1-2 for Hub, 3-4 for Shroud
                self.table.setSpan(row, 1, 1, 2)  # Hub merged
                self.table.setSpan(row, 3, 1, 2)  # Shroud merged

                # Create merged cells
                hub_item = QTableWidgetItem('-')
                hub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                hub_item.setBackground(QBrush(self.COLOR_MERGED_BG))
                self.table.setItem(row, 1, hub_item)

                shroud_item = QTableWidgetItem('-')
                shroud_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                shroud_item.setBackground(QBrush(self.COLOR_MERGED_BG))
                self.table.setItem(row, 3, shroud_item)
            else:
                # Normal rows: 4 separate cells
                for col in range(1, 5):
                    item = QTableWidgetItem('-')
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, col, item)

    def set_data(self, data: InfoTableData):
        """
        Update table with new data.

        Args:
            data: InfoTableData from TurbomachineryCalculator
        """
        self._data = data
        self._update_display()

    def _update_display(self):
        """Update all table cells from current data."""
        if self._data is None:
            return

        d = self._data

        for row, (key, label, decimals, is_merged) in enumerate(self.ROW_DEFS):
            if is_merged:
                # Get merged values for Hub and Shroud
                hub_val, shroud_val = self._get_merged_value(key)
                self._set_cell(row, 1, hub_val, decimals)
                self._set_cell(row, 3, shroud_val, decimals)
            else:
                # Get individual values for each station
                hub_in, hub_out, shroud_in, shroud_out = self._get_station_values(key)
                self._set_cell(row, 1, hub_in, decimals)
                self._set_cell(row, 2, hub_out, decimals)
                self._set_cell(row, 3, shroud_in, decimals)
                self._set_cell(row, 4, shroud_out, decimals)

    def _get_station_values(self, key: str):
        """
        Get values for all 4 stations (hub_in, hub_out, shroud_in, shroud_out).
        """
        d = self._data

        value_map = {
            'z': (d.z_hub_in, d.z_hub_out, d.z_tip_in, d.z_tip_out),
            'r': (d.r_hub_in, d.r_hub_out, d.r_tip_in, d.r_tip_out),
            'd': (d.d_hub_in, d.d_hub_out, d.d_tip_in, d.d_tip_out),
            'alpha': (d.alpha_hub_in, d.alpha_hub_out, d.alpha_tip_in, d.alpha_tip_out),
            'beta': (d.beta_hub_in, d.beta_hub_out, d.beta_tip_in, d.beta_tip_out),
            'u': (d.u_hub_in, d.u_hub_out, d.u_tip_in, d.u_tip_out),
            'cm': (d.cm_hub_in, d.cm_hub_out, d.cm_tip_in, d.cm_tip_out),
            'cu': (d.cu_hub_in, d.cu_hub_out, d.cu_tip_in, d.cu_tip_out),
            'cr': (d.cr_hub_in, d.cr_hub_out, d.cr_tip_in, d.cr_tip_out),
            'cz': (d.cz_hub_in, d.cz_hub_out, d.cz_tip_in, d.cz_tip_out),
            'c': (d.c_hub_in, d.c_hub_out, d.c_tip_in, d.c_tip_out),
            'wu': (d.wu_hub_in, d.wu_hub_out, d.wu_tip_in, d.wu_tip_out),
            'w': (d.w_hub_in, d.w_hub_out, d.w_tip_in, d.w_tip_out),
            'cur': (d.cur_hub_in, d.cur_hub_out, d.cur_tip_in, d.cur_tip_out),
            'tau': (d.tau_hub_in, d.tau_hub_out, d.tau_tip_in, d.tau_tip_out),
            'i_delta': (d.i_hub_in, d.delta_hub_out, d.i_tip_in, d.delta_tip_out),
        }

        return value_map.get(key, (0.0, 0.0, 0.0, 0.0))

    def _get_merged_value(self, key: str):
        """
        Get merged values (single value per hub/shroud section).
        """
        d = self._data

        value_map = {
            'w2_w1': (d.w2_w1_hub, d.w2_w1_tip),
            'c2_c1': (d.c2_c1_hub, d.c2_c1_tip),
            'delta_alpha': (d.delta_alpha_hub, d.delta_alpha_tip),
            'delta_beta': (d.delta_beta_hub, d.delta_beta_tip),
            'camber': (d.camber_hub, d.camber_tip),
            'gamma': (d.gamma_hub, d.gamma_tip),
            'delta_cur': (d.delta_cur_hub, d.delta_cur_tip),
            'torque': (d.torque, d.torque),  # Same value for both
            'head': (d.head, d.head),        # Same value for both
        }

        return value_map.get(key, (0.0, 0.0))

    def _set_cell(self, row: int, col: int, value: float, decimals: int):
        """Set a cell value with formatting."""
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        if value is None:
            item.setText('-')
        else:
            item.setText(f'{value:.{decimals}f}')

    def clear_data(self):
        """Clear all data from the table."""
        self._data = None
        for row in range(self.table.rowCount()):
            for col in range(1, 5):
                item = self.table.item(row, col)
                if item:
                    item.setText('-')

    def update_from_calculator(self, calculator):
        """
        Update table from a TurbomachineryCalculator instance.

        Args:
            calculator: TurbomachineryCalculator instance
        """
        data = calculator.get_info_table_data()
        self.set_data(data)


class CompactInfoTableWidget(QWidget):
    """
    More compact info table with colored section headers.
    Matches the CFturbo-style visual layout more closely.
    """

    # Same row definitions
    ROW_DEFS = InfoTableWidget.ROW_DEFS

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: Optional[InfoTableData] = None
        self._setup_ui()

    def _setup_ui(self):
        """Create compact table layout with section headers."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Section header bar
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)
        header_bar.setSpacing(0)

        # Hub header (blue/teal accent)
        hub_header = QLabel("@Hub")
        hub_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hub_header.setStyleSheet("""
            QLabel {
                background-color: #45475a;
                color: #89b4fa;
                font-weight: bold;
                font-size: 10px;
                padding: 6px;
                border-bottom: 3px solid #89b4fa;
            }
        """)
        header_bar.addWidget(hub_header, 2)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(2)
        sep.setStyleSheet("background-color: #585b70;")
        header_bar.addWidget(sep)

        # Shroud header (green accent)
        shroud_header = QLabel("@Shroud")
        shroud_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shroud_header.setStyleSheet("""
            QLabel {
                background-color: #45475a;
                color: #a6e3a1;
                font-weight: bold;
                font-size: 10px;
                padding: 6px;
                border-bottom: 3px solid #a6e3a1;
            }
        """)
        header_bar.addWidget(shroud_header, 2)

        layout.addLayout(header_bar)

        # Main table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setRowCount(len(self.ROW_DEFS))

        # Column headers
        self.table.setHorizontalHeaderLabels([
            '', 'Leading\nedge', 'Trailing\nedge', 'Leading\nedge', 'Trailing\nedge'
        ])

        # Configure columns
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 50)

        # Hide row headers
        self.table.verticalHeader().setVisible(False)

        # Table config
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Compact styling
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e2e;
                color: #cdd6f4;
                gridline-color: #45475a;
                border: none;
                font-size: 9px;
            }
            QTableWidget::item {
                padding: 1px 2px;
            }
            QHeaderView::section {
                background-color: #313244;
                color: #a6adc8;
                padding: 3px;
                border: 1px solid #45475a;
                font-size: 8px;
            }
        """)

        # Initialize rows
        self._init_rows()

        layout.addWidget(self.table)

    def _init_rows(self):
        """Initialize table with row labels and structure."""
        for row, (key, label, decimals, is_merged) in enumerate(self.ROW_DEFS):
            self.table.setRowHeight(row, 18)

            # Label
            label_item = QTableWidgetItem(label)
            label_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            label_item.setForeground(QBrush(QColor('#a6adc8')))
            font = QFont('Segoe UI', 8)
            font.setBold(True)
            label_item.setFont(font)
            self.table.setItem(row, 0, label_item)

            if is_merged:
                self.table.setSpan(row, 1, 1, 2)
                self.table.setSpan(row, 3, 1, 2)

                for col in [1, 3]:
                    item = QTableWidgetItem('-')
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setBackground(QBrush(QColor('#181825')))
                    self.table.setItem(row, col, item)
            else:
                for col in range(1, 5):
                    item = QTableWidgetItem('-')
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, col, item)

    def set_data(self, data: InfoTableData):
        """Update table with data."""
        self._data = data
        self._update_display()

    def _update_display(self):
        """Update all cells."""
        if self._data is None:
            return

        d = self._data

        for row, (key, label, decimals, is_merged) in enumerate(self.ROW_DEFS):
            if is_merged:
                hub_val, shroud_val = self._get_merged_value(key)
                self._set_cell(row, 1, hub_val, decimals)
                self._set_cell(row, 3, shroud_val, decimals)
            else:
                vals = self._get_station_values(key)
                for i, val in enumerate(vals):
                    self._set_cell(row, i + 1, val, decimals)

    def _get_station_values(self, key: str):
        """Get 4 station values."""
        d = self._data

        mapping = {
            'z': (d.z_hub_in, d.z_hub_out, d.z_tip_in, d.z_tip_out),
            'r': (d.r_hub_in, d.r_hub_out, d.r_tip_in, d.r_tip_out),
            'd': (d.d_hub_in, d.d_hub_out, d.d_tip_in, d.d_tip_out),
            'alpha': (d.alpha_hub_in, d.alpha_hub_out, d.alpha_tip_in, d.alpha_tip_out),
            'beta': (d.beta_hub_in, d.beta_hub_out, d.beta_tip_in, d.beta_tip_out),
            'u': (d.u_hub_in, d.u_hub_out, d.u_tip_in, d.u_tip_out),
            'cm': (d.cm_hub_in, d.cm_hub_out, d.cm_tip_in, d.cm_tip_out),
            'cu': (d.cu_hub_in, d.cu_hub_out, d.cu_tip_in, d.cu_tip_out),
            'cr': (d.cr_hub_in, d.cr_hub_out, d.cr_tip_in, d.cr_tip_out),
            'cz': (d.cz_hub_in, d.cz_hub_out, d.cz_tip_in, d.cz_tip_out),
            'c': (d.c_hub_in, d.c_hub_out, d.c_tip_in, d.c_tip_out),
            'wu': (d.wu_hub_in, d.wu_hub_out, d.wu_tip_in, d.wu_tip_out),
            'w': (d.w_hub_in, d.w_hub_out, d.w_tip_in, d.w_tip_out),
            'cur': (d.cur_hub_in, d.cur_hub_out, d.cur_tip_in, d.cur_tip_out),
            'tau': (d.tau_hub_in, d.tau_hub_out, d.tau_tip_in, d.tau_tip_out),
            'i_delta': (d.i_hub_in, d.delta_hub_out, d.i_tip_in, d.delta_tip_out),
        }

        return mapping.get(key, (0.0, 0.0, 0.0, 0.0))

    def _get_merged_value(self, key: str):
        """Get merged values."""
        d = self._data

        mapping = {
            'w2_w1': (d.w2_w1_hub, d.w2_w1_tip),
            'c2_c1': (d.c2_c1_hub, d.c2_c1_tip),
            'delta_alpha': (d.delta_alpha_hub, d.delta_alpha_tip),
            'delta_beta': (d.delta_beta_hub, d.delta_beta_tip),
            'camber': (d.camber_hub, d.camber_tip),
            'gamma': (d.gamma_hub, d.gamma_tip),
            'delta_cur': (d.delta_cur_hub, d.delta_cur_tip),
            'torque': (d.torque, d.torque),
            'head': (d.head, d.head),
        }

        return mapping.get(key, (0.0, 0.0))

    def _set_cell(self, row: int, col: int, value: float, decimals: int):
        """Set cell value."""
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, col, item)

        if value is None:
            item.setText('-')
        else:
            item.setText(f'{value:.{decimals}f}')

    def update_from_calculator(self, calculator):
        """Update from calculator."""
        data = calculator.get_info_table_data()
        self.set_data(data)
