"""
OllamaChatTab - UI for Ollama chat interface
"""

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from pathlib import Path
from datetime import datetime
import threading
import re

from debug_config import DebugConfig
from ui.ollama_chat_handler import OllamaChatHandler


class OllamaChatTab:
    """Ollama chat tab UI"""
    
    def __init__(self, parent, app):
        """Initialize Ollama chat tab"""
        self.parent = parent
        self.app = app
        self.server_type = "ollama"
        self.server_display_name = "Ollama Chat"
        
        # Initialize handler for business logic
        self.handler = OllamaChatHandler(self)
        
        # Load settings
        from settings_manager import load_settings
        saved_settings = load_settings()
        
        tab_prefix = f"{self.server_type}_"
        self.return_to_send_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}return_to_send", False))
        self.tts_enabled_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}tts_enabled", False))
        self.stt_enabled_var = tk.BooleanVar(value=False)
        self.clean_text_for_tts_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}clean_text_for_tts", True))
        self.image_gen_enabled_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}image_gen_enabled", False))
        self.align_image_text_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}align_image_text", False))
        
        # Store scroll position for this tab
        self.scroll_position = saved_settings.get(f"{tab_prefix}scroll_position", 0)
        
        # Create UI
        self.create_widgets()
        
        # Load history
        self.handler.load_message_history()
        
        # Update TTS size display
        self.update_tts_size_display()
        
        # Add voice_listening attribute for compatibility
        self.voice_listening = False
    
    # Delegate properties to handler
    @property
    def message_history(self):
        return self.handler.message_history
    
    @message_history.setter
    def message_history(self, value):
        self.handler.message_history = value
    
    @property
    def timestamp_audio(self):
        return self.handler.timestamp_audio
    
    @timestamp_audio.setter
    def timestamp_audio(self, value):
        self.handler.timestamp_audio = value
    
    @property
    def audio_folder(self):
        return self.handler.audio_folder
    
    def save_message_history(self):
        return self.handler.save_message_history()
    
    def update_chat_info_display(self):
        """Update the chat info label"""
        if hasattr(self.handler, 'chat_manager') and self.handler.chat_manager:
            chat_name = self.handler.chat_manager.current_chat_name
            size_bytes = self.handler.chat_manager.get_chat_size(chat_name)
            size_str = self.handler.chat_manager.format_size(size_bytes)
            self.chat_info_label.config(text=f"📄 {chat_name}.json ({size_str})")
    
    def update_tts_size_display(self):
        """Update TTS size display"""
        if hasattr(self.handler, 'chat_manager') and self.handler.chat_manager:
            total_size = self.handler.chat_manager.get_all_tts_size()
            size_str = self.handler.chat_manager.format_size(total_size)
            self.tts_size_label.config(text=f"({size_str})")
    
    def save_scroll_position(self):
        """Save current scroll position"""
        try:
            self.scroll_position = self.chat_display.yview()[0]
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Saved scroll position: {self.scroll_position}")
        except:
            pass
    
    def restore_scroll_position(self):
        """Restore saved scroll position"""
        try:
            self.chat_display.yview_moveto(self.scroll_position)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Restored scroll position: {self.scroll_position}")
        except:
            pass
    
    def load_chat_dialog(self):
        """Delegate to handler"""
        return self.handler.load_chat_dialog()
    
    def load_chat(self, chat_name):
        """Delegate to handler"""
        return self.handler.load_chat(chat_name)
    
    def new_chat_dialog(self):
        """Delegate to handler"""
        return self.handler.new_chat_dialog()
    
    def save_chat_as_dialog(self):
        """Delegate to handler"""
        return self.handler.save_chat_as_dialog()
    
    def create_widgets(self):
        """Create chat interface widgets"""
        
        # Top frame for server settings
        settings_frame = tk.Frame(self.parent, bg="#f0f0f0")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Server label
        server_label = tk.Label(
            settings_frame,
            text=f"{self.server_display_name}",
            bg="#f0f0f0",
            font=("Arial", 9, "bold"),
            fg="#0066cc"
        )
        server_label.pack(side=tk.LEFT, padx=10)
        
        # Connect button
        tk.Button(
            settings_frame,
            text="Connect",
            command=self.connect_to_server,
            font=("Arial", 9),
            bg="#0066cc",
            fg="white"
        ).pack(side=tk.LEFT, padx=5)
        
        # Connection status label
        self.connection_status_label = tk.Label(
            settings_frame,
            text="⚪ Not connected",
            bg="#f0f0f0",
            fg="#666666",
            font=("Arial", 9)
        )
        self.connection_status_label.pack(side=tk.LEFT, padx=10)
        
        # Add spacer to push chat controls to the right
        spacer = tk.Frame(settings_frame, bg="#f0f0f0")
        spacer.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Chat info and controls (right side)
        self.chat_info_label = tk.Label(
            settings_frame,
            text="📄 default.json (0 B)",
            bg="#f0f0f0",
            fg="#333333",
            font=("Arial", 9)
        )
        self.chat_info_label.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            settings_frame,
            text="Load",
            command=self.handler.load_chat_dialog,
            font=("Arial", 9),
            bg="#0099cc",
            fg="white",
            width=6
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            settings_frame,
            text="New",
            command=self.handler.new_chat_dialog,
            font=("Arial", 9),
            bg="#00cc66",
            fg="white",
            width=6
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            settings_frame,
            text="Save As",
            command=self.handler.save_chat_as_dialog,
            font=("Arial", 9),
            bg="#ff9900",
            fg="white",
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            settings_frame,
            text="Clear Chat & TTS",
            command=self.clear_chat,
            font=("Arial", 9),
            bg="#ff6600",
            fg="white",
            width=15
        ).pack(side=tk.LEFT, padx=2)
        
        # Model selection frame
        model_frame = tk.Frame(self.parent, bg="#f0f0f0")
        model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.model_label = tk.Label(model_frame, text="Model:", bg="#f0f0f0", font=("Arial", 9))
        self.model_label.pack(side=tk.LEFT)
        self.server_model_combo = ttk.Combobox(
            model_frame,
            state="readonly",
            width=40,
            font=("Arial", 9)
        )
        self.server_model_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.server_model_combo['values'] = ["(connect to see models)"]
        self.server_model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)
        
        # Separator
        separator = tk.Frame(self.parent, height=2, bg="#cccccc")
        separator.pack(fill=tk.X, padx=10, pady=5)
        
        # Split view container (chat + images side by side)
        split_container = tk.Frame(self.parent, bg="#f0f0f0")
        split_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Configure grid columns: 60% chat, 40% images
        split_container.grid_columnconfigure(0, weight=60)  # Chat column
        split_container.grid_columnconfigure(1, weight=40)  # Image column
        split_container.grid_rowconfigure(0, weight=1)
        
        # LEFT SIDE: Chat display area (60%)
        chat_frame = tk.Frame(split_container, bg="#f0f0f0")
        chat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        tk.Label(chat_frame, text="Chat History:", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(anchor="w")
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            height=20,
            width=60,
            bg="white",
            fg="#333333",
            font=("Courier", 11),
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Input area - MOVED INSIDE CHAT FRAME so it matches width
        input_frame = tk.Frame(chat_frame, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, pady=5)
        
        # RIGHT SIDE: Image viewer (40%, responsive)
        image_frame = tk.Frame(split_container, bg="#f0f0f0")
        image_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Import image viewer
        from ui.image_viewer import ImageViewerWidget
        self.image_viewer = ImageViewerWidget(
            image_frame, 
            width=250, 
            height=600, 
            on_image_changed=self.on_image_changed,
            zoom_mode=self.align_image_text_var.get()
        )
        
        # Configure text tags
        self.chat_display.tag_config("user", foreground="#0066cc", font=("Courier", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#1a1a1a", font=("Courier", 11))
        self.chat_display.tag_config("system", foreground="#cc6600", font=("Courier", 10, "italic"))
        self.chat_display.tag_config("error", foreground="#cc0000", font=("Courier", 11))
        self.chat_display.tag_config("timestamp", foreground="#0066cc", underline=True, font=("Courier", 11, "bold"))
        
        # Bind mouse events for timestamp click
        self.chat_display.bind("<Button-1>", self._on_chat_click)
        
        # Message label and checkboxes
        label_frame = tk.Frame(input_frame, bg="#f0f0f0")
        label_frame.pack(anchor="w")
        
        tk.Label(label_frame, text="Your message:", bg="#f0f0f0").pack(side=tk.LEFT)
        
        tk.Checkbutton(
            label_frame,
            text="Send on Return",
            variable=self.return_to_send_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        ).pack(side=tk.LEFT, padx=20)
        
        # STT checkbox
        self.stt_checkbox = tk.Checkbutton(
            label_frame,
            text="🎤 Speech Input",
            variable=self.stt_enabled_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.toggle_voice_listening
        )
        self.stt_checkbox.pack(side=tk.LEFT, padx=5)
        
        # Voice status label
        self.voice_status_label = tk.Label(label_frame, text="", bg="#f0f0f0", fg="#ff9900", font=("Arial", 9))
        self.voice_status_label.pack(side=tk.LEFT, padx=5)
        
        # TTS checkbox
        self.tts_checkbox = tk.Checkbutton(
            label_frame,
            text="🔊 Speech Output",
            variable=self.tts_enabled_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        )
        self.tts_checkbox.pack(side=tk.LEFT, padx=5)
        
        # TTS size label
        self.tts_size_label = tk.Label(
            label_frame,
            text="(0 MB)",
            bg="#f0f0f0",
            fg="#666666",
            font=("Arial", 9)
        )
        self.tts_size_label.pack(side=tk.LEFT, padx=2)
        
        # TTS interrupt checkbox
        tk.Checkbutton(
            label_frame,
            text="⏸ Cut off TTS",
            variable=self.app.tts_interrupt_var,
            bg="#f0f0f0",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)
        
        # Clean text for TTS checkbox
        tk.Checkbutton(
            label_frame,
            text="🧹 Clean text for TTS",
            variable=self.clean_text_for_tts_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        ).pack(side=tk.LEFT, padx=5)
        
        # Text input field
        text_frame = tk.Frame(input_frame, bg="white", relief=tk.SUNKEN, bd=1)
        text_frame.pack(fill=tk.BOTH, pady=5)
        
        self.input_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            height=4,
            width=100,
            bg="white",
            fg="#333333",
            font=("Courier", 11)
        )
        self.input_text.pack(fill=tk.X)
        
        # Bind Return keys
        self.input_text.bind("<Return>", self.handle_return_key)
        self.input_text.bind("<Control-Return>", lambda e: self.send_message())
        
        # Buttons frame - ALSO INSIDE CHAT FRAME for consistent width
        button_frame = tk.Frame(chat_frame, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, pady=8)
        
        tk.Button(
            button_frame,
            text="Send (Ctrl+Enter)",
            command=self.send_message,
            bg="#0066cc",
            fg="white",
            width=20,
            font=("Arial", 11, "bold"),
            padx=10,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(
            button_frame,
            text="Stop",
            command=self.stop_generation,
            bg="#ff6600",
            fg="white",
            width=20,
            font=("Arial", 11, "bold"),
            padx=10,
            pady=8,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Stop TTS button
        self.stop_tts_button = tk.Button(
            button_frame,
            text="Stop TTS",
            command=self.stop_tts,
            bg="#ff0000",
            fg="white",
            width=20,
            font=("Arial", 11, "bold"),
            padx=10,
            pady=8,
            state=tk.NORMAL
        )
        self.stop_tts_button.pack(side=tk.LEFT, padx=5)
        
        # Image generation controls
        self.image_gen_checkbox = tk.Checkbutton(
            button_frame,
            text="🎨 Generate Images",
            variable=self.image_gen_enabled_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        )
        self.image_gen_checkbox.pack(side=tk.LEFT, padx=5)
        
        # Align text and image checkbox (renamed to Zoom to Image Area)
        self.align_image_text_checkbox = tk.Checkbutton(
            button_frame,
            text="Zoom to Image Area",
            variable=self.align_image_text_var,
            bg="#f0f0f0",
            font=("Arial", 9),
            command=self.on_zoom_mode_changed
        )
        self.align_image_text_checkbox.pack(side=tk.LEFT, padx=2)
    
    def on_image_changed(self, timestamp):
        """Callback when image changes (for text-image alignment)"""
        if self.align_image_text_var.get() and timestamp:
            # Find and scroll to the message with this timestamp
            try:
                # Search through message history for this timestamp
                for msg in self.message_history:
                    if msg.get("timestamp") == timestamp:
                        # Find the text position for this message
                        # Use the text tag search to find the timestamp in the display
                        search_text = f"[{timestamp}]"
                        pos = self.chat_display.search(search_text, "1.0", tk.END)
                        if pos:
                            # Scroll to show this position
                            self.chat_display.see(pos)
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] Scrolled chat to timestamp: {timestamp}")
                        break
            except Exception as e:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Error aligning text with image: {e}")
    
    def on_zoom_mode_changed(self):
        """Handle zoom mode checkbox change"""
        zoom_enabled = self.align_image_text_var.get()
        if hasattr(self, 'image_viewer'):
            self.image_viewer.set_zoom_mode(zoom_enabled)
        self.save_tab_settings()
    
    def connect_to_server(self):
        """Connect to the server"""
        self.app.server_type_var.set(self.server_type)
        self.app.test_connection(chat_window=self)
    
    def on_model_selected(self, event=None):
        """Save model selection when combo is changed"""
        selected_model = self.server_model_combo.get()
        if selected_model and selected_model != "(connect to see models)":
            self.app.server_model_var.set(selected_model)
            from settings_manager import load_settings, save_settings
            settings = load_settings()
            settings["server_model"] = selected_model
            save_settings(settings)
    
    def toggle_voice_listening(self):
        """Toggle voice listening"""
        if self.stt_enabled_var.get():
            self.start_voice_listening()
        else:
            self.stop_voice_listening()
    
    def handle_return_key(self, event):
        """Handle Return key"""
        if self.return_to_send_var.get():
            self.send_message()
            return "break"
        return None
    
    def send_message(self):
        """Send message to server"""
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
        
        self.input_text.config(state=tk.NORMAL)
        self.input_text.delete("1.0", tk.END)
        
        self.handler.add_chat_message("You", message, "user")
        
        self.app.server_type_var.set(self.server_type)
        
        server_status_text = self.app.server_status_label.cget("text")
        if "not connected" in server_status_text:
            self.connection_status_label.config(
                text="❌ Not connected",
                fg="#cc0000"
            )
            return
        
        from settings_manager import load_settings, save_settings
        settings = load_settings()
        settings["server_type"] = self.server_type
        settings["server_model"] = self.app.server_model_var.get()
        save_settings(settings)
        
        thread = threading.Thread(
            target=self.handler.get_server_response,
            args=(message,),
            daemon=True
        )
        thread.start()
    
    def _on_chat_click(self, event):
        """Handle timestamp click"""
        pos = self.chat_display.index(f"@{event.x},{event.y}")
        line_start = self.chat_display.index(f"{pos} linestart")
        line_end = self.chat_display.index(f"{pos} lineend")
        line_content = self.chat_display.get(line_start, line_end)
        
        import re
        timestamp_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line_content)
        if not timestamp_match:
            return
        
        timestamp = timestamp_match.group(1)
        
        # Check for audio first
        if timestamp in self.handler.timestamp_audio:
            audio_file = self.handler.timestamp_audio[timestamp]
            if Path(audio_file).exists():
                import pygame
                try:
                    pygame.mixer.music.load(audio_file)
                    pygame.mixer.music.play()
                except Exception as e:
                    print(f"❌ Error playing audio: {e}")
            else:
                print(f"❌ Audio file not found: {audio_file}")
        
        # Check for image and display it
        if timestamp in self.handler.timestamp_image:
            image_file = self.handler.timestamp_image[timestamp]
            if Path(image_file).exists():
                self.image_viewer.display_image_by_path(image_file)
                print(f"✓ Displaying image for timestamp: {timestamp}")
            else:
                print(f"❌ Image file not found: {image_file}")
        
        if timestamp not in self.handler.timestamp_audio and timestamp not in self.handler.timestamp_image:
            print(f"❌ No audio or image found for timestamp: {timestamp}")
    
    def clear_chat(self):
        """Clear chat history and TTS audio files for current chat only"""
        response = messagebox.askyesno("Clear Chat & TTS", f"Clear {self.server_display_name} chat history and TTS audio files?")
        if response:
            # Clear chat display
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # Clear handler state
            self.handler.message_history = []
            self.handler.timestamp_audio = {}
            self.handler.save_message_history()
            
            # Clear TTS audio files for current chat only
            try:
                if self.handler.audio_folder.exists():
                    for audio_file in self.handler.audio_folder.glob("*.wav"):
                        audio_file.unlink()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Cleared TTS files in {self.handler.audio_folder}")
            except Exception as e:
                print(f"Error clearing TTS files: {e}")
            
            self.app.show_status(f"✅ Cleared chat and TTS audio", 2000)
    
    def stop_generation(self):
        """Stop generation"""
        self.app.stop_generation = True
        self.app.tts_interrupt = True
        self.stop_button.config(state=tk.DISABLED)
    
    def stop_tts(self):
        """Stop TTS playback"""
        try:
            if self.app.current_tts:
                try:
                    self.app.current_tts.stop()
                except:
                    pass
                self.app.current_tts = None
            
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.stop()
                pygame.mixer.stop()
            except:
                pass
            
            self.app.tts_is_playing = False
            self.app.tts_queue = []
            
            self.app.show_status("✅ TTS stopped", 2000)
        except Exception as e:
            print(f"Error stopping TTS: {e}")
    
    def save_tab_settings(self):
        """Save tab-specific settings"""
        from settings_manager import load_settings, save_settings
        
        settings = load_settings()
        tab_prefix = f"{self.server_type}_"
        
        settings[f"{tab_prefix}return_to_send"] = self.return_to_send_var.get()
        settings[f"{tab_prefix}tts_enabled"] = self.tts_enabled_var.get()
        settings[f"{tab_prefix}clean_text_for_tts"] = self.clean_text_for_tts_var.get()
        settings[f"{tab_prefix}image_gen_enabled"] = self.image_gen_enabled_var.get()
        settings[f"{tab_prefix}align_image_text"] = self.align_image_text_var.get()
        
        save_settings(settings)
    
    def start_voice_listening(self):
        """Start listening for voice input"""
        try:
            from speech_to_text import SpeechToText
            import numpy as np
            import os
            
            os.environ['WHISPER_TEMPERATURE'] = str(self.app.stt_temperature_var.get())
            os.environ['WHISPER_RMS_THRESHOLD'] = str(self.app.stt_rms_threshold_var.get())
            os.environ['WHISPER_NO_SPEECH_THRESHOLD'] = str(self.app.stt_no_speech_threshold_var.get())
            os.environ['WHISPER_LOG_PROB_THRESHOLD'] = str(self.app.stt_log_prob_threshold_var.get())
            
            self.voice_listening = True
            self.app.set_mic_status(True, self.server_type)
            
            self.voice_status_label.config(text="🎤 Listening...", fg="#ff9900")
            self.voice_status_label.update()
            
            def listen_thread():
                try:
                    if hasattr(self.app, 'stt_device_var'):
                        device_str = self.app.stt_device_var.get()
                        device_id = int(device_str.split(":")[0]) if device_str else None
                    else:
                        device_id = None
                    
                    model = self.app.stt_model_var.get()
                    compute_device = self.app.stt_compute_device_var.get()
                    
                    stt = SpeechToText(model, device=device_id, compute_device=compute_device)
                    self._record_with_silence_detection(stt, device_id)
                    
                except Exception as e:
                    print(f"Voice listening error: {e}")
                    self.voice_status_label.config(text="❌ Error", fg="#cc0000")
                finally:
                    self.voice_listening = False
                    if not self.stt_enabled_var.get():
                        self.voice_status_label.config(text="", fg="#ff9900")
            
            thread = threading.Thread(target=listen_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            print(f"Error starting voice listening: {e}")
            self.voice_status_label.config(text="❌ Error", fg="#cc0000")
            self.stt_enabled_var.set(False)
    
    def stop_voice_listening(self):
        """Stop voice listening"""
        self.voice_listening = False
        self.app.set_mic_status(False, self.server_type)
        self.voice_status_label.config(text="", fg="#ff9900")
        print(f"\nVoice listening stopped on {self.server_display_name}.\n")
        
        # Unload whisper model from memory
        from voice_input_manager import VoiceInputManager
        voice_manager = VoiceInputManager()
        voice_manager.set_active_tab(None)  # This will call unload_whisper_model()
    
    def _record_with_silence_detection(self, stt, device_id):
        """Record audio and detect silence to trigger transcription"""
        import numpy as np
        import sounddevice as sd
        import time
        
        try:
            supported_rates = stt._get_supported_sample_rates(device_id)
            sample_rate = supported_rates[0] if supported_rates else 16000
            stt.sample_rate = sample_rate
            
            while self.voice_listening and self.stt_enabled_var.get():
                chunk_duration = 0.1
                chunk_samples = int(sample_rate * chunk_duration)
                
                speech_start_chunks = int(self.app.stt_speech_start_delay_var.get() / (chunk_duration * 1000))
                silence_end_chunks = int(self.app.stt_silence_end_delay_var.get() / (chunk_duration * 1000))
                
                consecutive_silence = 0
                consecutive_speech = 0
                audio_chunks = []
                speech_detected = False
                pre_speech_buffer = []
                buffer_size = 3
                
                while self.voice_listening and self.stt_enabled_var.get():
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
                                self.voice_status_label.config(text="🎤 Listening... [SPEECH]", fg="#009900")
                                self.app.root.update()
                            
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
                                
                                if consecutive_silence >= silence_end_chunks:
                                    break
                        
                        if speech_detected and len(audio_chunks) > 600:
                            break
                    except Exception as e:
                        print(f"Exception in recording loop: {e}")
                        break
                
                if audio_chunks and self.stt_enabled_var.get():
                    stt.audio_data = np.concatenate(audio_chunks).flatten()
                    
                    if len(stt.audio_data) > 0:
                        self.voice_status_label.config(text="🎤 Transcribing...", fg="#0066cc")
                        self.app.root.update()
                        
                        language = self.app.stt_language_var.get()
                        result = stt.transcribe(language=language)
                        
                        text = result.get('text', '').strip() if isinstance(result, dict) else (result.strip() if result else '')
                        
                        if text and len(text) > 0:
                            print(f"Transcription: {text}")
                            self.voice_status_label.config(text="✓ Done! Listening again...", fg="#009900")
                            self.app.root.update()
                            
                            self.input_text.insert(tk.END, text + " ")
                            
                            if self.return_to_send_var.get():
                                self.app.root.after(500, lambda: self.send_message())
                                time.sleep(1)
                        else:
                            self.voice_status_label.config(text="🎤 Listening... (no speech)", fg="#ff9900")
                            self.app.root.update()
                else:
                    break
                
        except Exception as e:
            print(f"Voice listening error: {e}")
            self.voice_status_label.config(text="❌ Error", fg="#cc0000")
    
    def load_message_history(self):
        """Load message history from handler"""
        return self.handler.load_message_history()
    
    def check_responses(self):
        """Check for responses from handler"""
        self.handler.check_responses()
