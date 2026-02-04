"""
Voice Input Manager Wrapper - Handles speech-to-text recording and voice input control
Thread-safe voice recording with queue-based communication
"""

import threading
import queue
import numpy as np
import sounddevice as sd
from PyQt5.QtCore import QTimer, Qt
from settings_manager import load_settings
from debug_config import DebugConfig


def _normalize_device_id(device_setting):
    """Convert device setting to a valid sounddevice device ID or None
    
    Args:
        device_setting: Can be None, an integer ID, or a string name
        
    Returns:
        None (for system default) or an integer device ID
    """
    if device_setting is None:
        return None
    
    # If it's a string, try to convert or return None
    if isinstance(device_setting, str):
        # Special case: "Default System Device" means use None
        if device_setting.lower() in ["default system device", "default", ""]:
            return None
        
        # Try to convert to integer
        try:
            return int(device_setting)
        except ValueError:
            # Can't parse as integer, treat as device name - but sounddevice doesn't support names well
            # So return None to use default
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Warning: Device name '{device_setting}' not supported, using system default")
            return None
    
    # If it's already an integer, return it
    if isinstance(device_setting, int):
        return device_setting
    
    # Default fallback
    return None


class VoiceInputWrapper:
    """Wrapper for voice input management - coordinates between chat tab and background threads"""
    
    def __init__(self, chat_tab):
        """
        Initialize voice input wrapper
        
        Args:
            chat_tab: Parent chat tab instance
        """
        self.chat_tab = chat_tab
        self.stt_enabled_checkbox = chat_tab.stt_enabled_checkbox
        self.input_text = chat_tab.input_text
        self.return_to_send_checkbox = chat_tab.return_to_send_checkbox
        self.server_type = chat_tab.server_type
        self.voice_input_queue = chat_tab.voice_input_queue
        self.app = chat_tab.app
    
    def on_stt_toggled(self, state):
        """Handle STT checkbox toggle - with mutually exclusive behavior"""
        if state == Qt.Checked:
            # Send loading status immediately
            self._update_checkbox_status("⏳ Loading...")
            
            # Set this tab as active in Voice Input Manager
            self.chat_tab.voice_manager.set_active_tab(self.server_type)
            if hasattr(self.chat_tab, 'start_voice_listening'):
                self.chat_tab.start_voice_listening()
        else:
            # Deactivate this tab
            self.chat_tab.voice_manager.set_active_tab(None)
            if hasattr(self.chat_tab, 'stop_voice_listening'):
                self.chat_tab.stop_voice_listening()
    
    def _voice_input_callback(self, should_be_checked):
        """Callback from Voice Input Manager to uncheck this tab's checkbox"""
        # Disconnect the signal to avoid recursion
        self.stt_enabled_checkbox.stateChanged.disconnect(self.on_stt_toggled)
        
        # Update checkbox state
        self.stt_enabled_checkbox.setChecked(should_be_checked)
        
        # Reconnect the signal
        self.stt_enabled_checkbox.stateChanged.connect(self.on_stt_toggled)
        
        if not should_be_checked and hasattr(self.chat_tab, 'stop_voice_listening'):
            self.chat_tab.stop_voice_listening()
    
    def _update_checkbox_status(self, status):
        """Update status label with status (checkbox stays simple)"""
        # Keep checkbox text simple, show details in status label
        if hasattr(self.chat_tab, 'voice_status_label'):
            self.chat_tab.voice_status_label.setText(status)
    
    def _append_to_input(self, text):
        """Append transcribed text to input field and auto-send if enabled"""
        # SAFETY CHECK: Don't append if LLM is currently generating a response
        if self.chat_tab.is_generating:
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Transcription received while LLM is generating - discarding: {text[:50]}")
            return
        
        current_text = self.input_text.toPlainText()
        new_text = current_text + text if current_text else text
        self.input_text.setText(new_text)
        
        # Auto-send if "Send on Return" is checked AND we're not generating
        if self.return_to_send_checkbox.isChecked() and not self.chat_tab.is_generating:
            # Give small delay for UI to update
            QTimer.singleShot(100, self.chat_tab.send_message)
    
    def _update_ui_after_listening_stops(self):
        """Update UI when listening stops"""
        self.stt_enabled_checkbox.setText("🎤 Speech Input")
        # Clear the status label
        if hasattr(self.chat_tab, 'voice_status_label'):
            self.chat_tab.voice_status_label.setText("")
    
    def _process_voice_input_queue(self):
        """Process messages from voice input thread (main thread safe)"""
        try:
            while True:
                msg_type, msg_content = self.voice_input_queue.get_nowait()
                
                if msg_type == "text":
                    # Transcribed text received
                    if DebugConfig.chat_memory_operations:
                        print(f"[VOICE_INPUT] Processing transcribed text: {msg_content[:50]}...")
                    self._append_to_input(msg_content)
                
                elif msg_type == "status":
                    # Status update
                    if DebugConfig.chat_memory_operations:
                        print(f"[VOICE_INPUT] Status: {msg_content}")
                    self._update_checkbox_status(msg_content)
                
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[VOICE_INPUT] Error processing queue: {e}")
    
    def stop_voice_listening(self):
        """Stop voice listening"""
        if self.chat_tab.voice_input_active:
            self.chat_tab.voice_input_active = False
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Stopping voice listening for {self.server_type}")
            
            # Stop timer
            if hasattr(self.chat_tab, 'voice_input_timer') and self.chat_tab.voice_input_timer:
                self.chat_tab.voice_input_timer.stop()
                self.chat_tab.voice_input_timer = None
            
            # Wait for thread
            if hasattr(self.chat_tab, 'voice_input_thread') and self.chat_tab.voice_input_thread:
                self.chat_tab.voice_input_thread.join(timeout=1)
                self.chat_tab.voice_input_thread = None
            
            self._update_ui_after_listening_stops()
    
    def resume_voice_listening(self):
        """Resume voice listening after LLM response completes"""
        if not self.chat_tab.voice_input_active:
            return
        
        if self.chat_tab.voice_input_paused:
            self.chat_tab.voice_input_paused = False
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] ✅ Resumed listening for {self.server_type}")
            # Update status to listening
            self._update_checkbox_status("🎙️ Listening")
    
    def start_voice_listening(self):
        """Start listening for voice input with silence detection - THREAD-SAFE"""
        try:
            from speech_to_text import SpeechToText
            import os
            
            # Send loading status to queue (thread-safe)
            self.voice_input_queue.put(("status", "⏳ Loading..."))
            
            # Set Whisper parameters from settings
            settings = load_settings()
            os.environ['WHISPER_TEMPERATURE'] = str(settings.get('stt_temperature', 0.0))
            os.environ['WHISPER_RMS_THRESHOLD'] = str(settings.get('stt_rms_threshold', 0.001))
            os.environ['WHISPER_NO_SPEECH_THRESHOLD'] = str(settings.get('stt_no_speech_threshold', 0.6))
            os.environ['WHISPER_LOG_PROB_THRESHOLD'] = str(settings.get('stt_log_prob_threshold', -1.0))
            
            self.chat_tab.voice_input_paused = False
            
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Starting voice listening for {self.server_type}")
            
            def listen_thread():
                """Background thread for voice recording - thread-safe via queue"""
                try:
                    # Get device and model from settings
                    settings = load_settings()
                    device_id = _normalize_device_id(settings.get('stt_input_device', None))
                    model = settings.get('stt_model', 'base')
                    compute_device = settings.get('stt_device', 'cpu')  # Use stt_device from settings tab
                    
                    # Initialize SpeechToText
                    stt = SpeechToText(model, device=device_id, compute_device=compute_device)
                    
                    # Send listening status via thread-safe queue
                    self.voice_input_queue.put(("status", "🎙️ Listening"))
                    
                    # Record with silence detection
                    self._record_with_silence_detection(stt, device_id)
                    
                except RuntimeError as e:
                    # STT libraries not available
                    error_msg = str(e)
                    if DebugConfig.chat_memory_operations:
                        print(f"[VOICE_INPUT] Voice input unavailable: {error_msg}")
                    self.voice_input_queue.put(("status", "❌ Voice input disabled"))
                except Exception as e:
                    if DebugConfig.chat_memory_operations:
                        print(f"[VOICE_INPUT] Error during voice listening: {e}")
                    import traceback
                    traceback.print_exc()
                    # Send error status via queue
                    self.voice_input_queue.put(("status", "❌ Error"))
                finally:
                    self.chat_tab.voice_input_active = False
            
            # Start background thread
            self.chat_tab.voice_input_thread = threading.Thread(target=listen_thread, daemon=True)
            self.chat_tab.voice_input_thread.start()
            
            # Start timer to process queue periodically (main thread safe)
            if not hasattr(self.chat_tab, 'voice_input_timer') or self.chat_tab.voice_input_timer is None:
                self.chat_tab.voice_input_timer = QTimer()
                self.chat_tab.voice_input_timer.timeout.connect(self._process_voice_input_queue)
                self.chat_tab.voice_input_timer.start(100)  # Check queue every 100ms
            
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Error starting voice listening: {e}")
            # Clear status
            self.chat_tab.voice_status_label.setText("")
    
    def _record_with_silence_detection(self, stt, device_id):
        """Record audio with silence detection - THREAD-SAFE via queue
        
        This runs in a background thread and communicates via thread-safe queue.
        All UI updates are queued and processed on main thread.
        """
        try:
            # Detect supported sample rate
            supported_rates = stt._get_supported_sample_rates(device_id)
            sample_rate = supported_rates[0] if supported_rates else 16000
            stt.sample_rate = sample_rate
            
            settings = load_settings()
            speech_start_delay = settings.get('stt_speech_start_delay', 200)  # ms
            silence_end_delay = settings.get('stt_silence_end_delay', 800)  # ms
            
            # Keep listening while active
            while self.chat_tab.voice_input_active and self.stt_enabled_checkbox.isChecked():
                chunk_duration = 0.1  # 100ms chunks
                chunk_samples = int(sample_rate * chunk_duration)
                
                speech_start_chunks = int(speech_start_delay / (chunk_duration * 1000))
                silence_end_chunks = int(silence_end_delay / (chunk_duration * 1000))
                
                consecutive_silence = 0
                consecutive_speech = 0
                audio_chunks = []
                speech_detected = False
                pre_speech_buffer = []
                buffer_size = 3
                
                # Load speech threshold from settings (user configurable), default 0.03
                speech_threshold = settings.get('stt_rms_threshold', 0.03)
                
                # Record until silence detected
                while self.chat_tab.voice_input_active and self.stt_enabled_checkbox.isChecked():
                    try:
                        # Record chunk
                        chunk = sd.rec(chunk_samples, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        chunk = chunk.flatten()
                        
                        # Detect speech based on RMS level
                        rms_level = float(np.sqrt(np.mean(chunk ** 2)))
                        
                        if rms_level > speech_threshold:
                            # Speech detected
                            consecutive_speech += 1
                            consecutive_silence = 0
                            
                            if not speech_detected and consecutive_speech >= speech_start_chunks:
                                speech_detected = True
                                audio_chunks.extend(pre_speech_buffer)
                                pre_speech_buffer = []
                                # Send listening with speech indicator via queue (thread-safe)
                                self.voice_input_queue.put(("status", "🎙️ Listening [SPEECH]"))
                            
                            if speech_detected:
                                audio_chunks.append(chunk)
                        else:
                            # Silence detected
                            consecutive_speech = 0
                            
                            if not speech_detected:
                                pre_speech_buffer.append(chunk)
                                if len(pre_speech_buffer) > buffer_size:
                                    pre_speech_buffer.pop(0)
                            else:
                                consecutive_silence += 1
                                audio_chunks.append(chunk)
                                
                                # Send silence status update via queue (thread-safe)
                                if consecutive_silence % 5 == 0:  # Update every 500ms
                                    silence_ms = consecutive_silence * chunk_duration * 1000
                                    silence_target_ms = silence_end_chunks * chunk_duration * 1000
                                    self.voice_input_queue.put(("status", f"🎤 Silence: {silence_ms:.0f}ms / {silence_target_ms:.0f}ms"))
                                
                                # Stop after silence threshold
                                if consecutive_silence >= silence_end_chunks:
                                    break
                        
                        # Limit recording length
                        if speech_detected and len(audio_chunks) > 600:
                            break
                    
                    except Exception as e:
                        if DebugConfig.chat_memory_operations:
                            print(f"[VOICE_INPUT] Recording error: {e}")
                        break
                
                # Transcribe if audio was recorded
                if audio_chunks and self.chat_tab.voice_input_active:
                    try:
                        # Combine audio chunks
                        stt.audio_data = np.concatenate(audio_chunks).flatten()
                        
                        # Get transcription settings
                        settings = load_settings()
                        language = settings.get('stt_language', 'en')
                        rms_threshold = settings.get('stt_rms_threshold', 0.03)
                        
                        # Check RMS BEFORE showing "Transcribing..." status
                        # This avoids showing "Transcribing..." if audio will be rejected for being too quiet
                        rms_level = float(np.sqrt(np.mean(stt.audio_data ** 2)))
                        
                        if rms_level < rms_threshold:
                            # Audio too quiet - reject silently and go back to listening
                            if DebugConfig.chat_memory_operations:
                                print(f"[VOICE_INPUT] Audio rejected before transcription (RMS {rms_level:.6f} < {rms_threshold:.6f})")
                            self.voice_input_queue.put(("status", "🎙️ Listening"))
                        else:
                            # Audio looks good - proceed with transcription
                            self.voice_input_queue.put(("status", "⏳ Transcribing..."))
                            
                            result = stt.transcribe(language=language, rms_threshold=rms_threshold)
                            
                            if result and result.get('text'):
                                text = result['text'].strip()
                                if text:
                                    # Send transcribed text via queue (thread-safe)
                                    self.voice_input_queue.put(("text", text + " "))
                                    if DebugConfig.chat_memory_operations:
                                        print(f"[VOICE_INPUT] Transcribed: {text}")
                                    
                                    # Send listening again via queue (thread-safe)
                                    self.voice_input_queue.put(("status", "🎙️ Listening"))
                            else:
                                # Transcription returned None (no speech detected)
                                if DebugConfig.chat_memory_operations:
                                    print(f"[VOICE_INPUT] No speech detected during transcription")
                                # Go back to listening
                                self.voice_input_queue.put(("status", "🎙️ Listening"))
                    
                    except Exception as e:
                        if DebugConfig.chat_memory_operations:
                            print(f"[VOICE_INPUT] Transcription error: {e}")
        
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Error in voice recording: {e}")
