"""
Theme Manager
Responsibility: Centralized QSS styling and SVG icon generation for the IDE.
"""
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QByteArray

def get_stylesheet(is_dark=True, is_productive=False, is_candy=False):
    radius_btn = "4px"
    radius_tab = "4px"
    radius_item = "4px"

    if is_candy:
        # EXACT FIX: Light Baby-Pink Candy Pop Palette
        bg = "#ffd9ec"
        editor_bg = "#fff5fa"
        panel_bg = "#fff0f7"
        sub_panel_bg = "#fff5fa"
        border = "#ffbedd"
        accent_pri = "#ffd166"
        accent_sec = "#5ec8f7"
        text_pri = "#4a3b45"
        text_sec = "#a983a0"
        hover_bg = "rgba(255, 209, 102, 0.15)"
        selected_bg = "rgba(255, 209, 102, 0.3)"
        
        radius_btn = "12px"
        radius_tab = "12px"
        radius_item = "12px"
    elif is_productive:
        bg = "#0A0E17"
        editor_bg = "#121821"
        panel_bg = "#11151F"
        sub_panel_bg = "#1C2330"
        border = "#1F2937"
        accent_pri = "#7C5CFF"
        accent_sec = "#00E5FF"
        text_pri = "#E8EDF5"
        text_sec = "#9AA6B8"
        hover_bg = "rgba(124, 92, 255, 0.15)"
        selected_bg = "rgba(124, 92, 255, 0.2)"
    elif is_dark:
        bg = "#0A0E17"
        editor_bg = "#0D1117"
        panel_bg = "#11151F"
        sub_panel_bg = "#1C2330"
        border = "#1F2937"
        accent_pri = "#FF79C6"
        accent_sec = "#82AAFF"
        text_pri = "#E8EAF0"
        text_sec = "#7B8496"
        hover_bg = panel_bg
        selected_bg = sub_panel_bg
    else:
        bg = "#F7F5F0"
        editor_bg = "#FFFFFF"
        panel_bg = "#FFFFFF"
        sub_panel_bg = "#F5F4F0"
        border = "#E8E4DA"
        accent_pri = "#8B5CF6"
        accent_sec = "#3B82F6"
        text_pri = "#33393F"
        text_sec = "#8A94A6"
        hover_bg = sub_panel_bg
        selected_bg = sub_panel_bg

    return f"""
    QMainWindow, QDialog {{ background-color: {bg}; color: {text_pri}; }}
    QWidget {{ color: {text_pri}; font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 13px; }}
    
    QMenuBar {{ background-color: {panel_bg}; color: {text_pri}; border-bottom: 1px solid {border}; }}
    QMenuBar::item {{ background-color: transparent; color: {text_pri}; padding: 4px 8px; border-radius: {radius_item}; }}
    QMenuBar::item:selected {{ background-color: {hover_bg}; color: {text_pri}; }}
    QMenu {{ background-color: {panel_bg}; color: {text_pri}; border: 1px solid {border}; border-radius: {radius_item}; }}
    QMenu::item {{ background-color: transparent; color: {text_pri}; padding: 6px 24px 6px 12px; border-radius: {radius_item}; margin: 2px 4px; }}
    QMenu::item:selected {{ background-color: {hover_bg}; color: {text_pri}; }}
    QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0px; }}
    
    QToolBar {{ background-color: {panel_bg}; border-bottom: 1px solid {border}; padding: 6px; spacing: 12px; }}
    QToolButton {{ background-color: transparent; border: 1px solid transparent; border-radius: {radius_btn}; padding: 6px 12px; color: {text_pri}; font-weight: 600; }}
    QToolButton:hover {{ background-color: {hover_bg}; border: 1px solid {accent_pri if is_candy or is_productive else border}; }}
    QToolButton:pressed {{ background-color: {selected_bg}; }}
    QToolButton:disabled {{ color: {border}; }}
    
    QTabWidget::pane {{ border: 1px solid {border}; background: {editor_bg}; }}
    QTabBar::tab {{ background: {panel_bg}; border: 1px solid {border}; border-bottom: none; padding: 8px 16px; color: {text_sec}; margin-right: 2px; border-top-left-radius: {radius_tab}; border-top-right-radius: {radius_tab}; font-weight: bold; letter-spacing: 1px; }}
    QTabBar::tab:selected {{ background: {editor_bg}; color: {accent_pri}; border-top: 2px solid {accent_pri}; }}
    QTabBar::tab:hover:!selected {{ background: {hover_bg}; color: {text_pri}; }}
    
    QTreeWidget {{ background-color: {editor_bg}; border: none; color: {text_pri}; alternate-background-color: {panel_bg}; }}
    QTreeWidget::item {{ padding: 4px; border-radius: {radius_item}; margin: 1px 4px; }}
    QTreeWidget::item:selected {{ background-color: {selected_bg}; color: {text_pri}; }}
    QTreeWidget::item:hover:!selected {{ background-color: {hover_bg}; }}
    
    QSplitter::handle {{ background-color: {bg}; }}
    QStatusBar {{ background-color: {panel_bg}; border-top: 1px solid {border}; color: {text_sec}; }}
    
    QLineEdit, QPushButton, QSpinBox, QComboBox {{ background-color: {bg}; border: 1px solid {border}; color: {text_pri}; padding: 4px 8px; border-radius: {radius_btn}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 0px; }}
    QCheckBox {{ color: {text_pri}; }}
    QGroupBox {{ font-weight: bold; color: {text_sec}; border: 1px solid {border}; border-radius: {radius_btn}; margin-top: 2ex; padding: 10px; }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}
    
    QPushButton {{ background-color: {panel_bg if is_candy or is_productive else sub_panel_bg}; font-weight: bold; }}
    QPushButton:hover {{ background-color: {hover_bg}; border: 1px solid {accent_pri}; }}
    QPushButton:pressed {{ background-color: {bg}; }}
    
    QPlainTextEdit, QTextBrowser {{ background-color: {editor_bg}; color: {text_pri}; border: none; }}
    """

def create_eda_icon(name, is_dark, is_productive=False, is_candy=False):
    if is_candy:
        accent_pri = "#ffd166"
        accent_sec = "#5ec8f7"
        err = "#ff6b6b"
        text = "#4a3b45"
    elif is_productive:
        accent_pri = "#7C5CFF"
        accent_sec = "#00E5FF"
        err = "#FF4D6D"
        text = "#E8EDF5"
    elif is_dark:
        accent_pri = "#FF79C6"
        accent_sec = "#82AAFF"
        err = "#FF6B6B"
        text = "#E8EAF0"
    else:
        accent_pri = "#8B5CF6"
        accent_sec = "#3B82F6"
        err = "#E01A4F"
        text = "#33393F"

    svg_base = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    
    if name == "build":
        path = '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>'
        color = accent_pri
    elif name == "run":
        path = '<polygon points="5 3 19 12 5 21 5 3"></polygon>'
        color = accent_pri
    elif name == "stop":
        path = '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'
        color = err
    elif name == "waveform":
        path = '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>'
        color = accent_sec
    elif name == "synthesis":
        path = '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect><rect x="4" y="18" width="16" height="4" rx="1" ry="1"></rect><path d="M12 6v3"></path><path d="M8 12h8"></path><path d="M8 12v6"></path><path d="M16 12v6"></path>'
        color = accent_sec
    elif name == "schematic":
        path = '<circle cx="12" cy="12" r="3"></circle><path d="M3 12h3M18 12h3M12 3v3M12 18v3"></path>'
        # EXACT FIX: Schematic icon uses tertiary success green for Candy Pop
        color = "#7ed957" if is_candy else accent_sec
    else:
        path = '<circle cx="12" cy="12" r="10"></circle>'
        color = text

    svg_content = svg_base.format(color=color) + path + '</svg>'
    pixmap = QPixmap()
    pixmap.loadFromData(QByteArray(svg_content.encode('utf-8')), "SVG")
    return QIcon(pixmap)