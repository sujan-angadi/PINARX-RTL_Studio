"""
Project Analyzer
Responsibility: Lightweight heuristic parsing of RTL files to detect modules and testbenches.
"""
import os
import re

class ProjectAnalyzer:
    def __init__(self, root_path):
        self.root_path = root_path
        self.rtl_files = []
        self.modules = {} # { name: {"file": path, "line": int, "is_tb": bool} }
        self.top_modules = []
        self.testbenches = []

    def analyze(self):
        self.rtl_files.clear()
        self.modules.clear()
        self.top_modules.clear()
        self.testbenches.clear()
        
        if not self.root_path: return

        # 1. File Discovery
        valid_exts = ('.v', '.sv', '.vh', '.svh')
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ("build", "dist", ".rtlstudio")]
            for f in files:
                if f.endswith(valid_exts):
                    self.rtl_files.append(os.path.join(root, f))

        # 2. Module Detection
        mod_pattern = re.compile(r"\bmodule\s+(\w+)")
        tb_indicators = re.compile(r"\b(initial|#\d+|\$display|\$monitor|\$finish|\$dumpfile|\$dumpvars)\b")
        
        file_contents = {}
        for filepath in self.rtl_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_contents[filepath] = content
                    
                    is_tb_file = "tb" in os.path.basename(filepath).lower() or "test" in os.path.basename(filepath).lower()
                    
                    for i, line in enumerate(content.split('\n')):
                        match = mod_pattern.search(line)
                        if match:
                            mod_name = match.group(1)
                            is_tb = is_tb_file or bool(tb_indicators.search(content))
                            self.modules[mod_name] = {
                                "file": filepath,
                                "line": i + 1,
                                "is_tb": is_tb
                            }
                            if is_tb and mod_name not in self.testbenches:
                                self.testbenches.append(mod_name)
            except Exception:
                pass

        # 3. Top Module Detection (Hardware Top)
        # A design top is a non-testbench module that is NOT instantiated by any OTHER non-testbench module.
        for mod_name in self.modules:
            if self.modules[mod_name]["is_tb"]: 
                continue
            
            is_instantiated_by_design = False
            inst_pattern = re.compile(rf"\b{mod_name}\b")
            
            for filepath, content in file_contents.items():
                if filepath != self.modules[mod_name]["file"]:
                    # Check if the file doing the instantiating is a design file or a TB file
                    file_is_tb = any(m["is_tb"] for m in self.modules.values() if m["file"] == filepath)
                    
                    # If instantiated by another hardware file, it is NOT the top module
                    if not file_is_tb:
                        if inst_pattern.search(content):
                            is_instantiated_by_design = True
                            break
            
            if not is_instantiated_by_design:
                self.top_modules.append(mod_name)