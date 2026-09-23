import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal
from PySide6.QtGui import QPixmap

class SplashScreen(QWidget):
    # Custom signal to notify when the fade animation is fully complete
    finished = Signal()

    def __init__(self):
        super().__init__()
        
        # Frameless, stays on top, standard splash behavior
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(640, 420)
        
        # FIX: Force the top-level QWidget to paint its background using the stylesheet
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Strict theme compliance for the splash background
        self.setStyleSheet("background-color: #fefdf8;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Center Logo
        self.logo_label = QLabel(self)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Resolve absolute path to assets/RTL.png safely relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.abspath(os.path.join(base_dir, "..", "..", "assets", "RTL.png"))
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Scale gracefully, preserving aspect ratio
            pixmap = pixmap.scaled(350, 350, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.setText("PINARX RTL Studio")
            self.logo_label.setStyleSheet("color: #171717; font-size: 32px; font-weight: bold;")
            
        # Loading Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(2) # Thin, minimal line
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # Minimal styling: transparent background, dark accent chunk
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: transparent; 
            }
            QProgressBar::chunk {
                background-color: #171717;
            }
        """)
        
        # Spacing to keep layout professional and balanced
        layout.addStretch()
        layout.addWidget(self.logo_label)
        layout.addSpacing(40)
        layout.addWidget(self.progress_bar)
        layout.addStretch()
        
        # Setup opacity effect for smooth fade out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Setup timing: 4.8 seconds to reach 100% (5000ms - 200ms buffer)
        self.progress = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(48) # 100 ticks * 48ms = 4.8 seconds
        
    def update_progress(self):
        self.progress += 1
        self.progress_bar.setValue(self.progress)
        
        if self.progress >= 100:
            self.timer.stop()
            self.fade_out()
            
    def fade_out(self):
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(500) # 0.5 seconds fade
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.finished.connect(self.on_fade_finished)
        self.animation.start()
        
    def on_fade_finished(self):
        self.finished.emit()
        self.close()