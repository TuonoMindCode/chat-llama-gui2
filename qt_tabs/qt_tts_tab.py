"""
Qt TTS Tab - Text-to-Speech Configuration (matching old tts_tab.py)
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QSpinBox, QCheckBox, QPushButton, QGroupBox, QScrollArea, QRadioButton,
    QButtonGroup, QComboBox, QFileDialog, QSlider, QFrame
)
from PyQt5.QtCore import Qt
from settings_manager import load_settings
from settings_saver import get_settings_saver
from pathlib import Path


class QtTTSTab(QWidget):
    """TTS tab for Text-to-Speech Configuration - Global settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.settings = load_settings()
        
        self.create_widgets()
        self.load_settings_values()
        
        # Connect tab changes to reload settings
        if parent and hasattr(parent, 'tabs'):
            parent.tabs.currentChanged.connect(self.on_tab_changed)
    
    def create_widgets(self):
        """Create TTS settings UI"""
        main_layout = QVBoxLayout()
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Save button at top
        save_button = QPushButton("💾 Save TTS Settings")
        save_button.clicked.connect(self.save_tts_settings)
        save_button.setStyleSheet("background-color: #009900; color: white; font-weight: bold;")
        scroll_layout.addWidget(save_button)
        
        # === TTS ENGINE SELECTION ===
        engine_group = QGroupBox("TTS Engine Selection")
        engine_layout = QVBoxLayout()
        
        self.engine_buttons = QButtonGroup()
        
        # Python TTS (pyttsx3)
        python_btn = QRadioButton("Python TTS (pyttsx3 - Built-in)")
        self.engine_buttons.addButton(python_btn, 0)
        engine_layout.addWidget(python_btn)
        
        # Piper
        piper_btn = QRadioButton("Piper (Fast, Local)")
        self.engine_buttons.addButton(piper_btn, 1)
        engine_layout.addWidget(piper_btn)
        
        # F5-TTS
        f5_btn = QRadioButton("F5-TTS (High Quality)")
        self.engine_buttons.addButton(f5_btn, 2)
        engine_layout.addWidget(f5_btn)
        
        # Default to Piper
        piper_btn.setChecked(True)
        
        engine_group.setLayout(engine_layout)
        scroll_layout.addWidget(engine_group)
        
        # === PYTHON TTS SETTINGS ===
        # These settings apply only to Python TTS (pyttsx3)
        python_tts_group = QGroupBox("Python TTS Settings (pyttsx3)")
        common_layout = QVBoxLayout()
        voice_layout = QHBoxLayout()
        voice_layout.addWidget(QLabel("Voice:"), 0)
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["en-US", "en-GB", "default"])
        voice_layout.addWidget(self.voice_combo, 1)
        common_layout.addLayout(voice_layout)
        
        # Speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed (0.5-2.0):"), 0)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(5, 20)  # 0.5 to 2.0
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setValue(10)  # 1.0
        speed_layout.addWidget(self.speed_slider, 1)
        self.speed_label = QLabel("1.0x")
        self.speed_label.setMinimumWidth(40)
        speed_layout.addWidget(self.speed_label, 0)
        self.speed_slider.valueChanged.connect(lambda v: self._update_speed_label(v))
        common_layout.addLayout(speed_layout)
        
        # Volume
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume (0.0-1.0):"), 0)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setTickPosition(QSlider.TicksBelow)
        self.volume_slider.setValue(100)
        volume_layout.addWidget(self.volume_slider, 1)
        self.volume_label = QLabel("1.0")
        self.volume_label.setMinimumWidth(30)
        volume_layout.addWidget(self.volume_label, 0)
        self.volume_slider.valueChanged.connect(lambda v: self._update_volume_label(v))
        common_layout.addLayout(volume_layout)
        
        python_tts_group.setLayout(common_layout)
        scroll_layout.addWidget(python_tts_group)
        
        # === PIPER SETTINGS ===
        piper_group = QGroupBox("Piper Settings")
        piper_layout = QVBoxLayout()
        
        # Piper executable path
        piper_exe_layout = QHBoxLayout()
        piper_exe_layout.addWidget(QLabel("Piper Executable:"), 0)
        self.piper_exe_input = QLineEdit()
        piper_exe_layout.addWidget(self.piper_exe_input, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_piper_exe)
        piper_exe_layout.addWidget(browse_btn, 0)
        piper_layout.addLayout(piper_exe_layout)
        
        # Piper model
        piper_model_layout = QHBoxLayout()
        piper_model_layout.addWidget(QLabel("Piper Model:"), 0)
        self.piper_model_input = QLineEdit()
        piper_model_layout.addWidget(self.piper_model_input, 1)
        piper_layout.addLayout(piper_model_layout)
        
        piper_group.setLayout(piper_layout)
        scroll_layout.addWidget(piper_group)
        
        # === F5-TTS SETTINGS ===
        f5_group = QGroupBox("F5-TTS Settings")
        f5_layout = QVBoxLayout()
        
        # F5-TTS URL
        f5_url_layout = QHBoxLayout()
        f5_url_layout.addWidget(QLabel("F5-TTS Server URL:"), 0)
        self.f5_url_input = QLineEdit()
        self.f5_url_input.setText("http://127.0.0.1:7860")
        f5_url_layout.addWidget(self.f5_url_input, 1)
        f5_layout.addLayout(f5_url_layout)
        
        # Reference audio
        ref_audio_layout = QHBoxLayout()
        ref_audio_layout.addWidget(QLabel("Reference Audio:"), 0)
        self.ref_audio_input = QLineEdit()
        ref_audio_layout.addWidget(self.ref_audio_input, 1)
        browse_audio_btn = QPushButton("Browse")
        browse_audio_btn.setMaximumWidth(80)
        browse_audio_btn.clicked.connect(self.browse_ref_audio)
        ref_audio_layout.addWidget(browse_audio_btn, 0)
        f5_layout.addLayout(ref_audio_layout)
        
        # F5-TTS folder
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("F5-TTS Folder:"), 0)
        self.f5_folder_input = QLineEdit()
        folder_layout.addWidget(self.f5_folder_input, 1)
        browse_folder_btn = QPushButton("Browse")
        browse_folder_btn.setMaximumWidth(80)
        browse_folder_btn.clicked.connect(self.browse_f5_folder)
        folder_layout.addWidget(browse_folder_btn, 0)
        f5_layout.addLayout(folder_layout)
        
        # Remove silence
        self.remove_silence_checkbox = QCheckBox("Remove silence")
        f5_layout.addWidget(self.remove_silence_checkbox)
        
        # Randomize seed
        self.randomize_seed_checkbox = QCheckBox("Randomize seed")
        f5_layout.addWidget(self.randomize_seed_checkbox)
        
        # Seed input
        seed_layout = QHBoxLayout()
        seed_layout.addWidget(QLabel("Seed:"), 0)
        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 2147483647)
        seed_layout.addWidget(self.seed_input, 1)
        f5_layout.addLayout(seed_layout)
        
        # Cross-fade duration
        crossfade_layout = QHBoxLayout()
        crossfade_layout.addWidget(QLabel("Cross-fade Duration (seconds):"), 0)
        self.crossfade_input = QDoubleSpinBox()
        self.crossfade_input.setRange(0.0, 1.0)
        self.crossfade_input.setDecimals(2)
        self.crossfade_input.setSingleStep(0.05)
        self.crossfade_input.setValue(0.15)  # Default 0.15 seconds
        crossfade_layout.addWidget(self.crossfade_input, 1)
        f5_layout.addLayout(crossfade_layout)
        
        # NFE slider
        nfe_layout = QHBoxLayout()
        nfe_layout.addWidget(QLabel("NFE (Inference Steps):"), 0)
        self.nfe_slider = QSlider(Qt.Horizontal)
        self.nfe_slider.setRange(16, 32)
        self.nfe_slider.setValue(16)
        nfe_layout.addWidget(self.nfe_slider, 1)
        self.nfe_label = QLabel("16")
        self.nfe_label.setMinimumWidth(30)
        nfe_layout.addWidget(self.nfe_label, 0)
        self.nfe_slider.valueChanged.connect(lambda v: self.nfe_label.setText(str(v)))
        f5_layout.addLayout(nfe_layout)
        
        # Speed slider
        f5_speed_layout = QHBoxLayout()
        f5_speed_layout.addWidget(QLabel("Speed (0.5-2.0):"), 0)
        self.f5_speed_slider = QSlider(Qt.Horizontal)
        self.f5_speed_slider.setRange(5, 20)
        self.f5_speed_slider.setValue(10)
        f5_speed_layout.addWidget(self.f5_speed_slider, 1)
        self.f5_speed_label = QLabel("1.0x")
        self.f5_speed_label.setMinimumWidth(40)
        f5_speed_layout.addWidget(self.f5_speed_label, 0)
        self.f5_speed_slider.valueChanged.connect(lambda v: self._update_f5_speed_label(v))
        f5_layout.addLayout(f5_speed_layout)
        
        f5_group.setLayout(f5_layout)
        scroll_layout.addWidget(f5_group)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def _update_speed_label(self, value):
        """Update speed label"""
        speed = value / 10.0
        self.speed_label.setText(f"{speed:.1f}x")
    
    def _update_volume_label(self, value):
        """Update volume label"""
        vol = value / 100.0
        self.volume_label.setText(f"{vol:.1f}")
    
    def _update_f5_speed_label(self, value):
        """Update F5 speed label"""
        speed = value / 10.0
        self.f5_speed_label.setText(f"{speed:.1f}x")
    
    def browse_piper_exe(self):
        """Browse for Piper executable"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Piper Executable")
        if file_path:
            self.piper_exe_input.setText(file_path)
    
    def browse_ref_audio(self):
        """Browse for reference audio file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Reference Audio", filter="Audio Files (*.wav *.mp3)")
        if file_path:
            self.ref_audio_input.setText(file_path)
    
    def browse_f5_folder(self):
        """Browse for F5-TTS folder"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select F5-TTS Folder")
        if folder_path:
            self.f5_folder_input.setText(folder_path)
    
    def on_tab_changed(self, index):
        """Called when tab changes - reload settings (TTS is global, not per-server)"""
        # TTS settings are global now, not per-server
        self.settings = load_settings()  # Reload settings from disk
        self.load_settings_values()
    
    def load_settings_values(self):
        """Load current settings into UI"""
        # Reload settings from disk to get latest values
        self.settings = load_settings()
        
        # Load engine selection (global, no server prefix)
        engine = self.settings.get("tts_engine", "piper")
        
        if engine == "python-tts":
            self.engine_buttons.button(0).setChecked(True)
        elif engine == "f5tts":
            self.engine_buttons.button(2).setChecked(True)
        else:  # piper or any other default
            self.engine_buttons.button(1).setChecked(True)
        
        # Load Python TTS settings
        self.voice_combo.setCurrentText(self.settings.get("tts_voice", "en-US"))
        self.speed_slider.setValue(int(self.settings.get("tts_speed", 1.0) * 10))
        self.volume_slider.setValue(int(self.settings.get("tts_volume", 1.0) * 100))
        
        # Load Piper settings
        self.piper_exe_input.setText(self.settings.get("tts_piper_exe", ""))
        self.piper_model_input.setText(self.settings.get("tts_piper_model", ""))
        
        # Load F5-TTS settings
        self.f5_url_input.setText(self.settings.get("tts_f5tts_url", "http://127.0.0.1:7860"))
        self.ref_audio_input.setText(self.settings.get("tts_f5tts_ref_audio", ""))
        self.f5_folder_input.setText(self.settings.get("tts_f5tts_folder", ""))
        self.remove_silence_checkbox.setChecked(self.settings.get("tts_f5tts_remove_silence", False))
        self.randomize_seed_checkbox.setChecked(self.settings.get("tts_f5tts_randomize_seed", False))
        self.seed_input.setValue(int(self.settings.get("tts_f5tts_seed_input", 0)))
        self.crossfade_input.setValue(float(self.settings.get("tts_f5tts_cross_fade_duration", 0.15)))
        self.nfe_slider.setValue(int(self.settings.get("tts_f5tts_nfe_slider", 16)))
        self.f5_speed_slider.setValue(int(self.settings.get("tts_f5tts_speed_slider", 1.0) * 10))
    
    def save_tts_settings(self):
        """Save all TTS settings (global, not per-server)"""
        settings = load_settings()
        
        # Save engine selection (global keys, no server prefix)
        engine_id = self.engine_buttons.checkedId()
        if engine_id == 0:
            engine_name = "python-tts"
        elif engine_id == 2:
            engine_name = "f5tts"
        else:  # button 1
            engine_name = "piper"
        settings["tts_engine"] = engine_name
        
        print(f"[DEBUG] Saving engine_id={engine_id}, engine_name={engine_name}")
        print(f"[DEBUG] Before save - settings['tts_engine'] = {settings.get('tts_engine')}")
        
        # Save Python TTS settings (global keys)
        settings["tts_voice"] = self.voice_combo.currentText()
        settings["tts_speed"] = self.speed_slider.value() / 10.0
        settings["tts_volume"] = self.volume_slider.value() / 100.0
        
        # Save Piper settings (global keys)
        settings["tts_piper_exe"] = self.piper_exe_input.text()
        settings["tts_piper_model"] = self.piper_model_input.text()
        
        # Save F5-TTS settings (global keys)
        settings["tts_f5tts_url"] = self.f5_url_input.text()
        settings["tts_f5tts_ref_audio"] = self.ref_audio_input.text()
        settings["tts_f5tts_folder"] = self.f5_folder_input.text()
        settings["tts_f5tts_remove_silence"] = self.remove_silence_checkbox.isChecked()
        settings["tts_f5tts_randomize_seed"] = self.randomize_seed_checkbox.isChecked()
        settings["tts_f5tts_seed_input"] = self.seed_input.value()
        settings["tts_f5tts_cross_fade_duration"] = self.crossfade_input.value()
        settings["tts_f5tts_nfe_slider"] = self.nfe_slider.value()
        settings["tts_f5tts_speed_slider"] = self.f5_speed_slider.value() / 10.0
        
        saver = get_settings_saver()
        saver.sync_from_ui_dict(settings)
        saver.save()
        print(f"[DEBUG] ✅ TTS settings saved: {engine_name}")
        
        # Verify the save worked
        verify_settings = load_settings()
        verify_engine = verify_settings.get("tts_engine", "NOT_FOUND")
        print(f"[DEBUG] Verification - tts_engine in file: {verify_engine}")
        if verify_engine != engine_name:
            print(f"[ERROR] Save failed! Expected {engine_name}, but file has {verify_engine}")
        else:
            print(f"[DEBUG] ✅ Verification passed - saved correctly to file")
        
        # Extra debug: read and print raw file content
        try:
            import json
            with open("chat_settings.json", "r", encoding="utf-8") as f:
                raw_content = json.load(f)
            print(f"[DEBUG] Raw file tts_engine value: {raw_content.get('tts_engine', 'NOT_FOUND')}")
        except Exception as e:
            print(f"[DEBUG] Could not read raw file: {e}")

