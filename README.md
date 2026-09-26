# RTL Studio
By PINARX

**Version:** 1.0

## 1. About RTL Studio
A modern RTL development environment for designing, simulating, synthesizing, and visualizing Verilog designs. Built on Python and PySide6, RTL Studio provides a unified graphical frontend for industry-standard open-source EDA tools.

## 2. Features
- Verilog RTL editing with syntax highlighting and bracket matching
- Project management & File explorer
- Icarus Verilog compilation and simulation integration
- GTKWave waveform viewing
- Yosys generic synthesis workflows
- Hardware schematic visualization
- Design & PPA statistics dashboard
- Cross-platform development environment

## 3. Requirements
- Linux Desktop Environment (GNOME, KDE, Xfce, etc.)
- Basic standard build tools

## 4. External EDA Tools
RTL Studio relies on the following external EDA tools. They are **NOT** bundled with RTL Studio and must be installed separately and available in your system's `PATH`:
- **Icarus Verilog**: `iverilog`, `vvp`
- **GTKWave**: `gtkwave`
- **Yosys**: `yosys`
- **Graphviz**: `dot`

*(Note: Installing the OSS CAD Suite satisfies all tool requirements automatically. RTL Studio will auto-detect them if they are in your PATH).*

## 5. Installation
RTL Studio performs a user-local installation without requiring `sudo` or modifying your `.bashrc`.

1. Open a terminal in the RTL-Studio-v1.0 release directory.
2. Make the installer executable (if it isn't already):
   ```bash
   chmod +x install.sh