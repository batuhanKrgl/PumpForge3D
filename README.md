# PumpForge3D — Inducer Meridional Designer

A modular, testable, Windows-first GUI tool for inducer geometry design, inspired by CFturbo workflow principles.

## Features

- **Step-by-step workflow**: Main Dimensions → Meridional Contour → Edges → Analysis → Export
- **Interactive Bezier editing**: Drag control points, right-click for options
- **4th-order Bezier curves**: 5 control points with endpoint constraints
- **Context menus**: Fit view, save image, import reference polylines, measure tool
- **Analysis views**: Curvature progression and cross-sectional area plots
- **Versioned export**: JSON format with schema versioning and validation
- **Dark theme**: Modern, clean UI with Catppuccin-inspired colors

## Installation

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Offline Installation

For users without internet access, the project supports offline installation using pre-downloaded wheel files.

### Step 1: Prepare Wheel Files (requires internet - do this once)

On a machine with internet access, download all dependencies:

```powershell
# Windows (x64)
pip download -r requirements.txt -d whls --only-binary=:all:
```

This creates a `whls/` folder containing all required wheel files (~300MB).

> **Note:** Wheel files are platform-specific. Download on the same OS/architecture as the target machine.

### Step 2: Install Offline

Copy the entire project folder (including `whls/`) to the offline machine, then run:

**Windows:**
```powershell
.\install_offline.bat
```

**Linux/Mac:**
```bash
chmod +x install_offline.sh
./install_offline.sh
```

**Or manually:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --no-index --find-links=whls -r requirements.txt
```

> **Important:** The `whls/` folder is excluded from git due to file size limits. You must download wheel files manually before offline installation.

## Running the Application

```powershell
# From the project root directory
python -m apps.PumpForge3D
```

## Running Tests

```powershell
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_bezier.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ -v --cov=pumpforge3d_core
```

## Project Structure

```
PumpForge3D/
├── apps/
│   └── PumpForge3D/          # GUI application
│       ├── __main__.py       # Entry point
│       ├── main_window.py    # Main window
│       ├── widgets/          # Reusable widgets
│       │   ├── diagram_widget.py
│       │   └── numeric_input_dialog.py
│       └── steps/            # Step panels (A-E)
│
├── pumpforge3d_core/         # Core library (no Qt deps)
│   ├── geometry/             # Bezier, meridional, inducer
│   ├── io/                   # Export/import, schema
│   └── validation/           # Geometry validation
│
├── tests/                    # pytest test suite
├── requirements.txt
└── README.md
```

## Design Workflow

1. **Step A: Main Dimensions** - Define inlet/outlet radii and axial length
2. **Step B: Meridional Contour** - Edit hub and tip Bezier curves interactively
3. **Step C: Leading/Trailing Edges** - Design edge curves (straight or Bezier)
4. **Step D: Analysis Views** - View curvature and area progression plots
5. **Step E: Export** - Save to versioned JSON, load existing designs

## Export Format

Designs are saved as JSON with:
- Schema version (semver, current: 0.1.0)
- App version for traceability
- Complete control point data
- Sampled geometry points (200 per curve)
- Metadata and constraints

## CFturbo-Inspired UX

This tool follows CFturbo's interaction philosophy (not a clone):
- Right-click on diagram area → Context menu (zoom, fit, save, import, measure)
- Right-click on control point → Numeric input dialog
- Hover highlighting on curves and points
- Drag-and-drop control point editing
- Constraint toggle for tangent angles

## License

Internal use.
