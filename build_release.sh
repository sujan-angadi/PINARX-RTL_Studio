#!/bin/bash
# Final Release Packager for RTL Studio v1.0
set -e

echo "Cleaning previous build artifacts..."
rm -rf build/ dist/RTL_Studio/

echo "Building PyInstaller Executable..."
# Build as RTL_Studio and explicitly include the assets folder
pyinstaller --name "RTL_Studio" --windowed --noconfirm --add-data "assets:assets" run.py

if [ ! -f "dist/RTL_Studio/RTL_Studio" ]; then
    echo "ERROR: PyInstaller failed to produce dist/RTL_Studio/RTL_Studio"
    exit 1
fi

echo "Creating Final Release Directory..."
RELEASE_DIR="$HOME/Documents/RTL-Studio-v3.0"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR/app"

echo "Copying application payload..."
cp -r dist/RTL_Studio/* "$RELEASE_DIR/app/"

echo "Copying installer scripts and assets..."
cp install.sh "$RELEASE_DIR/"
cp uninstall.sh "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"
cp assets/LOGO.png "$RELEASE_DIR/" 2>/dev/null || echo "Ensure LOGO.png is in assets/"

echo "Setting permissions..."
chmod +x "$RELEASE_DIR/install.sh"
chmod +x "$RELEASE_DIR/uninstall.sh"

echo "=================================================="
echo "SUCCESS! Release package created at:"
echo "$RELEASE_DIR"
echo "=================================================="