"""
Debug Settings Tab for PyQt5
Provides UI to control debug output for different components
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QScrollArea,
    QPushButton, QMessageBox, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from debug_config import DebugConfig
from settings_manager import load_settings
from settings_saver import get_settings_saver


class QtDebugSettingsTab(QWidget):
    """Debug Settings Tab - Control what debug info is printed to console"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.checkboxes = {}
        self.create_widgets()
        self.load_settings()
    
    def create_widgets(self):
        """Create debug settings UI"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title
        title = QLabel("🐛 Debug Settings")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Description
        description = QLabel("Control what debug information is printed to the Python console:")
        description.setStyleSheet("color: #666666; margin-bottom: 10px;")
        main_layout.addWidget(description)
        
        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # === EXTRACTION DEBUG ===
        extraction_group = self.create_group("📸 Image Extraction", scroll_layout)
        self.add_checkbox(extraction_group, "extraction_enabled", "Enable extraction debug output")
        self.add_checkbox(extraction_group, "extraction_system_prompt", "Show system prompt")
        self.add_checkbox(extraction_group, "extraction_user_prompt", "Show user prompt")
        self.add_checkbox(extraction_group, "extraction_response_snippet", "Show LLM response (first 100 chars)")
        self.add_checkbox(extraction_group, "extraction_full_result", "Show full extracted prompt")
        
        # === COMFYUI DEBUG ===
        comfyui_group = self.create_group("🎨 ComfyUI Image Generation", scroll_layout)
        self.add_checkbox(comfyui_group, "comfyui_enabled", "Enable ComfyUI debug output")
        self.add_checkbox(comfyui_group, "comfyui_workflow", "Show workflow parameters")
        self.add_checkbox(comfyui_group, "comfyui_generation_settings", "Show generation settings (resolution, steps, sampler, scheduler)")
        self.add_checkbox(comfyui_group, "comfyui_copy_operations", "Show file copy operations")
        self.add_checkbox(comfyui_group, "comfyui_queue_operations", "Show queue/prompt operations")
        
        # === PROMPTS DEBUG ===
        prompts_group = self.create_group("💬 System & User Prompts", scroll_layout)
        self.add_checkbox(prompts_group, "system_prompt_enabled", "Enable system prompt debug")
        self.add_checkbox(prompts_group, "system_prompt_full", "Show full system prompt")
        self.add_checkbox(prompts_group, "user_prompt_enabled", "Enable user prompt debug")
        self.add_checkbox(prompts_group, "user_prompt_full", "Show full user prompt")
        
        # === TEMPLATES DEBUG ===
        templates_group = self.create_group("📝 Chat Templates", scroll_layout)
        self.add_checkbox(templates_group, "chat_template_enabled", "Enable template debug output")
        self.add_checkbox(templates_group, "chat_template_selection", "Show template selection")
        self.add_checkbox(templates_group, "chat_template_formatting", "Show template formatting")
        
        # === CHAT & MEMORY DEBUG ===
        chat_group = self.create_group("💾 Chat & Memory", scroll_layout)
        self.add_checkbox(chat_group, "chat_enabled", "Enable chat debug output")
        self.add_checkbox(chat_group, "chat_memory_operations", "Show memory operations")
        self.add_checkbox(chat_group, "chat_message_history", "Show message history operations")
        
        # === TTS DEBUG ===
        tts_group = self.create_group("🔊 Text-to-Speech (TTS)", scroll_layout)
        self.add_checkbox(tts_group, "tts_enabled", "Enable TTS debug output")
        self.add_checkbox(tts_group, "tts_operations", "Show TTS operations")
        
        # === MEDIA PLAYBACK DEBUG ===
        media_group = self.create_group("▶️ Media Playback (Audio & Images)", scroll_layout)
        self.add_checkbox(media_group, "media_playback_enabled", "Enable media playback debug output")
        self.add_checkbox(media_group, "media_playback_audio", "Show audio playback operations (pygame, file paths)")
        self.add_checkbox(media_group, "media_playback_images", "Show image display operations (paths, display info)")
        
        # === STT DEBUG ===
        stt_group = self.create_group("🎤 Speech-to-Text (STT)", scroll_layout)
        self.add_checkbox(stt_group, "stt_enabled", "Enable STT debug output")
        self.add_checkbox(stt_group, "stt_operations", "Show STT operations")
        
        # === CONNECTION DEBUG ===
        connection_group = self.create_group("🌐 Connection & Network", scroll_layout)
        self.add_checkbox(connection_group, "connection_enabled", "Enable connection debug output")
        self.add_checkbox(connection_group, "connection_requests", "Show API requests")
        self.add_checkbox(connection_group, "connection_responses", "Show API responses")
        self.add_checkbox(connection_group, "connection_status", "Show status updates (ollama/llama-server online/offline)")
        
        # === SETTINGS DEBUG ===
        settings_group = self.create_group("⚙️ Settings & Config", scroll_layout)
        self.add_checkbox(settings_group, "settings_enabled", "Enable settings debug output")
        self.add_checkbox(settings_group, "settings_save_load", "Show settings save/load operations")
        self.add_checkbox(settings_group, "settings_changes", "Show settings changes and loading details")
        self.add_checkbox(settings_group, "settings_list", "Show all saved settings list")
        
        # === MODEL LOADING DEBUG ===
        model_group = self.create_group("🤖 Model Loading & Management", scroll_layout)
        self.add_checkbox(model_group, "model_loading_enabled", "Enable model loading debug output")
        self.add_checkbox(model_group, "model_scanning", "Show directory scanning for models (VAE, CLIP, etc)")
        self.add_checkbox(model_group, "model_discovery", "Show discovered models and counts")
        self.add_checkbox(model_group, "model_restore", "Show profile restoration")
        
        # === TOKEN DEBUG ===
        token_group = self.create_group("🔢 Token Counting", scroll_layout)
        self.add_checkbox(token_group, "token_counting_enabled", "Enable token counting debug")
        self.add_checkbox(token_group, "token_count_details", "Show token count breakdowns")
        
        scroll_layout.addStretch()
        
        # === BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        enable_all_btn = QPushButton("✓ Enable All")
        enable_all_btn.clicked.connect(self.enable_all_debug)
        button_layout.addWidget(enable_all_btn)
        
        disable_all_btn = QPushButton("✗ Disable All")
        disable_all_btn.clicked.connect(self.disable_all_debug)
        button_layout.addWidget(disable_all_btn)
        
        reset_defaults_btn = QPushButton("Reset to Defaults")
        reset_defaults_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_defaults_btn)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_and_apply)
        button_layout.addWidget(save_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
    
    def create_group(self, title, parent_layout):
        """Create a grouped section for related debug settings"""
        group_box = QGroupBox(title)
        group_layout = QVBoxLayout()
        group_box.setLayout(group_layout)
        parent_layout.addWidget(group_box)
        return group_layout
    
    def add_checkbox(self, layout, config_key, label_text):
        """Add a checkbox for a debug setting"""
        checkbox = QCheckBox(label_text)
        self.checkboxes[config_key] = checkbox
        # Connect checkbox state change to update config immediately
        checkbox.stateChanged.connect(self.update_debug_config)
        layout.addWidget(checkbox)
        return checkbox
    
    def load_settings(self):
        """Load debug settings from config and settings file"""
        try:
            settings = load_settings()
            debug_settings = settings.get("debug_settings", {})
            
            # Apply loaded settings
            for key, checkbox in self.checkboxes.items():
                if key in debug_settings:
                    checkbox.setChecked(debug_settings[key])
                else:
                    # Use default from DebugConfig
                    checkbox.setChecked(getattr(DebugConfig, key, False))
            
            # Apply settings to DebugConfig (but don't save - we're just loading)
            self.update_debug_config(should_save=False)
        except Exception as e:
            print(f"[DEBUG] Error loading debug settings: {e}")
    
    def update_debug_config(self, should_save=True):
        """Update DebugConfig class with current checkbox states"""
        for key, checkbox in self.checkboxes.items():
            setattr(DebugConfig, key, checkbox.isChecked())
            
            # Special handling: if settings_list checkbox was just enabled, print settings
            if key == "settings_list" and checkbox.isChecked():
                self._print_settings_list()
        
        # Only save if explicitly requested (e.g., user changed settings)
        if should_save:
            self.save_settings()
    
    def _print_settings_list(self):
        """Print all saved settings to console"""
        try:
            settings = load_settings()
            settings_list = sorted(settings.keys())
            count = len(settings_list)
            
            print(f"\n[SETTINGS-DEBUG] ========================================")
            print(f"[SETTINGS-DEBUG] Total saved settings: {count}")
            print(f"[SETTINGS-DEBUG] ========================================")
            for setting in settings_list:
                print(f"[SETTINGS-DEBUG]   {setting}")
            print(f"[SETTINGS-DEBUG] ========================================\n")
        except Exception as e:
            print(f"[SETTINGS-DEBUG] Error printing settings: {e}")
    
    def save_settings(self):
        """Save debug settings to settings saver"""
        try:
            debug_settings = {}
            for key, checkbox in self.checkboxes.items():
                debug_settings[key] = checkbox.isChecked()
            
            saver = get_settings_saver()
            saver.set("debug_settings", debug_settings)
        except Exception as e:
            print(f"[DEBUG] Error queueing debug settings: {e}")
    
    def enable_all_debug(self):
        """Enable all debug output"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
        self.update_debug_config()
        QMessageBox.information(self, "Debug Settings", "All debug output enabled!")
    
    def disable_all_debug(self):
        """Disable all debug output"""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)
        self.update_debug_config()
        QMessageBox.information(self, "Debug Settings", "All debug output disabled!")
    
    def reset_defaults(self):
        """Reset to default debug settings"""
        for key, checkbox in self.checkboxes.items():
            default_value = getattr(DebugConfig, key, False)
            checkbox.setChecked(default_value)
        self.update_debug_config()
        QMessageBox.information(self, "Debug Settings", "Reset to default settings!")
    
    def save_and_apply(self):
        """Explicitly save settings to file and apply to DebugConfig"""
        try:
            # Update DebugConfig with current states
            self.update_debug_config(should_save=False)
            
            # Queue settings for save
            saver = get_settings_saver()
            debug_settings = {}
            for key, checkbox in self.checkboxes.items():
                debug_settings[key] = checkbox.isChecked()
                # Also set on DebugConfig to ensure immediate effect
                setattr(DebugConfig, key, checkbox.isChecked())
            
            saver.set("debug_settings", debug_settings)
            saver.save()  # Explicitly save to disk
            
            # Count enabled/disabled
            enabled_count = sum(1 for v in debug_settings.values() if v)
            disabled_count = len(debug_settings) - enabled_count
            
            QMessageBox.information(
                self, 
                "Settings Saved", 
                f"Debug settings saved!\n\n✓ Enabled: {enabled_count}\n✗ Disabled: {disabled_count}\n\nSettings take effect immediately."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
