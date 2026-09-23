"""
Syntax Highlighter
Responsibility: Applies regex-based syntax highlighting for Verilog/SystemVerilog.
"""
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt, QRegularExpression

class RTLHighlighter(QSyntaxHighlighter):
    def __init__(self, document, is_dark_theme=True):
        super().__init__(document)
        self.is_dark_theme = is_dark_theme
        self.highlighting_rules = []
        self.setup_rules()

    def set_theme(self, is_dark_theme):
        self.is_dark_theme = is_dark_theme
        self.setup_rules()
        self.rehighlight()

    def setup_rules(self):
        self.highlighting_rules = []
        
        # Define Palettes
        if self.is_dark_theme:
            c_keyword = QColor("#F3A6C8") # Pink accent
            c_type = QColor("#89DDFF")    # Cyan
            c_string = QColor("#C3E88D")  # Green
            c_number = QColor("#F78C6C")  # Orange
            c_comment = QColor("#717CB4") # Muted Indigo
            c_preproc = QColor("#C792EA") # Purple
        else:
            c_keyword = QColor("#d85c96")
            c_type = QColor("#2962FF")
            c_string = QColor("#2E7D32")
            c_number = QColor("#E65100")
            c_comment = QColor("#9E9E9E")
            c_preproc = QColor("#6A1B9A")

        # Formats
        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(c_keyword)
        keyword_fmt.setFontWeight(QFont.Weight.Bold)

        type_fmt = QTextCharFormat()
        type_fmt.setForeground(c_type)

        preproc_fmt = QTextCharFormat()
        preproc_fmt.setForeground(c_preproc)

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(c_number)

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(c_string)

        self.comment_fmt = QTextCharFormat()
        self.comment_fmt.setForeground(c_comment)
        self.comment_fmt.setFontItalic(True)

        # 1. Keywords
        keywords = [
            "module", "endmodule", "always", "always_ff", "always_comb", "initial",
            "begin", "end", "if", "else", "case", "endcase", "for", "while",
            "generate", "genvar", "function", "endfunction", "task", "endtask",
            "assign", "interface", "endinterface", "package", "endpackage",
            "class", "endclass", "import", "export", "assert", "cover", 
            "property", "endproperty", "sequence", "endsequence"
        ]
        for word in keywords:
            rule = QRegularExpression(rf"\b{word}\b")
            self.highlighting_rules.append((rule, keyword_fmt))

        # 2. Types
        types = ["input", "output", "inout", "wire", "reg", "logic", "integer", 
                 "parameter", "localparam", "typedef", "struct", "enum"]
        for word in types:
            rule = QRegularExpression(rf"\b{word}\b")
            self.highlighting_rules.append((rule, type_fmt))

        # 3. Preprocessor
        self.highlighting_rules.append((QRegularExpression(r"`\w+"), preproc_fmt))

        # 4. Numbers (Base formats like 8'hFF, 32'd10, or raw digits)
        self.highlighting_rules.append((QRegularExpression(r"\b\d+'[bBoOdDhH][0-9a-fA-FxXzZ_]+\b"), number_fmt))
        self.highlighting_rules.append((QRegularExpression(r"\b\d+\b"), number_fmt))

        # 5. Strings
        self.highlighting_rules.append((QRegularExpression(r'".*?"'), string_fmt))
        
        # 6. Single Line Comments
        self.highlighting_rules.append((QRegularExpression(r"//[^\n]*"), self.comment_fmt))

        # Multi-line comment state tracking
        self.comment_start_expr = QRegularExpression(r"/\*")
        self.comment_end_expr = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

        # Multi-line comment parsing
        self.setCurrentBlockState(0)
        startIndex = 0
        if self.previousBlockState() != 1:
            startIndex = text.find("/*")
        
        while startIndex >= 0:
            match = self.comment_end_expr.match(text, startIndex)
            endIndex = match.capturedStart()
            commentLength = 0
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + match.capturedLength()
            
            self.setFormat(startIndex, commentLength, self.comment_fmt)
            startIndex = text.find("/*", startIndex + commentLength)