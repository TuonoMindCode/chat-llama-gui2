"""
Chat Tab Base Class - Orchestrator for Ollama and Llama tabs
Phase 4: Stripped version with duplicate manager code removed
Essential code only: UI creation, manager init, orchestration, helper methods
"""
# pylint: disable=no-name-in-module

import json
import queue
import threading
import re
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QMessageBox, QFrame,
    QProgressBar, QCheckBox, QSplitter, QInputDialog, QSizePolicy
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor, QTextCursor, QPixmap, QTextCharFormat

# Import ResizableImageLabel from image settings right tab (new modular file)
from qt_tabs.qt_image_settings_right_tab import ResizableImageLabel

from chat_manager import ChatManager
from settings_manager import load_settings, get_setting
from settings_saver import get_settings_saver
from qt_tabs.message_display_widget import ClickableTextEdit
from qt_tabs.chat_worker import ChatWorkerThread
from chat_template_manager import template_manager
from debug_config import DebugConfig

# Import component managers
from .response_display_manager import ResponseDisplayManager
from .image_manager import ImageManager
from .tts_audio_manager import TTSAudioManager
from .voice_input_wrapper import VoiceInputWrapper
from .chat_persistence_manager import ChatPersistenceManager
from .server_connection_manager import ServerConnectionManager
from .time_aware_context import TimeAwareContext


from voice_input_manager import VoiceInputManager
from persistent_whisper_manager import PersistentWhisperManager

# Try to import pygame for audio playback
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


def format_folder_size(folder_path):
    """Calculate total size of all files in a folder and return formatted string"""
    try:
        folder = Path(folder_path)
        if not folder.exists():
            return "0 B"
        
        total_size = 0
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        # Format bytes to human-readable format
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_size < 1024:
                return f"{total_size:.1f} {unit}"
            total_size /= 1024
        return f"{total_size:.1f} TB"
    except Exception as e:
        return f"Error: {e}"


class QtChatTabBase(QWidget):
    """Base class for chat tabs (Ollama and Llama) - streamlined orchestrator"""
    
    def __init__(self, app, server_type, client):
        """
        Initialize chat tab base
        
        Args:
            app: Main application instance
            server_type: "ollama" or "llama-server"
            client: OllamaClient or LlamaServerClient instance
        """
        super().__init__()
        self.app = app
        self.server_type = server_type
        self.client = client
        
        # Chat management
        self.chat_manager = ChatManager(server_type)
        # Try to restore last used chat from settings, fallback to default
        self.settings = load_settings()
        chat_key = f"last_used_{server_type}_chat"
        last_chat_name = self.settings.get(chat_key)
        
        # Verify the last chat actually exists, otherwise use default
        if last_chat_name:
            try:
                chat_list = self.chat_manager.list_chats()
                if last_chat_name in chat_list:
                    self.current_chat_name = last_chat_name
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Restored last used chat: {last_chat_name}.json")
                else:
                    self.current_chat_name = self.chat_manager.get_default_chat().name
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Last chat '{last_chat_name}' not found, using default")
            except Exception as e:
                self.current_chat_name = self.chat_manager.get_default_chat().name
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Error restoring last chat: {e}")
        else:
            self.current_chat_name = self.chat_manager.get_default_chat().name
        
        # NOTE: Do NOT cache audio_folder and image_folder - use @property for dynamic access
        # This ensures we always use the current chat's folders when chats are switched
        
        # UI state
        self.message_history = []
        self.worker_thread = None
        self.is_generating = False
        self.generation_stopped = False
        self.timestamp_audio = {}
        self.current_image_list = []
        self.current_image_index = 0
        self.current_zoom = 1.0
        self.current_tts = None
        self.current_audio_player = None
        self.current_audio_process = None
        self.current_image_pixmap = None
        
        # Border state tracking
        self.input_border_timer = None
        self.is_connected = False
        
        # Model unload timeout tracking
        self.model_unload_timer = None
        self.model_unload_timeout_minutes = 0  # Will be loaded from settings
        
        # Voice input state
        self.voice_input_thread = None
        self.voice_input_active = False
        self.voice_input_paused = False
        self.persistent_whisper = None
        self.voice_input_queue = queue.Queue()
        self.voice_input_timer = None
        
        # Threading lock to prevent concurrent send_message calls (fixes voice input race condition)
        self.send_message_lock = threading.Lock()
        
        # Settings
        self.settings = load_settings()
        
        # Register with Voice Input Manager
        voice_manager = VoiceInputManager()
        voice_manager.register_tab(server_type, self._voice_input_callback)
        self.voice_manager = voice_manager
        
        # Initialize conversation memory system
        try:
            from memory_integration import MemoryIntegration
            if self.server_type == "ollama":
                self.memory = MemoryIntegration(ollama_chat_name=self.current_chat_name, llama_chat_name="default")
            else:
                self.memory = MemoryIntegration(ollama_chat_name="default", llama_chat_name=self.current_chat_name)
            if DebugConfig.chat_memory_operations:
                if DebugConfig.chat_memory_operations:
                    print(f"[MEMORY] {self.server_type} memory system initialized")
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                if DebugConfig.chat_memory_operations:
                    print(f"[MEMORY] Failed to initialize memory: {e}")
            self.memory = None
        
        # Create UI
        self.create_widgets()
        
        # Initialize component managers
        self._init_managers()
        
        # Load initial data
        self.load_checkbox_values()
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] {self.server_type.upper()} chat tab initializing with chat: {self.current_chat_name}.json")
        self.load_message_history()
        self.load_timestamp_audio_files()
        self.update_chat_info_display()
        self.connection_manager.update_connection_status()
    
    def _init_managers(self):
        """Initialize all component managers"""
        self.response_manager = ResponseDisplayManager(self)
        self.image_manager = ImageManager(self)
        self.tts_manager = TTSAudioManager(self)
        self.voice_input_wrapper = VoiceInputWrapper(self)
        self.persistence_manager = ChatPersistenceManager(self)
        self.connection_manager = ServerConnectionManager(self)
        self._wire_connections()
    
    def _wire_connections(self):
        """Wire up signals and slots between managers and UI"""
        # Chat operations
        self.load_chat_button.clicked.connect(self.persistence_manager.load_chat_dialog)
        self.new_chat_button.clicked.connect(self.persistence_manager.new_chat_dialog)
        self.save_chat_as_button.clicked.connect(self.persistence_manager.save_chat_as_dialog)
        self.delete_chat_button.clicked.connect(self.persistence_manager.delete_chat_with_confirmation)
        
        # Model selection (only for Ollama)
        if self.model_combo is not None:
            self.model_combo.currentTextChanged.connect(self.connection_manager.on_model_selected)
        
        # Connection
        self.connect_button.clicked.connect(self.connection_manager.connect_to_server)
        self.refresh_models_button.clicked.connect(self.connection_manager.refresh_models)
        
        # Voice input
        self.stt_enabled_checkbox.stateChanged.connect(self.voice_input_wrapper.on_stt_toggled)
        
        # Image viewer
        self.show_images_bottom_checkbox.stateChanged.connect(self.image_manager.toggle_image_view)
        self.fit_image_checkbox.stateChanged.connect(self.image_manager.on_fit_image_toggled)
        self.prev_image_button.clicked.connect(self.image_manager.show_previous_image)
        self.next_image_button.clicked.connect(self.image_manager.show_next_image)
    
    def create_widgets(self):
        """Create chat tab UI - full widget hierarchy"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)
        self.setLayout(main_layout)
        
        # === TOP SECTION ===
        top_frame = QFrame()
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(5)
        top_frame.setLayout(top_layout)
        
        if self.server_type == "ollama":
            server_label = QLabel("💙 Ollama Chat")
            color = "#0066cc"
        else:
            server_label = QLabel("🦙 Llama Chat")
            color = "#cc6600"
        
        server_font = QFont()
        server_font.setBold(True)
        server_font.setPointSize(11)
        server_label.setFont(server_font)
        top_layout.addWidget(server_label)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.setMaximumWidth(100)
        self.connect_button.setMaximumHeight(30)
        top_layout.addWidget(self.connect_button)
        
        self.status_label = QLabel("⚪ Not connected")
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        
        self.chat_info_label = QLabel(f"📄 {self.current_chat_name}.json")
        top_layout.addWidget(self.chat_info_label)
        
        load_button = QPushButton("Load")
        load_button.setMaximumWidth(60)
        load_button.setMaximumHeight(30)
        top_layout.addWidget(load_button)
        
        new_button = QPushButton("New")
        new_button.setMaximumWidth(60)
        new_button.setMaximumHeight(30)
        top_layout.addWidget(new_button)
        
        save_as_button = QPushButton("Save As")
        save_as_button.setMaximumWidth(80)
        save_as_button.setMaximumHeight(30)
        top_layout.addWidget(save_as_button)
        
        self.delete_chat_button = QPushButton("🗑️ Delete Chat+Images+Audio")
        self.delete_chat_button.setMaximumWidth(200)
        self.delete_chat_button.setMaximumHeight(30)
        top_layout.addWidget(self.delete_chat_button)
        
        self.load_chat_button = load_button
        self.new_chat_button = new_button
        self.save_chat_as_button = save_as_button
        
        main_layout.addWidget(top_frame, 0)
        
        # === MODEL SELECTION (Ollama only) ===
        # Llama-Server doesn't support model selection, so hide this for that server type
        if self.server_type == "ollama":
            model_frame = QFrame()
            model_layout = QHBoxLayout()
            model_layout.setContentsMargins(0, 0, 0, 0)
            model_layout.setSpacing(5)
            model_frame.setLayout(model_layout)
            
            model_layout.addWidget(QLabel("Model:"))
            self.model_combo = QComboBox()
            self.model_combo.addItem("(Connect to see models)")
            # Show approximately 40 visible characters
            self.model_combo.setMinimumWidth(300)
            self.model_combo.setMaximumWidth(450)
            model_layout.addWidget(self.model_combo, 0)
            
            refresh_button = QPushButton("Refresh")
            refresh_button.setMaximumWidth(100)
            refresh_button.setMaximumHeight(30)
            model_layout.addWidget(refresh_button)
            self.refresh_models_button = refresh_button
        else:
            # Llama-Server: create minimal frame with just info label and disabled refresh
            model_frame = QFrame()
            model_layout = QHBoxLayout()
            model_layout.setContentsMargins(0, 0, 0, 0)
            model_layout.setSpacing(5)
            model_frame.setLayout(model_layout)
            
            info_label = QLabel("🦙 Llama-Server (Model: Fixed)")
            info_label.setStyleSheet("color: #666666; font-style: italic;")
            model_layout.addWidget(info_label)
            
            refresh_button = QPushButton("Refresh")
            refresh_button.setMaximumWidth(100)
            refresh_button.setMaximumHeight(30)
            refresh_button.setEnabled(False)  # Gray out - not applicable for Llama-Server
            refresh_button.setToolTip("Refresh not available for Llama-Server (fixed model)")
            model_layout.addWidget(refresh_button)
            self.refresh_models_button = refresh_button
            self.model_combo = None  # No model combo for Llama
        
        # Save settings button for chat tab checkboxes
        save_chat_settings_button = QPushButton("💾 Save")
        save_chat_settings_button.setMaximumWidth(80)
        save_chat_settings_button.setMaximumHeight(30)
        save_chat_settings_button.setToolTip("Save chat tab settings (Send on Return, Speech Input/Output)")
        save_chat_settings_button.clicked.connect(self.save_chat_tab_settings)
        model_layout.addWidget(save_chat_settings_button)
        self.save_chat_settings_button = save_chat_settings_button
        
        # Status label for save feedback (appears to the right of buttons)
        self.save_status_label = QLabel("")
        self.save_status_label.setStyleSheet("color: #00aa00; font-weight: bold; font-size: 9pt;")
        self.save_status_label.setMinimumWidth(120)
        model_layout.addWidget(self.save_status_label)
        
        model_layout.addStretch()
        main_layout.addWidget(model_frame, 0)
        
        # === MAIN CONTENT ===
        content_splitter = QSplitter(Qt.Horizontal)
        
        # LEFT: Chat
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(3)
        chat_widget.setLayout(chat_layout)
        
        self.message_display = ClickableTextEdit(self)
        self.message_display.setFont(QFont("Courier", 9))
        chat_layout.addWidget(self.message_display, 1)
        
        # Message input frame
        input_frame = QFrame()
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(2)
        input_frame.setLayout(input_layout)
        input_frame.setMinimumHeight(0)
        input_frame.setMaximumHeight(200)
        
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        size_policy.setRetainSizeWhenHidden(False)
        input_frame.setSizePolicy(size_policy)
        
        # Options row
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(5, 5, 5, 5)
        options_layout.setSpacing(12)
        
        options_layout.addWidget(QLabel("Your message:"))
        
        self.return_to_send_checkbox = QCheckBox("Send on Return")
        options_layout.addWidget(self.return_to_send_checkbox)
        
        self.stt_enabled_checkbox = QCheckBox("🎤 Speech Input")
        options_layout.addWidget(self.stt_enabled_checkbox)
        
        # Voice status label (shows loading, silence detected, etc)
        self.voice_status_label = QLabel("")
        self.voice_status_label.setStyleSheet("color: #ff9900; font-size: 9pt; font-weight: bold;")
        self.voice_status_label.setMinimumWidth(150)
        options_layout.addWidget(self.voice_status_label)
        
        self.tts_enabled_checkbox = QCheckBox("🔊 Speech Output")
        options_layout.addWidget(self.tts_enabled_checkbox)
        
        self.tts_size_label = QLabel("(0 MB)")
        self.tts_size_label.setStyleSheet("color: #666666; font-size: 9pt;")
        options_layout.addWidget(self.tts_size_label)
        
        self.clean_text_for_tts_checkbox = QCheckBox("🧹 Clean text for TTS")
        options_layout.addWidget(self.clean_text_for_tts_checkbox)
        
        self.time_aware_checkbox = QCheckBox("⏰ Time Aware")
        options_layout.addWidget(self.time_aware_checkbox)
        
        options_layout.addStretch()
        input_layout.addLayout(options_layout)
        
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(80)
        self.input_text.setMinimumHeight(30)
        self.input_text.setFont(QFont("Arial", 10))
        self.input_text.setPlaceholderText("Enter your message here... (Ctrl+Enter to send)")
        self.input_text.keyPressEvent = self.handle_input_key
        input_layout.addWidget(self.input_text)
        
        # Button row
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 8, 5, 5)
        button_layout.setSpacing(8)
        
        self.send_button = QPushButton("Send (Ctrl+Enter)")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setMinimumHeight(35)
        button_layout.addWidget(self.send_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.setMaximumWidth(70)
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_generation)
        button_layout.addWidget(self.stop_button)
        
        self.stop_tts_button = QPushButton("Stop TTS")
        self.stop_tts_button.setMaximumWidth(90)
        self.stop_tts_button.setMinimumHeight(35)
        self.stop_tts_button.clicked.connect(self.stop_tts)
        button_layout.addWidget(self.stop_tts_button)
        
        button_layout.addSpacing(20)
        
        self.generating_images_checkbox = QCheckBox("🤖 Generate Image")
        button_layout.addWidget(self.generating_images_checkbox)
        
        self.show_images_bottom_checkbox = QCheckBox("📷 Show Images")
        button_layout.addWidget(self.show_images_bottom_checkbox)
        
        self.fit_image_checkbox = QCheckBox("Fit Image")
        button_layout.addWidget(self.fit_image_checkbox)
        
        self.sync_image_text_checkbox = QCheckBox("Sync Text & Image")
        self.sync_image_text_checkbox.setChecked(False)
        button_layout.addWidget(self.sync_image_text_checkbox)
        
        button_layout.addStretch()
        input_layout.addLayout(button_layout)
        chat_layout.addWidget(input_frame, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(0)
        self.progress_bar.setMinimumHeight(0)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        size_policy.setRetainSizeWhenHidden(False)
        self.progress_bar.setSizePolicy(size_policy)
        chat_layout.addWidget(self.progress_bar, 0)
        chat_layout.setSpacing(0)
        
        content_splitter.addWidget(chat_widget)
        
        # RIGHT: Images
        image_widget = QWidget()
        image_layout = QVBoxLayout()
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(3)
        image_widget.setLayout(image_layout)
        
        image_title_layout = QHBoxLayout()
        image_title_layout.setContentsMargins(0, 0, 0, 0)
        image_title_layout.setSpacing(5)
        
        image_title = QLabel("🖼️ Generated Images")
        title_font = QFont()
        title_font.setBold(True)
        image_title.setFont(title_font)
        image_title_layout.addWidget(image_title, 0)
        
        self.image_counter_label = QLabel("0/0")
        image_title_layout.addWidget(self.image_counter_label, 0)
        
        self.prev_image_button = QPushButton("◀")
        self.prev_image_button.setMaximumWidth(35)
        self.prev_image_button.setMaximumHeight(20)
        self.prev_image_button.setToolTip("Previous image")
        image_title_layout.addWidget(self.prev_image_button)
        
        self.next_image_button = QPushButton("▶")
        self.next_image_button.setMaximumWidth(35)
        self.next_image_button.setMaximumHeight(20)
        self.next_image_button.setToolTip("Next image")
        image_title_layout.addWidget(self.next_image_button)
        
        image_title_layout.addStretch()
        image_layout.addLayout(image_title_layout, 0)
        
        self.image_label = ResizableImageLabel()
        self.image_label.setText("(No images yet)")
        image_layout.addWidget(self.image_label, 1)
        
        content_splitter.addWidget(image_widget)
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 1)
        
        image_widget.setMinimumWidth(300)
        image_widget.setMinimumHeight(250)
        image_widget.setVisible(False)
        self.image_widget = image_widget
        self.image_viewer_hidden = True
        
        self.show_images_bottom_checkbox.stateChanged.connect(self.toggle_image_view)
        
        main_layout.addWidget(content_splitter, 1)
    
    # ===== DYNAMIC FOLDER PROPERTIES =====
    
    @property
    def audio_folder(self):
        """Get current chat's audio folder - dynamically retrieves from ChatManager"""
        self.chat_manager.load_chat(self.current_chat_name)
        return self.chat_manager.get_audio_folder()
    
    @property
    def image_folder(self):
        """Get current chat's image folder - dynamically retrieves from ChatManager"""
        self.chat_manager.load_chat(self.current_chat_name)
        return self.chat_manager.get_image_folder()
    
    # ===== ESSENTIAL METHODS ONLY =====
    
    def update_input_border_state(self, bright=False):
        """Update input text box border based on connection state with pulsing animation"""
        if bright and self.is_connected and not self.is_generating:
            # Bright pulsing cyan for 3 seconds after send - VERY eye-catching!
            self.input_text.setStyleSheet("""
                QTextEdit {
                    border: 4px solid #FF1493;
                    border-radius: 4px;
                    background-color: #ffe0f0;
                }
            """)
            if self.input_border_timer:
                self.input_border_timer.stop()
            self.input_border_timer = QTimer()
            self.input_border_timer.setSingleShot(True)
            self.input_border_timer.timeout.connect(self.update_input_border_state)
            self.input_border_timer.start(3000)
        elif self.is_connected and not self.is_generating:
            # Magenta/Hot Pink when ready to type - very noticeable!
            self.input_text.setStyleSheet("""
                QTextEdit {
                    border: 3px solid #FF1493;
                    border-radius: 4px;
                }
            """)
        else:
            # Gray when not connected or generating
            self.input_text.setStyleSheet("""
                QTextEdit {
                    border: 2px solid #999999;
                    border-radius: 4px;
                }
            """)
    
    def load_checkbox_values(self):
        """Load checkbox values from settings"""
        tab_prefix = ""
        if self.server_type == "ollama":
            tab_prefix = "ollama_"
        elif self.server_type == "llama-server":
            tab_prefix = "llama-server_"
        
        self.return_to_send_checkbox.setChecked(self.settings.get(f"{tab_prefix}return_to_send", False))
        # NOTE: Speech Input (STT) is NOT saved - always starts unchecked for safety
        self.stt_enabled_checkbox.setChecked(False)
        self.tts_enabled_checkbox.setChecked(self.settings.get(f"{tab_prefix}tts_enabled", False))
        self.clean_text_for_tts_checkbox.setChecked(self.settings.get(f"{tab_prefix}clean_text_for_tts", False))
        self.time_aware_checkbox.setChecked(self.settings.get(f"{tab_prefix}time_aware", False))
        
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] Loaded checkboxes for {tab_prefix}: tts_enabled={self.tts_enabled_checkbox.isChecked()}")
    
    def save_chat_tab_settings(self):
        """Save chat tab checkbox settings (Send on Return, Speech Input/Output, etc.)"""
        try:
            tab_prefix = ""
            if self.server_type == "ollama":
                tab_prefix = "ollama_"
            elif self.server_type == "llama-server":
                tab_prefix = "llama-server_"
            
            # Build settings dict with current checkbox values
            # NOTE: stt_enabled is NOT saved - always starts unchecked
            settings_to_save = {
                f"{tab_prefix}return_to_send": self.return_to_send_checkbox.isChecked(),
                f"{tab_prefix}tts_enabled": self.tts_enabled_checkbox.isChecked(),
                f"{tab_prefix}clean_text_for_tts": self.clean_text_for_tts_checkbox.isChecked(),
                f"{tab_prefix}time_aware": self.time_aware_checkbox.isChecked(),
            }
            
            # Use SettingsSaver to save changes
            saver = get_settings_saver()
            saver.sync_from_ui_dict(settings_to_save)
            saver.save()
            
            # Show status message to the right of buttons (auto-clear after 2 seconds)
            self.save_status_label.setText("✅ Saved")
            QTimer.singleShot(2000, lambda: self.save_status_label.setText(""))
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] ✅ Saved chat tab settings for {tab_prefix}: {settings_to_save}")
        except Exception as e:
            self.save_status_label.setText(f"❌ Error")
            QTimer.singleShot(3000, lambda: self.save_status_label.setText(""))
            print(f"[ERROR] Saving chat tab settings: {e}")
    
    def on_stt_toggled(self, state):
        """Handle STT checkbox toggle"""
        if state == Qt.Checked:
            self.voice_manager.set_active_tab(self.server_type)
            if not self.voice_input_active:
                self.voice_input_active = True
                if DebugConfig.chat_memory_operations:
                    if DebugConfig.stt_enabled:
                        print(f"[VOICE_INPUT] Starting voice listening for {self.server_type}")
        else:
            self.voice_manager.set_active_tab(None)
            self.voice_input_wrapper.stop_voice_listening()
    
    def _voice_input_callback(self, should_be_checked):
        """Callback from Voice Input Manager"""
        self.stt_enabled_checkbox.stateChanged.disconnect(self.on_stt_toggled)
        self.stt_enabled_checkbox.setChecked(should_be_checked)
        self.stt_enabled_checkbox.stateChanged.connect(self.on_stt_toggled)
        
        if not should_be_checked:
            self.voice_input_wrapper.stop_voice_listening()
    
    def handle_input_key(self, event):
        """Handle key press in input field"""
        if event.key() == Qt.Key_Return:
            if event.modifiers() == Qt.ControlModifier:
                self.send_message()
            elif self.return_to_send_checkbox.isChecked() and event.modifiers() == Qt.NoModifier:
                self.send_message()
            else:
                QTextEdit.keyPressEvent(self.input_text, event)
        else:
            QTextEdit.keyPressEvent(self.input_text, event)
    
    def send_message(self):
        """Send message to LLM - orchestrates managers"""
        # Use lock to prevent concurrent send_message calls (fixes voice input race condition)
        if not self.send_message_lock.acquire(blocking=False):
            # Another send_message call is already in progress
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-SEND] send_message() called while already processing - rejecting")
            return
        
        try:
            # Cancel any pending model unload timer (user is sending a new message)
            self.cancel_model_unload_timer()
            
            message = self.input_text.toPlainText().strip()
            if not message:
                return
            
            # Double-check is_generating while holding the lock
            if self.is_generating:
                QMessageBox.warning(self, "Warning", "Already generating a response - please wait")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-SEND] Rejected send_message() - is_generating=True")
                return
            
            model = self.model_combo.currentText() if self.model_combo else "default"
            if not model or model.startswith("("):
                if self.model_combo:
                    QMessageBox.warning(self, "Warning", "Please select a model")
                return
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            timestamp_iso = datetime.now().isoformat()
            
            # Remove empty "You:" prompt if present
            chat_text = self.message_display.toPlainText()
            if re.search(r'\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\] You: *$', chat_text):
                chat_text = re.sub(r'\n+\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\] You: *$', '', chat_text)
                self.message_display.setText(chat_text)
            
            # Display user message
            self.response_manager.display_message(message, is_user=True, timestamp=timestamp)
            self.input_text.clear()
            self.input_text.setMinimumHeight(30)
            self.input_text.setFocus()  # Return focus to input for next message
            
            # Save to history
            self.message_history.append({
                "role": "user",
                "content": message,
                "timestamp": timestamp_iso
            })
            
            # Add user message to memory for personal facts extraction
            if self.memory:
                try:
                    if self.server_type == "ollama":
                        self.memory.add_ollama_message("user", message)
                    else:
                        self.memory.add_llama_message("user", message)
                    if DebugConfig.chat_memory_operations:
                        if DebugConfig.chat_memory_operations:
                            print(f"[MEMORY] Added user message to {self.server_type} memory")
                except Exception as e:
                    if DebugConfig.chat_memory_operations:
                        if DebugConfig.chat_memory_operations:
                            print(f"[MEMORY] Error adding user message to memory: {e}")
            
            if DebugConfig.chat_enabled:
                print(f"\n[DEBUG-SEND] User message added to history. message_history now has {len(self.message_history)} messages")
            
            # Get system prompt - always reload from current settings
            # Fallback to SYSTEM_PROMPT from config.py for default friendly, upbeat assistant behavior
            from config import SYSTEM_PROMPT
            if self.server_type == "ollama":
                system_prompt = load_settings().get("system_prompt_ollama", SYSTEM_PROMPT)
            else:
                system_prompt = load_settings().get("system_prompt_llama", SYSTEM_PROMPT)
            
            # Add time context FIRST if Time Aware is enabled (before other modifications)
            if self.time_aware_checkbox.isChecked():
                time_context = TimeAwareContext.get_context(self.message_history)
                if time_context:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-PROMPT] Time Aware ENABLED - adding context: {time_context[:100]}...")
                    # Add time context at the BEGINNING - inform LLM of time without forcing repetition
                    # IMPORTANT: Explicitly tell LLM NOT to repeat these time/date strings
                    system_prompt = f"[TEMPORAL CONTEXT: {time_context}]\nNEVER mention or repeat the time, date, or date context in your responses unless the user specifically asks about the time.\n\n{system_prompt}"
                else:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-PROMPT] Time Aware ENABLED but no context generated")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-PROMPT] Time Aware DISABLED")
            
            # Replace [nomic] placeholder with personal facts if present
            if "[nomic]" in system_prompt and self.memory:
                personal_facts = self.memory.get_ollama_personal_facts() if self.server_type == "ollama" else self.memory.get_llama_personal_facts()
                if personal_facts:
                    if DebugConfig.chat_memory_operations:
                        print(f"[DEBUG-PROMPT] [nomic] found - replacing with personal facts ({len(personal_facts)} chars)")
                    system_prompt = system_prompt.replace("[nomic]", personal_facts)
                else:
                    if DebugConfig.chat_memory_operations:
                        print(f"[DEBUG-PROMPT] [nomic] found but no personal facts to replace with")
                    system_prompt = system_prompt.replace("[nomic]", "")
            elif "[nomic]" in system_prompt and not self.memory:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-PROMPT] [nomic] found but memory not initialized, removing placeholder")
                system_prompt = system_prompt.replace("[nomic]", "")
            
            # Add trivia instruction if Daily Trivia is enabled
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-PROMPT] System prompt (first 300 chars): {system_prompt[:300]}...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-SEND] ===== AFTER SYSTEM PROMPT DEBUG - About to build session history")
            
            # Build session history - EXCLUDE the current message (it will be added separately in chat_worker)
            # We only include previous messages to avoid duplication
            previous_messages = self.message_history[:-1]  # Exclude the last message (current user message)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-SEND] ===== SESSION HISTORY BUILT: {len(previous_messages)} messages")
            session_history = [{"role": msg["role"], "content": msg["content"]} for msg in previous_messages]
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-SEND] ===== SESSION HISTORY CONVERTED TO LIST")
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-SEND] Building request with {len(session_history)} messages from message_history")
                for i, msg in enumerate(self.message_history[-3:]):
                    idx = len(self.message_history) - 3 + i
                    print(f"  [{idx}] {msg['role']}: {msg['content'][:50]}")
            
            # Get LLM settings
            # Read timeout from app settings (can be overridden to infinite if request_infinite_timeout is True)
            if hasattr(self.app, 'request_infinite_timeout') and self.app.request_infinite_timeout:
                timeout = None  # None = infinite timeout
            elif hasattr(self.app, 'request_timeout'):
                timeout = self.app.request_timeout
            else:
                timeout = 120  # fallback default
            
            temperature = 0.9
            top_p = 0.99
            top_k = 60
            max_tokens = 8192  # Changed default to 8k
            
            try:
                # ALWAYS load from settings file FIRST to get consistent defaults
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-SEND] ===== LOADING SETTINGS FROM FILE")
                settings = load_settings()
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-SEND] ===== SETTINGS LOADED")
                temperature = settings.get("temperature", 0.9)
                top_p = settings.get("top_p", 0.99)
                top_k = settings.get("top_k", 60)
                max_tokens = settings.get("n_predict", 8192)
                
                if DebugConfig.connection_requests:
                    print(f"[DEBUG-SETTINGS] Loaded from file: temp={temperature}, top_p={top_p}, top_k={top_k}, max_tokens={max_tokens}")
                
                # THEN override with UI slider values if settings_tab exists (for real-time changes)
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-SEND] ===== CHECKING IF SETTINGS_TAB EXISTS")
                if hasattr(self.app, 'settings_tab') and self.app.settings_tab:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-SEND] ===== SETTINGS_TAB EXISTS, ATTEMPTING TO GET SLIDER VALUES")
                    temperature = self.app.settings_tab.temp_slider.value() / 10.0
                    top_p = self.app.settings_tab.top_p_slider.value() / 20.0
                    top_k = self.app.settings_tab.top_k_slider.value()
                    max_tokens = self.app.settings_tab.max_tokens_slider.value()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-SEND] ===== GOT SLIDER VALUES")
                    if DebugConfig.connection_requests:
                        print(f"[DEBUG-SETTINGS] Overridden by UI: temp={temperature}, top_p={top_p}, top_k={top_k}, max_tokens={max_tokens}")
                else:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-SEND] ===== SETTINGS_TAB DOES NOT EXIST OR IS NONE")
            except Exception as e:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Error getting settings: {e}")
                # Final fallback: try settings file one more time
                try:
                    settings = load_settings()
                    temperature = settings.get("temperature", 0.9)
                    top_p = settings.get("top_p", 0.99)
                    top_k = settings.get("top_k", 60)
                    max_tokens = settings.get("n_predict", 8192)
                except:
                    pass  # Use hardcoded defaults (0.9, 0.99, 60)
            

            
            max_context_messages = get_setting("ollama_max_context_messages" if self.server_type == "ollama" else "llama_max_context_messages", 20)
            
            # Ensure chat manager has current chat folder set (for debug file location)
            if self.chat_manager.current_chat_name != self.current_chat_name:
                # Chat changed, update the chat manager's internal tracking
                self.chat_manager._ensure_chat_folder(self.current_chat_name)
                self.chat_manager.current_chat_name = self.current_chat_name
                self.chat_manager.current_chat_folder = self.chat_manager.base_folder / self.current_chat_name
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-SEND] Updated chat_manager to track: {self.current_chat_name} -> {self.chat_manager.current_chat_folder}")
            
            # Start worker thread
            self.is_generating = True
            self.generation_stopped = False
            self.send_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.update_input_border_state(bright=False)
            
            if hasattr(self.app, 'status_panel'):
                self.app.status_panel.set_llm_status('generating')
            
            # Check if user is asking about time - if so, add current time to their message
            user_message_to_send = message
            if self.time_aware_checkbox.isChecked():
                # Detect time-related questions
                time_keywords = ['what time', 'current time', 'what\'s the time', "what's the time", 'do you know the time', 'time is it', 'time of day', 'how late']
                message_lower = message.lower()
                if any(keyword in message_lower for keyword in time_keywords):
                    # User is asking about time - append current time to their message
                    current_time = TimeAwareContext.get_context(self.message_history)
                    if current_time:
                        user_message_to_send = f"{message}\n\n[Current time: {current_time}]"
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG-PROMPT] Time question detected - appending current time to user message")
            
            self._streaming_header_added = False
            self._streaming_word_buffer = ""
            
            # Load prepend setting based on server type
            settings = load_settings()
            if self.server_type == "ollama":
                prepend_enabled = settings.get("ollama_prepend_system_to_message", False)
                keep_alive = settings.get("ollama_model_unload_timeout", 0)  # Default: 0 = immediate unload
            else:  # llama
                prepend_enabled = settings.get("llama_prepend_system_to_message", False)
                keep_alive = settings.get("llama-server_model_unload_timeout", 0)  # Default: 0 = immediate unload
            
            if DebugConfig.connection_requests:
                print(f"[DEBUG-WORKER] Creating ChatWorkerThread with keep_alive={keep_alive}s (model unload timeout)")
            
            # Extract memory context if memory is enabled
            memory_context = ""
            try:
                if self.memory and settings.get("memory_enabled", False):
                    # Get custom keywords from settings
                    custom_keywords = settings.get("memory_custom_keywords", "")
                    
                    # Extract BOTH semantic search context AND personal facts
                    context_parts = []
                    
                    # 1. Get semantic search results
                    if self.server_type == "ollama":
                        semantic_context = self.memory.get_ollama_context(
                            message,
                            custom_keywords=custom_keywords
                        )
                        personal_facts = self.memory.get_ollama_personal_facts()
                    else:  # llama
                        semantic_context = self.memory.get_llama_context(
                            message,
                            custom_keywords=custom_keywords
                        )
                        personal_facts = self.memory.get_llama_personal_facts()
                    
                    # 2. Combine both if available
                    if personal_facts:
                        context_parts.append(personal_facts)
                    if semantic_context:
                        context_parts.append(semantic_context)
                    
                    memory_context = "\n".join(context_parts)
                    
                    if memory_context and DebugConfig.chat_memory_operations:
                        if DebugConfig.chat_memory_operations:
                            print(f"[MEMORY] Extracted context ({len(memory_context)} chars):")
                        if DebugConfig.chat_memory_operations:
                            print(f"[MEMORY] {memory_context[:200]}..." if len(memory_context) > 200 else f"[MEMORY] {memory_context}")
            except Exception as e:
                if DebugConfig.chat_memory_operations:
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Error extracting context: {e}")
                memory_context = ""
            
            self.worker_thread = ChatWorkerThread(
                self.client,
                user_message_to_send,
                model,
                system_prompt,
                conversation_history=session_history,
                memory_context=memory_context,  # Use extracted memory facts
                timeout=timeout,
                enable_streaming=True,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_tokens=max_tokens,
                max_context_messages=max_context_messages,
                chat_folder=self.chat_manager.current_chat_folder,  # Pass current chat folder for debug file
                prepend_enabled=prepend_enabled,  # NEW: Pass prepend setting
                keep_alive=keep_alive  # NEW: Pass model unload timeout
            )
            
            self.worker_thread.message_chunk.connect(self.response_manager.on_message_chunk)
            self.worker_thread.token_info.connect(self.response_manager.on_token_info)
            self.worker_thread.message_received.connect(self.response_manager.on_message_received)
            self.worker_thread.error_occurred.connect(self.response_manager.on_error)
            self.worker_thread.generation_stopped.connect(self.on_generation_stopped)
            self.worker_thread.finished.connect(self.on_response_generated)
            self.worker_thread.start()
        
        finally:
            # Always release the lock when exiting send_message
            self.send_message_lock.release()
    
    def stop_generation(self):
        """Stop message generation"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.should_stop = True
            self.worker_thread.wait(1000)
            if self.worker_thread.isRunning():
                self.worker_thread.terminate()
                self.worker_thread.wait()
        
        self.is_generating = False
        self.generation_stopped = True
        self.send_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setMaximumHeight(0)
        self.progress_bar.setVisible(False)
    
    def on_generation_stopped(self):
        """Called when generation is stopped by user"""
        if DebugConfig.chat_enabled:
            print(f"\n[DEBUG-RESPONSE] on_generation_stopped() - User stopped generation")
        self.generation_stopped = True
    
    def on_response_generated(self):
        """Called when LLM response is complete - add to history and extract trivia"""
        if DebugConfig.chat_enabled:
            print(f"\n[DEBUG-RESPONSE] on_response_generated() CALLED")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-RESPONSE] generation_stopped = {self.generation_stopped}")
        
        # Skip saving if generation was stopped by user
        if self.generation_stopped:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-RESPONSE] Skipping save - generation was stopped")
            self.generation_stopped = False  # Reset flag
            self.response_manager.on_generation_finished()
            return
        
        # CRITICAL: Add response to message_history BEFORE enabling send button
        # This prevents race condition where user sends next message before response is in history
        if hasattr(self.response_manager, '_last_response') and self.response_manager._last_response:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-RESPONSE] _last_response exists: {self.response_manager._last_response[:50]}")
            
            response_text = self.response_manager._last_response
            
            msg_data = {
                "role": "assistant",
                "content": response_text,
                "timestamp": self.response_manager._last_response_timestamp
            }
            self.message_history.append(msg_data)
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-RESPONSE] ✓ Added response to message_history")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-RESPONSE] message_history now has {len(self.message_history)} messages")
            
            # Trigger persistence manager to save
            if hasattr(self, 'persistence_manager'):
                self.persistence_manager.save_message_history()
            
            # Add to memory (without trivia)
            if self.memory and response_text:
                try:
                    if self.server_type == "ollama":
                        self.memory.add_ollama_message("assistant", response_text)
                    else:
                        self.memory.add_llama_message("assistant", response_text)
                    if DebugConfig.chat_memory_operations:
                        if DebugConfig.chat_memory_operations:
                            print(f"[MEMORY] Added assistant message to {self.server_type} memory")
                except Exception as e:
                    if DebugConfig.chat_memory_operations:
                        if DebugConfig.chat_memory_operations:
                            print(f"[MEMORY] Error adding to memory: {e}")
        else:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-RESPONSE] ✗ NO _last_response found!")
        
        # Then call the original response display finished handler
        self.response_manager.on_generation_finished()
        
        # Start model unload timeout if configured
        self._start_model_unload_timer()
    
    def _start_model_unload_timer(self):
        """Start timer to unload model from memory after idle timeout"""
        # Load timeout setting for this server
        settings = load_settings()
        if self.server_type == "ollama":
            timeout_minutes = settings.get("ollama_model_unload_timeout", 0)
        else:  # llama-server
            timeout_minutes = settings.get("llama-server_model_unload_timeout", 0)
        
        # Cancel existing timer if any
        if self.model_unload_timer:
            self.model_unload_timer.stop()
            self.model_unload_timer = None
        
        if timeout_minutes > 0:  # -1 means "Never"
            # Create new timer
            self.model_unload_timer = QTimer()
            self.model_unload_timer.setSingleShot(True)
            self.model_unload_timer.timeout.connect(self._on_model_unload_timeout)
            # Convert minutes to milliseconds
            timeout_ms = timeout_minutes * 60 * 1000
            self.model_unload_timer.start(timeout_ms)
            if DebugConfig.connection_enabled:
                if DebugConfig.chat_memory_operations:
                    print(f"[MODEL-UNLOAD] Started unload timer for {self.server_type}: {timeout_minutes} minutes")
    
    def _on_model_unload_timeout(self):
        """Called when model unload timeout expires"""
        if DebugConfig.connection_enabled:
            if DebugConfig.chat_memory_operations:
                print(f"[MODEL-UNLOAD] Timeout expired for {self.server_type}, unloading model...")
        self._unload_model_immediately()
    
    def _unload_model_immediately(self):
        """Unload model from memory immediately"""
        try:
            if hasattr(self.client, 'unload_model'):
                # Get current model from settings
                settings = load_settings()
                if self.server_type == "ollama":
                    model = settings.get("server_model", "mistral")
                else:
                    model = settings.get("llama-server_server_model", "default")
                
                self.client.unload_model(model)
                if DebugConfig.connection_enabled:
                    if DebugConfig.chat_memory_operations:
                        print(f"[MODEL-UNLOAD] ✓ Unloaded {model} from {self.server_type}")
            else:
                if DebugConfig.connection_enabled:
                    if DebugConfig.chat_memory_operations:
                        print(f"[MODEL-UNLOAD] Client does not support unload_model()")
        except Exception as e:
            if DebugConfig.connection_enabled:
                if DebugConfig.chat_memory_operations:
                    print(f"[MODEL-UNLOAD] Error unloading model: {e}")
    
    def cancel_model_unload_timer(self):
        """Cancel pending model unload timer (called when user sends next message)"""
        if self.model_unload_timer:
            self.model_unload_timer.stop()
            self.model_unload_timer = None
            if DebugConfig.connection_enabled:
                if DebugConfig.chat_memory_operations:
                    print(f"[MODEL-UNLOAD] Cancelled unload timer for {self.server_type}")
    
    def stop_tts(self):
        """Stop TTS playback - delegates to manager"""
        if hasattr(self, 'tts_manager') and self.tts_manager:
            self.tts_manager.stop_tts()
    
    def toggle_image_view(self, state):
        """Toggle image viewer visibility while maintaining scroll percentage"""
        is_visible = state == Qt.Checked
        
        text_edit = self.message_display
        scroll_bar = text_edit.verticalScrollBar()
        
        # Calculate current scroll position as a percentage (0.0 to 1.0)
        max_scroll = scroll_bar.maximum()
        current_scroll = scroll_bar.value()
        scroll_percentage = current_scroll / max_scroll if max_scroll > 0 else 0.0
        
        self.image_widget.setVisible(is_visible)
        self.image_viewer_hidden = not is_visible
        
        if is_visible:
            self.image_manager.load_chat_images()
            self.image_widget.setMinimumSize(300, 250)
            self.image_widget.setMaximumSize(2000, 2000)
        else:
            self.image_widget.setMinimumSize(0, 0)
            self.image_widget.setMaximumSize(16777215, 16777215)
        
        # After layout changes, restore to the same scroll percentage
        def restore_view():
            try:
                new_max_scroll = scroll_bar.maximum()
                new_scroll_value = int(scroll_percentage * new_max_scroll)
                scroll_bar.setValue(new_scroll_value)
            except:
                pass
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(10, restore_view)
    
    def scroll_to_timestamp(self, timestamp_str):
        """Scroll chat to show message with given timestamp at the top"""
        try:
            # Format: "2026-01-03 12:56:56"
            text_content = self.message_display.toPlainText()
            
            # Search for the timestamp in the text
            if timestamp_str in text_content:
                # Find the position of this timestamp
                pos = text_content.find(timestamp_str)
                
                # Create a cursor at that position
                cursor = self.message_display.textCursor()
                cursor.setPosition(pos)
                
                # Get the block number for this position
                block = self.message_display.document().findBlock(pos)
                block_number = block.blockNumber()
                
                # Get the layout and scroll to position this block at the top
                layout = self.message_display.document().documentLayout()
                block_rect = layout.blockBoundingRect(block)
                
                # Adjust scrollbar so this block appears at top of viewport
                scroll_bar = self.message_display.verticalScrollBar()
                scroll_bar.setValue(int(block_rect.top()))
                
                # Also set cursor for visual feedback
                self.message_display.setTextCursor(cursor)
                
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Scrolled to top - timestamp: {timestamp_str}")
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error scrolling to timestamp: {e}")
    
    def update_chat_info_display(self):
        """Update chat info label - delegates to persistence manager"""
        if hasattr(self, 'persistence_manager') and self.persistence_manager:
            self.persistence_manager.update_chat_info_display()
    
    def load_message_history(self):
        """Load chat history - delegates to persistence manager"""
        if hasattr(self, 'persistence_manager') and self.persistence_manager:
            self.persistence_manager.load_message_history()
    
    def save_message_history(self):
        """Save chat history - delegates to persistence manager"""
        if hasattr(self, 'persistence_manager') and self.persistence_manager:
            self.persistence_manager.save_message_history()
    
    def load_timestamp_audio_files(self):
        """Load audio files from chat folder - delegates to TTS manager"""
        try:
            if self.audio_folder and self.audio_folder.exists():
                for audio_file in self.audio_folder.glob("*.wav"):
                    filename = audio_file.stem
                    import re
                    # New format: 2026-01-03T14-23-45_audio
                    timestamp_match = re.search(r'(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})', filename)
                    
                    if timestamp_match:
                        year, month, day, hours, minutes, seconds = timestamp_match.groups()
                        timestamp = f"{year}-{month}-{day} {hours}:{minutes}:{seconds}"
                        self.message_display.timestamp_audio[timestamp] = str(audio_file)
                        if hasattr(self, 'tts_manager') and self.tts_manager:
                            self.tts_manager.timestamp_audio[timestamp] = str(audio_file)
                
                if DebugConfig.media_playback_audio:
                    print(f"[DEBUG] Loaded {len(self.message_display.timestamp_audio)} audio files")
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error loading audio files: {e}")
    
    def auto_focus_input_if_visible(self):
        """Auto-focus input when tab is visible"""
        try:
            if hasattr(self, 'parent'):
                parent = self.parent()
                if parent and hasattr(parent, 'currentWidget'):
                    current_widget = parent.currentWidget()
                    if current_widget is self or current_widget is None:
                        QTimer.singleShot(0, self._do_focus_input)
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG] Error in auto_focus: {e}")
    
    def _do_focus_input(self):
        """Focus input text widget on main thread"""
        try:
            if hasattr(self, 'input_text') and self.input_text:
                self.input_text.setFocus()
                self.input_text.selectAll()
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG] Error focusing input: {e}")
    
    def showEvent(self, event):
        """Called when tab becomes visible"""
        super().showEvent(event)
        self.auto_focus_input_if_visible()
        
        # Update global status panel to reflect this tab's connection state
        if hasattr(self, 'connection_manager'):
            try:
                if self.is_connected:
                    if self.server_type == "ollama":
                        server_display = "Ollama Connected"
                    else:
                        server_display = "Llama-Server Connected"
                    if hasattr(self.app, 'status_panel'):
                        self.app.status_panel.set_connection_status(True, server_display, server_type=self.server_type)
                else:
                    if self.server_type == "ollama":
                        server_display = "Ollama Offline"
                    else:
                        server_display = "Llama-Server Offline"
                    if hasattr(self.app, 'status_panel'):
                        self.app.status_panel.set_connection_status(False, server_display, server_type=self.server_type)
            except Exception as e:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Error updating status on tab show: {e}")
    
    def start_voice_listening(self):
        """Start listening for voice input - delegates to voice_input_wrapper"""
        self.voice_input_active = True
        self.voice_input_wrapper.start_voice_listening()
    
    def stop_voice_listening(self):
        """Stop voice listening - delegates to voice_input_wrapper"""
        self.voice_input_wrapper.stop_voice_listening()
    
    def add_system_message(self, message_text):
        """Add a system message to the chat display
        
        Args:
            message_text: The message text to display (markdown supported)
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Display as a system message (no user attribution)
        self.response_manager.display_message(message_text, is_user=False, timestamp=timestamp)
