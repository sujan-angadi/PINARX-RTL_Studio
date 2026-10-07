"""
EDA Tools Management
Responsibility: Safely detects local EDA toolchains (Icarus, GTKWave, Yosys, Graphviz).
"""
import os
import shutil
import subprocess
# ARCHITECTURAL FIX: Removed top-level PySide6 import to support headless execution.

def get_oss_cad_suite_bin():
    """Returns the expected OSS CAD Suite bin directory using the user's home folder."""
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, "tools", "oss-cad-suite", "bin")

def get_tool_path(tool_name):
    """Resolves the absolute path to an EDA tool, independent of interactive shells."""
    system_path = shutil.which(tool_name)
    if system_path:
        return system_path
        
    fallback_path = os.path.join(get_oss_cad_suite_bin(), tool_name)
    if os.path.isfile(fallback_path) and os.access(fallback_path, os.X_OK):
        return fallback_path
        
    return None

def get_eda_env_dict():
    """Returns an environment dictionary for Python subprocess calls (HEADLESS SAFE)."""
    env = os.environ.copy()
    oss_bin = get_oss_cad_suite_bin()
    if os.path.isdir(oss_bin):
        env["PATH"] = f"{oss_bin}{os.pathsep}{env.get('PATH', '')}"
    return env

def get_eda_qenv():
    """Returns a QProcessEnvironment for PySide6 QProcess calls (GUI ONLY)."""
    # EXACT FIX: Lazy import PySide6 only when explicitly requested by the GUI
    from PySide6.QtCore import QProcessEnvironment 
    
    qenv = QProcessEnvironment.systemEnvironment()
    oss_bin = get_oss_cad_suite_bin()
    if os.path.isdir(oss_bin):
        current_path = qenv.value("PATH", "")
        qenv.insert("PATH", f"{oss_bin}{os.pathsep}{current_path}")
    return qenv

class IcarusToolchain:
    def __init__(self):
        self.iverilog_path = get_tool_path("iverilog")
        self.vvp_path = get_tool_path("vvp")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.iverilog_path and self.vvp_path:
            self.available = True
            try:
                result = subprocess.run([self.iverilog_path, "-V"], capture_output=True, text=True, timeout=2, env=get_eda_env_dict())
                first_line = result.stdout.split('\n')[0].strip()
                if "Icarus Verilog version" in first_line:
                    self.version = first_line.replace("Icarus Verilog version ", "").split(' ')[0]
            except Exception:
                self.version = "Error detecting version"

class GTKWaveTool:
    def __init__(self):
        self.path = get_tool_path("gtkwave")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.path:
            self.available = True
            try:
                result = subprocess.run([self.path, "--version"], capture_output=True, text=True, timeout=2, env=get_eda_env_dict())
                first_line = result.stdout.split('\n')[0].strip()
                if "GTKWave Analyzer v" in first_line:
                    self.version = first_line.split("GTKWave Analyzer v")[1].split(" ")[0]
                else:
                    self.version = "Detected"
            except Exception:
                self.version = "Error detecting version"

class YosysTool:
    def __init__(self):
        self.path = get_tool_path("yosys")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.path:
            self.available = True
            try:
                result = subprocess.run([self.path, "-V"], capture_output=True, text=True, timeout=2, env=get_eda_env_dict())
                first_line = result.stdout.split('\n')[0].strip()
                if "Yosys" in first_line:
                    self.version = first_line.split(" ")[1] if len(first_line.split(" ")) > 1 else "Detected"
            except Exception:
                self.version = "Error detecting version"

class GraphvizTool:
    def __init__(self):
        self.path = get_tool_path("dot")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.path:
            self.available = True
            try:
                result = subprocess.run([self.path, "-V"], capture_output=True, text=True, timeout=2, env=get_eda_env_dict())
                out = result.stdout if result.stdout else result.stderr
                if "graphviz version" in out.lower():
                    self.version = out.lower().split("version")[1].strip().split(" ")[0]
                else:
                    self.version = "Detected"
            except Exception:
                self.version = "Error detecting version"