"""
Input area widget for message composition and submission
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QCheckBox, QLabel, QFrame, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class InputAreaWidget(QWidget):
    """Widget for message input area with all controls and checkboxes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the input area UI"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # Remove all spacing
        self.setLayout(main_layout)
        
        # Input options checkboxes row
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(5, 5, 5, 5)
        options_layout.setSpacing(12)
        
        options_layout.addWidget(QLabel("Your message:"))
        
        # Send on Return checkbox
        self.return_to_send_checkbox = QCheckBox("Send on Return")
        options_layout.addWidget(self.return_to_send_checkbox)
        
        # Speech Input checkbox
        self.stt_enabled_checkbox = QCheckBox("🎤 Speech Input")
        options_layout.addWidget(self.stt_enabled_checkbox)
        
        # Speech Output checkbox
        self.tts_enabled_checkbox = QCheckBox("🔊 Speech Output")
        options_layout.addWidget(self.tts_enabled_checkbox)
        
        # TTS size label
        self.tts_size_label = QLabel("(0 MB)")
        self.tts_size_label.setStyleSheet("color: #666666; font-size: 9pt;")
        options_layout.addWidget(self.tts_size_label)
        
        # Clean text for TTS checkbox
        self.clean_text_for_tts_checkbox = QCheckBox("🧹 Clean text for TTS")
        options_layout.addWidget(self.clean_text_for_tts_checkbox)
        
        options_layout.addStretch()
        
        main_layout.addLayout(options_layout)
        
        # Input text area
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(80)
        self.input_text.setMinimumHeight(60)
        self.input_text.setFont(QFont("Arial", 10))
        self.input_text.setPlaceholderText("Enter your message here... (Ctrl+Enter to send)")
        main_layout.addWidget(self.input_text)
        
        # Send and control buttons row
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)
        button_layout.setSpacing(8)
        
        self.send_button = QPushButton("Send (Ctrl+Enter)")
        self.send_button.setMinimumHeight(35)
        button_layout.addWidget(self.send_button)
        
        # Stop button
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMaximumWidth(70)
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        # Stop TTS button
        self.stop_tts_button = QPushButton("Stop TTS")
        self.stop_tts_button.setMaximumWidth(90)
        self.stop_tts_button.setMinimumHeight(35)
        button_layout.addWidget(self.stop_tts_button)
        
        button_layout.addSpacing(20)
        
        # Load CLIP checkbox
        self.load_clip_checkbox = QCheckBox("📎 Load CLIP")
        button_layout.addWidget(self.load_clip_checkbox)
        
        # CLIP Type dropdown
        self.clip_type_label = QLabel("Type:")
        self.clip_type_label.setStyleSheet("color: #666666;")
        button_layout.addWidget(self.clip_type_label)
        
        self.clip_type_combo = QComboBox()
        self.clip_type_combo.addItems(["flux2", "clip_l", "clip_g", "auto"])
        self.clip_type_combo.setMaximumWidth(80)
        self.clip_type_combo.setEnabled(False)
        button_layout.addWidget(self.clip_type_combo)
        
        # Connect checkbox to enable/disable dropdown
        self.load_clip_checkbox.stateChanged.connect(self._on_load_clip_toggled)
        
        button_layout.addSpacing(20)
        
        # Generating Images checkbox
        self.generating_images_checkbox = QCheckBox("🤖 Generating Images")
        button_layout.addWidget(self.generating_images_checkbox)
        
        # Show Images checkbox
        self.show_images_bottom_checkbox = QCheckBox("📷 Show Images")
        button_layout.addWidget(self.show_images_bottom_checkbox)
        
        # Fit image checkbox
        self.fit_image_checkbox = QCheckBox("Fit Image")
        button_layout.addWidget(self.fit_image_checkbox)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # No extra stretch at the end - this prevents the "text box below send button" issue!
        self.setMinimumHeight(0)
    
    def _on_load_clip_toggled(self, state):
        """Enable/disable CLIP type dropdown based on checkbox state"""
        self.clip_type_combo.setEnabled(state == 2)  # 2 = Qt.Checked
        self.clip_type_label.setStyleSheet("color: #000000;" if state == 2 else "color: #666666;")

