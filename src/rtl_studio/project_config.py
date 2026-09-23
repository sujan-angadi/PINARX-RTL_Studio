"""
Project Configuration
Responsibility: Loads and saves the RTL project settings (JSON).
"""
import os
import json

class ProjectConfig:
    def __init__(self, root_path):
        self.root_path = root_path
        self.config_file = os.path.join(root_path, "rtl_project.json")
        self.data = {
            "project_name": os.path.basename(root_path) if root_path else "Unknown",
            "top_module": "",
            "testbench_module": "",
            "design_sources": [],
            "testbench_sources": []
        }
        self.load()

    def load(self):
        if not self.root_path or not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                
                # Safe migration from older schemas
                if "sources" in loaded and "design_sources" not in loaded:
                    loaded["design_sources"] = loaded.pop("sources")
                    loaded["testbench_sources"] = []
                if "testbench" in loaded and "testbench_module" not in loaded:
                    loaded["testbench_module"] = loaded.pop("testbench")
                    
                self.data.update(loaded)
        except Exception:
            pass 

    def save(self):
        if not self.root_path: return
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception:
            pass