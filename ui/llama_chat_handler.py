"""
LlamaChatHandler - Business logic for Llama chat (responses, voice, audio, history)
"""

import tkinter as tk
from tkinter import simpledialog
import json
from pathlib import Path
from datetime import datetime
import queue
import threading
import re

from chat_manager import ChatManager
from debug_config import DebugConfig


class LlamaChatHandler:
    """Handles Llama chat business logic: responses, voice input, audio playback, history"""
    
    def __init__(self, chat_tab):
        """
        Initialize handler
        
        Args:
            chat_tab: Reference to LlamaChatTab instance
        """
        self.tab = chat_tab
        self.response_queue = queue.Queue()
        self.message_history = []
        self.timestamp_audio = {}
        self.timestamp_image = {}
        self.streaming_text = ""
        self.voice_listening = False
        
        # Initialize ChatManager
        self.chat_manager = ChatManager("llama-server")
        
        # Load saved current chat or default to "default"
        from settings_manager import load_settings
        settings = load_settings()
        saved_chat = settings.get("llama_server_current_chat")
        
        if saved_chat and (self.chat_manager.base_folder / saved_chat).exists():
            self.current_chat_name = saved_chat
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Loaded saved llama-server chat: {saved_chat}")
        else:
            self.current_chat_name = self.chat_manager.get_default_chat().name
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Using default llama-server chat")
        
        # Set up file paths
        self.history_file = Path("chat_history_llama.json")
        self.audio_folder = self.chat_manager.get_audio_folder()
        self.audio_folder.mkdir(exist_ok=True)
    
    def get_server_response(self, message):
        """Get response from server and put in queue"""
        try:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] get_server_response called for llama-server with message: {message[:50]}")
            if not self.tab.app.server_client:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] No server client")
                self.response_queue.put(("error", "Server not connected"))
                return
            
            self.tab.app.stop_generation = False
            system_prompt = self.tab.app.system_prompt_llama
            formatted_prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"
            model = self.tab.app.server_model_var.get()
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Using model: {model}")
            
            temperature = self.tab.app.temperature_var.get() if hasattr(self.tab.app, 'temperature_var') else 0.7
            top_p = self.tab.app.top_p_var.get() if hasattr(self.tab.app, 'top_p_var') else 0.9
            top_k = self.tab.app.top_k_var.get() if hasattr(self.tab.app, 'top_k_var') else 40
            n_predict = self.tab.app.n_predict_var.get() if hasattr(self.tab.app, 'n_predict_var') else -1
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] LLM Parameters: temperature={temperature}, top_p={top_p}, top_k={top_k}, n_predict={n_predict}")
            
            if self.tab.app.streaming_enabled_var.get():
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Using streaming")
                try:
                    self.response_queue.put(("stream_start",))
                    for chunk in self.tab.app.server_client.generate_stream(
                        formatted_prompt,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        n_predict=n_predict
                    ):
                        if self.tab.app.stop_generation:
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] Stop generation flag set")
                            self.response_queue.put(("stream_interrupted",))
                            return
                        self.response_queue.put(("stream_chunk", chunk))
                    self.response_queue.put(("stream_end",))
                except Exception as e:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Streaming error: {e}")
                    self.response_queue.put(("error", f"Streaming error: {str(e)}"))
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Using non-streaming")
                generated_text = self.tab.app.server_client.generate(
                    formatted_prompt,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    n_predict=n_predict
                )
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Generated text: {generated_text[:100]}")
                
                lines = generated_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.strip().startswith("User:"):
                        break
                    cleaned_lines.append(line)
                
                generated_text = '\n'.join(cleaned_lines).strip()
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Putting success message in queue")
                self.response_queue.put(("success", generated_text))
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Exception in get_server_response: {e}")
            self.response_queue.put(("error", f"Error: {str(e)}"))
    
    def add_chat_message(self, sender, message, tag="assistant"):
        """Add message to chat display and history"""
        if DebugConfig.chat_enabled:
            if DebugConfig.chat_enabled:
                print(f"[HANDLER] add_chat_message called: sender={sender}, message_len={len(message)}, tag={tag}")
        self.tab.chat_display.config(state=tk.NORMAL)
        
        display_label = sender
        if sender == "Assistant":
            display_label = "llama"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # If this is a user message, remove the placeholder
        if sender == "You":
            chat_content = self.tab.chat_display.get("1.0", tk.END)
            match = re.search(r'\(\d{2}:\d{2}:\d{2}\) You: [\s]*$', chat_content)
            if match:
                start_pos = len(chat_content) - len(match.group())
                self.tab.chat_display.delete("1.0", tk.END)
                content_before = chat_content[:start_pos].rstrip() + "\n\n"
                self.tab.chat_display.insert("1.0", content_before)
        
        if sender == "Assistant":
            if DebugConfig.chat_enabled:
                if DebugConfig.chat_enabled:
                    print(f"[HANDLER] Inserting assistant message: [{timestamp}] llama: {message[:50]}")
            self.tab.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
            self.tab.chat_display.insert(tk.END, f" {display_label}: {message}\n\n", tag)
        else:
            if DebugConfig.chat_enabled:
                if DebugConfig.chat_enabled:
                    print(f"[HANDLER] Inserting user message: ({timestamp}) {display_label}: {message[:50]}")
            self.tab.chat_display.insert(tk.END, f"({timestamp}) {display_label}: {message}\n\n", tag)
        
        self.tab.chat_display.see(tk.END)
        self.tab.chat_display.config(state=tk.DISABLED)
        
        msg_entry = {
            "timestamp": timestamp,
            "sender": display_label,
            "content": message,
            "audio_file": None,
            "image_file": None,
            "server": "llama-server" if sender == "Assistant" else None
        }
        self.message_history.append(msg_entry)
        self.save_message_history()
        if DebugConfig.chat_enabled:
            if DebugConfig.chat_enabled:
                print(f"[HANDLER] Message saved to history")
    
    def update_streaming_message(self, text):
        """Update the last assistant message with streamed text"""
        self.tab.chat_display.config(state=tk.NORMAL)
        
        try:
            all_text = self.tab.chat_display.get("1.0", tk.END)
            
            # Find the last timestamp marker: [HH:MM:SS]
            last_timestamp_pos = all_text.rfind("[")
            if last_timestamp_pos < 0:
                self.tab.chat_display.config(state=tk.DISABLED)
                return
            
            # Find the closing bracket
            close_bracket = all_text.find("]", last_timestamp_pos)
            if close_bracket < 0:
                self.tab.chat_display.config(state=tk.DISABLED)
                return
            
            # Keep everything up to and including "] llama: "
            # The format is "[HH:MM:SS] llama: "
            prefix_end = all_text.find(":", close_bracket) + 2  # +2 for ": "
            prefix_to_keep = all_text[:prefix_end]
            
            new_full_text = prefix_to_keep + text + "\n\n"
            
            self.tab.chat_display.delete("1.0", tk.END)
            self.tab.chat_display.insert("1.0", new_full_text)
            
            # Reapply all tags to preserve formatting
            self._apply_tags_to_content(new_full_text)
            
        except Exception as e:
            print(f"Error updating streaming message: {e}")
            import traceback
            traceback.print_exc()
        
        self.tab.chat_display.see(tk.END)
        self.tab.chat_display.config(state=tk.DISABLED)
    
    def _apply_tags_to_content(self, content):
        """Reapply tags to text content after deletion/rebuild"""
        import re
        
        # First, remove all existing tags
        self.tab.chat_display.tag_remove("timestamp", "1.0", tk.END)
        self.tab.chat_display.tag_remove("assistant", "1.0", tk.END)
        self.tab.chat_display.tag_remove("user", "1.0", tk.END)
        
        # Find and tag all timestamps using Text widget search
        idx = "1.0"
        while True:
            idx = self.tab.chat_display.search(r"\[[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\]", idx, tk.END, regexp=True)
            if not idx:
                break
            end_idx = self.tab.chat_display.index(f"{idx}+10c")  # timestamp is 10 chars: [HH:MM:SS]
            self.tab.chat_display.tag_add("timestamp", idx, end_idx)
            idx = end_idx
        
        # Tag assistant messages (llama:) using search
        idx = "1.0"
        while True:
            idx = self.tab.chat_display.search("llama:", idx, tk.END)
            if not idx:
                break
            # Find start of message content (after "llama: ")
            msg_start = self.tab.chat_display.index(f"{idx}+7c")
            # Find end of line
            line_end = self.tab.chat_display.index(f"{idx} lineend")
            self.tab.chat_display.tag_add("assistant", msg_start, line_end)
            idx = self.tab.chat_display.index(f"{idx}+1c")
        
        # Tag user messages
        idx = "1.0"
        while True:
            idx = self.tab.chat_display.search(r"\([0-2][0-9]:[0-5][0-9]:[0-5][0-9]\) You:", idx, tk.END, regexp=True)
            if not idx:
                break
            # Find start of message content
            msg_start = self.tab.chat_display.index(f"{idx}+12c")  # (HH:MM:SS) You: = 12 chars
            # Find end of line
            line_end = self.tab.chat_display.index(f"{idx} lineend")
            self.tab.chat_display.tag_add("user", msg_start, line_end)
            idx = self.tab.chat_display.index(f"{idx}+1c")
    
    def check_responses(self):
        """Check response queue and update UI"""
        try:
            while True:
                message_data = self.response_queue.get_nowait()
                
                if isinstance(message_data, tuple) and len(message_data) >= 1:
                    status = message_data[0]
                    message = message_data[1] if len(message_data) > 1 else ""
                else:
                    status = message_data
                    message = ""
                
                if status == "stream_start":
                    self.tab.stop_button.config(state=tk.NORMAL)
                    self.tab.app.set_generating_status(True)
                    self.streaming_text = ""
                    self.add_chat_message("llama", "", "assistant")
                
                elif status == "stream_chunk":
                    self.streaming_text += message
                    self.update_streaming_message(self.streaming_text)
                
                elif status == "stream_end" or status == "stream_interrupted":
                    self.tab.stop_button.config(state=tk.DISABLED)
                    self.tab.app.set_generating_status(False)
                    
                    # Update the empty message with streaming text
                    if self.message_history:
                        for msg in reversed(self.message_history):
                            if msg["sender"] == "llama" and msg.get("content") == "":
                                msg["content"] = self.streaming_text
                                break
                    
                    if self.tab.tts_enabled_var.get() and self.streaming_text and status != "stream_interrupted":
                        self.tab.app.speak_response(self.streaming_text)
                    
                    self.tab.chat_display.config(state=tk.NORMAL)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.tab.chat_display.insert(tk.END, f"({timestamp}) You: ", "user")
                    self.tab.chat_display.see(tk.END)
                    self.tab.chat_display.config(state=tk.DISABLED)
                
                elif status == "success":
                    self.tab.app.set_generating_status(False)
                    self.add_chat_message("llama", message, "assistant")
                    
                    if self.tab.tts_enabled_var.get():
                        self.tab.app.speak_response(message)
                    
                    self.save_message_history()
                
                else:
                    self.add_chat_message("System", message, "error")
                    self.tab.stop_button.config(state=tk.DISABLED)
        
        except queue.Empty:
            pass
    
    def save_message_history(self):
        """Save chat history to file"""
        if not self.tab.app.save_history_var.get():
            return
        
        try:
            self.chat_manager.save_chat(self.current_chat_name, self.message_history)
            self.tab.update_chat_info_display()
            if DebugConfig.chat_enabled:
                print(f"[DEBUG SAVE] Saved {len(self.message_history)} messages")
        except Exception as e:
            print(f"Error saving message history: {e}")
    
    def load_message_history(self):
        """Load chat history from file"""
        if not self.tab.app.save_history_var.get():
            return
        
        try:
            messages = self.chat_manager.load_chat(self.current_chat_name)
            self.tab.chat_display.config(state=tk.NORMAL)
            audio_count = 0
            image_count = 0
            
            for msg in messages:
                timestamp = msg.get("timestamp", "")
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                audio_file = msg.get("audio_file")
                image_file = msg.get("image_file")
                
                if sender == "You":
                    tag = "user"
                else:
                    tag = "assistant"
                
                if sender == "You":
                    self.tab.chat_display.insert(tk.END, f"({timestamp})", tag)
                    self.tab.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                else:
                    self.tab.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
                    self.tab.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                
                if audio_file:
                    self.timestamp_audio[timestamp] = audio_file
                    audio_count += 1
                    if DebugConfig.media_playback_audio:
                        print(f"[DEBUG] Loaded audio: {timestamp} -> {audio_file}")
                
                if image_file:
                    self.timestamp_image[timestamp] = image_file
                    image_count += 1
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Loaded image: {timestamp} -> {image_file}")
                
                self.message_history.append({
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                    "audio_file": audio_file,
                    "image_file": image_file,
                    "server": msg.get("server")
                })
            
            # Populate image viewer with saved images
            if image_count > 0 and hasattr(self.tab, 'image_viewer'):
                self.tab.image_viewer.images_list = []
                for msg in messages:
                    if msg.get("image_file"):
                        image_file = msg.get("image_file")
                        timestamp = msg.get("timestamp")
                        # Add to image viewer if file exists
                        from pathlib import Path
                        if Path(image_file).exists():
                            self.tab.image_viewer.images_list.append(image_file)
                            # Set timestamp for image alignment
                            if hasattr(self.tab.image_viewer, 'set_image_timestamp'):
                                self.tab.image_viewer.set_image_timestamp(image_file, timestamp)
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] Added image to viewer: {image_file}")
                
                # Update image viewer display
                if self.tab.image_viewer.images_list:
                    self.tab.image_viewer.current_image_index = 0
                    self.tab.image_viewer.display_images()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Populated image viewer with {len(self.tab.image_viewer.images_list)} images")
            
            self.tab.chat_display.config(state=tk.DISABLED)
            self.tab.update_chat_info_display()
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Loaded {len(messages)} messages, {audio_count} audio mappings, {image_count} image mappings")
        except Exception as e:
            print(f"Error loading message history: {e}")
    
    def play_audio_for_timestamp(self, timestamp):
        """Play audio file for a given timestamp"""
        if timestamp in self.timestamp_audio:
            audio_file = self.timestamp_audio[timestamp]
            if Path(audio_file).exists():
                import pygame
                try:
                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"Error playing audio: {e}")
            else:
                print(f"Audio file not found: {audio_file}")
        else:
            print(f"No audio found for timestamp: {timestamp}")
    
    def start_voice_listening(self):
        """Start listening for voice input"""
        try:
            from speech_to_text import SpeechToText
            import os
            
            os.environ['WHISPER_TEMPERATURE'] = str(self.tab.app.stt_temperature_var.get())
            os.environ['WHISPER_RMS_THRESHOLD'] = str(self.tab.app.stt_rms_threshold_var.get())
            os.environ['WHISPER_NO_SPEECH_THRESHOLD'] = str(self.tab.app.stt_no_speech_threshold_var.get())
            os.environ['WHISPER_LOG_PROB_THRESHOLD'] = str(self.tab.app.stt_log_prob_threshold_var.get())
            
            self.voice_listening = True
            self.tab.app.set_mic_status(True, "llama-server")
            self.tab.voice_status_label.config(text="🎤 Listening...", fg="#ff9900")
            self.tab.voice_status_label.update()
            
            print("\n" + "="*60)
            print(f"VOICE LISTENING STARTED - Llama Chat")
            print("="*60)
            print(f"Whisper Temperature: {self.tab.app.stt_temperature_var.get()}")
            print(f"RMS Threshold: {self.tab.app.stt_rms_threshold_var.get()}")
            print(f"No Speech Threshold: {self.tab.app.stt_no_speech_threshold_var.get()}")
            print(f"Log Prob Threshold: {self.tab.app.stt_log_prob_threshold_var.get()}")
            print(f"Speech Start Delay: {self.tab.app.stt_speech_start_delay_var.get()}ms")
            print(f"Silence End Delay: {self.tab.app.stt_silence_end_delay_var.get()}ms")
            print("="*60 + "\n")
            
            def listen_thread():
                try:
                    if hasattr(self.tab.app, 'stt_device_var'):
                        device_str = self.tab.app.stt_device_var.get()
                        device_id = int(device_str.split(":")[0]) if device_str else None
                    else:
                        device_id = None
                    
                    model = self.tab.app.stt_model_var.get()
                    compute_device = self.tab.app.stt_compute_device_var.get()
                    
                    stt = SpeechToText(model, device=device_id, compute_device=compute_device)
                    self._record_with_silence_detection(stt, device_id)
                    
                except Exception as e:
                    print(f"Voice listening error: {e}")
                    import traceback
                    traceback.print_exc()
                    self.tab.voice_status_label.config(text="❌ Error", fg="#cc0000")
                finally:
                    self.voice_listening = False
                    if not self.tab.stt_enabled_var.get():
                        self.tab.voice_status_label.config(text="", fg="#ff9900")
            
            thread = threading.Thread(target=listen_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            print(f"Error starting voice listening: {e}")
            self.tab.voice_status_label.config(text="❌ Error", fg="#cc0000")
            self.tab.stt_enabled_var.set(False)
    
    def stop_voice_listening(self):
        """Stop voice listening"""
        self.voice_listening = False
        self.tab.app.set_mic_status(False, "llama-server")
        self.tab.voice_status_label.config(text="", fg="#ff9900")
        print(f"\nVoice listening stopped on Llama Chat.\n")
        
        # Unload whisper model from memory
        from voice_input_manager import VoiceInputManager
        voice_manager = VoiceInputManager()
        voice_manager.set_active_tab(None)  # This will call unload_whisper_model()
    
    def _record_with_silence_detection(self, stt, device_id):
        """Record audio and detect silence to trigger transcription"""
        import numpy as np
        import sounddevice as sd
        import time
        
        if DebugConfig.chat_enabled:
            print(f"[DEBUG REC START] Entering recording. voice_listening={self.voice_listening}, stt_enabled={self.tab.stt_enabled_var.get()}")
        
        try:
            supported_rates = stt._get_supported_sample_rates(device_id)
            sample_rate = supported_rates[0] if supported_rates else 16000
            stt.sample_rate = sample_rate
            if DebugConfig.chat_enabled:
                print(f"[DEBUG REC] Sample rate: {sample_rate}, Device: {device_id}")
            
            while self.voice_listening and self.tab.stt_enabled_var.get():
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG REC] Outer loop check: voice_listening={self.voice_listening}, stt_enabled={self.tab.stt_enabled_var.get()}")
                chunk_duration = 0.1
                chunk_samples = int(sample_rate * chunk_duration)
                
                speech_start_chunks = int(self.tab.app.stt_speech_start_delay_var.get() / (chunk_duration * 1000))
                silence_end_chunks = int(self.tab.app.stt_silence_end_delay_var.get() / (chunk_duration * 1000))
                
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG REC] Starting new recording. speech_start_chunks={speech_start_chunks}, silence_end_chunks={silence_end_chunks}")
                
                consecutive_silence = 0
                consecutive_speech = 0
                audio_chunks = []
                speech_detected = False
                last_status_update = 0
                pre_speech_buffer = []
                buffer_size = 3
                
                while self.voice_listening and self.tab.stt_enabled_var.get():
                    try:
                        chunk = sd.rec(chunk_samples, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        
                        chunk = chunk.flatten()
                        rms_level = float(np.sqrt(np.mean(chunk ** 2)))
                        speech_threshold = 0.02
                        
                        if rms_level > speech_threshold:
                            consecutive_speech += 1
                            consecutive_silence = 0
                            
                            if not speech_detected and consecutive_speech >= speech_start_chunks:
                                speech_detected = True
                                audio_chunks.extend(pre_speech_buffer)
                                pre_speech_buffer = []
                                self.tab.voice_status_label.config(text="🎤 Listening... [SPEECH]", fg="#009900")
                                self.tab.app.root.update()
                                print(f"  🎤 Speech detected (after {consecutive_speech * chunk_duration * 1000:.0f}ms)")
                            
                            if speech_detected:
                                audio_chunks.append(chunk)
                        else:
                            consecutive_speech = 0
                            
                            if not speech_detected:
                                pre_speech_buffer.append(chunk)
                                if len(pre_speech_buffer) > buffer_size:
                                    pre_speech_buffer.pop(0)
                            else:
                                consecutive_silence += 1
                                audio_chunks.append(chunk)
                                
                                current_time = time.time()
                                if current_time - last_status_update >= 0.5:
                                    silence_ms = consecutive_silence * chunk_duration * 1000
                                    silence_target_ms = silence_end_chunks * chunk_duration * 1000
                                    self.tab.voice_status_label.config(
                                        text=f"🎤 Silence: {silence_ms:.0f}ms / {silence_target_ms:.0f}ms",
                                        fg="#ff9900"
                                    )
                                    self.tab.app.root.update()
                                    last_status_update = current_time
                                
                                if consecutive_silence >= silence_end_chunks:
                                    silence_ms = consecutive_silence * chunk_duration * 1000
                                    print(f"  ⏸ {silence_ms:.0f}ms silence detected - Transcribing...")
                                    break
                        
                        if speech_detected and len(audio_chunks) > 600:
                            print("  ⚠ Max recording time reached")
                            break
                    except Exception as e:
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG REC] Exception in recording loop: {e}")
                        break
                
                if audio_chunks and self.tab.stt_enabled_var.get():
                    stt.audio_data = np.concatenate(audio_chunks).flatten()
                    
                    if len(stt.audio_data) > 0:
                        self.tab.voice_status_label.config(text="🎤 Transcribing...", fg="#0066cc")
                        self.tab.app.root.update()
                        
                        # Use global language setting from main app settings (not auto-detect)
                        language = self.tab.app.stt_language_var.get()
                        result = stt.transcribe(language=language)
                        
                        # Extract text from result dict
                        text = result.get('text', '').strip() if isinstance(result, dict) else (result.strip() if result else '')
                        
                        if text and len(text) > 0:
                            print(f"  ✓ Transcription: {text}")
                            self.tab.voice_status_label.config(text="✓ Done! Listening again...", fg="#009900")
                            self.tab.app.root.update()
                            
                            self.tab.input_text.insert(tk.END, text + " ")
                            
                            if self.tab.return_to_send_var.get():
                                print("  📤 Auto-sending...")
                                self.tab.app.root.after(500, lambda: self.tab.send_message())
                                time.sleep(1)
                        else:
                            print("  ⚠ No speech detected")
                            self.tab.voice_status_label.config(text="🎤 Listening... (no speech)", fg="#ff9900")
                            self.tab.app.root.update()
                    else:
                        self.tab.voice_status_label.config(text="🎤 Listening... (no audio)", fg="#ff9900")
                        self.tab.app.root.update()
                else:
                    break
                
        except Exception as e:
            print(f"❌ Voice listening error: {e}")
            self.tab.voice_status_label.config(text="❌ Error", fg="#cc0000")
    
    def load_chat_dialog(self):
        """Show dialog to load a saved chat"""
        chats = self.chat_manager.list_chats()
        if not chats:
            self.tab.app.show_status("❌ No saved chats", 2000)
            return
        
        # Create a simple dialog with listbox
        dialog = tk.Toplevel(self.tab.app.root)
        dialog.title("Load Chat")
        dialog.geometry("300x300")
        dialog.transient(self.tab.app.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Select a chat to load:", font=("Arial", 10)).pack(pady=10)
        
        listbox = tk.Listbox(dialog, font=("Arial", 10), height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        for chat in chats:
            size = self.chat_manager.get_chat_size(chat)
            size_str = self.chat_manager.format_size(size)
            listbox.insert(tk.END, f"{chat} ({size_str})")
        
        def load_selected():
            selection = listbox.curselection()
            if selection:
                chat_name = chats[selection[0]]
                self.load_chat(chat_name)
                dialog.destroy()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Load", command=load_selected, bg="#0099cc", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#666666", fg="white", width=10).pack(side=tk.LEFT, padx=5)
    
    def load_chat(self, chat_name):
        """Load a specific chat"""
        try:
            messages = self.chat_manager.load_chat(chat_name)
            self.current_chat_name = chat_name
            
            # Update audio folder path
            self.audio_folder = self.chat_manager.get_audio_folder()
            
            # Load the messages
            self.message_history = messages
            self.timestamp_audio = {}
            self.timestamp_image = {}
            
            # Parse audio and image mappings
            image_count = 0
            for msg in messages:
                if msg.get("audio_file"):
                    self.timestamp_audio[msg.get("timestamp")] = msg.get("audio_file")
                if msg.get("image_file"):
                    self.timestamp_image[msg.get("timestamp")] = msg.get("image_file")
                    image_count += 1
            
            # Refresh display
            self.tab.chat_display.config(state=tk.NORMAL)
            self.tab.chat_display.delete("1.0", tk.END)
            self.tab.chat_display.config(state=tk.DISABLED)
            
            # Re-display messages
            for msg in messages:
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                if sender == "You":
                    tag = "user"
                elif sender == "Assistant" or sender == self.tab.server_display_name.split()[0]:
                    tag = "assistant"
                else:
                    tag = "system"
                
                self.tab.chat_display.config(state=tk.NORMAL)
                if sender == "Assistant" or sender == self.tab.server_display_name.split()[0]:
                    self.tab.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
                    self.tab.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                else:
                    self.tab.chat_display.insert(tk.END, f"({timestamp})", tag)
                    self.tab.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                self.tab.chat_display.config(state=tk.DISABLED)
            
            # Populate image viewer with saved images from this chat
            if image_count > 0 and hasattr(self.tab, 'image_viewer'):
                self.tab.image_viewer.images_list = []
                for msg in messages:
                    if msg.get("image_file"):
                        image_file = msg.get("image_file")
                        timestamp = msg.get("timestamp")
                        # Add to image viewer if file exists
                        from pathlib import Path
                        if Path(image_file).exists():
                            self.tab.image_viewer.images_list.append(image_file)
                            # Set timestamp for image alignment
                            if hasattr(self.tab.image_viewer, 'set_image_timestamp'):
                                self.tab.image_viewer.set_image_timestamp(image_file, timestamp)
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] Added image to viewer: {image_file}")
                
                # Update image viewer display
                if self.tab.image_viewer.images_list:
                    self.tab.image_viewer.current_image_index = 0
                    self.tab.image_viewer.display_images()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Populated image viewer with {len(self.tab.image_viewer.images_list)} images")
            
            self.tab.update_chat_info_display()
            self.tab.app.show_status(f"✅ Loaded chat: {chat_name}", 2000)
            
            # Save current chat name to settings (for next app startup)
            from settings_manager import load_settings, save_settings
            settings = load_settings()
            settings["llama_server_current_chat"] = chat_name
            save_settings(settings)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Saved current llama-server chat: {chat_name}")
        except Exception as e:
            print(f"Error loading chat: {e}")
            self.tab.app.show_status(f"❌ Error loading chat: {str(e)}", 2000)
    
    def new_chat_dialog(self):
        """Show dialog to create a new chat"""
        dialog = tk.Toplevel(self.tab.app.root)
        dialog.title("New Chat")
        dialog.geometry("350x150")
        dialog.transient(self.tab.app.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="Chat name:", font=("Arial", 10)).pack(pady=10)
        
        entry = tk.Entry(dialog, font=("Arial", 10), width=30)
        entry.pack(pady=5, padx=20)
        entry.insert(0, "new_chat")
        entry.select_range(0, tk.END)
        entry.focus()
        
        def create_new():
            chat_name = entry.get().strip()
            if not chat_name:
                self.tab.app.show_status("❌ Chat name cannot be empty", 2000)
                return
            
            # Sanitize name (remove special characters)
            chat_name = "".join(c for c in chat_name if c.isalnum() or c in "_-")
            
            try:
                self.chat_manager.new_chat(chat_name)
                self.current_chat_name = chat_name
                self.audio_folder = self.chat_manager.get_audio_folder()
                self.message_history = []
                self.timestamp_audio = {}
                
                self.tab.chat_display.config(state=tk.NORMAL)
                self.tab.chat_display.delete("1.0", tk.END)
                self.tab.chat_display.config(state=tk.DISABLED)
                
                self.tab.update_chat_info_display()
                self.tab.app.show_status(f"✅ Created new chat: {chat_name}", 2000)
                
                # Save current chat name to settings
                from settings_manager import load_settings, save_settings
                settings = load_settings()
                settings["llama_server_current_chat"] = chat_name
                save_settings(settings)
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Saved new llama-server chat as current: {chat_name}")
                
                dialog.destroy()
            except Exception as e:
                self.tab.app.show_status(f"❌ Error creating chat: {str(e)}", 2000)
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Create", command=create_new, bg="#00cc66", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#666666", fg="white", width=10).pack(side=tk.LEFT, padx=5)
    
    def save_chat_as_dialog(self):
        """Show dialog to rename/save chat as"""
        dialog = tk.Toplevel(self.tab.app.root)
        dialog.title("Save Chat As")
        dialog.geometry("350x150")
        dialog.transient(self.tab.app.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="New chat name:", font=("Arial", 10)).pack(pady=10)
        
        entry = tk.Entry(dialog, font=("Arial", 10), width=30)
        entry.pack(pady=5, padx=20)
        entry.insert(0, self.current_chat_name or "new_chat")
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save_as():
            new_name = entry.get().strip()
            if not new_name:
                self.tab.app.show_status("❌ Chat name cannot be empty", 2000)
                return
            
            # Sanitize name
            new_name = "".join(c for c in new_name if c.isalnum() or c in "_-")
            
            try:
                old_name = self.current_chat_name
                if old_name == new_name:
                    dialog.destroy()
                    return
                
                # Save current messages to new location
                self.chat_manager.save_chat(new_name, self.message_history)
                
                # Rename if it was already saved
                if old_name and old_name != new_name:
                    try:
                        self.chat_manager.rename_chat(old_name, new_name)
                    except:
                        pass
                
                self.current_chat_name = new_name
                self.tab.update_chat_info_display()
                self.tab.app.show_status(f"✅ Chat saved as: {new_name}", 2000)
                dialog.destroy()
            except Exception as e:
                self.tab.app.show_status(f"❌ Error saving chat: {str(e)}", 2000)
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Save", command=save_as, bg="#ff9900", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#666666", fg="white", width=10).pack(side=tk.LEFT, padx=5)
