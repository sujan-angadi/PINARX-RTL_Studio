"""
Verilog Editor
Responsibility: Provides a text editor with line numbers, syntax highlighting, and bracket matching.
"""
import os
import re
from PySide6.QtWidgets import QTabWidget, QPlainTextEdit, QWidget, QTextEdit
from PySide6.QtCore import Qt, Signal, QRect, QRegularExpression, QSettings
from PySide6.QtGui import QColor, QTextFormat, QPainter, QFont, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QFontMetrics

class VerilogHighlighter(QSyntaxHighlighter):
    def __init__(self, document, is_dark=False, is_productive=False, is_candy=False):
        super().__init__(document)
        self.is_dark = is_dark
        self.is_productive = is_productive
        self.is_candy = is_candy
        self.update_palette()

    def update_palette(self):
        if self.is_candy:
            # EXACT FIX: Candy Pop specific syntax colors
            keyword_color = QColor("#ff8fb1")
            type_color = QColor("#5ec8f7")
            comment_color = QColor("#c39cc0")
            string_color = QColor("#7ed957")
            number_color = QColor("#ffd166")
        elif self.is_productive:
            keyword_color = QColor("#FF79C6")
            type_color = QColor("#82AAFF")
            comment_color = QColor("#6F849C")
            string_color = QColor("#55E6A5")
            number_color = QColor("#F78C6C")
        elif self.is_dark:
            keyword_color = QColor("#FF79C6")
            type_color = QColor("#82AAFF")
            comment_color = QColor("#8A94A6")
            string_color = QColor("#C3E88D")
            number_color = QColor("#F78C6C")
        else:
            keyword_color = QColor("#8B5CF6")
            type_color = QColor("#3B82F6")
            comment_color = QColor("#5F6B78")
            string_color = QColor("#22A06B")
            number_color = QColor("#F97316")

        self.rules = []
        
        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(keyword_color)
        kw_fmt.setFontWeight(QFont.Weight.Bold)
        keywords = [r'\bmodule\b', r'\bendmodule\b', r'\bassign\b', r'\balways\b', r'\binitial\b', 
                    r'\bbegin\b', r'\bend\b', r'\bif\b', r'\belse\b', r'\bcase\b', r'\bendcase\b', 
                    r'\bposedge\b', r'\bnegedge\b', r'\bdefault\b', r'\bparameter\b', r'\blocalparam\b']
        for kw in keywords:
            self.rules.append((re.compile(kw), kw_fmt))

        type_fmt = QTextCharFormat()
        type_fmt.setForeground(type_color)
        types = [r'\binput\b', r'\boutput\b', r'\binout\b', r'\bwire\b', r'\breg\b', r'\binteger\b', r'\bgenvar\b']
        for t in types:
            self.rules.append((re.compile(t), type_fmt))

        num_fmt = QTextCharFormat()
        num_fmt.setForeground(number_color)
        self.rules.append((re.compile(r"\b\d+'[bBoOdDhH][0-9a-fA-F_xXzZ]+\b"), num_fmt))
        self.rules.append((re.compile(r"\b\d+\b"), num_fmt))

        str_fmt = QTextCharFormat()
        str_fmt.setForeground(string_color)
        self.rules.append((re.compile(r'"[^"\\]*(\\.[^"\\]*)*"'), str_fmt))

        self.comment_fmt = QTextCharFormat()
        self.comment_fmt.setForeground(comment_color)
        self.rules.append((re.compile(r'//[^\n]*'), self.comment_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
                
        self.setCurrentBlockState(0)
        start_index = 0
        if self.previousBlockState() != 1:
            start_index = text.find("/*")

        while start_index >= 0:
            end_index = text.find("*/", start_index)
            if end_index == -1:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + 2
            
            self.setFormat(start_index, comment_length, self.comment_fmt)
            start_index = text.find("/*", start_index + comment_length)

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return self.codeEditor.get_gutter_width()

    def paintEvent(self, event):
        self.codeEditor.draw_gutter(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self, is_dark=False, is_productive=False, is_candy=False):
        super().__init__()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        self.gutter = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_gutter_width)
        self.updateRequest.connect(self.update_gutter_rect)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.cursorPositionChanged.connect(self.match_brackets)
        
        self.highlighter = VerilogHighlighter(self.document(), is_dark, is_productive, is_candy)
        
        # Pull font/tab preferences synchronously at startup
        self.apply_user_settings()
        self.update_gutter_width()
        self.set_theme(is_dark, is_productive, is_candy)

    def apply_user_settings(self):
        settings = QSettings("PINARX", "RTL_Studio")
        settings.sync() # Force synchronous pull from disk
        
        # EXACT FIX: Support native V2.0 keys ("font_size") and fallback keys
        fs = settings.value("font_size")
        if fs is None: fs = settings.value("editor_font_size", 11)
        
        tw = settings.value("tab_width")
        if tw is None: tw = settings.value("editor_tab_width", 4)
        
        try:
            font_size = int(fs)
            tab_width = int(tw)
        except (ValueError, TypeError):
            font_size = 11
            tab_width = 4
            
        font = QFont("Courier New", font_size)
        self.setFont(font)
        
        # Calculate exactly using the new font object
        fm = QFontMetrics(font)
        self.setTabStopDistance(fm.horizontalAdvance(' ') * tab_width)
        
        # Explicitly force the stylesheet to override the global 13px UI limit
        self.setStyleSheet(f"QPlainTextEdit {{ font-family: 'Courier New'; font-size: {font_size}pt; }}")
        
        self.update_gutter_width()
        self.viewport().update()

    def set_theme(self, is_dark, is_productive=False, is_candy=False):
        self.highlighter.is_productive = is_productive
        self.highlighter.is_dark = is_dark
        self.highlighter.is_candy = is_candy
        self.highlighter.update_palette()
        
        if is_candy:
            # EXACT FIX: Light pink editor UI specifics
            self.lineHighlightColor = QColor("#fff0f7")
            self.lineNumberColor = QColor("#a983a0")
            self.lineNumberBgColor = QColor("#ffd9ec")
            self.bracketMatchColor = QColor("#ffbedd")
        elif is_productive:
            self.lineHighlightColor = QColor("#1E2735")
            self.lineNumberColor = QColor("#8192AA")
            self.lineNumberBgColor = QColor("#0A0E17")
            self.bracketMatchColor = QColor("#1F2937")
        elif is_dark:
            self.lineHighlightColor = QColor("#29292D")
            self.lineNumberColor = QColor("#7B8496")
            self.lineNumberBgColor = QColor("#17171A")
            self.bracketMatchColor = QColor("#5caed8")
        else:
            self.lineHighlightColor = QColor("#e8e8ed")
            self.lineNumberColor = QColor("#8A94A6")
            self.lineNumberBgColor = QColor("#f8f8fa")
            self.bracketMatchColor = QColor("#b3e5fc")
            
        self.match_brackets()
        self.viewport().update()

    def get_gutter_width(self):
        digits = max(1, len(str(self.blockCount())))
        width = self.fontMetrics().horizontalAdvance('9') * digits + 10
        return width

    def update_gutter_width(self, blockCount=0):
        self.setViewportMargins(self.get_gutter_width(), 0, 0, 0)

    def update_gutter_rect(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_gutter_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.get_gutter_width(), cr.height()))

    def draw_gutter(self, event):
        painter = QPainter(self.gutter)
        painter.fillRect(event.rect(), self.lineNumberBgColor)
        painter.setPen(self.lineNumberColor)

        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_num + 1)
                painter.drawText(0, top, self.gutter.width() - 4, self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_num += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(self.lineHighlightColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def match_brackets(self):
        cursor = self.textCursor()
        selections = self.extraSelections()
        selections = [s for s in selections if s.format.property(QTextFormat.Property.FullWidthSelection)]

        doc = self.document()
        pos = cursor.position()
        text = doc.toPlainText()

        pairs = {'(': ')', '[': ']', '{': '}'}
        rev_pairs = {v: k for k, v in pairs.items()}

        def highlight_pair(p1, p2):
            fmt = QTextCharFormat()
            fmt.setBackground(self.bracketMatchColor)
            
            s1 = QTextEdit.ExtraSelection()
            s1.format = fmt
            c1 = QTextCursor(doc)
            c1.setPosition(p1)
            c1.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            s1.cursor = c1
            
            s2 = QTextEdit.ExtraSelection()
            s2.format = fmt
            c2 = QTextCursor(doc)
            c2.setPosition(p2)
            c2.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            s2.cursor = c2
            
            selections.extend([s1, s2])

        if pos < len(text) and text[pos] in pairs:
            char = text[pos]
            match_char = pairs[char]
            depth = 1
            for i in range(pos + 1, len(text)):
                if text[i] == char: depth += 1
                elif text[i] == match_char: depth -= 1
                if depth == 0:
                    highlight_pair(pos, i)
                    break
        elif pos > 0 and text[pos - 1] in rev_pairs:
            char = text[pos - 1]
            match_char = rev_pairs[char]
            depth = 1
            for i in range(pos - 2, -1, -1):
                if text[i] == char: depth += 1
                elif text[i] == match_char: depth -= 1
                if depth == 0:
                    highlight_pair(pos - 1, i)
                    break
                    
        self.setExtraSelections(selections)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            current_line = cursor.block().text()
            indentation = len(current_line) - len(current_line.lstrip())
            super().keyPressEvent(e)
            self.insertPlainText(" " * indentation)
            return
        super().keyPressEvent(e)

class EditorTabs(QTabWidget):
    file_saved = Signal(str)
    editor_status_changed = Signal(str)

    def __init__(self, is_dark_theme):
        super().__init__()
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.currentChanged.connect(self.on_tab_changed)
        self.is_dark = is_dark_theme
        self.is_productive = False
        self.is_candy = False
        self.file_paths = {}

    def open_file(self, filepath):
        norm_filepath = os.path.normpath(filepath)
        
        for i in range(self.count()):
            known_path = self.file_paths.get(id(self.widget(i)))
            if known_path and os.path.normpath(known_path) == norm_filepath:
                self.setCurrentIndex(i)
                return

        editor = CodeEditor(self.is_dark, self.is_productive, self.is_candy)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                editor.setPlainText(f.read())
        except Exception as e:
            self.editor_status_changed.emit(f"Failed to open {os.path.basename(filepath)}")
            return

        filename = os.path.basename(filepath)
        idx = self.addTab(editor, filename)
        self.file_paths[id(editor)] = filepath
        self.setCurrentIndex(idx)
        
        editor.document().modificationChanged.connect(
            lambda modified, w=editor, i=idx: self.mark_tab_modified(w, modified)
        )
        self.editor_status_changed.emit(f"Opened {filename}")

    def mark_tab_modified(self, widget, modified):
        idx = self.indexOf(widget)
        if idx != -1:
            filepath = self.file_paths.get(id(widget), "")
            filename = os.path.basename(filepath)
            if modified:
                self.setTabText(idx, filename + "*")
            else:
                self.setTabText(idx, filename)

    def save_active_file(self):
        editor = self.currentWidget()
        if editor:
            filepath = self.file_paths.get(id(editor))
            if filepath:
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(editor.toPlainText())
                    editor.document().setModified(False)
                    self.file_saved.emit(filepath)
                    self.editor_status_changed.emit(f"Saved {os.path.basename(filepath)}")
                except Exception:
                    self.editor_status_changed.emit(f"Error saving {os.path.basename(filepath)}")

    def save_all_files(self):
        for i in range(self.count()):
            editor = self.widget(i)
            if editor and editor.document().isModified():
                filepath = self.file_paths.get(id(editor))
                if filepath:
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(editor.toPlainText())
                        editor.document().setModified(False)
                        self.file_saved.emit(filepath)
                    except Exception:
                        pass
        self.editor_status_changed.emit("All files saved.")

    def close_tab(self, index):
        editor = self.widget(index)
        self.removeTab(index)
        self.file_paths.pop(id(editor), None)
        editor.deleteLater()

    def close_all_tabs(self):
        while self.count() > 0:
            self.close_tab(0)
        return True

    def on_tab_changed(self, index):
        if index >= 0:
            filepath = self.file_paths.get(id(self.widget(index)), "")
            self.editor_status_changed.emit(filepath)

    def set_theme(self, is_dark, is_productive=False, is_candy=False):
        self.is_dark = is_dark
        self.is_productive = is_productive
        self.is_candy = is_candy
        for i in range(self.count()):
            editor = self.widget(i)
            if isinstance(editor, CodeEditor):
                editor.set_theme(is_dark, is_productive, is_candy)

    # THIS IS THE VITAL LOOP THAT PUSHES THE SETTINGS TO THE TABS
    def reload_settings(self):
        for i in range(self.count()):
            editor = self.widget(i)
            if isinstance(editor, CodeEditor):
                editor.apply_user_settings()

    def is_modified(self, filepath):
        norm_filepath = os.path.normpath(filepath)
        for i in range(self.count()):
            known_path = self.file_paths.get(id(self.widget(i)))
            if known_path and os.path.normpath(known_path) == norm_filepath:
                return self.widget(i).document().isModified()
        return False

    def close_file(self, filepath):
        norm_filepath = os.path.normpath(filepath)
        for i in range(self.count()):
            known_path = self.file_paths.get(id(self.widget(i)))
            if known_path and os.path.normpath(known_path) == norm_filepath:
                self.removeTab(i)
                return

    def rename_file(self, old_path, new_path):
        norm_old_path = os.path.normpath(old_path)
        for i in range(self.count()):
            editor_id = id(self.widget(i))
            known_path = self.file_paths.get(editor_id)
            if known_path and os.path.normpath(known_path) == norm_old_path:
                self.file_paths[editor_id] = os.path.normpath(new_path)
                is_mod = self.widget(i).document().isModified()
                self.setTabText(i, os.path.basename(new_path) + ("*" if is_mod else ""))
                return