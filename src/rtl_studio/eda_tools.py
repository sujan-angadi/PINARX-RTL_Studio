"""
EDA Tools Management
Responsibility: Safely detects local EDA toolchains (Icarus, GTKWave, Yosys, Graphviz).
"""
import shutil
import subprocess

class IcarusToolchain:
    def __init__(self):
        self.iverilog_path = shutil.which("iverilog")
        self.vvp_path = shutil.which("vvp")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.iverilog_path and self.vvp_path:
            self.available = True
            try:
                result = subprocess.run([self.iverilog_path, "-V"], capture_output=True, text=True, timeout=2)
                first_line = result.stdout.split('\n')[0].strip()
                if "Icarus Verilog version" in first_line:
                    self.version = first_line.replace("Icarus Verilog version ", "").split(' ')[0]
            except Exception:
                self.version = "Error detecting version"

class GTKWaveTool:
    def __init__(self):
        self.path = shutil.which("gtkwave")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.path:
            self.available = True
            try:
                result = subprocess.run([self.path, "--version"], capture_output=True, text=True, timeout=2)
                first_line = result.stdout.split('\n')[0].strip()
                if "GTKWave Analyzer v" in first_line:
                    self.version = first_line.split("GTKWave Analyzer v")[1].split(" ")[0]
                else:
                    self.version = "Detected"
            except Exception:
                self.version = "Error detecting version"

class YosysTool:
    def __init__(self):
        self.path = self._find_yosys()
        self.version = "Unknown"
        self.available = False
        self.detect()

    def _find_yosys(self):
        system_path = shutil.which("yosys")
        if system_path:
            return system_path
            
        import os
        home_dir = os.path.expanduser("~")
        fallback_path = os.path.join(home_dir, "tools", "oss-cad-suite", "bin", "yosys")
        
        if os.path.isfile(fallback_path) and os.access(fallback_path, os.X_OK):
            return fallback_path
            
        return None

    def detect(self):
        if self.path:
            self.available = True
            try:
                result = subprocess.run([self.path, "-V"], capture_output=True, text=True, timeout=2)
                first_line = result.stdout.split('\n')[0].strip()
                if "Yosys" in first_line:
                    self.version = first_line.split(" ")[1] if len(first_line.split(" ")) > 1 else "Detected"
            except Exception:
                self.version = "Error detecting version"

class GraphvizTool:
    def __init__(self):
        self.path = shutil.which("dot")
        self.version = "Unknown"
        self.available = False
        self.detect()

    def detect(self):
        if self.path:
            self.available = True
            try:
                # dot outputs version info to stderr
                result = subprocess.run([self.path, "-V"], capture_output=True, text=True, timeout=2)
                out = result.stdout if result.stdout else result.stderr
                if "graphviz version" in out.lower():
                    self.version = out.lower().split("version")[1].strip().split(" ")[0]
                else:
                    self.version = "Detected"
            except Exception:
                self.version = "Error detecting version"