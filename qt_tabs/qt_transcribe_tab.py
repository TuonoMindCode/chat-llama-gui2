"""
Qt Transcribe Tab - Speech-to-Text Transcription (Independent Tab)
Converts audio to text using Whisper with language auto-detection
"""
# pylint: disable=no-name-in-module

import threading
import sounddevice as sd
import soundfile as sf
from pathlib import Path
from datetime import datetime
import pygame

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QButtonGroup, QComboBox, QFileDialog, QSlider, QFrame, QGroupBox,
    QTextEdit, QMessageBox, QProgressBar, QScrollArea, QListWidget, QListWidgetItem, QLineEdit, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont

from debug_config import DebugConfig


class TranscriptionWorker(QObject):
    """Worker thread for transcription to avoid blocking UI"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, audio_file, language=None, device=None, model="base", temperature=0.0):
        super().__init__()
        self.audio_file = audio_file
        self.language = language
        self.device = device or "cpu"  # Default to CPU if not specified
        self.model = model or "base"
        self.temperature = temperature
    
    def run(self):
        """Run transcription"""
        try:
            self.progress.emit("Initializing Whisper...")
            import whisper
            
            self.progress.emit("Loading audio file...")
            
            # Load model on specified device
            self.progress.emit(f"Loading Whisper model ({self.model}) on {self.device.upper()}...")
            model = whisper.load_model(self.model, device=self.device)
            
            # Transcribe with specified temperature
            self.progress.emit("Transcribing...")
            try:
                if self.language:
                    result = model.transcribe(str(self.audio_file), language=self.language, temperature=self.temperature)
                else:
                    result = model.transcribe(str(self.audio_file), temperature=self.temperature)
            except Exception as trans_err:
                self.error.emit(f"Transcription error: {str(trans_err)}\n\nTip: Try re-recording or loading a different audio file.")
                return
            
            text = result.get("text", "")
            self.result.emit(text)
            self.progress.emit("Transcription complete!")
            
        except Exception as e:
            self.error.emit(f"Transcription error: {str(e)}")
        finally:
            self.finished.emit()


class LanguageDetectionWorker(QObject):
    """Worker thread for language detection"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(str, str)  # language_code, language_name
    progress = pyqtSignal(str)
    
    def __init__(self, audio_file, device=None, model="base", temperature=0.0):
        super().__init__()
        self.audio_file = audio_file
        self.device = device or "cpu"  # Default to CPU if not specified
        self.model = model or "base"
        self.temperature = temperature
    
    def run(self):
        """Run language detection"""
        try:
            self.progress.emit("Detecting language...")
            import whisper
            
            # Load model on specified device
            self.progress.emit(f"Loading {self.model} model...")
            model = whisper.load_model(self.model, device=self.device)
            
            # Detect language with temperature
            self.progress.emit("Loading audio...")
            try:
                audio = whisper.load_audio(str(self.audio_file))
                audio = whisper.pad_or_trim(audio)
            except Exception as audio_err:
                self.error.emit(f"Audio loading error: {str(audio_err)}\n\nTip: Make sure the audio file is a valid WAV/MP3. Try re-recording.")
                return
            
            try:
                mel = whisper.log_mel_spectrogram(audio).to(model.device)
            except Exception as mel_err:
                self.error.emit(f"Audio processing error: {str(mel_err)}\n\nTip: Try using a smaller model (tiny/base) or a different audio file.")
                return
            
            # Run detection with temperature parameter
            _, probs = model.detect_language(mel)
            detected_language = max(probs, key=probs.get)
            
            # Language code to name mapping
            lang_names = {
                "en": "English", "es": "Spanish", "fr": "French", "de": "German",
                "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
                "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "ar": "Arabic",
            }
            language_name = lang_names.get(detected_language, detected_language.upper())
            
            self.result.emit(detected_language, language_name)
            self.progress.emit(f"Detected: {language_name}")
            
        except Exception as e:
            self.error.emit(f"Language detection error: {str(e)}")
        finally:
            self.finished.emit()


class QtTranscribeTab(QWidget):
    """Transcribe Tab - Convert audio to text using Whisper"""
    
    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.audio_file = None
        self.custom_audio_file = None  # File loaded via "Load custom file"
        self.is_recording = False
        self.recording_thread = None
        self.audio_data = None
        self.sample_rate = 16000  # 16 kHz - Whisper optimal sample rate (resamples to 16kHz anyway)
        self.detected_language_code = None
        self.detected_language_name = None
        self.microphone_gain = 1.0  # Default 1.0x (no amplification)
        
        # Audio playback
        self.is_playing = False
        self.playback_thread = None
        self.total_duration = 0  # Total duration in seconds
        self.current_position = 0  # Current playback position
        
        # Recordings folder - in project directory (not home)
        self.recordings_folder = Path.cwd() / "whisper_recordings"
        self.recordings_folder.mkdir(exist_ok=True)
        
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Pygame mixer init error: {e}")
        
        # Workers
        self.transcription_worker = None
        self.detection_worker = None
        self.transcription_thread = None
        self.detection_thread = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create transcribe UI - Left side controls, Right side output"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        self.setLayout(main_layout)
        
        # === LEFT SIDE - Controls ===
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_widget.setMinimumWidth(550)
        left_widget.setMaximumWidth(760)
        left_widget.setLayout(left_layout)
        
        # Title
        title = QLabel("🎤 Audio Transcription")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        left_layout.addWidget(title)
        
        # Scrollable left content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(8)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        # === 1. INPUT SOURCE SELECTION ===
        source_group = QGroupBox("1️⃣ Input Source")
        source_layout = QVBoxLayout()
        
        self.source_buttons = QButtonGroup()
        
        # Record from input device
        record_radio = QRadioButton("🎙️ Record from Input Device")
        self.source_buttons.addButton(record_radio, 0)
        source_layout.addWidget(record_radio)
        
        # Input device selection
        device_layout = QHBoxLayout()
        device_layout.setContentsMargins(30, 0, 0, 0)
        device_layout.addWidget(QLabel("Device:"), 0)
        self.device_combo = QComboBox()
        self.populate_input_devices()
        device_layout.addWidget(self.device_combo, 1)
        source_layout.addLayout(device_layout)
        
        # Microphone gain/volume control
        gain_layout = QHBoxLayout()
        gain_layout.setContentsMargins(30, 0, 0, 0)
        gain_layout.addWidget(QLabel("Volume:"), 0)
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setRange(50, 200)  # 0.5x to 2.0x
        self.gain_slider.setValue(100)  # Default 1.0x
        self.gain_slider.setTickPosition(QSlider.TicksBelow)
        self.gain_slider.setTickInterval(10)
        gain_layout.addWidget(self.gain_slider, 1)
        self.gain_label = QLabel("1.0x")
        self.gain_label.setMinimumWidth(40)
        gain_layout.addWidget(self.gain_label, 0)
        self.gain_slider.valueChanged.connect(self._on_gain_changed)
        source_layout.addLayout(gain_layout)
        
        # Load custom file
        file_radio = QRadioButton("📁 Load Custom Audio File")
        self.source_buttons.addButton(file_radio, 1)
        source_layout.addWidget(file_radio)
        
        # File selection
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(30, 0, 0, 0)
        file_layout.addWidget(QLabel("File:"), 0)
        self.file_label = QLabel("(No file selected)")
        self.file_label.setStyleSheet("color: #666666;")
        file_layout.addWidget(self.file_label, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.browse_audio_file)
        file_layout.addWidget(browse_btn, 0)
        source_layout.addLayout(file_layout)
        
        record_radio.setChecked(True)
        self.source_buttons.buttonClicked.connect(self.on_source_changed)
        
        source_group.setLayout(source_layout)
        scroll_layout.addWidget(source_group)
        
        # === 2. RECORDING CONTROLS (shown only for record mode) ===
        record_group = QGroupBox("2️⃣ Record Audio")
        record_layout = QVBoxLayout()
        
        button_layout = QHBoxLayout()
        self.record_btn = QPushButton("⏺️ Record")
        self.record_btn.setMinimumHeight(40)
        self.record_btn.clicked.connect(self.start_recording)
        button_layout.addWidget(self.record_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)
        button_layout.addWidget(self.stop_btn)
        
        record_layout.addLayout(button_layout)
        
        self.record_status = QLabel("Ready")
        self.record_status.setStyleSheet("color: #008800;")
        record_layout.addWidget(self.record_status)
        
        record_group.setLayout(record_layout)
        self.record_group = record_group
        scroll_layout.addWidget(record_group)
        
        # === 3. SELECT AUDIO FILE ===
        select_group = QGroupBox("3️⃣ Select Audio")
        select_layout = QVBoxLayout()
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        self.file_list.itemSelectionChanged.connect(self.on_file_selected)
        select_layout.addWidget(self.file_list)
        
        # Delete button (for saved recordings only)
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setMaximumWidth(100)
        delete_btn.clicked.connect(self.delete_selected_file)
        select_layout.addWidget(delete_btn)
        
        select_group.setLayout(select_layout)
        scroll_layout.addWidget(select_group)
        
        # === 4. AUDIO PLAYBACK CONTROLS (shown after recording/file load) ===
        playback_group = QGroupBox("4️⃣ Playback Controls")
        playback_layout = QVBoxLayout()
        
        # Seekbar
        seekbar_layout = QHBoxLayout()
        self.seekbar = QSlider(Qt.Horizontal)
        self.seekbar.setRange(0, 0)
        seekbar_layout.addWidget(self.seekbar)
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setMinimumWidth(80)
        seekbar_layout.addWidget(self.time_label)
        playback_layout.addLayout(seekbar_layout)
        
        # Play/Pause/Stop buttons
        button_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.clicked.connect(self.play_audio)
        button_layout.addWidget(self.play_btn)
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setMaximumWidth(80)
        self.pause_btn.clicked.connect(self.pause_audio)
        button_layout.addWidget(self.pause_btn)
        
        self.stop_btn_playback = QPushButton("⏹️ Stop")
        self.stop_btn_playback.setMaximumWidth(80)
        self.stop_btn_playback.clicked.connect(self.stop_audio)
        button_layout.addWidget(self.stop_btn_playback)
        
        button_layout.addStretch()
        playback_layout.addLayout(button_layout)
        
        self.duration_label = QLabel("Duration: --")
        playback_layout.addWidget(self.duration_label)
        
        playback_group.setLayout(playback_layout)
        self.playback_group = playback_group
        self.playback_group.setVisible(True)  # Make visible
        scroll_layout.addWidget(playback_group)
        
        # === 5. LANGUAGE DETECTION ===
        lang_group = QGroupBox("5️⃣ Language Detection")
        lang_layout = QVBoxLayout()
        
        # Detection model
        detect_model_layout = QHBoxLayout()
        detect_model_layout.addWidget(QLabel("Model:"), 0)
        self.detect_model_combo = QComboBox()
        self.detect_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.detect_model_combo.setCurrentText("base")
        detect_model_layout.addWidget(self.detect_model_combo, 1)
        lang_layout.addLayout(detect_model_layout)
        
        # Detection temperature
        detect_temp_layout = QHBoxLayout()
        detect_temp_layout.addWidget(QLabel("Temperature:"), 0)
        self.detect_temp_spinbox = QDoubleSpinBox()
        self.detect_temp_spinbox.setRange(0.0, 1.0)
        self.detect_temp_spinbox.setSingleStep(0.1)
        self.detect_temp_spinbox.setValue(0.0)
        detect_temp_layout.addWidget(self.detect_temp_spinbox, 1)
        detect_temp_layout.addWidget(QLabel("(0=deterministic, 1=random)"), 0)
        lang_layout.addLayout(detect_temp_layout)
        
        self.detect_btn = QPushButton("🔍 Auto Detect Language")
        self.detect_btn.setMinimumHeight(35)
        self.detect_btn.clicked.connect(self.detect_language)
        self.detect_btn.setEnabled(False)  # Disabled until audio loaded
        lang_layout.addWidget(self.detect_btn)
        
        # Detection status/progress
        self.detect_status = QLabel("Language: Not detected")
        self.detect_status.setStyleSheet("color: #666666;")
        lang_layout.addWidget(self.detect_status)
        
        self.detect_progress_label = QLabel("")
        self.detect_progress_label.setStyleSheet("color: #0066cc;")
        lang_layout.addWidget(self.detect_progress_label)
        
        # Language to use
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("Language to use:"), 0)
        self.language_input = QLineEdit()
        self.language_input.setPlaceholderText("e.g., 'en' for English (auto-detected language will appear here)")
        self.language_input.setText("en")  # Default to English
        language_layout.addWidget(self.language_input, 1)
        lang_layout.addLayout(language_layout)
        
        lang_group.setLayout(lang_layout)
        scroll_layout.addWidget(lang_group)
        
        # === 6. TRANSCRIBE ACTION ===
        action_group = QGroupBox("6️⃣ Transcribe Settings & Action")
        action_layout = QVBoxLayout()
        
        # Transcription model
        trans_model_layout = QHBoxLayout()
        trans_model_layout.addWidget(QLabel("Model:"), 0)
        self.trans_model_combo = QComboBox()
        self.trans_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.trans_model_combo.setCurrentText("base")
        trans_model_layout.addWidget(self.trans_model_combo, 1)
        action_layout.addLayout(trans_model_layout)
        
        # Transcription temperature
        trans_temp_layout = QHBoxLayout()
        trans_temp_layout.addWidget(QLabel("Temperature:"), 0)
        self.trans_temp_spinbox = QDoubleSpinBox()
        self.trans_temp_spinbox.setRange(0.0, 1.0)
        self.trans_temp_spinbox.setSingleStep(0.1)
        self.trans_temp_spinbox.setValue(0.0)
        trans_temp_layout.addWidget(self.trans_temp_spinbox, 1)
        trans_temp_layout.addWidget(QLabel("(0=deterministic, 1=random)"), 0)
        action_layout.addLayout(trans_temp_layout)
        
        self.transcribe_btn = QPushButton("📝 Transcribe Audio")
        self.transcribe_btn.setMinimumHeight(40)
        self.transcribe_btn.setStyleSheet("background-color: #0066cc; color: white; font-weight: bold;")
        self.transcribe_btn.clicked.connect(self.transcribe_audio)
        self.transcribe_btn.setEnabled(False)
        action_layout.addWidget(self.transcribe_btn)
        
        # Progress bar and label for transcription
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        action_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #0066cc;")
        action_layout.addWidget(self.progress_label)
        
        action_group.setLayout(action_layout)
        scroll_layout.addWidget(action_group)
        
        scroll_layout.addStretch()
        
        # === RIGHT SIDE - Output ===
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setSpacing(8)
        
        # Title
        output_title = QLabel("📄 Transcribed Text")
        output_title_font = QFont()
        output_title_font.setBold(True)
        output_title.setFont(output_title_font)
        right_layout.addWidget(output_title)
        
        # Text output
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(False)
        self.output_text.setPlaceholderText("Transcribed text will appear here...")
        right_layout.addWidget(self.output_text, 1)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.clicked.connect(self.clear_output)
        button_layout.addWidget(clear_btn)
        
        send_btn = QPushButton("💬 Send to Chat")
        send_btn.clicked.connect(self.send_to_chat)
        button_layout.addWidget(send_btn)
        
        button_layout.addStretch()
        right_layout.addLayout(button_layout)
        
        right_widget.setLayout(right_layout)
        
        # Add left and right to main layout with proper stretch
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 1)
        
        # Initialize
        self.populate_input_devices()
        self.refresh_file_list()
    
    def populate_input_devices(self):
        """Populate available input devices"""
        try:
            devices = sd.query_devices()
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    self.device_combo.addItem(f"{device['name']}", i)
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Error populating input devices: {e}")
    
    def _on_gain_changed(self):
        """Handle microphone gain slider change"""
        slider_value = self.gain_slider.value()
        self.microphone_gain = slider_value / 100.0  # Convert to 0.5x - 2.0x
        self.gain_label.setText(f"{self.microphone_gain:.1f}x")
    
    def on_source_changed(self):
        """Handle input source change"""
        source = self.source_buttons.checkedId()
        if source == 0:  # Record from device
            self.record_group.setVisible(True)
            self.audio_file = None
            self.playback_group.setVisible(False)
            self.transcribe_btn.setEnabled(False)
        else:  # Load custom file
            self.record_group.setVisible(False)
    
    def start_recording(self):
        """Start recording audio"""
        self.is_recording = True
        self.record_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.record_status.setText("🔴 Recording...")
        self.record_status.setStyleSheet("color: #ff0000;")
        
        device_idx = self.device_combo.currentData()
        
        self.recording_thread = threading.Thread(
            target=self._record_audio,
            args=(device_idx,),
            daemon=True
        )
        self.recording_thread.start()
    
    def _record_audio(self, device_idx):
        """Record audio in background thread"""
        try:
            duration = 300  # Max 5 minutes
            self.audio_data = sd.rec(
                int(self.sample_rate * duration),
                samplerate=self.sample_rate,
                channels=1,
                device=device_idx,
                blocking=True
            )
            if DebugConfig.stt_enabled:
                actual_duration = len(self.audio_data) / self.sample_rate
                print(f"[DEBUG] Recorded {actual_duration:.2f} seconds")
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Recording error: {e}")
    
    def stop_recording(self):
        """Stop recording audio"""
        try:
            self.is_recording = False
            sd.stop()  # Actually stop the recording
            
            # Wait for thread to finish with timeout
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=2)
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Error stopping recording: {e}")
        
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.record_status.setText("✓ Recording complete")
        self.record_status.setStyleSheet("color: #008800;")
        
        # Save to recordings folder with date_time_transcribe format
        try:
            if self.audio_data is not None:
                import numpy as np
                
                # Apply microphone gain amplification
                audio_to_save = self.audio_data * self.microphone_gain
                
                # Find actual recording length (where signal drops below threshold)
                audio_array = np.abs(audio_to_save.flatten())
                # Find last sample with significant energy (threshold: 1% of max)
                max_level = np.max(audio_array)
                if max_level > 0:
                    threshold = max_level * 0.01
                    active_indices = np.where(audio_array > threshold)[0]
                    if len(active_indices) > 0:
                        # Trim to last active sample with small buffer
                        trim_idx = min(active_indices[-1] + 8820, len(audio_to_save))  # 8820 = 0.2s buffer at 44.1kHz
                        trimmed_audio = audio_to_save[:trim_idx]
                    else:
                        trimmed_audio = audio_to_save
                else:
                    trimmed_audio = audio_to_save
                
                # Name format: 20260102_143022_transcribe.wav
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_transcribe.wav"
                temp_path = self.recordings_folder / filename
                sf.write(str(temp_path), trimmed_audio, self.sample_rate)
                
                # Verify file was written
                if temp_path.exists():
                    self.audio_file = temp_path
                    self.transcribe_btn.setEnabled(True)
                    self.detect_btn.setEnabled(True)
                    self.update_duration_label()
                    self.refresh_file_list()
                    # Auto-select the new recording
                    self.select_file_by_path(temp_path)
                    if DebugConfig.stt_enabled:
                        actual_duration = len(trimmed_audio) / self.sample_rate
                        print(f"[DEBUG] Recording saved to: {temp_path} ({actual_duration:.2f}s)")
                else:
                    self.record_status.setText("✗ Failed to save recording")
                    self.record_status.setStyleSheet("color: #880000;")
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Error saving recording: {e}")
            self.record_status.setText(f"✗ Error: {str(e)[:30]}")
            self.record_status.setStyleSheet("color: #880000;")
    
    def browse_audio_file(self):
        """Browse and select audio file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac);;All Files (*.*)"
        )
        
        if file_path:
            self.custom_audio_file = Path(file_path)
            self.audio_file = self.custom_audio_file
            self.transcribe_btn.setEnabled(True)
            self.detect_btn.setEnabled(True)
            self.update_duration_label()
            self.refresh_file_list()
            self.select_file_by_path(self.audio_file)
    
    def update_duration_label(self):
        """Update duration label using soundfile"""
        if not self.audio_file or not self.audio_file.exists():
            self.duration_label.setText("Duration: --")
            self.total_duration = 0
            self.time_label.setText("0:00 / 0:00")
            return
        
        try:
            import soundfile as sf
            # Read audio file info
            with sf.SoundFile(str(self.audio_file)) as f:
                frames = f.frames
                sr = f.samplerate
                self.total_duration = frames / sr
                
                if DebugConfig.stt_enabled:
                    print(f"[DEBUG] Duration: frames={frames}, sr={sr}, total={self.total_duration:.2f}s")
            
            minutes, seconds = int(self.total_duration // 60), int(self.total_duration % 60)
            self.duration_label.setText(f"Duration: {minutes}:{seconds:02d}")
            self.time_label.setText(f"0:00 / {minutes}:{seconds:02d}")
            self.seekbar.setRange(0, int(self.total_duration * 1000))  # milliseconds
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Error reading duration: {e}")
                print(f"[DEBUG] File: {self.audio_file}")
            self.duration_label.setText("Duration: --")
            self.total_duration = 0
            self.time_label.setText("0:00 / 0:00")
    
    def refresh_file_list(self):
        """Refresh the file list with custom file first, then saved recordings (newest first, max 5)"""
        self.file_list.clear()
        
        try:
            # Add custom file first if selected
            if self.custom_audio_file and self.custom_audio_file.exists():
                item = QListWidgetItem(f"📁 custom: {self.custom_audio_file.name}")
                item.setData(Qt.UserRole, str(self.custom_audio_file))
                self.file_list.addItem(item)
            
            # Get all .wav files from recordings folder, sorted by date (newest first)
            wav_files = sorted(
                self.recordings_folder.glob("*.wav"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:5]  # Only show 5 most recent
            
            for file_path in wav_files:
                item = QListWidgetItem(f"🎙️ {file_path.stem}")
                item.setData(Qt.UserRole, str(file_path))
                self.file_list.addItem(item)
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Error refreshing file list: {e}")
    
    def on_file_selected(self):
        """Handle file selection from list"""
        current_item = self.file_list.currentItem()
        if current_item:
            file_path = Path(current_item.data(Qt.UserRole))
            if file_path.exists():
                self.audio_file = file_path
                self.transcribe_btn.setEnabled(True)
                self.detect_btn.setEnabled(True)
                self.update_duration_label()
    
    def select_file_by_path(self, file_path):
        """Select a file in the list by its path"""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if Path(item.data(Qt.UserRole)) == file_path:
                self.file_list.setCurrentItem(item)
                break
    
    def delete_selected_file(self):
        """Delete selected file (only saved recordings, not custom loaded files)"""
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a file to delete")
            return
        
        file_text = current_item.text()
        file_path = Path(current_item.data(Qt.UserRole))
        
        # Don't allow deletion of custom loaded files
        if file_text.startswith("📁 custom:"):
            QMessageBox.warning(self, "Warning", "Cannot delete custom loaded files. Only saved recordings can be deleted.")
            return
        
        # Ask for confirmation
        reply = QMessageBox.question(
            self,
            "Delete Recording",
            f"Are you sure you want to delete this recording?\n{file_path.name}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Stop playback and release the file if it's currently playing
                if self.is_playing:
                    self.is_playing = False
                    pygame.mixer.music.stop()
                
                # Close mixer to release file lock
                pygame.mixer.music.unload()
                
                file_path.unlink()  # Delete the file
                
                # If this was the current audio file, clear it
                if self.audio_file == file_path:
                    self.audio_file = None
                    self.transcribe_btn.setEnabled(False)
                    self.detect_btn.setEnabled(False)
                    self.duration_label.setText("Duration: --")
                    self.time_label.setText("0:00 / 0:00")
                
                # Refresh the file list
                self.refresh_file_list()
                QMessageBox.information(self, "Success", "Recording deleted successfully")
            except Exception as e:
                if DebugConfig.stt_enabled:
                    print(f"[DEBUG] Error deleting file: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete file: {str(e)}")
    
    def detect_language(self):
        """Auto-detect language from audio"""
        if not self.audio_file or not self.audio_file.exists():
            QMessageBox.warning(self, "Warning", "Please record or load an audio file first")
            return
        
        # Check if audio file has content
        try:
            import soundfile as sf
            with sf.SoundFile(str(self.audio_file)) as f:
                if f.frames == 0:
                    QMessageBox.warning(self, "Warning", "Audio file is empty. Please record some audio or load a valid audio file.")
                    return
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Cannot read audio file: {str(e)}\n\nMake sure it's a valid WAV, MP3, or other audio format.")
            return
        
        self.detect_progress_label.setText("Detecting language...")
        
        # Get device from settings
        device = "cpu"  # Default to CPU
        if self.app and hasattr(self.app, 'settings_tab') and hasattr(self.app.settings_tab, 'stt_device_combo'):
            device = self.app.settings_tab.stt_device_combo.currentText()
        
        # Get detection model and temperature from UI
        detect_model = self.detect_model_combo.currentText()
        detect_temp = self.detect_temp_spinbox.value()
        
        self.detection_worker = LanguageDetectionWorker(self.audio_file, device=device, model=detect_model, temperature=detect_temp)
        self.detection_worker.result.connect(self.on_language_detected)
        self.detection_worker.error.connect(self.on_detection_error)
        self.detection_worker.progress.connect(lambda msg: self.detect_progress_label.setText(msg))
        
        self.detection_thread = threading.Thread(target=self.detection_worker.run, daemon=True)
        self.detection_thread.start()
    
    def on_language_detected(self, lang_code, lang_name):
        """Handle detected language"""
        self.detected_language_code = lang_code
        self.detected_language_name = lang_name
        self.detect_status.setText(f"✅ Detected: {lang_name} ({lang_code})")
        self.detect_status.setStyleSheet("color: #008800;")
        
        # Update language input field with detected language
        self.language_input.setText(lang_code)
        
        self.detect_progress_label.setText("")
    
    def on_detection_error(self, error_msg):
        """Handle detection error"""
        QMessageBox.critical(self, "Detection Error", error_msg)
        self.detect_progress_label.setText("")
    
    def transcribe_audio(self):
        """Start transcription"""
        if not self.audio_file or not self.audio_file.exists():
            QMessageBox.warning(self, "Warning", "No audio file to transcribe")
            return
        
        # Check if audio file has content
        try:
            import soundfile as sf
            with sf.SoundFile(str(self.audio_file)) as f:
                if f.frames == 0:
                    QMessageBox.warning(self, "Warning", "Audio file is empty. Please record some audio or load a valid audio file.")
                    return
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Cannot read audio file: {str(e)}\n\nMake sure it's a valid WAV, MP3, or other audio format.")
            return
        
        # Get language from the language input field
        language_text = self.language_input.text().strip()
        language = language_text if language_text else None
        
        self.transcribe_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting transcription...")
        
        # Get device from settings
        device = "cpu"  # Default to CPU
        if self.app and hasattr(self.app, 'settings_tab') and hasattr(self.app.settings_tab, 'stt_device_combo'):
            device = self.app.settings_tab.stt_device_combo.currentText()
        
        # Get transcription model and temperature from UI
        trans_model = self.trans_model_combo.currentText()
        trans_temp = self.trans_temp_spinbox.value()
        
        self.transcription_worker = TranscriptionWorker(self.audio_file, language, device=device, model=trans_model, temperature=trans_temp)
        self.transcription_worker.result.connect(self.on_transcription_complete)
        self.transcription_worker.error.connect(self.on_transcription_error)
        self.transcription_worker.progress.connect(lambda msg: self.progress_label.setText(msg))
        
        self.transcription_thread = threading.Thread(target=self.transcription_worker.run, daemon=True)
        self.transcription_thread.start()
    
    def on_transcription_complete(self, text):
        """Handle transcription completion"""
        self.output_text.setText(text)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("✓ Transcription complete!")
        self.transcribe_btn.setEnabled(True)
    
    def on_transcription_error(self, error_msg):
        """Handle transcription error"""
        QMessageBox.critical(self, "Transcription Error", error_msg)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.transcribe_btn.setEnabled(True)
    
    def play_audio(self):
        """Play selected audio file"""
        if not self.audio_file or not self.audio_file.exists():
            QMessageBox.warning(self, "Warning", "No audio file to play")
            return
        
        if self.is_playing:
            QMessageBox.information(self, "Info", "Already playing audio")
            return
        
        try:
            self.is_playing = True
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            
            # Play audio in background thread
            self.playback_thread = threading.Thread(
                target=self._play_audio_worker,
                daemon=True
            )
            self.playback_thread.start()
        except Exception as e:
            self.is_playing = False
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Error starting playback: {e}")
            QMessageBox.critical(self, "Error", f"Failed to play audio: {str(e)}")
    
    def _play_audio_worker(self):
        """Worker thread for audio playback - updates seekbar during playback"""
        try:
            pygame.mixer.music.load(str(self.audio_file))
            pygame.mixer.music.play()
            
            # Update seekbar position during playback
            import time
            while pygame.mixer.music.get_busy():
                # Get current playback position in milliseconds
                pos = pygame.mixer.music.get_pos()
                if pos >= 0:
                    # Update seekbar and time label
                    self.seekbar.blockSignals(True)  # Block signals to prevent seek during update
                    self.seekbar.setValue(pos)
                    
                    # Update time label
                    current_seconds = pos / 1000.0
                    current_min = int(current_seconds // 60)
                    current_sec = int(current_seconds % 60)
                    total_min = int(self.total_duration // 60)
                    total_sec = int(self.total_duration % 60)
                    self.time_label.setText(f"{current_min}:{current_sec:02d} / {total_min}:{total_sec:02d}")
                    
                    self.seekbar.blockSignals(False)
                
                time.sleep(0.1)  # Update 10 times per second
            
            # Playback finished
            self.is_playing = False
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.seekbar.setValue(0)
            self.time_label.setText(f"0:00 / {int(self.total_duration // 60)}:{int(self.total_duration % 60):02d}")
        except Exception as e:
            self.is_playing = False
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Playback error: {e}")
    
    def pause_audio(self):
        """Pause audio playback"""
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Pause error: {e}")
    
    def stop_audio(self):
        """Stop audio playback"""
        try:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
        except Exception as e:
            if DebugConfig.stt_enabled:
                print(f"[DEBUG] Stop error: {e}")
    
    def copy_to_clipboard(self):
        """Copy transcribed text to clipboard"""
        text = self.output_text.toPlainText()
        if text:
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "Success", "Text copied to clipboard!")
    
    def clear_output(self):
        """Clear output text"""
        self.output_text.clear()
    
    def send_to_chat(self):
        """Send transcribed text to active chat tab"""
        text = self.output_text.toPlainText()
        if not text:
            QMessageBox.warning(self, "Warning", "No text to send")
            return
        
        # Try to send to active chat tab
        if self.app and hasattr(self.app, 'chat_tabs'):
            current_tab = self.app.chat_tabs.currentWidget()
            if current_tab and hasattr(current_tab, 'input_text'):
                current_tab.input_text.setText(text)
                self.app.chat_tabs.setCurrentWidget(current_tab)
                QMessageBox.information(self, "Success", "Text sent to chat input!")
            else:
                QMessageBox.warning(self, "Warning", "No active chat tab found")
        else:
            QMessageBox.warning(self, "Warning", "Cannot access chat tabs")
