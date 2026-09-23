"""
Editor & Tabs
Responsibility: Holds open files, tracks modification states, auto-indents, highlights syntax.
"""
import os
from PySide6.QtWidgets import (QTabWidget, QPlainTextEdit, QWidget, QMessageBox, QTextEdit)
from PySide6.QtGui import QFont, QPainter, QColor, QTextCursor, QTextFormat
from PySide6.QtCore import Qt, QRect, Signal, QSettings

from src.rtl_studio.widgets.highlighter import RTLHighlighter

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    def sizeHint(self):
        return self.editor.line_number_area_sizeHint()
    def paintEvent(self, event):
        self.editor.line_number_area_paintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, filepath="", is_dark_theme=True):
        super().__init__()
        self.filepath = filepath
        self.setObjectName("Editor")
        self.settings = QSettings("PINARX", "RTL_Studio")
        
        self.update_font()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Line numbers
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.update_line_number_area_width(0)

        # Highlighting (Syntax, Current Line, Brackets)
        self.highlighter = RTLHighlighter(self.document(), is_dark_theme)
        self.cursorPositionChanged.connect(self.highlight_current_line_and_brackets)
        self.is_dark_theme = is_dark_theme
        
        # Initial highlight
        self.highlight_current_line_and_brackets()

    def update_font(self):
        size = int(self.settings.value("font_size", 11))
        font = QFont("monospace", size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def set_theme(self, is_dark_theme):
        self.is_dark_theme = is_dark_theme
        self.highlighter.set_theme(is_dark_theme)
        self.highlight_current_line_and_brackets()

    # --- INDENTATION & COMMENTS ---
    def keyPressEvent(self, event):
        cursor = self.textCursor()
        use_spaces = self.settings.value("use_spaces", True, type=bool)
        tab_width = int(self.settings.value("tab_width", 4))
        tab_str = " " * tab_width if use_spaces else "\t"

        # Tab / Shift+Tab
        if event.key() == Qt.Key_Tab:
            if cursor.hasSelection():
                self.indent_selection(tab_str)
            else:
                cursor.insertText(tab_str)
            return
        elif event.key() == Qt.Key_Backtab:
            self.unindent_selection(tab_width, use_spaces)
            return

        # Comments (Ctrl+/)
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Slash:
            self.toggle_comments()
            return

        # Auto-Indentation (Enter)
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            super().keyPressEvent(event)
            block = cursor.block().previous()
            text = block.text()
            
            # Copy previous whitespace
            indentation = ""
            for char in text:
                if char in (' ', '\t'): indentation += char
                else: break
                
            # Increase indent for specific Verilog constructs
            if text.strip().endswith("begin") or text.strip().endswith("module") or text.strip().endswith("case"):
                indentation += tab_str
                
            self.insertPlainText(indentation)
            return

        super().keyPressEvent(event)

    def indent_selection(self, tab_str):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.beginEditBlock()
        while cursor.position() <= end:
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.insertText(tab_str)
            if not cursor.movePosition(QTextCursor.NextBlock): break
            end += len(tab_str)
        cursor.endEditBlock()

    def unindent_selection(self, tab_width, use_spaces):
        cursor = self.textCursor()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.beginEditBlock()
        while cursor.position() <= end:
            cursor.movePosition(QTextCursor.StartOfBlock)
            cursor.select(QTextCursor.Right)
            # Simplistic unindent for safety
            for _ in range(tab_width if use_spaces else 1):
                if cursor.selectedText() in (' ', '\t'):
                    cursor.removeSelectedText()
                    end -= 1
                    cursor.select(QTextCursor.Right)
                else: break
            if not cursor.movePosition(QTextCursor.NextBlock): break
        cursor.endEditBlock()

    def toggle_comments(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        
        start_block = self.document().findBlock(cursor.selectionStart())
        end_block = self.document().findBlock(cursor.selectionEnd())
        
        block = start_block
        while block.isValid():
            c = QTextCursor(block)
            c.movePosition(QTextCursor.StartOfBlock)
            text = block.text().strip()
            
            if text.startswith("//"):
                # Uncomment
                idx = block.text().find("//")
                c.setPosition(block.position() + idx)
                c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 2)
                c.removeSelectedText()
            else:
                # Comment
                c.insertText("// ")
                
            if block == end_block: break
            block = block.next()
            
        cursor.endEditBlock()

    # --- DYNAMIC HIGHLIGHTING (Current Line & Brackets) ---
    def highlight_current_line_and_brackets(self):
        extra_selections = []

        # Current Line
        if self.settings.value("highlight_current_line", True, type=bool):
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#222226") if self.is_dark_theme else QColor("#e8e8ed")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        # Bracket Matching (Simple adjacent search)
        cursor = self.textCursor()
        pos = cursor.position()
        doc = self.document()
        
        # Check char before and after
        match_pos = -1
        char_idx = -1
        
        if pos > 0:
            ch_before = doc.characterAt(pos - 1)
            if ch_before in "()[]{}":
                match_pos = self.find_matching_bracket(ch_before, pos - 1)
                char_idx = pos - 1
                
        if match_pos == -1 and pos < doc.characterCount():
            ch_after = doc.characterAt(pos)
            if ch_after in "()[]{}":
                match_pos = self.find_matching_bracket(ch_after, pos)
                char_idx = pos

        if match_pos != -1:
            fmt = QTextCharFormat()
            fmt.setBackground(QColor("#3A2731") if self.is_dark_theme else QColor("#fce8f1"))
            fmt.setForeground(QColor("#F3A6C8") if self.is_dark_theme else QColor("#d85c96"))
            fmt.setFontWeight(QFont.Weight.Bold)
            
            # Highlight original
            sel1 = QTextEdit.ExtraSelection()
            sel1.format = fmt
            c1 = QTextCursor(doc)
            c1.setPosition(char_idx)
            c1.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            sel1.cursor = c1
            extra_selections.append(sel1)
            
            # Highlight matched
            sel2 = QTextEdit.ExtraSelection()
            sel2.format = fmt
            c2 = QTextCursor(doc)
            c2.setPosition(match_pos)
            c2.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            sel2.cursor = c2
            extra_selections.append(sel2)

        self.setExtraSelections(extra_selections)

    def find_matching_bracket(self, char, pos):
        doc = self.document()
        pairs = {'(': ')', '{': '}', '[': ']'}
        reverse_pairs = {')': '(', '}': '{', ']': '['}
        
        if char in pairs:
            target = pairs[char]
            direction = 1
            start = pos + 1
            end = doc.characterCount()
        else:
            target = reverse_pairs[char]
            direction = -1
            start = pos - 1
            end = -1
            
        count = 1
        for i in range(start, end, direction):
            ch = doc.characterAt(i)
            if ch == char: count += 1
            elif ch == target: count -= 1
            
            if count == 0: return i
        return -1

    # --- LINE NUMBERS (Preserved UI logic) ---
    def line_number_area_sizeHint(self):
        if not self.settings.value("show_line_numbers", True, type=bool): return 0
        digits = 1
        max_blocks = max(1, self.blockCount())
        while max_blocks >= 10:
            max_blocks /= 10
            digits += 1
        return 24 + self.fontMetrics().horizontalAdvance('9') * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_sizeHint(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy: self.line_number_area.scroll(0, dy)
        else: self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_sizeHint(), cr.height()))

    def line_number_area_paintEvent(self, event):
        if not self.settings.value("show_line_numbers", True, type=bool): return
        painter = QPainter(self.line_number_area)
        bg_color = self.palette().color(self.backgroundRole()).darker(105)
        text_color = self.palette().color(self.foregroundRole()).lighter(150)
        painter.fillRect(event.rect(), bg_color)
        painter.setPen(text_color)
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, top, self.line_number_area.width() - 8, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, number)
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1


class EditorTabs(QTabWidget):
    file_saved = Signal(str)
    editor_status_changed = Signal(str) # To feed the MainWindow status bar

    def __init__(self, is_dark_theme=True):
        super().__init__()
        self.is_dark_theme = is_dark_theme
        self.setTabsClosable(True)
        self.setMovable(True)
        self.tabCloseRequested.connect(self.request_close_tab)
        self.currentChanged.connect(self.on_tab_changed)

    def set_theme(self, is_dark):
        self.is_dark_theme = is_dark
        for i in range(self.count()):
            self.widget(i).set_theme(is_dark)

    def reload_settings(self):
        for i in range(self.count()):
            self.widget(i).update_font()
            self.widget(i).update_line_number_area_width(0)

    def on_tab_changed(self, index):
        if index != -1:
            editor = self.widget(index)
            editor.setFocus()
            self.update_status(editor)

    def update_status(self, editor=None):
        if not editor:
            editor = self.currentWidget()
        if not editor:
            self.editor_status_changed.emit("RTL Studio Ready")
            return
            
        cursor = editor.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        settings = QSettings("PINARX", "RTL_Studio")
        sp = settings.value("tab_width", 4)
        sp_txt = "Spaces" if settings.value("use_spaces", True, type=bool) else "Tabs"
        self.editor_status_changed.emit(f"Ln {ln}, Col {col}  |  {sp_txt}: {sp}  |  UTF-8")

    def open_file(self, filepath):
        for i in range(self.count()):
            if self.widget(i).filepath == filepath:
                self.setCurrentIndex(i)
                return True

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read file:\n{str(e)}")
            return False

        editor = CodeEditor(filepath, self.is_dark_theme)
        editor.setPlainText(content)
        
        # Determine if it's RTL to apply highligher, else disable
        if not filepath.endswith(('.v', '.sv', '.vh', '.svh')):
            editor.highlighter.setDocument(None)
            
        editor.textChanged.connect(lambda: self.mark_modified(editor))
        editor.cursorPositionChanged.connect(lambda: self.update_status(editor))
        
        filename = os.path.basename(filepath)
        index = self.addTab(editor, filename)
        self.setTabToolTip(index, filepath)
        self.setCurrentIndex(index)
        editor.document().setModified(False)
        return True

    def mark_modified(self, editor):
        index = self.indexOf(editor)
        if index == -1: return
        filename = os.path.basename(editor.filepath)
        self.setTabText(index, f"{filename} *" if editor.document().isModified() else filename)

    def save_active_file(self):
        index = self.currentIndex()
        if index != -1: self.save_file(index)

    def save_all_files(self):
        for i in range(self.count()):
            if self.widget(i).document().isModified():
                self.save_file(i)

    def save_file(self, index):
        editor = self.widget(index)
        if not editor.filepath: return
        try:
            with open(editor.filepath, 'w', encoding='utf-8') as f:
                f.write(editor.toPlainText())
            editor.document().setModified(False)
            self.mark_modified(editor)
            self.file_saved.emit(editor.filepath)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{str(e)}")

    def request_close_tab(self, index):
        editor = self.widget(index)
        if editor.document().isModified():
            filename = os.path.basename(editor.filepath)
            reply = QMessageBox.question(
                self, "Unsaved Changes", 
                f"'{filename}' has unsaved changes.\nDo you want to save before closing?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Save: self.save_file(index)
            elif reply == QMessageBox.StandardButton.Cancel: return False

        self.removeTab(index)
        if self.count() == 0:
            self.update_status(None)
        return True

    def close_all_tabs(self):
        while self.count() > 0:
            if not self.request_close_tab(0): return False
        return True