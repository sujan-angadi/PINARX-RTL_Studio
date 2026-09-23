"""
Schematic Viewer
Responsibility: Displays the synthesized SVG schematic with zoom, pan, and fit-to-view capabilities.
"""
import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsView, QGraphicsScene
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtGui import QPainter
from PySide6.QtCore import Qt

class SchematicViewer(QDialog):
    def __init__(self, svg_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Schematic Viewer - {os.path.basename(svg_path)}")
        self.resize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Toolbar Controls
        toolbar = QHBoxLayout()
        self.zoom_in_btn = QPushButton("Zoom In")
        self.zoom_out_btn = QPushButton("Zoom Out")
        self.fit_view_btn = QPushButton("Fit to View")
        
        toolbar.addWidget(self.zoom_in_btn)
        toolbar.addWidget(self.zoom_out_btn)
        toolbar.addWidget(self.fit_view_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Graphics View setup
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.view)
        
        # Load and render the SVG
        self.svg_item = QGraphicsSvgItem(svg_path)
        self.scene.addItem(self.svg_item)
        
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.fit_view_btn.clicked.connect(self.fit_to_view)
        
        self.fit_to_view()
        
    def zoom_in(self):
        self.view.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.view.scale(1/1.2, 1/1.2)
        
    def fit_to_view(self):
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
    def wheelEvent(self, event):
        # Enable Ctrl + Scroll Wheel Zoom
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)