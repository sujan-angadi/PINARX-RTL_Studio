"""
Project Analyzer
Responsibility: Lightweight heuristic parsing of RTL files to detect modules, testbenches, and ports.
"""
import os
import re

class ProjectAnalyzer:
    def __init__(self, root_path):
        self.root_path = root_path
        self.rtl_files = []
        self.modules = {} # { name: {"file": path, "line": int, "is_tb": bool, "inputs": int, "outputs": int, "regs": int} }
        self.top_modules = []
        self.testbenches = []

    def analyze(self, actual_files=None):
        self.modules.clear()
        self.top_modules.clear()
        self.testbenches.clear()
        self.rtl_files = []
        
        # FIX: Reverted to V2.0's 'self.root_path' attribute
        if not self.root_path or not os.path.exists(self.root_path):
            return
            
        mod_re = re.compile(r'\bmodule\s+([a-zA-Z_][a-zA-Z0-9_]*)\b')
        dump_re = re.compile(r'\$(?:dumpfile|dumpvars)')

        files_to_scan = actual_files if actual_files is not None else []
        if not files_to_scan:
            for root, _, files in os.walk(self.root_path):
                if '.rtlstudio' in root or '__pycache__' in root: continue
                for f in files:
                    if f.endswith(('.v', '.sv', '.vh', '.svh')):
                        files_to_scan.append(os.path.relpath(os.path.join(root, f), self.root_path).replace('\\', '/'))
        
        self.rtl_files = files_to_scan

        file_contents = {}
        declared_modules = set()
        
        for rel_file in files_to_scan:
            abs_file = os.path.join(self.root_path, rel_file)
            if not os.path.exists(abs_file): continue
            try:
                with open(abs_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                    code_clean = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
                    code_clean = re.sub(r'//.*', '', code_clean)
                    file_contents[rel_file] = code_clean
                    
                    mods = mod_re.findall(code_clean)
                    for m in mods: declared_modules.add(m)
            except Exception:
                pass

        instantiated_modules = set()
        for code in file_contents.values():
            for mod in declared_modules:
                if re.search(rf'\b{mod}\s+(?:#\s*\([\s\S]*?\)\s*)?[a-zA-Z_][a-zA-Z0-9_]*\s*\(', code):
                    instantiated_modules.add(mod)

        for rel_file, code in file_contents.items():
            abs_file = os.path.join(self.root_path, rel_file)
            mods = mod_re.findall(code)
            has_dump = bool(dump_re.search(code))
            
            for mod in mods:
                # Testbench definition: Dumps waveforms, or name has _tb / tb_
                is_tb = has_dump or '_tb' in mod.lower() or 'tb_' in mod.lower() or '_tb' in rel_file.lower() or 'tb_' in rel_file.lower()
                
                self.modules[mod] = {
                    "file": abs_file,
                    "rel_file": rel_file,
                    "is_tb": is_tb,
                    "has_dump": has_dump,
                    "is_instantiated": mod in instantiated_modules
                }
                
                if is_tb:
                    self.testbenches.append(mod)
                elif mod not in instantiated_modules:
                    self.top_modules.append(mod)

        self.design_top = self.top_modules[0] if self.top_modules else ""
        self.testbench_top = self.testbenches[0] if self.testbenches else ""