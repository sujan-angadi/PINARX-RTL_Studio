#!/bin/bash
# RTL Studio - Linux Desktop Installer
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/share/rtl-studio"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons"

echo "Installing RTL Studio v1.0..."

# Handle Reinstall / Update safely
if [ -d "$INSTALL_DIR" ]; then
    echo "Existing installation detected. Updating RTL Studio..."
    rm -rf "$INSTALL_DIR"
fi

# Create standard FreeDesktop user directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"
mkdir -p "$ICON_DIR"

# Verify package integrity
if [ ! -d "$SRC_DIR/app" ]; then
    echo "ERROR: Application bundle ('app' directory) not found."
    echo "Please ensure you are running this script from the RTL-Studio-v1.0 release package."
    exit 1
fi

# Install application files
cp -r "$SRC_DIR/app/"* "$INSTALL_DIR/"

# Install icon
if [ -f "$SRC_DIR/LOGO.png" ]; then
    cp "$SRC_DIR/LOGO.png" "$ICON_DIR/rtl-studio.png"
else
    echo "WARNING: LOGO.png not found. Application icon may be missing."
fi

# Create executable launcher
cat <<EOF > "$BIN_DIR/rtl-studio"
#!/bin/bash
exec "$INSTALL_DIR/RTL_Studio" "\$@"
EOF
chmod +x "$BIN_DIR/rtl-studio"

# Create Desktop Entry
cat <<EOF > "$APP_DIR/rtl-studio.desktop"
[Desktop Entry]
Name=RTL Studio
Comment=RTL development environment for Verilog
Exec=$HOME/.local/bin/rtl-studio
Icon=rtl-studio
Terminal=false
Type=Application
Categories=Development;Electronics;
StartupNotify=true
EOF

# Update desktop caches silently if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$ICON_DIR" >/dev/null 2>&1 || true
fi

echo ""
echo "=================================================="
echo "Installation Complete!"
echo "RTL Studio is now available in your Linux Applications menu."
echo ""
echo "Note: External EDA tools (Icarus, GTKWave, Yosys, Graphviz) are installed separately."
echo "=================================================="