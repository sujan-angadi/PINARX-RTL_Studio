"""
Output Panel
Responsibility: Displays messages, build output, and provides clickable error navigation.
"""
import re
import os
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Signal
from datetime import datetime

class OutputPanel(QPlainTextEdit):
    # Emits (filepath, line_number) when an Icarus error format is double-clicked
    error_clicked = Signal(str, int) 

    def __init__(self):
        super().__init__()
        self.setObjectName("OutputPanel")
        self.setReadOnly(True)
        self.log("RTL Studio initialized.")

    def log(self, message):
        """Appends a timestamped message to the output panel."""
        time_str = datetime.now().strftime("%H:%M:%S")
        self.appendPlainText(f"[{time_str}] > {message}")
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def append_raw(self, message):
        """Appends unformatted output (from external tools)."""
        self.appendPlainText(message.strip())
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def mouseDoubleClickEvent(self, event):
        """Parse double-clicks for Icarus error patterns (e.g., filename.v:14: syntax error)."""
        cursor = self.cursorForPosition(event.pos())
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        line_text = cursor.selectedText()
        
        # Regex to catch typical Icarus error formats: "src/and_gate.v:15: error..."
        match = re.search(r"([a-zA-Z0-9_./\\]+\.[s]?vh?):(\d+):", line_text)
        if match:
            file_path = match.group(1)
            line_num = int(match.group(2))
            self.error_clicked.emit(file_path, line_num)
            
        super().mouseDoubleClickEvent(event)