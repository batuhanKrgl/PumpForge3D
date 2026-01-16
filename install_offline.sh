#!/bin/bash
# ============================================
# PumpForge3D Offline Installation Script
# ============================================
# For users without internet access

echo "=== PumpForge3D Offline Install ==="
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "Make sure Python 3.10+ is installed."
        exit 1
    fi
fi

# Activate and install from wheel files
echo "Installing packages from whls folder..."
source .venv/bin/activate
pip install --no-index --find-links=whls -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "ERROR: Installation failed."
    echo "Make sure all required wheel files are in the whls folder."
    exit 1
fi

echo
echo "=== Installation Complete ==="
echo
echo "To run PumpForge3D:"
echo "  1. Activate: source .venv/bin/activate"
echo "  2. Run: python -m apps.PumpForge3D"
echo
