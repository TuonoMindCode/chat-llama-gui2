"""
BaseChatTab - Abstract base class for chat tabs
"""

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, simpledialog
import json
from pathlib import Path
from datetime import datetime
import queue
import threading

from debug_config import DebugConfig
from chat_manager import ChatManager


class BaseChatTab:
    """Base class for chat interfaces (Ollama and Llama)"""
    
    def __init__(self, parent, app, server_type):
        """
        Initialize BaseChatTab
        
        Args:
            parent: Parent frame for the chat tab
            app: Reference to the main LlamaChatGUI instance
            server_type: "ollama" or "llama-server"
        """
        self.parent = parent
        self.app = app
        self.server_type = server_type
        
        # Each tab has its own response queue to prevent responses from mixing between tabs
        self.response_queue = queue.Queue()
        
        # Initialize chat manager
        self.chat_manager = ChatManager(self.server_type)
        self.current_chat_name = self.chat_manager.get_default_chat().name
        
        # Set up file paths based on server type
        self._setup_paths()
        
        # Chat state
        self.message_history = []
        self.timestamp_audio = {}
        self.streaming_text = ""
        self.streaming_message_start_index = None
        self.voice_listening = False  # Track if this tab is listening
        
        # Store scroll position for this tab
        self.scroll_position = 0
        
        # Per-tab settings variables (loaded from settings)
        from settings_manager import load_settings
        saved_settings = load_settings()
        
        # Create tab-specific settings keys
        tab_prefix = f"{self.server_type}_"
        self.return_to_send_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}return_to_send", False))
        self.tts_enabled_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}tts_enabled", False))
        self.stt_enabled_var = tk.BooleanVar(value=False)
        self.clean_text_for_tts_var = tk.BooleanVar(value=saved_settings.get(f"{tab_prefix}clean_text_for_tts", True))
        
        # Create widgets
        self.create_widgets()
        
        # Load history
        self.load_message_history()
        
        # Update TTS size display
        self.update_tts_size_display()
    
    def _setup_paths(self):
        """Setup file paths based on server type"""
        if self.server_type == "ollama":
            self.server_display_name = "Ollama Chat"
        else:
            self.server_display_name = "Llama Chat"
        
        # Audio folder is now managed by chat_manager per chat
        self.audio_folder = self.chat_manager.get_audio_folder()
    
    def create_widgets(self):
        """Create the chat interface widgets"""
        
        # Top frame for server settings
        settings_frame = tk.Frame(self.parent, bg="#f0f0f0")
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Server label
        server_label = tk.Label(
            settings_frame,
            text=f"{self.server_display_name}",
            bg="#f0f0f0",
            font=("Arial", 9, "bold"),
            fg="#0066cc" if self.server_type == "ollama" else "#cc6600"
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
        
        # Model selection frame (hidden for llama-server since it runs one model at a time)
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
        # Bind selection change to save the model choice
        self.server_model_combo.bind("<<ComboboxSelected>>", self.on_model_selected)
        
        # Hide model selector for llama-server (it runs one model at a time)
        if self.server_type == "llama-server":
            self.model_label.pack_forget()
            self.server_model_combo.pack_forget()
        
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
        label_frame.pack(anchor="w", padx=5, pady=5)
        
        tk.Label(label_frame, text="Your message:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        
        tk.Checkbutton(
            label_frame,
            text="Send on Return",
            variable=self.return_to_send_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        ).pack(side=tk.LEFT, padx=15)
        
        # STT checkbox
        self.stt_enabled_var = tk.BooleanVar(value=False)
        self.stt_checkbox = tk.Checkbutton(
            label_frame,
            text="🎤 Speech Input",
            variable=self.stt_enabled_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.toggle_voice_listening
        )
        self.stt_checkbox.pack(side=tk.LEFT, padx=10)
        
        # Voice status label
        self.voice_status_label = tk.Label(label_frame, text="", bg="#f0f0f0", fg="#ff9900", font=("Arial", 9))
        self.voice_status_label.pack(side=tk.LEFT, padx=8)
        
        # TTS checkbox
        self.tts_checkbox = tk.Checkbutton(
            label_frame,
            text="🔊 Speech Output",
            variable=self.tts_enabled_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        )
        self.tts_checkbox.pack(side=tk.LEFT, padx=10)
        
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
        ).pack(side=tk.LEFT, padx=10)
        
        # Clean text for TTS checkbox
        tk.Checkbutton(
            label_frame,
            text="🧹 Clean text for TTS",
            variable=self.clean_text_for_tts_var,
            bg="#f0f0f0",
            font=("Arial", 10),
            command=self.save_tab_settings
        ).pack(side=tk.LEFT, padx=10)
        
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
    
    def connect_to_server(self):
        """Connect to the server"""
        self.app.server_type_var.set(self.server_type)
        self.app.test_connection(chat_window=self)
    
    def on_model_selected(self, event=None):
        """Save model selection when combo is changed"""
        selected_model = self.server_model_combo.get()
        if selected_model and selected_model != "(connect to see models)":
            self.app.server_model_var.set(selected_model)
            # Save to settings
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
        
        self.add_chat_message("You", message, "user")
        
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
            target=self.get_server_response,
            args=(message,),
            daemon=True
        )
        thread.start()
    
    def get_server_response(self, message):
        """Get response from server"""
        try:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] get_server_response called for {self.server_type} with message: {message[:50]}")
            if not self.app.server_client:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] No server client for {self.server_type}")
                self.response_queue.put(("error", "Server not connected"))
                return
            
            self.app.stop_generation = False
            
            # Get appropriate system prompt
            if self.server_type == "llama-server":
                system_prompt = self.app.system_prompt_llama
            else:  # ollama
                system_prompt = self.app.system_prompt
            
            formatted_prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"
            model = self.app.server_model_var.get()
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Using model: {model}")
            
            temperature = self.app.temperature_var.get() if hasattr(self.app, 'temperature_var') else 0.7
            top_p = self.app.top_p_var.get() if hasattr(self.app, 'top_p_var') else 0.9
            top_k = self.app.top_k_var.get() if hasattr(self.app, 'top_k_var') else 40
            n_predict = self.app.n_predict_var.get() if hasattr(self.app, 'n_predict_var') else -1
            
            if self.app.streaming_enabled_var.get():
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Using streaming for {self.server_type}")
                try:
                    # Get timeout settings
                    timeout = None if (hasattr(self.app, 'request_infinite_timeout') and self.app.request_infinite_timeout) else getattr(self.app, 'request_timeout', 60)
                    keep_alive = getattr(self.app, 'request_timeout', 120)  # Use request_timeout for keep_alive as well
                    
                    self.response_queue.put(("stream_start",))
                    for chunk in self.app.server_client.generate_stream(
                        formatted_prompt,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        n_predict=n_predict,
                        timeout=timeout,
                        keep_alive=keep_alive
                    ):
                        if self.app.stop_generation:
                            self.response_queue.put(("stream_interrupted",))
                            return
                        self.response_queue.put(("stream_chunk", chunk))
                    self.response_queue.put(("stream_end",))
                except Exception as e:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Streaming error for {self.server_type}: {e}")
                    self.response_queue.put(("error", f"Streaming error: {str(e)}"))
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Using non-streaming for {self.server_type}")
                # Get timeout settings
                timeout = None if (hasattr(self.app, 'request_infinite_timeout') and self.app.request_infinite_timeout) else getattr(self.app, 'request_timeout', 60)
                keep_alive = getattr(self.app, 'request_timeout', 120)  # Use request_timeout for keep_alive as well
                
                generated_text = self.app.server_client.generate(
                    formatted_prompt,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    n_predict=n_predict,
                    timeout=timeout,
                    keep_alive=keep_alive
                )
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Generated text from {self.server_type}: {generated_text[:100]}")
                
                lines = generated_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.strip().startswith("User:"):
                        break
                    cleaned_lines.append(line)
                
                generated_text = '\n'.join(cleaned_lines).strip()
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Putting success message in queue for {self.server_type}")
                self.response_queue.put(("success", generated_text))
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Exception in get_server_response for {self.server_type}: {e}")
            self.response_queue.put(("error", f"Error: {str(e)}"))
    
    def add_chat_message(self, sender, message, tag="assistant"):
        """Add message to chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        display_label = sender
        if sender == "Assistant":
            display_label = self.server_display_name.split()[0]
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # If this is a user message, remove the placeholder that was added after assistant response
        if sender == "You":
            chat_content = self.chat_display.get("1.0", tk.END)
            # Remove placeholder pattern: (HH:MM:SS) You: (may have trailing whitespace/newlines)
            import re
            # Try to match the placeholder anywhere near the end
            match = re.search(r'\(\d{2}:\d{2}:\d{2}\) You: [\s]*$', chat_content)
            if match:
                # Found placeholder, remove it by reconstructing without it
                start_pos = len(chat_content) - len(match.group())
                self.chat_display.delete("1.0", tk.END)
                # Keep the content up to the placeholder
                content_before = chat_content[:start_pos].rstrip() + "\n\n"
                self.chat_display.insert("1.0", content_before)
        
        if sender == "Assistant":
            self.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
            self.chat_display.insert(tk.END, f" {display_label}: {message}\n\n", tag)
        else:
            # For user messages, add proper spacing before the message
            self.chat_display.insert(tk.END, f"({timestamp}) {display_label}: {message}\n\n", tag)
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        msg_entry = {
            "timestamp": timestamp,
            "sender": display_label,
            "content": message,
            "audio_file": None,
            "server": self.server_type if sender == "Assistant" else None
        }
        self.message_history.append(msg_entry)
        
        self.save_message_history()
    
    def update_streaming_message(self, text):
        """Update the last assistant message with streamed text in real-time"""
        self.chat_display.config(state=tk.NORMAL)
        
        try:
            # Get the entire text
            all_text = self.chat_display.get("1.0", tk.END)
            
            # Find the last server label (ollama: or llama:)
            server_name = self.server_display_name.split()[0].lower()
            label_text = f"{server_name}:"
            last_label_pos = all_text.rfind(label_text)
            
            if last_label_pos < 0:
                self.chat_display.config(state=tk.DISABLED)
                return
            
            # Find the timestamp for this message
            timestamp_start = all_text.rfind("[", 0, last_label_pos)
            timestamp_end = all_text.find("]", timestamp_start)
            timestamp = all_text[timestamp_start+1:timestamp_end] if timestamp_start >= 0 else ""
            
            # Everything up to and including the label and space
            prefix_to_keep = all_text[:last_label_pos + len(label_text) + 1]
            
            # Rebuild with new text
            new_full_text = prefix_to_keep + text + "\n\n"
            
            # Replace everything in the widget
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.insert("1.0", new_full_text)
            
            # Reapply all tags to preserve formatting
            self._apply_tags_to_content(new_full_text, timestamp, server_name)
            
        except Exception as e:
            print(f"Error updating streaming message: {e}")
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def _apply_tags_to_content(self, content, current_timestamp, server_name):
        """Reapply tags to text content after deletion/rebuild"""
        import re
        
        # First, remove all existing tags
        self.chat_display.tag_remove("timestamp", "1.0", tk.END)
        self.chat_display.tag_remove("assistant", "1.0", tk.END)
        self.chat_display.tag_remove("user", "1.0", tk.END)
        
        # Find and tag all timestamps using Text widget search
        idx = "1.0"
        while True:
            idx = self.chat_display.search(r"\[[0-2][0-9]:[0-5][0-9]:[0-5][0-9]\]", idx, tk.END, regexp=True)
            if not idx:
                break
            end_idx = self.chat_display.index(f"{idx}+10c")  # timestamp is 10 chars: [HH:MM:SS]
            self.chat_display.tag_add("timestamp", idx, end_idx)
            idx = end_idx
        
        # Tag assistant messages using case-insensitive search from start
        # server_name is lowercase ("ollama", "llama") but display shows capitalized
        display_label = server_name.capitalize()
        idx = "1.0"
        while True:
            idx = self.chat_display.search(f"{display_label}:", idx, tk.END, nocase=False)
            if not idx:
                break
            # Find start of message content (after "display_label: ")
            msg_start = self.chat_display.index(f"{idx}+{len(display_label)+2}c")
            # Find end of line
            line_end = self.chat_display.index(f"{idx} lineend")
            self.chat_display.tag_add("assistant", msg_start, line_end)
            idx = self.chat_display.index(f"{idx}+1c")
        
        # Tag user messages
        idx = "1.0"
        while True:
            idx = self.chat_display.search(r"\([0-2][0-9]:[0-5][0-9]:[0-5][0-9]\) You:", idx, tk.END, regexp=True)
            if not idx:
                break
            # Find start of message content
            msg_start = self.chat_display.index(f"{idx}+12c")  # (HH:MM:SS) You: = 12 chars
            # Find end of line
            line_end = self.chat_display.index(f"{idx} lineend")
            self.chat_display.tag_add("user", msg_start, line_end)
            idx = self.chat_display.index(f"{idx}+1c")
    
    def clear_chat(self):
        """Clear chat history and TTS audio files for current chat only"""
        response = messagebox.askyesno("Clear Chat & TTS", f"Clear {self.server_display_name} chat history and TTS audio files?")
        if response:
            # Clear chat display
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # Clear message history
            self.message_history = []
            self.timestamp_audio = {}
            self.save_message_history()
            
            # Clear TTS audio files for current chat only
            try:
                if self.audio_folder.exists():
                    for audio_file in self.audio_folder.glob("*.wav"):
                        audio_file.unlink()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Cleared TTS files in {self.audio_folder}")
            except Exception as e:
                print(f"Error clearing TTS files: {e}")
            
            self.app.show_status(f"✅ Cleared chat and TTS audio", 2000)
    
    def stop_generation(self):
        """Stop generation"""
        self.app.stop_generation = True
        self.app.tts_interrupt = True  # Stop TTS audio if playing
        self.stop_button.config(state=tk.DISABLED)
    
    def stop_tts(self):
        """Stop TTS playback"""
        try:
            # Stop the current TTS if it exists
            if self.app.current_tts:
                try:
                    self.app.current_tts.stop()
                except:
                    pass
                self.app.current_tts = None
            
            # Stop pygame mixer (for playing saved audio files)
            try:
                import pygame
                # Initialize pygame mixer if not already done
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                
                # Stop playback
                pygame.mixer.music.stop()
                pygame.mixer.stop()
            except:
                pass
            
            # Reset flags
            self.app.tts_is_playing = False
            self.app.tts_queue = []
            
            self.app.show_status("✅ TTS stopped", 2000)
        except Exception as e:
            print(f"Error stopping TTS: {e}")
    
    def save_message_history(self):
        """Save chat history"""
        if not self.app.save_history_var.get():
            return
        
        try:
            history_data = [
                {
                    "timestamp": msg.get("timestamp"),
                    "sender": msg.get("sender"),
                    "content": msg.get("content"),
                    "audio_file": msg.get("audio_file"),
                    "server": msg.get("server")
                }
                for msg in self.message_history
            ]
            
            # Use chat manager to save
            self.chat_manager.save_chat(self.current_chat_name or "default", history_data)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG SAVE] Saved {len(history_data)} messages to {self.current_chat_name}")
            
            # Update chat info display with new size
            self.update_chat_info_display()
        except Exception as e:
            print(f"Error saving message history: {e}")
    
    def save_tab_settings(self):
        """Save tab-specific settings (return_to_send, tts_enabled, clean_text_for_tts, etc)"""
        from settings_manager import load_settings, save_settings
        
        settings = load_settings()
        tab_prefix = f"{self.server_type}_"
        
        # Save per-tab settings
        settings[f"{tab_prefix}return_to_send"] = self.return_to_send_var.get()
        settings[f"{tab_prefix}tts_enabled"] = self.tts_enabled_var.get()
        settings[f"{tab_prefix}clean_text_for_tts"] = self.clean_text_for_tts_var.get()
        
        save_settings(settings)
    
    def load_message_history(self):
        """Load chat history from current chat"""
        if not self.app.save_history_var.get():
            return
        
        try:
            # Load from chat manager
            history_data = self.chat_manager.load_chat(self.current_chat_name or "default")
            
            self.chat_display.config(state=tk.NORMAL)
            audio_count = 0
            
            for msg in history_data:
                timestamp = msg.get("timestamp", "")
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                audio_file = msg.get("audio_file")
                
                if sender == "You":
                    tag = "user"
                elif sender == "Assistant":
                    tag = "assistant"
                else:
                    tag = "system"
                
                if sender == "Assistant" or sender == "Ollama" or sender == "llama":
                    self.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
                    self.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                else:
                    self.chat_display.insert(tk.END, f"({timestamp})", tag)
                    self.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                
                if audio_file:
                    self.timestamp_audio[timestamp] = audio_file
                    audio_count += 1
                
                self.message_history.append({
                    "timestamp": timestamp,
                    "sender": sender,
                    "content": content,
                    "audio_file": audio_file,
                    "server": msg.get("server")
                })
            
            self.chat_display.config(state=tk.DISABLED)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Loaded {len(history_data)} messages, {audio_count} audio mappings")
            self.update_chat_info_display()
        except Exception as e:
            print(f"Error loading message history: {e}")
    
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
    
    def save_scroll_position(self):
        """Save current scroll position"""
        try:
            self.scroll_position = self.chat_display.yview()[0]
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Saved scroll position for {self.server_type}: {self.scroll_position}")
        except:
            pass
    
    def restore_scroll_position(self):
        """Restore saved scroll position"""
        try:
            self.chat_display.yview_moveto(self.scroll_position)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Restored scroll position for {self.server_type}: {self.scroll_position}")
        except:
            pass
    
    def check_responses(self):
        """Check response queue"""
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
                    self.stop_button.config(state=tk.NORMAL)
                    self.app.set_generating_status(True)
                    self.streaming_text = ""
                    server_name = self.server_display_name.split()[0].lower()
                    self.add_chat_message(server_name, "", "assistant")
                
                elif status == "stream_chunk":
                    self.streaming_text += message
                    # Update the chat display with accumulated streaming text
                    self.update_streaming_message(self.streaming_text)
                
                elif status == "stream_end" or status == "stream_interrupted":
                    self.stop_button.config(state=tk.DISABLED)
                    self.app.set_generating_status(False)
                    
                    # Update the empty message with streaming text
                    server_name = self.server_display_name.split()[0].lower()
                    if self.message_history:
                        for msg in reversed(self.message_history):
                            if msg["sender"] == server_name and msg.get("content") == "":
                                msg["content"] = self.streaming_text
                                break
                    
                    if self.tts_enabled_var.get() and self.streaming_text and status != "stream_interrupted":
                        self.app.speak_response(self.streaming_text)
                    
                    # Add placeholder for next input
                    self.chat_display.config(state=tk.NORMAL)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.chat_display.insert(tk.END, f"({timestamp}) You: ", "user")
                    self.chat_display.see(tk.END)
                    self.chat_display.config(state=tk.DISABLED)
                
                elif status == "success":
                    self.app.set_generating_status(False)
                    server_name = self.server_display_name.split()[0].lower()
                    self.add_chat_message(server_name, message, "assistant")
                    
                    if self.tts_enabled_var.get():
                        self.app.speak_response(message)
                    
                    self.save_message_history()
                
                else:
                    self.add_chat_message("System", message, "error")
                    self.stop_button.config(state=tk.DISABLED)
        
        except queue.Empty:
            pass
    
    def start_voice_listening(self):
        """Start listening for voice input with silence detection"""
        try:
            from speech_to_text import SpeechToText
            import numpy as np
            import os
            
            # Set Whisper parameters from settings
            os.environ['WHISPER_TEMPERATURE'] = str(self.app.stt_temperature_var.get())
            os.environ['WHISPER_RMS_THRESHOLD'] = str(self.app.stt_rms_threshold_var.get())
            os.environ['WHISPER_NO_SPEECH_THRESHOLD'] = str(self.app.stt_no_speech_threshold_var.get())
            os.environ['WHISPER_LOG_PROB_THRESHOLD'] = str(self.app.stt_log_prob_threshold_var.get())
            
            self.voice_listening = True
            self.app.set_mic_status(True, self.server_type)  # Update status bar with server name
            
            # Update this tab's voice status label
            self.voice_status_label.config(text="🎤 Listening...", fg="#ff9900")
            self.voice_status_label.update()
            
            print("\n" + "="*60)
            print(f"VOICE LISTENING STARTED - {self.server_display_name}")
            print("="*60)
            print(f"Whisper Temperature: {self.app.stt_temperature_var.get()}")
            print(f"RMS Threshold: {self.app.stt_rms_threshold_var.get()}")
            print(f"No Speech Threshold: {self.app.stt_no_speech_threshold_var.get()}")
            print(f"Log Prob Threshold: {self.app.stt_log_prob_threshold_var.get()}")
            print(f"Speech Start Delay: {self.app.stt_speech_start_delay_var.get()}ms")
            print(f"Silence End Delay: {self.app.stt_silence_end_delay_var.get()}ms")
            print("="*60 + "\n")
            
            def listen_thread():
                try:
                    # Get device and model from settings
                    if hasattr(self.app, 'stt_device_var'):
                        device_str = self.app.stt_device_var.get()
                        device_id = int(device_str.split(":")[0]) if device_str else None
                    else:
                        device_id = None
                    
                    model = self.app.stt_model_var.get()
                    compute_device = self.app.stt_compute_device_var.get()
                    
                    # Record with long duration (we'll stop on silence)
                    stt = SpeechToText(model, device=device_id, compute_device=compute_device)
                    self._record_with_silence_detection(stt, device_id)
                    
                except Exception as e:
                    print(f"Voice listening error: {e}")
                    import traceback
                    traceback.print_exc()
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
        self.app.set_mic_status(False, self.server_type)  # Update status bar with server name
        self.voice_status_label.config(text="", fg="#ff9900")
        print(f"\nVoice listening stopped on {self.server_display_name}.\n")
    
    def _record_with_silence_detection(self, stt, device_id):
        """Record audio and detect silence to trigger transcription"""
        import numpy as np
        import sounddevice as sd
        import time
        
        if DebugConfig.chat_enabled:
            print(f"[DEBUG REC START] Entering _record_with_silence_detection on {self.server_type}. voice_listening={self.voice_listening}, stt_enabled={self.stt_enabled_var.get()}")
        
        try:
            # Detect supported sample rate
            supported_rates = stt._get_supported_sample_rates(device_id)
            sample_rate = supported_rates[0] if supported_rates else 16000
            stt.sample_rate = sample_rate
            if DebugConfig.chat_enabled:
                print(f"[DEBUG REC] Sample rate: {sample_rate}, Device: {device_id}")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG REC PRE-LOOP] About to enter outer while. voice_listening={self.voice_listening}, stt_enabled={self.stt_enabled_var.get()}")
            
            # Keep listening while checkbox is enabled
            while self.voice_listening and self.stt_enabled_var.get():
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG REC] Outer loop check: voice_listening={self.voice_listening}, stt_enabled={self.stt_enabled_var.get()}")
                # Record in chunks and detect silence with improved VAD timing
                chunk_duration = 0.1  # 100ms chunks
                chunk_samples = int(sample_rate * chunk_duration)
                
                # Convert VAD timing settings from ms to chunks
                speech_start_chunks = int(self.app.stt_speech_start_delay_var.get() / (chunk_duration * 1000))  # 200-400ms = 2-4 chunks
                silence_end_chunks = int(self.app.stt_silence_end_delay_var.get() / (chunk_duration * 1000))  # 500-800ms = 5-8 chunks
                
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG REC] Starting new recording session. speech_start_chunks={speech_start_chunks}, silence_end_chunks={silence_end_chunks}")
                
                consecutive_silence = 0
                consecutive_speech = 0
                audio_chunks = []
                speech_detected = False
                last_status_update = 0
                pre_speech_buffer = []
                buffer_size = 3  # Keep ~300ms before speech
                
                inner_loop_count = 0
                while self.voice_listening and self.stt_enabled_var.get():
                    inner_loop_count += 1
                    if inner_loop_count == 1:
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG REC] Entering inner loop, chunk_samples={chunk_samples}")
                    try:
                        # Record one chunk
                        chunk = sd.rec(chunk_samples, samplerate=sample_rate, channels=1, dtype=np.float32, device=device_id)
                        sd.wait()
                        
                        chunk = chunk.flatten()
                        
                        # Check if this chunk has speech
                        rms_level = float(np.sqrt(np.mean(chunk ** 2)))
                        speech_threshold = 0.02
                        
                        if rms_level > speech_threshold:
                            # Speech/sound detected
                            consecutive_speech += 1
                            consecutive_silence = 0
                            
                            # Only trigger speech detection after enough continuous speech frames
                            if not speech_detected and consecutive_speech >= speech_start_chunks:
                                speech_detected = True
                                audio_chunks.extend(pre_speech_buffer)
                                pre_speech_buffer = []
                                self.voice_status_label.config(text="🎤 Listening... [SPEECH]", fg="#009900")
                                self.app.root.update()
                                print(f"  🎤 Speech detected (after {consecutive_speech * chunk_duration * 1000:.0f}ms)")
                            
                            # Add this chunk to audio if speech was detected
                            if speech_detected:
                                audio_chunks.append(chunk)
                        else:
                            # Silence detected
                            consecutive_speech = 0
                            
                            if not speech_detected:
                                # Keep buffering pre-speech audio (not yet recording)
                                pre_speech_buffer.append(chunk)
                                if len(pre_speech_buffer) > buffer_size:
                                    pre_speech_buffer.pop(0)
                            else:
                                # We were recording speech, now silence
                                consecutive_silence += 1
                                audio_chunks.append(chunk)  # Include silence for natural audio
                                
                                # Only update UI every 0.5s to reduce spam
                                current_time = time.time()
                                if current_time - last_status_update >= 0.5:
                                    silence_ms = consecutive_silence * chunk_duration * 1000
                                    silence_target_ms = silence_end_chunks * chunk_duration * 1000
                                    self.voice_status_label.config(
                                        text=f"🎤 Silence: {silence_ms:.0f}ms / {silence_target_ms:.0f}ms",
                                        fg="#ff9900"
                                    )
                                    self.app.root.update()
                                    last_status_update = current_time
                                
                                # Trigger transcription after enough silence
                                if consecutive_silence >= silence_end_chunks:
                                    silence_ms = consecutive_silence * chunk_duration * 1000
                                    print(f"  ⏸ {silence_ms:.0f}ms silence detected - Transcribing...")
                                    break
                        
                        # Prevent recording forever (max 60 seconds of actual audio)
                        if speech_detected and len(audio_chunks) > 600:  # 60 seconds
                            print("  ⚠ Max recording time reached")
                            break
                    except Exception as e:
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG REC] Exception in recording loop: {e}")
                        import traceback
                        traceback.print_exc()
                        break
                    
                
                # Check if we have audio to transcribe
                if audio_chunks and self.stt_enabled_var.get():
                    # Combine all chunks
                    stt.audio_data = np.concatenate(audio_chunks).flatten()
                    
                    if len(stt.audio_data) > 0:
                        # Transcribe
                        self.voice_status_label.config(text="🎤 Transcribing...", fg="#0066cc")
                        self.app.root.update()
                        
                        # Use global language setting from main app settings (not auto-detect)
                        language = self.app.stt_language_var.get()
                        result = stt.transcribe(language=language)
                        
                        # Extract text from result dict
                        text = result.get('text', '').strip() if isinstance(result, dict) else (result.strip() if result else '')
                        
                        if text and len(text) > 0:
                            print(f"  ✓ Transcription: {text}")
                            self.voice_status_label.config(text="✓ Done! Listening again...", fg="#009900")
                            self.app.root.update()
                            
                            # Insert text into this tab's input field
                            self.input_text.insert(tk.END, text + " ")
                            
                            # Auto-send if "Send on Return" is enabled for this tab
                            if self.return_to_send_var.get():
                                print("  📤 Auto-sending...")
                                self.app.root.after(500, lambda: self.send_message())
                                
                                # Wait a moment before listening again
                                time.sleep(1)
                        else:
                            print("  ⚠ No speech detected (audio too quiet or ambiguous)")
                            self.voice_status_label.config(text="🎤 Listening... (no speech)", fg="#ff9900")
                            self.app.root.update()
                    else:
                        self.voice_status_label.config(text="🎤 Listening... (no audio)", fg="#ff9900")
                        self.app.root.update()
                else:
                    # Checkbox was unchecked, exit loop
                    break
                
        except Exception as e:
            print(f"❌ Voice listening error: {e}")
            self.voice_status_label.config(text="❌ Error", fg="#cc0000")
    
    def update_chat_info_display(self):
        """Update the chat info label with current chat name and size"""
        chat_name = self.chat_manager.current_chat_name
        size_bytes = self.chat_manager.get_chat_size(chat_name)
        size_str = self.chat_manager.format_size(size_bytes)
        self.chat_info_label.config(text=f"📄 {chat_name}.json ({size_str})")
    
    def update_tts_size_display(self):
        """Update TTS size display - shows total of all TTS files"""
        total_size = self.chat_manager.get_all_tts_size()
        size_str = self.chat_manager.format_size(total_size)
        self.tts_size_label.config(text=f"({size_str})")
    
    def load_chat_dialog(self):
        """Show dialog to load a saved chat"""
        chats = self.chat_manager.list_chats()
        if not chats:
            self.app.show_status("❌ No saved chats", 2000)
            return
        
        # Create a simple dialog with listbox
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Load Chat")
        dialog.geometry("300x300")
        dialog.transient(self.app.root)
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
            
            # Parse audio mappings
            for msg in messages:
                if msg.get("audio_file"):
                    self.timestamp_audio[msg.get("timestamp")] = msg.get("audio_file")
            
            # Refresh display
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            # Re-display messages
            for msg in messages:
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                if sender == "You":
                    tag = "user"
                elif sender == "Ollama" or sender == "Assistant":
                    tag = "assistant"
                else:
                    tag = "system"
                
                self.chat_display.config(state=tk.NORMAL)
                if sender == "Ollama" or sender == "Assistant":
                    self.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
                    self.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                else:
                    self.chat_display.insert(tk.END, f"({timestamp})", tag)
                    self.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                self.chat_display.config(state=tk.DISABLED)
            
            self.update_chat_info_display()
            self.app.show_status(f"✅ Loaded chat: {chat_name}", 2000)
        except Exception as e:
            print(f"Error loading chat: {e}")
            self.app.show_status(f"❌ Error loading chat: {str(e)}", 2000)
    
    def new_chat_dialog(self):
        """Show dialog to create a new chat"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("New Chat")
        dialog.geometry("350x150")
        dialog.transient(self.app.root)
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
                self.app.show_status("❌ Chat name cannot be empty", 2000)
                return
            
            # Sanitize name (remove special characters)
            chat_name = "".join(c for c in chat_name if c.isalnum() or c in "_-")
            
            try:
                self.chat_manager.new_chat(chat_name)
                self.current_chat_name = chat_name
                self.audio_folder = self.chat_manager.get_audio_folder()
                self.message_history = []
                self.timestamp_audio = {}
                
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete("1.0", tk.END)
                self.chat_display.config(state=tk.DISABLED)
                
                self.update_chat_info_display()
                self.app.show_status(f"✅ Created new chat: {chat_name}", 2000)
                dialog.destroy()
            except Exception as e:
                self.app.show_status(f"❌ Error creating chat: {str(e)}", 2000)
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Create", command=create_new, bg="#00cc66", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#666666", fg="white", width=10).pack(side=tk.LEFT, padx=5)
    
    def save_chat_as_dialog(self):
        """Show dialog to rename/save chat as"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Save Chat As")
        dialog.geometry("350x150")
        dialog.transient(self.app.root)
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
                self.app.show_status("❌ Chat name cannot be empty", 2000)
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
                self.update_chat_info_display()
                self.app.show_status(f"✅ Chat saved as: {new_name}", 2000)
                dialog.destroy()
            except Exception as e:
                self.app.show_status(f"❌ Error saving chat: {str(e)}", 2000)
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Save", command=save_as, bg="#ff9900", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#666666", fg="white", width=10).pack(side=tk.LEFT, padx=5)
