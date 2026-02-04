"""
Qt Settings Tab - LLM and Server Configuration (matching old settings_tab.py)
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QDoubleSpinBox,
    QSpinBox, QCheckBox, QPushButton, QGroupBox, QScrollArea, QSlider,
    QComboBox, QFrame
)
from PyQt5.QtCore import Qt
from settings_manager import load_settings
from settings_saver import get_settings_saver
from debug_config import DebugConfig


class QtSettingsTab(QWidget):
    """Settings tab for LLM parameters and server configuration - exactly like old settings_tab.py"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.settings = load_settings()
        
        self.create_widgets()
        self.load_settings_values()
    
    def create_widgets(self):
        """Create settings UI matching old structure"""
        main_layout = QVBoxLayout()
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # === GENERATION PARAMETERS ===
        params_group = QGroupBox("Generation Parameters")
        params_layout = QVBoxLayout()
        
        # Save button at top
        save_button = QPushButton("💾 Save All Settings")
        save_button.clicked.connect(self.save_all_settings)
        save_button.setStyleSheet("background-color: #009900; color: white; font-weight: bold;")
        params_layout.addWidget(save_button)
        
        # Temperature (with slider)
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature (0.1-2.0):"), 0)
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setRange(1, 20)  # 0.1 to 2.0 in steps of 0.1
        self.temp_slider.setTickPosition(QSlider.TicksBelow)
        self.temp_slider.setTickInterval(2)
        self.temp_slider.setValue(9)  # 0.9 - more random for diverse responses
        temp_layout.addWidget(self.temp_slider, 1)
        self.temp_label = QLabel("0.9")
        self.temp_label.setMinimumWidth(30)
        temp_layout.addWidget(self.temp_label, 0)
        self.temp_slider.valueChanged.connect(lambda v: self._update_temp_label(v))
        params_layout.addLayout(temp_layout)
        
        # Top-P (with slider)
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(QLabel("Top-P (0.0-1.0):"), 0)
        self.top_p_slider = QSlider(Qt.Horizontal)
        self.top_p_slider.setRange(0, 20)  # 0.0 to 1.0 in steps of 0.05
        self.top_p_slider.setTickPosition(QSlider.TicksBelow)
        self.top_p_slider.setTickInterval(2)
        self.top_p_slider.setValue(19)  # 0.95 - more diverse word choices
        top_p_layout.addWidget(self.top_p_slider, 1)
        self.top_p_label = QLabel("0.90")
        self.top_p_label.setMinimumWidth(30)
        top_p_layout.addWidget(self.top_p_label, 0)
        self.top_p_slider.valueChanged.connect(lambda v: self._update_top_p_label(v))
        params_layout.addLayout(top_p_layout)
        
        # Top-K (with slider)
        top_k_layout = QHBoxLayout()
        top_k_layout.addWidget(QLabel("Top-K (1-100):"), 0)
        self.top_k_slider = QSlider(Qt.Horizontal)
        self.top_k_slider.setRange(1, 100)
        self.top_k_slider.setTickPosition(QSlider.TicksBelow)
        self.top_k_slider.setTickInterval(10)
        self.top_k_slider.setValue(60)  # 60 - more options to choose from
        top_k_layout.addWidget(self.top_k_slider, 1)
        self.top_k_label = QLabel("40")
        self.top_k_label.setMinimumWidth(30)
        top_k_layout.addWidget(self.top_k_label, 0)
        self.top_k_slider.valueChanged.connect(lambda v: self._update_top_k_label(v))
        params_layout.addLayout(top_k_layout)
        
        # Max Tokens (with slider)
        max_tokens_layout = QHBoxLayout()
        max_tokens_layout.addWidget(QLabel("Max Tokens (128-16384):"), 0)
        self.max_tokens_slider = QSlider(Qt.Horizontal)
        self.max_tokens_slider.setRange(128, 16384)
        self.max_tokens_slider.setTickPosition(QSlider.TicksBelow)
        self.max_tokens_slider.setTickInterval(1024)
        self.max_tokens_slider.setValue(8192)
        max_tokens_layout.addWidget(self.max_tokens_slider, 1)
        self.max_tokens_label = QLabel("8192")
        self.max_tokens_label.setMinimumWidth(40)
        max_tokens_layout.addWidget(self.max_tokens_label, 0)
        self.max_tokens_slider.valueChanged.connect(lambda v: self._update_max_tokens_label(v))
        params_layout.addLayout(max_tokens_layout)
        
        # Request Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Request Timeout (s):"), 0)
        self.timeout_slider = QSlider(Qt.Horizontal)
        self.timeout_slider.setRange(10, 300)
        self.timeout_slider.setTickPosition(QSlider.TicksBelow)
        self.timeout_slider.setTickInterval(30)
        self.timeout_slider.setValue(60)
        timeout_layout.addWidget(self.timeout_slider, 1)
        self.timeout_label = QLabel("60s")
        self.timeout_label.setMinimumWidth(40)
        timeout_layout.addWidget(self.timeout_label, 0)
        self.timeout_slider.valueChanged.connect(lambda v: self._update_timeout_label(v))
        params_layout.addLayout(timeout_layout)
        
        # Infinite timeout checkbox
        self.infinite_timeout_checkbox = QCheckBox("Infinite Timeout")
        self.infinite_timeout_checkbox.stateChanged.connect(self._update_infinite_timeout)
        params_layout.addWidget(self.infinite_timeout_checkbox)
        
        params_group.setLayout(params_layout)
        scroll_layout.addWidget(params_group)
        
        # === SERVER URLs ===
        server_group = QGroupBox("Server URLs")
        server_layout = QVBoxLayout()
        
        # Llama Server URL
        llama_url_layout = QHBoxLayout()
        llama_url_layout.addWidget(QLabel("llama-server URL:"), 0)
        self.llama_url_input = QLineEdit()
        self.llama_url_input.setText("http://127.0.0.1:8080")
        llama_url_layout.addWidget(self.llama_url_input, 1)
        server_layout.addLayout(llama_url_layout)
        
        # Ollama URL
        ollama_url_layout = QHBoxLayout()
        ollama_url_layout.addWidget(QLabel("Ollama URL:"), 0)
        self.ollama_url_input = QLineEdit()
        self.ollama_url_input.setText("http://localhost:11434")
        ollama_url_layout.addWidget(self.ollama_url_input, 1)
        server_layout.addLayout(ollama_url_layout)
        
        # Llama-server Model Unload Timeout
        llama_unload_layout = QHBoxLayout()
        llama_unload_layout.addWidget(QLabel("llama-server Model Unload from Memory:"), 0)
        self.llama_model_unload_combo = QComboBox()
        self.llama_model_unload_combo.addItems(["0 (Immediate)", "5 minutes", "15 minutes", "30 minutes", "Never"])
        llama_unload_layout.addWidget(self.llama_model_unload_combo, 1)
        llama_unload_layout.addWidget(QLabel("(Frees VRAM when idle)"), 0)
        server_layout.addLayout(llama_unload_layout)
        
        # Info about using 0 for image generation
        llama_info = QLabel("💡 Tip: Use '0 (Immediate)' if image generation is enabled to free VRAM for ComfyUI")
        llama_info.setStyleSheet("color: #0066cc; font-size: 9pt; font-style: italic;")
        llama_info.setWordWrap(True)
        server_layout.addWidget(llama_info)
        
        # Ollama Model Unload Timeout
        ollama_unload_layout = QHBoxLayout()
        ollama_unload_layout.addWidget(QLabel("Ollama Model Unload from Memory:"), 0)
        self.ollama_model_unload_combo = QComboBox()
        self.ollama_model_unload_combo.addItems(["0 (Immediate)", "5 minutes", "15 minutes", "30 minutes", "Never"])
        ollama_unload_layout.addWidget(self.ollama_model_unload_combo, 1)
        ollama_unload_layout.addWidget(QLabel("(Frees VRAM when idle)"), 0)
        server_layout.addLayout(ollama_unload_layout)
        
        # Info about using 0 for image generation
        ollama_info = QLabel("💡 Tip: Use '0 (Immediate)' if image generation is enabled to free VRAM for ComfyUI")
        ollama_info.setStyleSheet("color: #0066cc; font-size: 9pt; font-style: italic;")
        ollama_info.setWordWrap(True)
        server_layout.addWidget(ollama_info)
        
        server_group.setLayout(server_layout)
        scroll_layout.addWidget(server_group)
        
        # === WHISPER SPEECH-TO-TEXT SETTINGS ===
        whisper_group = QGroupBox("🎤 Speech-to-Text (Whisper)")
        whisper_layout = QVBoxLayout()
        
        # Model selection
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"), 0)
        self.stt_model_combo = QComboBox()
        self.stt_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.stt_model_combo.setCurrentText("base")
        model_layout.addWidget(self.stt_model_combo, 1)
        whisper_layout.addLayout(model_layout)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device (CPU/GPU):"), 0)
        self.stt_device_combo = QComboBox()
        self.stt_device_combo.addItems(["cpu", "cuda", "mps"])
        self.stt_device_combo.setCurrentText("cpu")
        device_layout.addWidget(self.stt_device_combo, 1)
        whisper_layout.addLayout(device_layout)
        
        # Language
        language_input_layout = QHBoxLayout()
        language_input_layout.addWidget(QLabel("Language Code:"), 0)
        self.stt_language_input = QLineEdit()
        self.stt_language_input.setPlaceholderText("e.g., 'en' for English (leave empty for auto)")
        language_input_layout.addWidget(self.stt_language_input, 1)
        whisper_layout.addLayout(language_input_layout)
        
        # Language reference
        language_ref = QLabel(
            "Common languages: en (English), es (Spanish), fr (French), de (German), it (Italian), "
            "pt (Portuguese), ru (Russian), ja (Japanese), zh (Chinese), ko (Korean), "
            "ar (Arabic), hi (Hindi), th (Thai), pl (Polish), tr (Turkish), vi (Vietnamese), "
            "nl (Dutch), sv (Swedish), no (Norwegian)"
        )
        language_ref.setStyleSheet("color: #666666; font-size: 7pt;")
        language_ref.setWordWrap(True)
        whisper_layout.addWidget(language_ref)
        
        # Audio Input Device
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Audio Input Device:"), 0)
        self.stt_input_device_combo = QComboBox()
        self.stt_input_device_combo.addItem("Default System Device")
        # Try to load available audio devices
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    self.stt_input_device_combo.addItem(f"{i}: {device['name']}")
        except Exception:
            pass
        device_layout.addWidget(self.stt_input_device_combo, 1)
        whisper_layout.addLayout(device_layout)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature (0.0-1.0):"), 0)
        self.stt_temperature_spinbox = QDoubleSpinBox()
        self.stt_temperature_spinbox.setRange(0.0, 1.0)
        self.stt_temperature_spinbox.setSingleStep(0.1)
        self.stt_temperature_spinbox.setValue(0.0)
        temp_layout.addWidget(self.stt_temperature_spinbox, 0)
        temp_layout.addWidget(QLabel("(Lower = more consistent)"), 1)
        whisper_layout.addLayout(temp_layout)
        
        # RMS Threshold (Speech Detection)
        rms_layout = QHBoxLayout()
        rms_layout.addWidget(QLabel("RMS Threshold (0.01-0.1):"), 0)
        self.stt_rms_threshold_spinbox = QDoubleSpinBox()
        self.stt_rms_threshold_spinbox.setRange(0.01, 0.1)
        self.stt_rms_threshold_spinbox.setSingleStep(0.01)
        self.stt_rms_threshold_spinbox.setValue(0.03)
        rms_layout.addWidget(self.stt_rms_threshold_spinbox, 0)
        rms_layout.addWidget(QLabel("(Higher = ignores more noise)"), 1)
        whisper_layout.addLayout(rms_layout)
        
        # No-Speech Threshold
        no_speech_layout = QHBoxLayout()
        no_speech_layout.addWidget(QLabel("No-Speech Threshold (0.0-1.0):"), 0)
        self.stt_no_speech_threshold_spinbox = QDoubleSpinBox()
        self.stt_no_speech_threshold_spinbox.setRange(0.0, 1.0)
        self.stt_no_speech_threshold_spinbox.setSingleStep(0.1)
        self.stt_no_speech_threshold_spinbox.setValue(0.6)
        no_speech_layout.addWidget(self.stt_no_speech_threshold_spinbox, 0)
        no_speech_layout.addWidget(QLabel("(Lower = stops faster on silence)"), 1)
        whisper_layout.addLayout(no_speech_layout)
        
        # Log Probability Threshold
        logprob_layout = QHBoxLayout()
        logprob_layout.addWidget(QLabel("Log Prob Threshold (-5.0 to 0.0):"), 0)
        self.stt_logprob_threshold_spinbox = QDoubleSpinBox()
        self.stt_logprob_threshold_spinbox.setRange(-5.0, 0.0)
        self.stt_logprob_threshold_spinbox.setSingleStep(0.5)
        self.stt_logprob_threshold_spinbox.setValue(-1.0)
        logprob_layout.addWidget(self.stt_logprob_threshold_spinbox, 0)
        logprob_layout.addWidget(QLabel("(Higher = more confident)"), 1)
        whisper_layout.addLayout(logprob_layout)
        
        # Silence Duration Threshold (stops recording after this many seconds of silence)
        silence_duration_layout = QHBoxLayout()
        silence_duration_layout.addWidget(QLabel("Silence Duration (seconds):"), 0)
        self.stt_silence_duration_spinbox = QDoubleSpinBox()
        self.stt_silence_duration_spinbox.setRange(0.5, 10.0)
        self.stt_silence_duration_spinbox.setSingleStep(0.5)
        self.stt_silence_duration_spinbox.setValue(2.0)
        silence_duration_layout.addWidget(self.stt_silence_duration_spinbox, 0)
        silence_duration_layout.addWidget(QLabel("(Stop recording after N seconds of silence)"), 1)
        whisper_layout.addLayout(silence_duration_layout)
        
        # Test Button
        test_button = QPushButton("🔊 Test Whisper Settings")
        test_button.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold;")
        test_button.clicked.connect(self.test_whisper_settings)
        
        # Detect Language Button
        detect_lang_button = QPushButton("🔍 Detect Language (5s)")
        detect_lang_button.setStyleSheet("background-color: #6633ff; color: white; font-weight: bold;")
        detect_lang_button.clicked.connect(self.detect_language)
        
        # Record to WAV Button
        record_button = QPushButton("🎙️ Record Test Audio (5s)")
        record_button.setStyleSheet("background-color: #ff9900; color: white; font-weight: bold;")
        record_button.clicked.connect(self.record_test_audio)
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(test_button)
        button_layout.addWidget(detect_lang_button)
        button_layout.addWidget(record_button)
        whisper_layout.addLayout(button_layout)
        
        # Status label for test
        self.whisper_test_status = QLabel("Ready to test")
        self.whisper_test_status.setStyleSheet("color: #666666; font-size: 8pt;")
        whisper_layout.addWidget(self.whisper_test_status)
        
        whisper_group.setLayout(whisper_layout)
        scroll_layout.addWidget(whisper_group)
        
        # === CHAT TEMPLATE FORMAT ===
        template_group = QGroupBox("💬 Chat Template Format")
        template_layout = QVBoxLayout()
        
        template_info = QLabel("Select the chat format that your model expects:")
        template_info.setStyleSheet("color: #666; font-style: italic;")
        template_layout.addWidget(template_info)
        
        template_combo_layout = QHBoxLayout()
        template_combo_layout.addWidget(QLabel("Template:"), 0)
        self.template_combo = QComboBox()
        
        # Import here to avoid circular imports
        from chat_template_manager import template_manager
        available_templates = template_manager.get_available_templates()
        self.template_combo.addItems(available_templates)
        
        # Load saved template
        saved_template = load_settings().get("chat_template_selection", "auto")
        index = self.template_combo.findText(saved_template)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)
        
        self.template_combo.currentTextChanged.connect(self.on_template_changed)
        template_combo_layout.addWidget(self.template_combo, 1)
        template_layout.addLayout(template_combo_layout)
        
        # Description
        self.template_description = QLabel("Automatically selects the best format for your model")
        self.template_description.setStyleSheet("color: #0066cc; font-size: 9pt;")
        self.template_description.setWordWrap(True)
        template_layout.addWidget(self.template_description)
        
        # Template descriptions
        template_help = QLabel(
            "• auto: Lets the model decide (model must have TEMPLATE in Modelfile)\n"
            "• built-in: chatml: ChatML format for Dolphin/Hermes models <|im_start|>...\n"
            "• built-in: zephyr: Zephyr format for Zephyr/HuggingFaceH4 models <|system|>...\n"
            "• built-in: alpaca: Alpaca instruction format for tuned models\n"
            "• built-in: plain: Simple text format (SYSTEM: ... USER: ...)"
        )
        template_help.setStyleSheet("color: #666; font-size: 8pt;")
        template_help.setWordWrap(True)
        template_layout.addWidget(template_help)
        
        template_group.setLayout(template_layout)
        scroll_layout.addWidget(template_group)
        
        # === INFO SECTION ===
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #ffffcc; border: 1px solid #cccc00;")
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "Parameter Guide:\n"
            "• Temperature: Controls randomness (0.1=focused, 2.0=creative)\n"
            "• Top-P: Nucleus sampling (lower=focused, higher=diverse)\n"
            "• Top-K: Keep top K tokens (higher=more variety)\n"
            "• Max Tokens: Maximum response length\n"
            "• Whisper Model: Larger models are more accurate but slower"
        )
        info_text.setStyleSheet("font-size: 8pt; color: #333333;")
        info_layout.addWidget(info_text)
        info_frame.setLayout(info_layout)
        scroll_layout.addWidget(info_frame)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def _update_temp_label(self, value):
        """Update temperature label from slider"""
        temp = value / 10.0
        self.temp_label.setText(f"{temp:.1f}")
    
    def _update_top_p_label(self, value):
        """Update top-p label from slider"""
        top_p = value / 20.0
        self.top_p_label.setText(f"{top_p:.2f}")
    
    def _update_top_k_label(self, value):
        """Update top-k label from slider"""
        self.top_k_label.setText(str(value))
    
    def _update_max_tokens_label(self, value):
        """Update max tokens label from slider"""
        self.max_tokens_label.setText(str(value))
    
    def _update_timeout_label(self, value):
        """Update timeout label from slider"""
        self.timeout_label.setText(f"{value}s")
        # Also update the app's request_timeout attribute so chat uses new value
        if hasattr(self.parent_app, 'request_timeout'):
            self.parent_app.request_timeout = value
        # Update the actual server client's timeout if it exists
        if hasattr(self.parent_app, 'server_client') and self.parent_app.server_client:
            self.parent_app.server_client.timeout = value
            if DebugConfig.connection_requests:
                print(f"[DEBUG-SETTINGS] Updated server_client.timeout to {value}s")
    
    def _update_infinite_timeout(self, state):
        """Update infinite timeout setting"""
        is_checked = state == Qt.Checked
        # Update the app's request_infinite_timeout attribute
        if hasattr(self.parent_app, 'request_infinite_timeout'):
            self.parent_app.request_infinite_timeout = is_checked
        # Update the actual server client's timeout
        if hasattr(self.parent_app, 'server_client') and self.parent_app.server_client:
            # None = infinite timeout
            timeout_value = None if is_checked else self.timeout_slider.value()
            self.parent_app.server_client.timeout = timeout_value
    
    def load_settings_values(self):
        """Load current settings into UI"""
        self.temp_slider.setValue(int(self.settings.get("temperature", 0.9) * 10))
        self.top_p_slider.setValue(int(self.settings.get("top_p", 0.99) * 20))
        self.top_k_slider.setValue(self.settings.get("top_k", 60))
        self.max_tokens_slider.setValue(self.settings.get("n_predict", 8192))
        self.timeout_slider.setValue(self.settings.get("request_timeout", 60))
        self.infinite_timeout_checkbox.setChecked(self.settings.get("request_infinite_timeout", False))
        
        self.llama_url_input.setText(self.settings.get("llama_url", "http://127.0.0.1:8080"))
        self.ollama_url_input.setText(self.settings.get("ollama_url", "http://localhost:11434"))
        
        # Load model unload timeout settings
        llama_timeout = self.settings.get("llama-server_model_unload_timeout", 0)
        self._set_unload_combo(self.llama_model_unload_combo, llama_timeout)
        ollama_timeout = self.settings.get("ollama_model_unload_timeout", 0)
        self._set_unload_combo(self.ollama_model_unload_combo, ollama_timeout)
        
        # Load Whisper settings
        self.stt_model_combo.setCurrentText(self.settings.get("stt_model", "base"))
        self.stt_device_combo.setCurrentText(self.settings.get("stt_device", "cpu"))
        self.stt_language_input.setText(self.settings.get("stt_language", "en"))
        self.stt_temperature_spinbox.setValue(self.settings.get("stt_temperature", 0.0))
        self.stt_rms_threshold_spinbox.setValue(self.settings.get("stt_rms_threshold", 0.03))
        self.stt_no_speech_threshold_spinbox.setValue(self.settings.get("stt_no_speech_threshold", 0.6))
        self.stt_logprob_threshold_spinbox.setValue(self.settings.get("stt_logprob_threshold", -1.0))
        self.stt_silence_duration_spinbox.setValue(self.settings.get("stt_silence_duration", 2.0))
        device = self.settings.get("stt_input_device")
        device_text = device if device and device != "Default (System Microphone)" else "Default System Device"
        # Try to set the device, default to first item if not found
        try:
            if self.stt_input_device_combo.count() > 0 and self.stt_input_device_combo.findText(device_text) >= 0:
                self.stt_input_device_combo.setCurrentText(device_text)
            else:
                self.stt_input_device_combo.setCurrentIndex(0)
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG-STT] Error setting input device: {e}")
            try:
                self.stt_input_device_combo.setCurrentIndex(0)
            except:
                pass
    
    def _set_unload_combo(self, combo, timeout_value):
        """Set model unload combo box based on timeout value"""
        if timeout_value == 0:
            combo.setCurrentText("0 (Immediate)")
        elif timeout_value == 5:
            combo.setCurrentText("5 minutes")
        elif timeout_value == 15:
            combo.setCurrentText("15 minutes")
        elif timeout_value == 30:
            combo.setCurrentText("30 minutes")
        else:  # -1 or any other value means Never
            combo.setCurrentText("Never")
    
    def _get_unload_timeout_value(self, combo):
        """Get timeout value in minutes from combo box selection"""
        current = combo.currentText()
        if current == "0 (Immediate)":
            return 0
        elif current == "5 minutes":
            return 5
        elif current == "15 minutes":
            return 15
        elif current == "30 minutes":
            return 30
        else:  # "Never"
            return -1
    
    def test_whisper_settings(self):
        """Test whisper settings with live audio recording"""
        try:
            import threading
            import numpy as np
            from pathlib import Path
            
            def test_in_thread():
                try:
                    import sounddevice as sd
                    
                    # Parse device from combo box
                    device_text = self.stt_input_device_combo.currentText()
                    device_id = None
                    if device_text != "Default (System Microphone)":
                        try:
                            device_id = int(device_text.split(":")[0])
                        except ValueError:
                            device_id = None
                    
                    # Record for 5 seconds
                    self.whisper_test_status.setText("🎙️ Recording for 5 seconds... (please speak!)")
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
                    
                    sample_rate = 16000
                    duration = 5
                    
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Recording audio from device: {device_id if device_id is not None else 'default'}")
                    audio = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=1, 
                                  dtype=np.float32, device=device_id, blocking=True)
                    sd.wait()
                    
                    # Save to temporary file
                    import tempfile
                    import soundfile as sf
                    
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    sf.write(tmp_path, audio, sample_rate)
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Saved test audio to: {tmp_path}")
                    
                    self.whisper_test_status.setText("⏳ Loading Whisper and transcribing...")
                    QApplication.processEvents()
                    
                    # Use the subprocess manager to transcribe
                    from speech_to_text_subprocess import WhisperSubprocessManager
                    
                    manager = WhisperSubprocessManager()
                    
                    # Use selected language (not auto-detect)
                    language = self.stt_language_input.text().strip() or None
                    
                    # Create transcribe request
                    request = {
                        "action": "transcribe",
                        "audio_file": tmp_path,
                        "model": self.stt_model_combo.currentText(),
                        "device": self.stt_device_combo.currentText(),
                        "language": language,
                        "temperature": self.stt_temperature_spinbox.value(),
                        "no_speech_threshold": self.stt_no_speech_threshold_spinbox.value(),
                        "logprob_threshold": self.stt_logprob_threshold_spinbox.value(),
                    }
                    
                    result = manager._run_worker(request)
                    
                    # Clean up temp file
                    import os
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                    
                    if result and result.get("text"):
                        text = result["text"].strip()
                        self.whisper_test_status.setText(f"✅ Recognized: \"{text}\"")
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Transcribed text: {text}")
                    else:
                        self.whisper_test_status.setText("❌ No speech detected. Try again or check audio input device.")
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] No speech detected in recording")
                        
                except Exception as e:
                    self.whisper_test_status.setText(f"❌ Error: {str(e)}")
                    print(f"[ERROR] Whisper test failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Run test in background thread
            thread = threading.Thread(target=test_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.whisper_test_status.setText(f"❌ Error: {str(e)}")
            print(f"[ERROR] Failed to start whisper test: {e}")
    
    def record_test_audio(self):
        """Record test audio to WAV file for verification"""
        try:
            import threading
            import numpy as np
            from pathlib import Path
            
            def record_in_thread():
                try:
                    import sounddevice as sd
                    import soundfile as sf
                    
                    # Parse device from combo box
                    device_text = self.stt_input_device_combo.currentText()
                    device_id = None
                    if device_text != "Default (System Microphone)":
                        try:
                            device_id = int(device_text.split(":")[0])
                        except ValueError:
                            device_id = None
                    
                    # Record for 5 seconds
                    self.whisper_test_status.setText("🎙️ Recording for 5 seconds... (please speak!)")
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
                    
                    sample_rate = 48000  # Higher quality
                    duration = 5
                    
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Recording test audio from device: {device_id if device_id is not None else 'default'}")
                    audio = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=2, 
                                  dtype=np.float32, device=device_id, blocking=True)
                    sd.wait()
                    
                    # Save to file in current directory
                    output_file = Path.cwd() / "test_audio_recording.wav"
                    sf.write(str(output_file), audio, sample_rate)
                    
                    self.whisper_test_status.setText(f"✅ Saved to: {output_file}")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Test audio saved to: {output_file}")
                    
                except Exception as e:
                    self.whisper_test_status.setText(f"❌ Error: {str(e)}")
                    print(f"[ERROR] Recording failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Run recording in background thread
            thread = threading.Thread(target=record_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.whisper_test_status.setText(f"❌ Error: {str(e)}")
            print(f"[ERROR] Failed to start recording: {e}")    
    def save_all_settings(self):
        """Save all settings"""
        settings = load_settings()
        
        # LLM settings
        settings["temperature"] = self.temp_slider.value() / 10.0
        settings["top_p"] = self.top_p_slider.value() / 20.0
        settings["top_k"] = self.top_k_slider.value()
        settings["n_predict"] = self.max_tokens_slider.value()
        settings["request_timeout"] = self.timeout_slider.value()
        settings["request_infinite_timeout"] = self.infinite_timeout_checkbox.isChecked()
        
        # Server URLs
        settings["llama_url"] = self.llama_url_input.text().rstrip('/')
        settings["ollama_url"] = self.ollama_url_input.text().rstrip('/')
        
        # Model unload timeouts
        settings["llama-server_model_unload_timeout"] = self._get_unload_timeout_value(self.llama_model_unload_combo)
        settings["ollama_model_unload_timeout"] = self._get_unload_timeout_value(self.ollama_model_unload_combo)
        
        # Whisper settings
        settings["stt_model"] = self.stt_model_combo.currentText()
        settings["stt_device"] = self.stt_device_combo.currentText()
        settings["stt_compute_device"] = self.stt_device_combo.currentText()  # Also save with old key for compatibility
        settings["stt_language"] = self.stt_language_input.text().strip()
        settings["stt_temperature"] = self.stt_temperature_spinbox.value()
        settings["stt_rms_threshold"] = self.stt_rms_threshold_spinbox.value()
        settings["stt_no_speech_threshold"] = self.stt_no_speech_threshold_spinbox.value()
        settings["stt_logprob_threshold"] = self.stt_logprob_threshold_spinbox.value()
        settings["stt_silence_duration"] = self.stt_silence_duration_spinbox.value()
        
        # Extract device ID from combo text (format is "1: Device Name" or "Default System Device")
        device_text = self.stt_input_device_combo.currentText()
        if device_text == "Default System Device":
            settings["stt_input_device"] = None
        elif ": " in device_text:
            # Extract device ID from "1: Device Name"
            try:
                device_id = int(device_text.split(":")[0])
                settings["stt_input_device"] = device_id
            except (ValueError, IndexError):
                settings["stt_input_device"] = None
        else:
            settings["stt_input_device"] = None
        
        saver = get_settings_saver()
        saver.sync_from_ui_dict(settings)
        saver.save()
        
        # Update app object attributes so they take effect immediately
        if self.parent_app:
            self.parent_app.request_timeout = settings["request_timeout"]
            self.parent_app.request_infinite_timeout = settings["request_infinite_timeout"]
            if DebugConfig.connection_enabled:
                print(f"[DEBUG-TIMEOUT] Updated parent app attributes: request_timeout={self.parent_app.request_timeout}, request_infinite_timeout={self.parent_app.request_infinite_timeout}")
        if DebugConfig.settings_save_load:
            print("[DEBUG] ✅ Settings saved")
    
    def detect_language(self):
        """Detect language from live audio recording and auto-fill language field"""
        try:
            import threading
            import numpy as np
            from pathlib import Path
            
            def detect_in_thread():
                try:
                    import sounddevice as sd
                    
                    # Parse device from combo box
                    device_text = self.stt_input_device_combo.currentText()
                    device_id = None
                    if device_text != "Default (System Microphone)":
                        try:
                            device_id = int(device_text.split(":")[0])
                        except ValueError:
                            device_id = None
                    
                    # Record for 5 seconds
                    self.whisper_test_status.setText("🎙️ Recording for 5 seconds... (please speak to detect language!)")
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()
                    
                    sample_rate = 16000
                    duration = 5
                    
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Recording for language detection from device: {device_id if device_id is not None else 'default'}")
                    audio = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=1, 
                                  dtype=np.float32, device=device_id, blocking=True)
                    sd.wait()
                    
                    # Save to temporary file
                    import tempfile
                    import soundfile as sf
                    
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    sf.write(tmp_path, audio, sample_rate)
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Saved test audio to: {tmp_path}")
                    
                    self.whisper_test_status.setText("⏳ Loading Whisper and detecting language...")
                    QApplication.processEvents()
                    
                    # Use the subprocess manager to transcribe
                    from speech_to_text_subprocess import WhisperSubprocessManager
                    
                    manager = WhisperSubprocessManager()
                    
                    # Create transcribe request with NO language (auto-detect)
                    request = {
                        "action": "transcribe",
                        "audio_file": tmp_path,
                        "model": self.stt_model_combo.currentText(),
                        "device": self.stt_device_combo.currentText(),
                        "language": None,  # Force auto-detect
                        "temperature": self.stt_temperature_spinbox.value(),
                        "no_speech_threshold": self.stt_no_speech_threshold_spinbox.value(),
                        "logprob_threshold": self.stt_logprob_threshold_spinbox.value(),
                    }
                    
                    result = manager._run_worker(request)
                    
                    # Clean up temp file
                    import os
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                    
                    if result and result.get("detected_language"):
                        detected_lang = result.get("detected_language", "unknown")
                        lang_code = detected_lang.lower() if detected_lang else ""
                        text = result.get("text", "").strip()
                        
                        # Auto-fill the language field
                        self.stt_language_input.setText(lang_code)
                        self.save_all_settings()
                        
                        lang_name = detected_lang.upper() if detected_lang else "Unknown"
                        self.whisper_test_status.setText(
                            f"✅ Detected: {lang_name} (code: {lang_code})\nText: \"{text}\"\nLanguage saved to field!"
                        )
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Detected language: {lang_code} ({lang_name}). Text: {text}")
                    else:
                        self.whisper_test_status.setText("❌ Could not detect language. Try again with clearer speech.")
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Language detection failed")
                        
                except Exception as e:
                    self.whisper_test_status.setText(f"❌ Error: {str(e)}")
                    print(f"[ERROR] Language detection failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Run detection in background thread
            thread = threading.Thread(target=detect_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            self.whisper_test_status.setText(f"❌ Error: {str(e)}")
            print(f"[ERROR] Failed to start language detection: {e}")
    
    def on_template_changed(self, template_name):
        """Handle chat template selection change"""
        # Save the selection
        from settings_manager import set_setting
        set_setting("chat_template_selection", template_name)
        
        # Update description
        descriptions = {
            "auto": "Automatically selects the best format for your model",
            "built-in: chatml": "ChatML format - Used by Dolphin and Hermes models",
            "built-in: zephyr": "Zephyr format - Used by Zephyr and HuggingFaceH4 models",
            "built-in: alpaca": "Alpaca format - Instruction-tuned models",
            "built-in: plain": "Plain text format - Simple SYSTEM/USER/ASSISTANT"
        }
        
        desc = descriptions.get(template_name, "Custom template format")
        self.template_description.setText(desc)
        
        if DebugConfig.chat_template_selection:
            print(f"[DEBUG-TEMPLATE] Chat template changed to: {template_name}")

