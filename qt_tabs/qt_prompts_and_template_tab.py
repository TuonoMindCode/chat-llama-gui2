"""
Prompts Tab for PyQt5
Allows editing system prompts
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, 
    QGroupBox, QMessageBox
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from pathlib import Path


class QtPromptsAndTemplateTab(QWidget):
    """Prompts and Chat Template Settings Tab"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # ============ OLLAMA SYSTEM PROMPT ============
        ollama_group = QGroupBox("Ollama System Prompt")
        ollama_layout = QVBoxLayout()
        
        ollama_info = QLabel("System prompt sent to Ollama model")
        ollama_info.setStyleSheet("color: #666; font-style: italic;")
        ollama_layout.addWidget(ollama_info)
        
        self.ollama_system_prompt = QTextEdit()
        self.ollama_system_prompt.setMinimumHeight(120)
        self.ollama_system_prompt.setPlaceholderText("Enter system prompt for Ollama model...")
        ollama_layout.addWidget(self.ollama_system_prompt)
        
        ollama_group.setLayout(ollama_layout)
        layout.addWidget(ollama_group)
        
        # ============ LLAMA SYSTEM PROMPT ============
        llama_group = QGroupBox("Llama Server System Prompt")
        llama_layout = QVBoxLayout()
        
        llama_info = QLabel("System prompt sent to Llama Server model")
        llama_info.setStyleSheet("color: #666; font-style: italic;")
        llama_layout.addWidget(llama_info)
        
        self.llama_system_prompt = QTextEdit()
        self.llama_system_prompt.setMinimumHeight(120)
        self.llama_system_prompt.setPlaceholderText("Enter system prompt for Llama Server model...")
        llama_layout.addWidget(self.llama_system_prompt)
        
        llama_group.setLayout(llama_layout)
        layout.addWidget(llama_group)
        
        # ============ SAVE SETTINGS BUTTON ============
        layout.addStretch()
        
        save_layout = QHBoxLayout()
        self.save_settings_btn = QPushButton("Save All Settings")
        self.save_settings_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_settings_btn.clicked.connect(self.save_all_settings)
        save_layout.addStretch()
        save_layout.addWidget(self.save_settings_btn)
        layout.addLayout(save_layout)
    
    def save_all_settings(self):
        """Save all settings"""
        from settings_manager import load_settings
        from settings_saver import get_settings_saver
        
        settings = load_settings()
        settings["ollama_system_prompt"] = self.ollama_system_prompt.toPlainText()
        settings["llama_system_prompt"] = self.llama_system_prompt.toPlainText()
        
        saver = get_settings_saver()
        saver.sync_from_ui_dict(settings)
        saver.save()
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "Success", "All settings saved successfully!")
    
    def load_settings(self):
        """Load settings from file"""
        from settings_manager import load_settings
        
        settings = load_settings()
        self.ollama_system_prompt.setPlainText(
            settings.get("ollama_system_prompt", "")
        )
        self.llama_system_prompt.setPlainText(
            settings.get("llama_system_prompt", "")
        )
