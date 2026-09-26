"""
Splash Screen
Responsibility: Displays the initial loading screen with progress bar and fade-out animation.
"""
import os
import sys
from PySide6.QtWidgets import QSplashScreen, QProgressBar, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QColor

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        # Assuming splash.py is inside src/rtl_studio/
        base_path = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    return os.path.join(base_path, relative_path)

class SplashScreen(QSplashScreen):
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.resize(640, 420)
        
        # Safely resolve the absolute path to RTL.png
        img_path = get_resource_path(os.path.join("assets", "RTL.png"))
        
        if os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            self.setPixmap(pixmap.scaled(640, 420, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            print(f"DIAGNOSTIC: Splash image not found at: {img_path}")
            # Use blank background as requested; explicitly omitting text fallback
            pixmap = QPixmap(640, 420)
            pixmap.fill(QColor("#fefdf8"))
            self.setPixmap(pixmap)

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        # EXACT FIX: Reduced bottom margin from 30 to 5. 
        # This pushes the progress bar 25 pixels further down, away from the logo text.
        self.layout.setContentsMargins(40, 0, 40, 5)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #E0E0E0;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #F3A6C8;
                border-radius: 3px;
            }
        """)
        self.layout.addWidget(self.progress_bar)

        self.progress = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        # 4.8 seconds / 100 steps = 48ms
        self.timer.start(48)

    def update_progress(self):
        self.progress += 1
        self.progress_bar.setValue(self.progress)
        if self.progress >= 100:
            self.timer.stop()
            self.fade_out()

    def fade_out(self):
        self.opacity = 1.0
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(self.do_fade)
        self.fade_timer.start(30)

    def do_fade(self):
        self.opacity -= 0.05
        if self.opacity <= 0:
            self.fade_timer.stop()
            self.finished.emit()
        else:
            self.setWindowOpacity(self.opacity)