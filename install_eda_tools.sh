#!/bin/bash
# RTL Studio - EDA Tool Installer
set -e

echo "=================================================="
echo " RTL Studio - EDA Tool Installer"
echo "=================================================="
echo ""

# 1. System checks
echo "Checking system..."
if [ "$(uname -s)" != "Linux" ]; then
    echo "[ERROR] This script requires Linux."
    exit 1
fi

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ] && [ "$ARCH" != "amd64" ]; then
    echo "[ERROR] This script requires an x86_64/amd64 architecture. Detected: $ARCH"
    exit 1
fi
echo "Linux x86_64 detected."
echo ""

echo "Checking dependencies..."
if command -v curl >/dev/null 2>&1; then
    FETCH_CMD="curl -s"
    DOWNLOAD_CMD="curl -L -o"
elif command -v wget >/dev/null 2>&1; then
    FETCH_CMD="wget -qO-"
    DOWNLOAD_CMD="wget -O"
else
    echo "[ERROR] 'curl' or 'wget' is required to download the tools. Please install one and try again."
    exit 1
fi

TOOLS_DIR="$HOME/tools"
OSS_DIR="$TOOLS_DIR/oss-cad-suite"
ENV_SCRIPT="$OSS_DIR/environment"
TMP_ARCHIVE="/tmp/oss-cad-suite-linux-x64.tgz"

mkdir -p "$TOOLS_DIR"

# 2. Idempotency Check / Download
NEED_DOWNLOAD=1
if [ -d "$OSS_DIR" ] && [ -f "$ENV_SCRIPT" ]; then
    echo "Existing OSS CAD Suite installation detected at $OSS_DIR."
    echo "Verifying..."

    # Temporarily source to check if tools actually work
    set +e
    source "$ENV_SCRIPT"
    if command -v iverilog >/dev/null 2>&1 && command -v yosys >/dev/null 2>&1; then
        echo "Existing tools verified successfully. Skipping download."
        NEED_DOWNLOAD=0
    else
        echo "Existing installation appears broken or incomplete. Re-downloading..."
    fi
    set -e
fi

if [ "$NEED_DOWNLOAD" -eq 1 ]; then
    echo "Downloading OSS CAD Suite..."
    # Dynamically fetch the latest linux-x64 tarball URL from GitHub API
    DOWNLOAD_URL=$($FETCH_CMD https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases/latest | grep "browser_download_url" | grep "linux-x64" | cut -d '"' -f 4 | head -n 1)

    if [ -z "$DOWNLOAD_URL" ]; then
        echo "[ERROR] Failed to fetch the latest download URL from YosysHQ GitHub."
        exit 1
    fi

    echo "Fetching: $DOWNLOAD_URL"
    $DOWNLOAD_CMD "$TMP_ARCHIVE" "$DOWNLOAD_URL"

    echo ""
    echo "Installing to:"
    echo "$OSS_DIR"

    rm -rf "$OSS_DIR"
    tar -xzf "$TMP_ARCHIVE" -C "$TOOLS_DIR"
    rm -f "$TMP_ARCHIVE"
fi

# 3. Environment Configuration
echo ""
echo "Configuring environment..."
BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    if ! grep -q "tools/oss-cad-suite/environment" "$BASHRC"; then
        echo "" >> "$BASHRC"
        echo "# OSS CAD Suite Environment (Added by RTL Studio Installer)" >> "$BASHRC"
        echo "source \"$ENV_SCRIPT\"" >> "$BASHRC"
        echo "Added environment activation to ~/.bashrc."
    else
        echo "Environment activation is already present in ~/.bashrc."
    fi
else
    echo "[WARNING] ~/.bashrc not found. You may need to manually source $ENV_SCRIPT."
fi

# Source it for the current script execution to verify
source "$ENV_SCRIPT"

# 4. Verification
echo ""
echo "Verifying EDA tools..."
echo ""

MISSING_TOOLS=0

verify_tool() {
    local cmd=$1
    local name=$2
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "[OK] $name"
    else
        echo "[ERROR] $name ($cmd) not found!"
        MISSING_TOOLS=1
    fi
}

verify_tool iverilog "Icarus Verilog"
verify_tool vvp "VVP"
verify_tool gtkwave "GTKWave"
verify_tool yosys "Yosys"
verify_tool dot "Graphviz"

echo ""
if [ "$MISSING_TOOLS" -eq 1 ]; then
    echo "=================================================="
    echo " EDA TOOL INSTALLATION ENCOUNTERED ERRORS"
    echo "=================================================="
    echo "Some required tools failed to execute. Please check the logs above."
    exit 1
fi

# 5. Print Versions for diagnostic clarity
echo "Tool Versions:"
iverilog -V | head -n 1
vvp -V | head -n 1
gtkwave --version | head -n 1 | awk '{$1=$1;print}'
yosys -V | head -n 1
dot -V 2>&1 | head -n 1

echo ""
echo "=================================================="
echo " EDA TOOL INSTALLATION COMPLETE"
echo "=================================================="
echo ""
echo "RTL Studio is now ready for Verilog development."
echo ""
echo "IMPORTANT:"
echo "Open a new terminal before launching RTL Studio,"
echo "or run:"
echo ""
echo "    source ~/.bashrc"
echo ""
