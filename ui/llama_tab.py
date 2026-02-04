"""
LlamaChatTab - UI for Llama server chat interface
"""

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from pathlib import Path
from datetime import datetime
import threading
import re

from debug_config import DebugConfig
from ui.llama_chat_handler import LlamaChatHandler


class LlamaChatTab:
    """Llama server chat tab UI"""
    
    def __init__(self, parent, app):
        """Initialize Llama chat tab"""
        self.parent = parent
        self.app = app
        self.server_type = "llama-server"
        self.server_display_name = "Llama Chat"
        
        # Initialize handler for business logic
        self.handler = LlamaChatHandler(self)
        
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
        
        # Store scroll position for this tab (load from settings if available)
        self.scroll_position = saved_settings.get(f"{tab_prefix}scroll_position", 0)
        
        # Create UI
        self.create_widgets()
        
        # Load history
        self.handler.load_message_history()
        
        # Update TTS size display
        self.update_tts_size_display()
    
    # Delegate properties to handler for compatibility
    @property
    def message_history(self):
        """Delegate to handler"""
        return self.handler.message_history
    
    @message_history.setter
    def message_history(self, value):
        """Delegate to handler"""
        self.handler.message_history = value
    
    @property
    def timestamp_audio(self):
        """Delegate to handler"""
        return self.handler.timestamp_audio
    
    @timestamp_audio.setter
    def timestamp_audio(self, value):
        """Delegate to handler"""
        self.handler.timestamp_audio = value
    
    @property
    def audio_folder(self):
        """Delegate to handler"""
        return self.handler.audio_folder
    
    def save_message_history(self):
        """Delegate to handler"""
        return self.handler.save_message_history()
    
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
            fg="#cc6600"
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
            command=self.load_chat_dialog,
            font=("Arial", 9),
            bg="#0099cc",
            fg="white",
            width=6
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            settings_frame,
            text="New",
            command=self.new_chat_dialog,
            font=("Arial", 9),
            bg="#00cc66",
            fg="white",
            width=6
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            settings_frame,
            text="Save As",
            command=self.save_chat_as_dialog,
            font=("Arial", 9),
            bg="#ff9900",
            fg="white",
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # Separator
        separator = tk.Frame(self.parent, height=2, bg="#cccccc")
        separator.pack(fill=tk.X, padx=10, pady=5)
        
        # Chat display area
        chat_frame = tk.Frame(self.parent, bg="#f0f0f0")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Label(chat_frame, text="Chat History:", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(anchor="w")
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            height=20,
            width=100,
            bg="white",
            fg="#333333",
            font=("Courier", 11),
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Configure text tags
        self.chat_display.tag_config("user", foreground="#0066cc", font=("Courier", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#1a1a1a", font=("Courier", 11))
        self.chat_display.tag_config("system", foreground="#cc6600", font=("Courier", 10, "italic"))
        self.chat_display.tag_config("error", foreground="#cc0000", font=("Courier", 11))
        self.chat_display.tag_config("timestamp", foreground="#0066cc", underline=True, font=("Courier", 11, "bold"))
        
        # Bind mouse events
        self.chat_display.bind("<Button-1>", self._on_chat_click)
        
        # Input area
        input_frame = tk.Frame(self.parent, bg="#f0f0f0")
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
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
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # Bind Return keys
        self.input_text.bind("<Return>", self.handle_return_key)
        self.input_text.bind("<Control-Return>", lambda e: self.send_message())
        
        # Buttons frame
        button_frame = tk.Frame(self.parent, bg="#f0f0f0")
        button_frame.pack(fill=tk.X, padx=10, pady=8)
        
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
        
        tk.Button(
            settings_frame,
            text="Clear Chat & TTS",
            command=self.clear_chat,
            font=("Arial", 9),
            bg="#ff6600",
            fg="white",
            width=15
        ).pack(side=tk.LEFT, padx=2)
        
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
        
        # Zoom to image area checkbox
        self.align_image_text_checkbox = tk.Checkbutton(
            button_frame,
            text="Zoom to Image Area",
            variable=self.align_image_text_var,
            bg="#f0f0f0",
            font=("Arial", 9),
            command=self.save_tab_settings
        )
        self.align_image_text_checkbox.pack(side=tk.LEFT, padx=2)
    
    def connect_to_server(self):
        """Connect to the server"""
        self.app.server_type_var.set(self.server_type)
        self.app.test_connection(chat_window=self)
    
    def toggle_voice_listening(self):
        """Toggle voice listening"""
        if self.stt_enabled_var.get():
            self.handler.start_voice_listening()
        else:
            self.handler.stop_voice_listening()
    
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
    
    def clear_chat(self):
        """Clear chat history and TTS audio files for current chat only"""
        response = messagebox.askyesno("Clear Chat & TTS", f"Clear {self.server_display_name} chat history and TTS audio files?")
        if response:
            from pathlib import Path
            
            # Clear chat display
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # Clear message history
            self.handler.message_history = []
            self.handler.timestamp_audio = {}
            self.handler.save_message_history()
            
            # Clear TTS audio files for current chat only
            try:
                audio_folder = self.handler.audio_folder
                if audio_folder.exists():
                    for audio_file in audio_folder.glob("*.wav"):
                        audio_file.unlink()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Cleared TTS files in {audio_folder}")
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
    
    def _on_chat_click(self, event):
        """Handle timestamp click to play audio or display image"""
        pos = self.chat_display.index(f"@{event.x},{event.y}")
        line_start = self.chat_display.index(f"{pos} linestart")
        line_end = self.chat_display.index(f"{pos} lineend")
        line_content = self.chat_display.get(line_start, line_end)
        
        timestamp_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line_content)
        if timestamp_match:
            timestamp = timestamp_match.group(1)
            self.handler.play_audio_for_timestamp(timestamp)
            
            # Also check for image and display it
            if timestamp in self.handler.timestamp_image:
                image_file = self.handler.timestamp_image[timestamp]
                if Path(image_file).exists():
                    if hasattr(self, 'image_viewer'):
                        self.image_viewer.display_image_by_path(image_file)
                        print(f"✓ Displaying image for timestamp: {timestamp}")
                else:
                    print(f"❌ Image file not found: {image_file}")
    
    def check_responses(self):
        """Check response queue"""
        self.handler.check_responses()
    
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
    
    def update_chat_info_display(self):
        """Update chat info display"""
        if hasattr(self.handler, 'chat_manager') and self.handler.chat_manager:
            chat_name = self.handler.chat_manager.current_chat_name
            size_bytes = self.handler.chat_manager.get_chat_size(chat_name)
            size_str = self.handler.chat_manager.format_size(size_bytes)
            self.chat_info_label.config(text=f"📄 {chat_name}.json ({size_str})")
    
    def update_tts_size_display(self):
        """Update TTS size display - shows total of all TTS files"""
        if hasattr(self.handler, 'chat_manager') and self.handler.chat_manager:
            total_size = self.handler.chat_manager.get_all_tts_size()
            size_str = self.handler.chat_manager.format_size(total_size)
            self.tts_size_label.config(text=f"({size_str})")
