#!/bin/bash
# DateForge - Simple launcher script
# This script installs dependencies and runs the PDF date extraction tool

set -e  # Exit on error

echo "DateForge - PDF Date Extraction Tool"
echo "======================================"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "ERROR: UV package manager is not installed."
    echo "Please install UV first: https://github.com/astral-sh/uv"
    echo ""
    echo "Quick install:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install/sync dependencies
echo "Installing dependencies..."
uv sync

echo ""
echo "Starting DateForge..."
echo ""

# Run the main script
uv run python main.py
