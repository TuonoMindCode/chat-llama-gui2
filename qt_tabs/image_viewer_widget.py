"""
Image viewer widget for displaying and navigating generated images
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap


class ImageViewerWidget(QWidget):
    """Widget for image viewing with navigation and zoom controls"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the image viewer UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(3)
        self.setLayout(main_layout)
        
        # Title
        image_title = QLabel("🖼️ Generated Images")
        title_font = QFont()
        title_font.setBold(True)
        image_title.setFont(title_font)
        main_layout.addWidget(image_title, 0)
        
        # Image control buttons (above image)
        image_controls_layout = QHBoxLayout()
        image_controls_layout.setContentsMargins(0, 0, 0, 0)
        image_controls_layout.setSpacing(2)
        
        # Previous image button
        self.prev_image_button = QPushButton("◀")
        self.prev_image_button.setMaximumWidth(40)
        self.prev_image_button.setMaximumHeight(25)
        self.prev_image_button.setToolTip("Previous image")
        image_controls_layout.addWidget(self.prev_image_button)
        
        # Next image button
        self.next_image_button = QPushButton("▶")
        self.next_image_button.setMaximumWidth(40)
        self.next_image_button.setMaximumHeight(25)
        self.next_image_button.setToolTip("Next image")
        image_controls_layout.addWidget(self.next_image_button)
        
        # Zoom controls
        self.zoom_out_button = QPushButton("🔍−")
        self.zoom_out_button.setMaximumWidth(40)
        self.zoom_out_button.setMaximumHeight(25)
        self.zoom_out_button.setToolTip("Zoom out")
        image_controls_layout.addWidget(self.zoom_out_button)
        
        self.zoom_in_button = QPushButton("🔍+")
        self.zoom_in_button.setMaximumWidth(40)
        self.zoom_in_button.setMaximumHeight(25)
        self.zoom_in_button.setToolTip("Zoom in")
        image_controls_layout.addWidget(self.zoom_in_button)
        
        image_controls_layout.addStretch()
        main_layout.addLayout(image_controls_layout, 0)
        
        # Image display area
        self.image_label = QLabel()
        self.image_label.setStyleSheet("border: 1px solid #cccccc; background-color: #f5f5f5;")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setText("(No images yet)")
        main_layout.addWidget(self.image_label, 1)
    
    def show_previous_image(self):
        """Show previous image"""
        if hasattr(self.parent_widget, 'current_image_index'):
            self.parent_widget.current_image_index = max(0, self.parent_widget.current_image_index - 1)
            self.update_image_display()
    
    def show_next_image(self):
        """Show next image"""
        if hasattr(self.parent_widget, 'current_image_list') and self.parent_widget.current_image_list:
            if not hasattr(self.parent_widget, 'current_image_index'):
                self.parent_widget.current_image_index = 0
            self.parent_widget.current_image_index = min(len(self.parent_widget.current_image_list) - 1, self.parent_widget.current_image_index + 1)
            self.update_image_display()
    
    def zoom_in_image(self):
        """Zoom in on image"""
        if hasattr(self.parent_widget, 'current_zoom'):
            self.parent_widget.current_zoom = min(3.0, self.parent_widget.current_zoom + 0.2)
        else:
            self.parent_widget.current_zoom = 1.2
        self.update_image_display()
    
    def zoom_out_image(self):
        """Zoom out from image"""
        if hasattr(self.parent_widget, 'current_zoom'):
            self.parent_widget.current_zoom = max(0.5, self.parent_widget.current_zoom - 0.2)
        else:
            self.parent_widget.current_zoom = 0.8
        self.update_image_display()
    
    def fit_image(self):
        """Fit image to window"""
        self.parent_widget.current_zoom = 1.0
        self.update_image_display()
    
    def on_fit_image_toggled(self, state):
        """Handle fit image checkbox toggle"""
        if state == Qt.Checked:
            self.fit_image()
    
    def update_image_display(self):
        """Update image display with current zoom level and index"""
        if not hasattr(self.parent_widget, 'current_image_list') or not self.parent_widget.current_image_list:
            return
        
        try:
            image_path = self.parent_widget.current_image_list[self.parent_widget.current_image_index]
            pixmap = QPixmap(str(image_path))
            
            if not pixmap.isNull():
                # Apply zoom
                zoom = getattr(self.parent_widget, 'current_zoom', 1.0)
                scaled = pixmap.scaledToHeight(int(300 * zoom), Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setVisible(True)
        except Exception as e:
            print(f"[DEBUG] Error updating image display: {e}")
