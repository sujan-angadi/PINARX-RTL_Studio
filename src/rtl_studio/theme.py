"""
Theme Manager & Icon Generator
Responsibility: Provides application stylesheets and procedural vector EDA icons.
"""
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

def create_eda_icon(icon_name: str, is_dark: bool = False) -> QIcon:
    """Generates crisp vector-drawn EDA toolbar icons matching the active theme."""
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    color = QColor("#F2F2F2" if is_dark else "#121214")
    
    if icon_name == "build":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(QRectF(3, 3, 10, 4), 1, 1)      
        painter.drawRoundedRect(QRectF(7, 7, 2, 7), 0.5, 0.5)   
        
    elif icon_name == "run":
        path = QPainterPath()
        path.moveTo(4, 3)
        path.lineTo(13, 8)
        path.lineTo(4, 13)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(path)
        
    elif icon_name == "stop":
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRoundedRect(QRectF(3.5, 3.5, 9, 9), 1.5, 1.5)
        
    elif icon_name == "waveform":
        path = QPainterPath()
        path.moveTo(2, 12); path.lineTo(2, 4); path.lineTo(6, 4); path.lineTo(6, 12)
        path.lineTo(10, 12); path.lineTo(10, 4); path.lineTo(14, 4); path.lineTo(14, 12)
        pen = QPen(color, 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        
    elif icon_name == "synthesis":
        pen = QPen(color, 1.4)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(4.5, 4.5, 7, 7), 1, 1)  
        painter.drawLine(QPointF(1.5, 6.5), QPointF(4.5, 6.5))
        painter.drawLine(QPointF(1.5, 9.5), QPointF(4.5, 9.5))
        painter.drawLine(QPointF(11.5, 6.5), QPointF(14.5, 6.5))
        painter.drawLine(QPointF(11.5, 9.5), QPointF(14.5, 9.5))
        painter.drawLine(QPointF(6.5, 1.5), QPointF(6.5, 4.5))
        painter.drawLine(QPointF(9.5, 1.5), QPointF(9.5, 4.5))
        painter.drawLine(QPointF(6.5, 11.5), QPointF(6.5, 14.5))
        painter.drawLine(QPointF(9.5, 11.5), QPointF(9.5, 14.5))

    elif icon_name == "schematic":
        pen = QPen(color, 1.5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(2, 6, 4, 4))
        painter.drawRect(QRectF(10, 2, 4, 4))
        painter.drawRect(QRectF(10, 10, 4, 4))
        painter.drawLine(QPointF(6, 8), QPointF(8, 8))
        painter.drawLine(QPointF(8, 8), QPointF(8, 4))
        painter.drawLine(QPointF(8, 8), QPointF(8, 12))
        painter.drawLine(QPointF(8, 4), QPointF(10, 4))
        painter.drawLine(QPointF(8, 12), QPointF(10, 12))
        
    painter.end()
    return QIcon(pixmap)

def get_stylesheet(is_dark=True):
    if is_dark:
        colors = {
            "base": "#0D0D0F", "surface": "#121214", "sec_surface": "#17171A",
            "border": "#29292D", "text": "#F2F2F2", "sec_text": "#92929A",
            "accent": "#F3A6C8", "editor_bg": "#18181B"
        }
    else:
        colors = {
            "base": "#f0f0f4", "surface": "#ffffff", "sec_surface": "#f8f8fa",
            "border": "#dcdce0", "text": "#121214", "sec_text": "#666670",
            "accent": "#d85c96", "editor_bg": "#ffffff"
        }

    return f"""
        QMainWindow, QWidget, QDialog {{ background-color: {colors["base"]}; color: {colors["text"]}; }}
        QPlainTextEdit#Editor {{ background-color: {colors["editor_bg"]}; color: {colors["text"]}; border: none; }}
        QLineEdit, QComboBox, QSpinBox {{ background-color: {colors["surface"]}; border: 1px solid {colors["border"]}; padding: 4px; color: {colors["text"]}; }}
        QListWidget {{ background-color: {colors["surface"]}; border: 1px solid {colors["border"]}; color: {colors["text"]}; }}
        
        QPushButton {{ background-color: {colors["sec_surface"]}; border: 1px solid {colors["border"]}; padding: 4px 12px; color: {colors["text"]}; }}
        QPushButton:hover {{ background-color: {colors["border"]}; }}
        
        QMenuBar {{ background-color: {colors["surface"]}; border-bottom: 1px solid {colors["border"]}; }}
        QMenuBar::item:selected {{ background-color: {colors["sec_surface"]}; color: {colors["accent"]}; }}
        QMenu {{ background-color: {colors["surface"]}; border: 1px solid {colors["border"]}; }}
        QMenu::item:selected {{ background-color: {colors["sec_surface"]}; color: {colors["accent"]}; }}

        QToolBar {{ background-color: {colors["surface"]}; border-bottom: 1px solid {colors["border"]}; spacing: 4px; padding: 4px; }}
        QToolBar::separator {{ background-color: {colors["border"]}; width: 1px; margin: 4px 10px; }}
        QToolButton {{ background-color: transparent; border: 1px solid transparent; border-radius: 4px; padding: 5px 12px; color: {colors["text"]}; font-weight: bold; font-size: 12px; }}
        QToolButton:hover {{ background-color: {colors["sec_surface"]}; border: 1px solid {colors["border"]}; }}
        QToolButton:pressed {{ background-color: {colors["border"]}; }}
        QToolButton:disabled {{ color: {colors["sec_text"]}; }}

        QTreeWidget {{ background-color: {colors["surface"]}; border: none; }}
        QTreeWidget::item:selected {{ background-color: {colors["sec_surface"]}; color: {colors["accent"]}; }}
        QHeaderView::section {{ background-color: {colors["sec_surface"]}; color: {colors["sec_text"]}; border: none; padding: 4px; font-weight: bold; font-size: 11px; }}

        QPlainTextEdit#OutputPanel {{ background-color: {colors["surface"]}; border: 1px solid {colors["border"]}; font-family: monospace; color: {colors["sec_text"]}; }}

        QTabWidget::pane {{ border: 1px solid {colors["border"]}; background: {colors["base"]}; }}
        QTabBar::tab {{ background: {colors["surface"]}; border: 1px solid {colors["border"]}; padding: 6px 12px; color: {colors["sec_text"]}; }}
        QTabBar::tab:selected {{ background: {colors["editor_bg"]}; color: {colors["accent"]}; border-bottom-color: {colors["editor_bg"]}; }}

        QSplitter::handle {{ background-color: {colors["border"]}; margin: 2px; }}
        QStatusBar {{ background-color: {colors["surface"]}; border-top: 1px solid {colors["border"]}; color: {colors["sec_text"]}; }}
    """