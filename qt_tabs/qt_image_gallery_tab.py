"""
Image Gallery Tab for PyQt5
Browse and manage generated images
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QGridLayout, QFileDialog, QMessageBox, QFrame, QSpinBox
)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QPixmap
from pathlib import Path
import shutil


class ImageGalleryWidget(QFrame):
    """Single image widget with thumbnail and controls"""
    
    def __init__(self, image_path):
        super().__init__()
        self.image_path = Path(image_path)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        layout.addStretch(0)  # Don't expand vertically
        self.setLayout(layout)
        
        # Thumbnail (larger)
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(140, 140)
        self.load_thumbnail()
        layout.addWidget(self.thumbnail, alignment=Qt.AlignCenter)
        
        # Filename + Size (with more room)
        size_mb = self.image_path.stat().st_size / (1024 * 1024)
        info_text = f"{self.image_path.name}\n({size_mb:.1f} MB)"
        info_label = QLabel(info_text)
        info_label.setMaximumWidth(180)
        info_label.setStyleSheet("font-size: 7pt; color: #666666; text-align: center;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # Buttons (more spacious)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(2)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        open_btn = QPushButton("View")
        open_btn.setMaximumWidth(50)
        open_btn.setStyleSheet("font-size: 7pt; padding: 2px;")
        open_btn.clicked.connect(self.open_image)
        button_layout.addWidget(open_btn)
        
        copy_btn = QPushButton("Copy")
        copy_btn.setMaximumWidth(50)
        copy_btn.setStyleSheet("font-size: 7pt; padding: 2px;")
        copy_btn.clicked.connect(self.copy_image)
        button_layout.addWidget(copy_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.setMaximumWidth(50)
        delete_btn.setStyleSheet("font-size: 7pt; padding: 2px;")
        delete_btn.clicked.connect(self.delete_image)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)
        
        # Fixed size for good gallery layout (6 images per row)
        self.setFixedSize(200, 270)
        
        # Frame styling
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                background-color: #fafafa;
            }
        """)
    
    def load_thumbnail(self):
        """Load and display thumbnail"""
        try:
            pixmap = QPixmap(str(self.image_path))
            scaled = pixmap.scaledToWidth(150, Qt.SmoothTransformation)
            self.thumbnail.setPixmap(scaled)
        except Exception as e:
            self.thumbnail.setText(f"Error\nLoading\nImage")
            print(f"[DEBUG] Could not load thumbnail: {e}")
    
    def open_image(self):
        """Open image in default viewer"""
        try:
            import os
            import platform
            if platform.system() == "Darwin":  # macOS
                os.system(f"open '{self.image_path}'")
            elif platform.system() == "Windows":
                os.startfile(str(self.image_path))
            else:  # Linux
                os.system(f"xdg-open '{self.image_path}'")
        except Exception as e:
            print(f"[DEBUG] Could not open image: {e}")
    
    def copy_image(self):
        """Copy image to clipboard and show notification"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(QPixmap(str(self.image_path)))
            print(f"[DEBUG] Image copied to clipboard")
        except Exception as e:
            print(f"[DEBUG] Could not copy image: {e}")
    
    def delete_image(self):
        """Delete image file"""
        try:
            self.image_path.unlink()
            self.setVisible(False)
            print(f"[DEBUG] Image deleted: {self.image_path}")
        except Exception as e:
            print(f"[DEBUG] Could not delete image: {e}")


class QtImageGalleryTab(QWidget):
    """Image gallery for browsing generated images"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.gallery_path = Path("generated_images")
        self.gallery_path.mkdir(exist_ok=True)
        
        self.create_widgets()
        self.load_gallery()
        
        # Auto-refresh gallery every 2 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_for_new_images)
        self.refresh_timer.start(2000)
    
    def create_widgets(self):
        """Create gallery widgets"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title
        title = QLabel("🎨 Generated Images Gallery")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_gallery)
        control_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self.clear_all)
        control_layout.addWidget(clear_btn)
        
        export_btn = QPushButton("💾 Export Folder")
        export_btn.clicked.connect(self.export_folder)
        control_layout.addWidget(export_btn)
        
        control_layout.addStretch()
        
        # Image count
        self.count_label = QLabel("0 images")
        control_layout.addWidget(self.count_label)
        
        # Total size
        self.size_label = QLabel("0 MB")
        self.size_label.setStyleSheet("color: #666666; font-weight: bold;")
        control_layout.addWidget(self.size_label)
        
        main_layout.addLayout(control_layout)
        
        # Gallery scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.gallery_widget = QWidget()
        self.gallery_layout = QGridLayout()
        self.gallery_layout.setSpacing(10)
        self.gallery_widget.setLayout(self.gallery_layout)
        
        scroll_area.setWidget(self.gallery_widget)
        main_layout.addWidget(scroll_area, 1)
        
        # Status bar
        self.bottom_status_label = QLabel("Ready")
        self.bottom_status_label.setStyleSheet("color: #666666; font-size: 9pt; padding: 3px 5px; border-top: 1px solid #cccccc;")
        main_layout.addWidget(self.bottom_status_label)
    
    def load_gallery(self):
        """Load all images from all chat folders and generated_images"""
        # Clear existing widgets
        while self.gallery_layout.count():
            item = self.gallery_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get project root (parent of qt_tabs folder)
        project_root = Path(__file__).parent.parent
        
        # Find all image files from all sources
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        image_files = []
        
        # Scan 1: generated_images folder (test images from Image Settings tab)
        generated_images = project_root / "generated_images"
        if generated_images.exists():
            for ext in image_extensions:
                image_files.extend(generated_images.glob(f'*{ext}'))
                image_files.extend(generated_images.glob(f'*{ext.upper()}'))
        
        # Scan 2: saved_chats_ollama - all chat folders and their images subfolders
        ollama_chats = project_root / "saved_chats_ollama"
        if ollama_chats.exists():
            for chat_folder in ollama_chats.iterdir():
                if chat_folder.is_dir():
                    # Look in images subfolder for images (where chat images are stored)
                    images_folder = chat_folder / "images"
                    if images_folder.exists():
                        for ext in image_extensions:
                            image_files.extend(images_folder.glob(f'*{ext}'))
                            image_files.extend(images_folder.glob(f'*{ext.upper()}'))
        
        # Scan 3: saved_chats_llama_server - all chat folders and their images subfolders
        llama_chats = project_root / "saved_chats_llama_server"
        if llama_chats.exists():
            for chat_folder in llama_chats.iterdir():
                if chat_folder.is_dir():
                    # Look in images subfolder for images (where chat images are stored)
                    images_folder = chat_folder / "images"
                    if images_folder.exists():
                        for ext in image_extensions:
                            image_files.extend(images_folder.glob(f'*{ext}'))
                            image_files.extend(images_folder.glob(f'*{ext.upper()}'))
        
        # Remove duplicates and sort by modification time (newest first)
        unique_files = {}
        for f in image_files:
            unique_files[str(f.resolve())] = f  # Use absolute path as key
        
        image_files = list(unique_files.values())
        image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Add to gallery in grid layout
        row, col = 0, 0
        for image_file in image_files:
            widget = ImageGalleryWidget(image_file)
            self.gallery_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= 6:  # 6 columns
                col = 0
                row += 1
        
        # Update count and total size
        total_size_mb = sum(f.stat().st_size for f in image_files) / (1024 * 1024)
        self.count_label.setText(f"{len(image_files)} images")
        self.size_label.setText(f"{total_size_mb:.1f} MB")
        
        if not image_files:
            label = QLabel("No images yet.\n\nGenerated images will appear here.")
            label.setAlignment(Qt.AlignCenter)
            self.gallery_layout.addWidget(label, 0, 0)
    
    def check_for_new_images(self):
        """Check if new images were added and refresh if needed"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(self.gallery_path.glob(f'*{ext}'))
            image_files.extend(self.gallery_path.glob(f'*{ext.upper()}'))
        
        current_count = len(image_files)
        if current_count != int(self.count_label.text().split()[0]):
            self.load_gallery()
    
    def clear_all(self):
        """Clear all images"""
        reply = QMessageBox.question(
            self,
            "Clear All",
            "Delete all generated images? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                for file in self.gallery_path.glob('*'):
                    if file.is_file():
                        file.unlink()
                self.load_gallery()
                QMessageBox.information(self, "Success", "All images deleted")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not clear images: {e}")
    
    def export_folder(self):
        """Export gallery to external folder"""
        try:
            export_path = QFileDialog.getExistingDirectory(
                self,
                "Select Export Destination"
            )
            
            if export_path:
                export_path = Path(export_path)
                count = 0
                
                for file in self.gallery_path.glob('*'):
                    if file.is_file():
                        dest = export_path / file.name
                        shutil.copy2(file, dest)
                        count += 1
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Exported {count} images to:\n{export_path}"
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not export: {e}")
