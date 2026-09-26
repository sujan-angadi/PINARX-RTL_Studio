"""
Output Panel
Responsibility: Displays formatted EDA tool console logs, supports clear actions, and provides double-click error navigation.
"""
import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont

class OutputPanel(QWidget):
    error_clicked = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_productive = False
        self.is_candy = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top toolbar for the console
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)
        
        lbl = QLabel("Console Output")
        lbl.setStyleSheet("font-weight: bold; color: #92929A;")
        
        clear_btn = QPushButton("Clear Console")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("padding: 2px 10px; font-size: 11px;")
        clear_btn.clicked.connect(self.clear_console)
        
        top_layout.addWidget(lbl)
        top_layout.addStretch()
        top_layout.addWidget(clear_btn)
        
        layout.addWidget(top_bar)
        
        # Text Area
        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        font = QFont("monospace", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_area.setFont(font)
        
        self.text_area.mouseDoubleClickEvent = self.on_double_click
        layout.addWidget(self.text_area)
        
        self.error_pattern = re.compile(r'([\w\./\\-]+\.[s]?vh?):(\d+)')

    def set_theme(self, is_dark, is_productive=False, is_candy=False):
        self.is_productive = is_productive
        self.is_candy = is_candy

    def log(self, msg, level="INFO"):
        fmt = QTextCharFormat()
        prefix = ""
        
        is_prod = getattr(self, 'is_productive', False)
        is_candy = getattr(self, 'is_candy', False)
        
        if level == "INFO":
            if is_candy: fmt.setForeground(QColor("#5ec8f7"))
            elif is_prod: fmt.setForeground(QColor("#00E5FF"))
            else: fmt.setForeground(QColor("#4EA8DE"))
            prefix = "[INFO] "
        elif level == "SUCCESS":
            if is_candy: fmt.setForeground(QColor("#7ed957"))
            elif is_prod: fmt.setForeground(QColor("#00FF9D"))
            else: fmt.setForeground(QColor("#7CB518"))
            prefix = "[SUCCESS] "
        elif level == "ERROR":
            if is_candy: fmt.setForeground(QColor("#ff6b6b"))
            elif is_prod: fmt.setForeground(QColor("#FF4D6D"))
            else: fmt.setForeground(QColor("#E01A4F"))
            prefix = "[ERROR] "
        elif level == "WARNING":
            if is_candy: fmt.setForeground(QColor("#ffd166"))
            elif is_prod: fmt.setForeground(QColor("#FFD166"))
            else: fmt.setForeground(QColor("#F3A712"))
            prefix = "[WARNING] "
        else:
            if is_candy: fmt.setForeground(QColor("#a983a0"))
            elif is_prod: fmt.setForeground(QColor("#DDEBFF"))
            else: fmt.setForeground(QColor("#92929A"))
        
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_area.setTextCursor(cursor)
        
        self.text_area.setCurrentCharFormat(fmt)
        if not self.text_area.toPlainText().endswith('\n') and self.text_area.toPlainText() != "":
            self.text_area.insertPlainText("\n")
        self.text_area.insertPlainText(f"{prefix}{msg}\n")
        
        self.text_area.verticalScrollBar().setValue(self.text_area.verticalScrollBar().maximum())

    def append_raw(self, text):
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.text_area.setTextCursor(cursor)
        
        is_prod = getattr(self, 'is_productive', False)
        is_candy = getattr(self, 'is_candy', False)
        
        reset_fmt = QTextCharFormat()
        if is_candy: reset_fmt.setForeground(QColor("#a983a0"))
        elif is_prod: reset_fmt.setForeground(QColor("#8192AA"))
        else: reset_fmt.setForeground(QColor("#92929A"))
            
        self.text_area.setCurrentCharFormat(reset_fmt)
        self.text_area.insertPlainText(text)
        self.text_area.verticalScrollBar().setValue(self.text_area.verticalScrollBar().maximum())

    def clear_console(self):
        self.text_area.clear()

    def on_double_click(self, event):
        cursor = self.text_area.cursorForPosition(event.pos())
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        
        match = self.error_pattern.search(line_text)
        if match:
            filepath = match.group(1)
            line_num = int(match.group(2))
            self.error_clicked.emit(filepath, line_num)
        
        super(QPlainTextEdit, self.text_area).mouseDoubleClickEvent(event)