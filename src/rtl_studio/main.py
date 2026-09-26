"""
Main Application Entry Point
Responsibility: Application bootstrapping, PyInstaller resource path resolution, and splash screen orchestration.
"""
import sys
import os
from PySide6.QtWidgets import QApplication

def get_base_path():
    """Get the absolute path to the project root or PyInstaller _MEIPASS."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    else:
        # Assuming main.py is in src/rtl_studio/
        return os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Set the current working directory to the base path immediately.
# This ensures that existing relative paths (e.g., 'assets/RTL.png') inside splash.py 
# resolve perfectly in both normal execution and PyInstaller environments.
os.chdir(get_base_path())

# Import components after path resolution
from src.rtl_studio.splash import SplashScreen
from src.rtl_studio.main_window import MainWindow

# Global reference to prevent garbage collection of the main window
main_window = None

def main():
    global main_window
    app = QApplication(sys.argv)
    
    # 1. Create the existing Splash Screen
    splash = SplashScreen()
    
    # 2. Define the transition sequence
    def launch_main_window():
        global main_window
        splash.close()
        main_window = MainWindow()
        # Enforce exact product naming
        main_window.setWindowTitle("RTL Studio")
        main_window.showMaximized()
        
    # 3. Connect the splash's existing 4.8-second finished signal to the launch sequence
    splash.finished.connect(launch_main_window)
    
    # 4. Show splash and start the Qt event loop
    splash.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())