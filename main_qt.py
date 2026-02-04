"""
Chat GUI with Image Generation - PyQt5 Version
Qt6-ready alternative to Tkinter
"""
# pylint: disable=no-name-in-module

import sys
from pathlib import Path

# Add current directory to path so qt_tabs can import root-level modules
sys.path.insert(0, str(Path(__file__).parent))

import json
from datetime import datetime
import queue
import threading

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QCheckBox, QDoubleSpinBox, QMessageBox, QFileDialog, QSplitter,
    QScrollArea, QFrame, QGridLayout, QProgressBar, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QByteArray
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QPalette

# Import existing modules - they don't depend on Tkinter
from settings_manager import load_settings
from settings_saver import get_settings_saver
from ollama_client import OllamaClient
from llama_client import LlamaServerClient
from chat_manager import ChatManager
from image_prompt_extractor import ImagePromptExtractor
from comfyui_model_manager import ComfyUIModelManager
from image_client import ComfyUIClient
from config import SYSTEM_PROMPT
from debug_config import DebugConfig


class LlamaChatQt(QMainWindow):
    """Main application window for Qt version"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Llama Chat - PyQt5")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(900, 700)
        
        # Load settings
        self.settings = load_settings()
        
        # Load debug settings into DebugConfig
        debug_settings = self.settings.get("debug_settings", {})
        if debug_settings:
            DebugConfig.set_from_dict(debug_settings)
        
        # Initialize timeout settings (for streaming requests)
        self.request_timeout = self.settings.get("request_timeout", 120)
        self.request_infinite_timeout = self.settings.get("request_infinite_timeout", False)
        if DebugConfig.connection_enabled:
            print(f"[DEBUG-INIT] Loaded request_timeout from settings: {self.request_timeout}s (infinite={self.request_infinite_timeout})")
        if DebugConfig.connection_enabled:
            print(f"[DEBUG-TIMEOUT] Loaded from settings: request_timeout={self.request_timeout}, request_infinite_timeout={self.request_infinite_timeout}")
        
        # Initialize system prompts from settings (will be updated by Prompts tab)
        # Use SYSTEM_PROMPT from config.py as the default if no setting exists
        self.system_prompt = self.settings.get("system_prompt_ollama", SYSTEM_PROMPT)
        self.system_prompt_llama = self.settings.get("system_prompt_llama", SYSTEM_PROMPT)
        
        # Initialize prepend system prompt to message settings
        self.ollama_prepend_system_to_message = self.settings.get("ollama_prepend_system_to_message", False)
        self.llama_prepend_system_to_message = self.settings.get("llama_prepend_system_to_message", False)
        
        # Initialize clients with timeout setting
        timeout = None if self.request_infinite_timeout else self.request_timeout
        self.ollama_client = OllamaClient(
            self.settings.get("ollama_url", "http://localhost:11434"),
            timeout=timeout
        )
        self.llama_client = LlamaServerClient(
            self.settings.get("llama_url", "http://127.0.0.1:8080"),
            timeout=timeout
        )
        
        # Image generation
        self.comfyui_url = self.settings.get("comfyui_url", "http://127.0.0.1:8188")
        self.comfyui_root = self.settings.get("comfyui_root_folder", "")
        self.image_client = ComfyUIClient(self.comfyui_url)
        self.model_manager = ComfyUIModelManager(self.comfyui_root)
        
        # Image viewer (will be set by image settings tab)
        self.image_viewer = None
        
        # Create UI
        self.create_widgets()
        self.apply_stylesheet()
        
        # Restore window geometry if saved
        geometry = self.settings.get("window_geometry")
        if geometry:
            try:
                from PyQt5.QtCore import QByteArray
                self.restoreGeometry(QByteArray.fromHex(geometry.encode()))
            except Exception as e:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Could not restore geometry: {e}")
    
    def create_widgets(self):
        """Create main UI structure with tabs"""
        # Remove menu bar and status bar for cleaner UI
        self.menuBar().hide()
        # Completely disable status bar
        self.statusBar().setVisible(False)
        self.statusBar().setSizePolicy(2, 0)  # Expand horizontally, minimum vertically
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create status info panel at bottom
        from qt_tabs.qt_status_info_panel import QtStatusInfoPanel
        self.status_panel = QtStatusInfoPanel(self)
        layout.addWidget(self.status_panel)
        
        # Create tabs
        from qt_tabs.qt_ollama_chat_tab import QtOllamaChatTab
        from qt_tabs.qt_llama_chat_tab import QtLlamaChatTab
        from qt_tabs.qt_settings_tab import QtSettingsTab
        from qt_tabs.qt_tts_tab import QtTTSTab
        from qt_tabs.qt_transcribe_tab import QtTranscribeTab
        from qt_tabs.qt_image_settings_tab import QtImageSettingsTab
        from qt_tabs.qt_image_gallery_tab import QtImageGalleryTab
        from qt_tabs.qt_system_prompts_tab import QtSystemPromptsTab
        from qt_tabs.qt_history_tab import QtHistoryTab
        from qt_tabs.qt_chat_memory_tab import QtChatMemoryTab
        from qt_tabs.qt_debug_settings_tab import QtDebugSettingsTab
        
        # Chat tabs
        self.ollama_tab = QtOllamaChatTab(self)
        self.llama_tab = QtLlamaChatTab(self)
        
        # Settings and other tabs
        self.settings_tab = QtSettingsTab(self)
        self.tts_tab = QtTTSTab(self)
        self.transcribe_tab = QtTranscribeTab(self)
        self.image_settings_tab = QtImageSettingsTab(self)
        self.image_gallery_tab = QtImageGalleryTab(self)
        self.prompts_tab = QtSystemPromptsTab(self)
        self.history_tab = QtHistoryTab(self)
        self.memory_tab = QtChatMemoryTab(self)
        self.debug_tab = QtDebugSettingsTab(self)
        
        # Add to tab widget
        self.tabs.addTab(self.ollama_tab, "💬 Ollama Chat")
        self.tabs.addTab(self.llama_tab, "🦙 Llama Chat")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        self.tabs.addTab(self.tts_tab, "🔊 TTS")
        self.tabs.addTab(self.transcribe_tab, "🎤 Transcribe")
        self.tabs.addTab(self.image_settings_tab, "🎨 Image Settings")
        self.tabs.addTab(self.image_gallery_tab, "🖼️ Gallery")
        self.tabs.addTab(self.prompts_tab, "📝 Prompts")
        self.tabs.addTab(self.memory_tab, "🧠 Memory")
        self.tabs.addTab(self.history_tab, "📚 History")
        self.tabs.addTab(self.debug_tab, "🐛 Debug")
        
        # Connect memory settings changes to update chat memory
        self.memory_tab.memory_settings_changed.connect(self.on_memory_settings_changed)
    
    def apply_stylesheet(self):
        """Apply consistent Qt stylesheet"""
        stylesheet = """
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QTabWidget::pane {
            border: 1px solid #cccccc;
        }
        
        QTabBar::tab {
            background-color: #e0e0e0;
            padding: 8px 20px;
            border: 1px solid #999999;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background-color: #ffffff;
            border-bottom: 2px solid #0066cc;
        }
        
        QTabBar::tab:hover {
            background-color: #f0f0f0;
        }
        
        QLabel {
            color: #333333;
        }
        
        QPushButton {
            background-color: #0066cc;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #0052a3;
        }
        
        QPushButton:pressed {
            background-color: #003d7a;
        }
        
        QPushButton:disabled {
            background-color: #cccccc;
            color: #999999;
        }
        
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 6px;
            background-color: #ffffff;
            color: #333333;
        }
        
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
            border: 2px solid #0066cc;
        }
        
        QCheckBox {
            color: #333333;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        
        QCheckBox::indicator:unchecked {
            background-color: #ffffff;
            border: 1px solid #cccccc;
            border-radius: 3px;
        }
        
        QCheckBox::indicator:checked {
            background-color: #0066cc;
            border: 1px solid #0066cc;
            border-radius: 3px;
        }
        
        QComboBox::drop-down {
            border: none;
        }
        
        QListWidget {
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #ffffff;
        }
        
        QListWidget::item:hover {
            background-color: #f0f0f0;
        }
        
        QListWidget::item:selected {
            background-color: #0066cc;
            color: white;
        }
        
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 4px;
            text-align: center;
            color: #333333;
        }
        
        QProgressBar::chunk {
            background-color: #0066cc;
        }
        
        QGroupBox {
            border: 1px solid #cccccc;
            border-radius: 4px;
            margin-top: 0.5em;
            padding-top: 0.5em;
            color: #333333;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
        """
        QApplication.instance().setStyle('Fusion')
        QApplication.instance().setStyleSheet(stylesheet)
    
    def closeEvent(self, event):
        """Save settings before closing"""
        try:
            # Stop any playing audio using centralized audio player (only need to call once)
            try:
                from audio_player import get_audio_player
                player = get_audio_player()
                player.stop()
            except:
                pass
            
            # Reload settings from disk first to get any changes made by tabs
            self.settings = load_settings()
            
            # Save checkbox states and model selection from chat tabs
            if hasattr(self, 'tabs'):
                try:
                    for i in range(self.tabs.count()):
                        tab = self.tabs.widget(i)
                        if hasattr(tab, 'return_to_send_checkbox'):
                            # Determine tab prefix
                            tab_prefix = ""
                            if hasattr(tab, 'tab_name'):
                                if "ollama" in tab.tab_name.lower():
                                    tab_prefix = "ollama_"
                                elif "llama" in tab.tab_name.lower():
                                    tab_prefix = "llama-server_"
                            
                            # Save checkbox states
                            if hasattr(tab, 'return_to_send_checkbox') and tab.return_to_send_checkbox:
                                self.settings[f"{tab_prefix}return_to_send"] = tab.return_to_send_checkbox.isChecked()
                            if hasattr(tab, 'stt_enabled_checkbox') and tab.stt_enabled_checkbox:
                                self.settings[f"{tab_prefix}stt_enabled"] = tab.stt_enabled_checkbox.isChecked()
                            if hasattr(tab, 'tts_enabled_checkbox') and tab.tts_enabled_checkbox:
                                self.settings[f"{tab_prefix}tts_enabled"] = tab.tts_enabled_checkbox.isChecked()
                            if hasattr(tab, 'clean_text_for_tts_checkbox') and tab.clean_text_for_tts_checkbox:
                                self.settings[f"{tab_prefix}clean_text_for_tts"] = tab.clean_text_for_tts_checkbox.isChecked()
                            
                            # Save model selection if it's a chat tab
                            if hasattr(tab, 'model_combo') and tab.model_combo:
                                model = tab.model_combo.currentText()
                                if model and not model.startswith("("):  # Skip placeholder and empty
                                    self.settings[f"{tab_prefix}server_model"] = model
                except Exception as e:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Error saving tab settings: {e}")
            
            # Save window geometry using proper QByteArray method
            try:
                geometry = self.saveGeometry().data().hex()
                self.settings["window_geometry"] = geometry
            except Exception as e:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Could not save geometry: {e}")
            saver = get_settings_saver()
            saver.sync_from_ui_dict(self.settings)
            saver.save()
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error in closeEvent: {e}")
        finally:
            event.accept()
    
    def save_settings_wrapper(self):
        """Wrapper to save all settings - called explicitly when needed"""
        saver = get_settings_saver()
        saver.sync_from_ui_dict(self.settings)
        saver.save()
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("📁 File")
        
        new_chat = file_menu.addAction("New Chat")
        new_chat.triggered.connect(self.new_chat_action)
        
        load_chat = file_menu.addAction("Load Chat")
        load_chat.triggered.connect(self.load_chat_action)
        
        save_chat = file_menu.addAction("Save Chat As")
        save_chat.triggered.connect(self.save_chat_action)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu("✏️ Edit")
        
        settings_action = edit_menu.addAction("⚙️ Settings")
        settings_action.triggered.connect(self.show_settings)
        
        # Help menu
        help_menu = menubar.addMenu("❓ Help")
        
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)
        
        docs_action = help_menu.addAction("Documentation")
        docs_action.triggered.connect(self.show_docs)
    
    def new_chat_action(self):
        """File > New Chat"""
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'new_chat_dialog'):
            current_tab.new_chat_dialog()
    
    def load_chat_action(self):
        """File > Load Chat"""
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'load_chat_dialog'):
            current_tab.load_chat_dialog()
    
    def save_chat_action(self):
        """File > Save Chat As"""
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'save_chat_as_dialog'):
            current_tab.save_chat_as_dialog()
    
    def show_settings(self):
        """Show settings dialog"""
        from qt_tabs.qt_settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec_()
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Llama Chat",
            "Llama Chat v2.0 (PyQt5)\n\n"
            "A chat interface for local LLMs using:\n"
            "• Ollama\n"
            "• Llama.cpp Server\n\n"
            "Features:\n"
            "• Real-time chat with local models\n"
            "• Image generation via ComfyUI\n"
            "• Speech-to-text and TTS\n"
            "• Chat history and export\n\n"
            "© 2025"
        )
    
    def on_memory_settings_changed(self, new_settings):
        """Handle memory settings changes"""
        if DebugConfig.chat_memory_operations:
            print("[MEMORY] Settings changed, reloading memory systems...")
        
        # Get current tabs and reload their memory
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'memory') and tab.memory:
                try:
                    tab.memory.reload_from_settings()
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Reloaded memory for tab {i}")
                except Exception as e:
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Error reloading: {e}")
    
    def show_docs(self):
        """Show documentation"""
        readme_file = Path("README.md")
        if readme_file.exists():
            QMessageBox.information(
                self,
                "Documentation",
                f"Please see {readme_file.name} for full documentation."
            )
        else:
            QMessageBox.information(
                self,
                "Documentation",
                "Documentation files not found.\n\nKey features:\n"
                "• Chat with Ollama or Llama Server\n"
                "• Save/load chat history\n"
                "• Generate images from descriptions\n"
                "• Voice input and output"
            )


def main():
    """Main entry point for Qt application"""
    app = QApplication(sys.argv)
    
    window = LlamaChatQt()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
