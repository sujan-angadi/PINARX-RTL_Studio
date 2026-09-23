import sys
from PySide6.QtWidgets import QApplication
from src.rtl_studio.main_window import MainWindow
from src.rtl_studio.splash import SplashScreen

def main():
    app = QApplication(sys.argv)
    
    # Initialize the main window, but DO NOT show it yet
    main_window = MainWindow()
    
    # Initialize and display the splash screen
    splash = SplashScreen()
    
    # When the splash fade animation completes, maximize the main window
    splash.finished.connect(main_window.showMaximized)
    splash.show()
    
    return app.exec()