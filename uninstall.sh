#!/bin/bash
# RTL Studio - Linux Desktop Uninstaller

printf "Uninstall RTL Studio? [Yes/Cancel]: "
read confirm

case "$confirm" in
    [yY]|[yY][eE][sS]|[Yy]es)
        echo "Uninstalling..."
        
        # Remove only the application, launcher, desktop entry, and icon
        rm -rf "$HOME/.local/share/rtl-studio"
        rm -f "$HOME/.local/bin/rtl-studio"
        rm -f "$HOME/.local/share/applications/rtl-studio.desktop"
        rm -f "$HOME/.local/share/icons/rtl-studio.png"
        
        # Update caches safely
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database "$HOME/.local/share/applications" || true
        fi
        
        echo "RTL Studio has been successfully uninstalled."
        echo "Note: Your RTL projects, Verilog files, and external tools were NOT removed."
        ;;
    *)
        echo "Uninstall canceled."
        ;;
esac