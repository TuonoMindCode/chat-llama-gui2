"""
Settings Dialog for PyQt5 GUI
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QPushButton, QTabWidget, QWidget,
    QMessageBox, QComboBox, QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from settings_manager import load_settings
from settings_saver import get_settings_saver


class SettingsDialog(QDialog):
    """Main settings dialog with multiple tabs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 600, 500)
        
        self.settings = load_settings()
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create settings dialog widgets"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Tabs
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # Server Settings
        server_widget = self.create_server_tab()
        tabs.addTab(server_widget, "🖥️ Servers")
        
        # Image Settings
        image_widget = self.create_image_tab()
        tabs.addTab(image_widget, "🖼️ Images")
        
        # Audio Settings
        audio_widget = self.create_audio_tab()
        tabs.addTab(audio_widget, "🔊 Audio")
        
        # Chat Settings
        chat_widget = self.create_chat_tab()
        tabs.addTab(chat_widget, "💬 Chat")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        close_btn = QPushButton("❌ Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_server_tab(self):
        """Create server settings tab"""
        widget = QWidget()
        layout = QFormLayout()
        widget.setLayout(layout)
        
        # Ollama settings
        ollama_label = QLabel("Ollama Server")
        ollama_font = QFont()
        ollama_font.setBold(True)
        ollama_label.setFont(ollama_font)
        layout.addRow(ollama_label)
        
        self.ollama_url = QLineEdit()
        self.ollama_url.setText(self.settings.get("ollama_url", "http://localhost:11434"))
        layout.addRow("Ollama URL:", self.ollama_url)
        
        # Llama Server settings
        llama_label = QLabel("Llama Server")
        llama_font = QFont()
        llama_font.setBold(True)
        llama_label.setFont(llama_font)
        layout.addRow(llama_label)
        
        self.llama_url = QLineEdit()
        self.llama_url.setText(self.settings.get("llama_url", "http://127.0.0.1:8000"))
        layout.addRow("Llama URL:", self.llama_url)
        
        layout.addRow("")  # Spacer
        
        # ComfyUI settings
        comfyui_label = QLabel("ComfyUI Image Generation")
        comfyui_font = QFont()
        comfyui_font.setBold(True)
        comfyui_label.setFont(comfyui_font)
        layout.addRow(comfyui_label)
        
        self.comfyui_url = QLineEdit()
        self.comfyui_url.setText(self.settings.get("comfyui_url", "http://127.0.0.1:8188"))
        layout.addRow("ComfyUI URL:", self.comfyui_url)
        
        self.comfyui_root = QLineEdit()
        self.comfyui_root.setText(self.settings.get("comfyui_root_folder", ""))
        layout.addRow("ComfyUI Root:", self.comfyui_root)
        
        layout.addStretch()
        return widget
    
    def create_image_tab(self):
        """Create image settings tab"""
        widget = QWidget()
        layout = QFormLayout()
        widget.setLayout(layout)
        
        self.auto_generate = QCheckBox("Auto-generate images from responses")
        self.auto_generate.setChecked(self.settings.get("auto_generate_images", False))
        layout.addRow(self.auto_generate)
        
        self.extraction_model = QLineEdit()
        self.extraction_model.setText(self.settings.get("extraction_model", "dolphin-2.1:2.4b"))
        layout.addRow("Extraction Model:", self.extraction_model)
        
        self.extraction_prefix = QLineEdit()
        self.extraction_prefix.setText(self.settings.get("extraction_prefix", ""))
        layout.addRow("Prompt Prefix:", self.extraction_prefix)
        
        self.extraction_suffix = QLineEdit()
        self.extraction_suffix.setText(self.settings.get("extraction_suffix", ""))
        layout.addRow("Prompt Suffix:", self.extraction_suffix)
        
        self.add_realistic = QCheckBox("Add realistic keywords")
        self.add_realistic.setChecked(self.settings.get("add_realistic_keywords", False))
        layout.addRow(self.add_realistic)
        
        layout.addStretch()
        return widget
    
    def create_audio_tab(self):
        """Create audio settings tab"""
        widget = QWidget()
        layout = QFormLayout()
        widget.setLayout(layout)
        
        # TTS Settings
        tts_label = QLabel("Text-to-Speech")
        tts_font = QFont()
        tts_font.setBold(True)
        tts_label.setFont(tts_font)
        layout.addRow(tts_label)
        
        self.tts_enabled = QCheckBox("Enable TTS output")
        self.tts_enabled.setChecked(self.settings.get("tts_output_enabled", False))
        layout.addRow(self.tts_enabled)
        
        self.tts_engine = QComboBox()
        self.tts_engine.addItems(["pyttsx3", "piper", "f5tts"])
        self.tts_engine.setCurrentText(self.settings.get("tts_engine", "pyttsx3"))
        layout.addRow("TTS Engine:", self.tts_engine)
        
        layout.addRow("")  # Spacer
        
        # STT Settings
        stt_label = QLabel("Speech-to-Text")
        stt_font = QFont()
        stt_font.setBold(True)
        stt_label.setFont(stt_font)
        layout.addRow(stt_label)
        
        self.stt_enabled = QCheckBox("Enable voice input (Whisper)")
        self.stt_enabled.setChecked(self.settings.get("whisper_enabled", False))
        layout.addRow(self.stt_enabled)
        
        self.whisper_model = QLineEdit()
        self.whisper_model.setText(self.settings.get("whisper_model", "base"))
        layout.addRow("Whisper Model:", self.whisper_model)
        
        layout.addStretch()
        return widget
    
    def create_chat_tab(self):
        """Create chat settings tab"""
        widget = QWidget()
        layout = QFormLayout()
        widget.setLayout(layout)
        
        self.save_history = QCheckBox("Save chat history")
        self.save_history.setChecked(self.settings.get("save_history", True))
        layout.addRow(self.save_history)
        
        self.max_history = QSpinBox()
        self.max_history.setMinimum(10)
        self.max_history.setMaximum(10000)
        self.max_history.setValue(self.settings.get("max_history", 1000))
        layout.addRow("Max History Messages:", self.max_history)
        
        self.message_timeout = QSpinBox()
        self.message_timeout.setMinimum(10)
        self.message_timeout.setMaximum(600)
        self.message_timeout.setValue(self.settings.get("message_timeout", 120))
        self.message_timeout.setSuffix(" seconds")
        layout.addRow("Message Timeout:", self.message_timeout)
        
        self.default_temp = QDoubleSpinBox()
        self.default_temp.setMinimum(0.0)
        self.default_temp.setMaximum(2.0)
        self.default_temp.setSingleStep(0.1)
        self.default_temp.setValue(self.settings.get("default_temperature", 0.7))
        layout.addRow("Default Temperature:", self.default_temp)
        
        layout.addStretch()
        return widget
    
    def save_settings(self):
        """Save all settings"""
        try:
            # Server settings
            self.settings["ollama_url"] = self.ollama_url.text()
            self.settings["llama_url"] = self.llama_url.text()
            self.settings["comfyui_url"] = self.comfyui_url.text()
            self.settings["comfyui_root_folder"] = self.comfyui_root.text()
            
            # Image settings
            self.settings["auto_generate_images"] = self.auto_generate.isChecked()
            self.settings["extraction_model"] = self.extraction_model.text()
            self.settings["extraction_prefix"] = self.extraction_prefix.text()
            self.settings["extraction_suffix"] = self.extraction_suffix.text()
            self.settings["add_realistic_keywords"] = self.add_realistic.isChecked()
            
            # Audio settings
            self.settings["tts_output_enabled"] = self.tts_enabled.isChecked()
            self.settings["tts_engine"] = self.tts_engine.currentText()
            self.settings["whisper_enabled"] = self.stt_enabled.isChecked()
            self.settings["whisper_model"] = self.whisper_model.text()
            
            # Chat settings
            self.settings["save_history"] = self.save_history.isChecked()
            self.settings["max_history"] = self.max_history.value()
            self.settings["message_timeout"] = self.message_timeout.value()
            self.settings["default_temperature"] = self.default_temp.value()
            
            saver = get_settings_saver()
            saver.sync_from_ui_dict(self.settings)
            saver.save()
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.close()
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save settings: {e}")
