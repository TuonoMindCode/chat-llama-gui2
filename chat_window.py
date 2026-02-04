"""
ChatWindow class - Reusable chat interface for different servers
"""

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import json
from pathlib import Path
from datetime import datetime
import queue
import threading


class ChatWindow:
    """Reusable chat interface for Ollama and Llama servers"""
    
    def __init__(self, parent, app, server_type):
        """
        Initialize ChatWindow
        
        Args:
            parent: Parent frame for the chat tab
            app: Reference to the main LlamaChatGUI instance
            server_type: "ollama" or "llama-server"
        """
        self.parent = parent
        self.app = app
        self.server_type = server_type
        
        # Set up file paths based on server type
        if server_type == "ollama":
            self.history_file = Path("chat_history_ollama.json")
            self.audio_folder = Path("tts_audio_ollama")
            self.server_display_name = "Ollama Chat"
        else:  # llama-server
            self.history_file = Path("chat_history_llama.json")
            self.audio_folder = Path("tts_audio_llama")
            self.server_display_name = "Llama Chat"
        
        # Ensure audio folder exists
        self.audio_folder.mkdir(exist_ok=True)
        
        # Chat state
        self.message_history = []
        self.timestamp_audio = {}  # Maps timestamp to audio file path
        self.streaming_text = ""
        self.streaming_message_start_index = None
        
        # Create widgets
        self.create_widgets()
        
        # Load history
        self.load_message_history()
    
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
        
        # Model selection frame
        model_frame = tk.Frame(self.parent, bg="#f0f0f0")
        model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(model_frame, text="Model:", bg="#f0f0f0", font=("Arial", 9)).pack(side=tk.LEFT)
        self.server_model_combo = ttk.Combobox(
            model_frame,
            state="readonly",
            width=40,
            font=("Arial", 9)
        )
        self.server_model_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.server_model_combo['values'] = ["(connect to see models)"]
        
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
        
        # Configure text tags for styling
        self.chat_display.tag_config("user", foreground="#0066cc", font=("Courier", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#1a1a1a", font=("Courier", 11))
        self.chat_display.tag_config("system", foreground="#cc6600", font=("Courier", 10, "italic"))
        self.chat_display.tag_config("error", foreground="#cc0000", font=("Courier", 11))
        self.chat_display.tag_config("timestamp", foreground="#0066cc", underline=True, font=("Courier", 11, "bold"))
        
        # Bind mouse events for timestamp clicks
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
            variable=self.app.return_to_send_var,
            bg="#f0f0f0",
            font=("Arial", 10)
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
            variable=self.app.tts_enabled_var,
            bg="#f0f0f0",
            font=("Arial", 10)
        )
        self.tts_checkbox.pack(side=tk.LEFT, padx=10)
        
        # TTS interrupt checkbox
        tk.Checkbutton(
            label_frame,
            text="⏸ Cut off TTS",
            variable=self.app.tts_interrupt_var,
            bg="#f0f0f0",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=10)
        
        # Text input field with scrollbar
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
            button_frame,
            text="Clear Chat",
            command=self.clear_chat,
            bg="#666666",
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
    
    def connect_to_server(self):
        """Connect to the server"""
        # Set server type for this chat tab
        self.app.server_type_var.set(self.server_type)
        # Call test_connection with this chat window instance
        self.app.test_connection(chat_window=self)
    
    def toggle_voice_listening(self):
        """Toggle voice listening for this chat tab"""
        if self.stt_enabled_var.get():
            self.app.start_voice_listening()
        else:
            self.app.stop_voice_listening()
    
    def handle_return_key(self, event):
        """Handle Return key in input field"""
        if self.app.return_to_send_var.get():
            self.send_message()
            return "break"
        return None
    
    def send_message(self):
        """Send message to the server"""
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
        
        # Clear input
        self.input_text.config(state=tk.NORMAL)
        self.input_text.delete("1.0", tk.END)
        
        # Add user message
        self.add_chat_message("You", message, "user")
        
        # Set server type for this chat tab
        self.app.server_type_var.set(self.server_type)
        
        # Check connection
        server_status_text = self.app.server_status_label.cget("text")
        if "not connected" in server_status_text:
            self.add_chat_message("System", f"❌ {self.server_display_name} is not connected", "error")
            return
        
        # Save settings
        from settings_manager import load_settings, save_settings
        settings = load_settings()
        settings["server_type"] = self.server_type
        settings["server_model"] = self.app.server_model_var.get()
        save_settings(settings)
        
        # Get response in background
        thread = threading.Thread(
            target=self.get_server_response,
            args=(message,),
            daemon=True
        )
        thread.start()
    
    def get_server_response(self, message):
        """Get response from server with proper system prompt"""
        try:
            if not self.app.server_client:
                self.app.response_queue.put(("error", "Server not connected"))
                return
            
            self.app.stop_generation = False
            
            # Get appropriate system prompt
            if self.server_type == "llama-server":
                system_prompt = self.app.system_prompt_llama
            else:  # ollama
                system_prompt = self.app.system_prompt
            
            formatted_prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"
            model = self.app.server_model_var.get()
            
            # Get temperature and other params from app
            temperature = self.app.temperature_var.get() if hasattr(self.app, 'temperature_var') else 0.7
            top_p = self.app.top_p_var.get() if hasattr(self.app, 'top_p_var') else 0.9
            top_k = self.app.top_k_var.get() if hasattr(self.app, 'top_k_var') else 40
            n_predict = self.app.n_predict_var.get() if hasattr(self.app, 'n_predict_var') else -1
            
            if self.app.streaming_enabled_var.get():
                # Streaming
                try:
                    self.app.response_queue.put(("stream_start",))
                    for chunk in self.app.server_client.generate_stream(
                        formatted_prompt,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        n_predict=n_predict
                    ):
                        if self.app.stop_generation:
                            self.app.response_queue.put(("stream_interrupted",))
                            return
                        self.app.response_queue.put(("stream_chunk", chunk))
                    self.app.response_queue.put(("stream_end",))
                except Exception as e:
                    self.app.response_queue.put(("error", f"Streaming error: {str(e)}"))
            else:
                # Non-streaming
                generated_text = self.app.server_client.generate(
                    formatted_prompt,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    n_predict=n_predict
                )
                
                # Clean up
                lines = generated_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.strip().startswith("User:"):
                        break
                    cleaned_lines.append(line)
                
                generated_text = '\n'.join(cleaned_lines).strip()
                self.app.response_queue.put(("success", generated_text))
        except Exception as e:
            self.app.response_queue.put(("error", f"Error: {str(e)}"))
    
    def add_chat_message(self, sender, message, tag="assistant"):
        """Add message to chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Determine display label
        display_label = sender
        if sender == "Assistant":
            display_label = self.server_display_name.split()[0]  # "Ollama" or "Llama"
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Add message with appropriate timestamp format
        if sender == "Assistant":
            self.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
            self.chat_display.insert(tk.END, f" {display_label}: {message}\n\n", tag)
        else:
            self.chat_display.insert(tk.END, f"({timestamp})", tag)
            self.chat_display.insert(tk.END, f" {display_label}: {message}\n\n", tag)
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # Track in history
        msg_entry = {
            "timestamp": timestamp,
            "sender": display_label if sender != "Assistant" else "Assistant",
            "content": message,
            "audio_file": None,
            "server": self.server_type if sender == "Assistant" else None
        }
        self.message_history.append(msg_entry)
        
        # Save immediately
        self.save_message_history()
    
    def clear_chat(self):
        """Clear chat history"""
        response = messagebox.askyesno("Clear Chat", f"Clear {self.server_display_name} chat history?")
        if response:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.message_history = []
            self.timestamp_audio = {}
            self.save_message_history()
    
    def stop_generation(self):
        """Stop generation"""
        self.app.stop_generation = True
        self.stop_button.config(state=tk.DISABLED)
    
    def save_message_history(self):
        """Save chat history to JSON file"""
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
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG SAVE] Saved {len(history_data)} messages to {self.history_file}")
        except Exception as e:
            print(f"Error saving message history: {e}")
    
    def load_message_history(self):
        """Load chat history from JSON file"""
        if not self.history_file.exists() or not self.app.save_history_var.get():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            self.chat_display.config(state=tk.NORMAL)
            audio_count = 0
            
            for msg in history_data:
                timestamp = msg.get("timestamp", "")
                sender = msg.get("sender", "")
                content = msg.get("content", "")
                audio_file = msg.get("audio_file")
                
                # Determine tag
                if sender == "You":
                    tag = "user"
                elif sender == "Assistant":
                    tag = "assistant"
                else:
                    tag = "system"
                
                # Insert message
                if sender == "Assistant" or sender == "Ollama" or sender == "llama":
                    self.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
                    self.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                else:
                    self.chat_display.insert(tk.END, f"({timestamp})", tag)
                    self.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                
                # Map timestamp to audio
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
            print(f"[DEBUG] Loaded {len(history_data)} messages, {audio_count} audio mappings from {self.history_file}")
        except Exception as e:
            print(f"Error loading message history: {e}")
    
    def _on_chat_click(self, event):
        """Handle click on timestamp to play audio"""
        # Get the position of the click
        pos = self.chat_display.index(f"@{event.x},{event.y}")
        
        # Get the line content
        line_start = self.chat_display.index(f"{pos} linestart")
        line_end = self.chat_display.index(f"{pos} lineend")
        line_content = self.chat_display.get(line_start, line_end)
        
        # Extract timestamp from [HH:MM:SS] format
        import re
        timestamp_match = re.search(r'\[(\d{2}:\d{2}:\d{2})\]', line_content)
        if not timestamp_match:
            return
        
        timestamp = timestamp_match.group(1)
        
        # Play audio if exists
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
    
    def check_responses(self):
        """Check response queue for messages from server - called periodically"""
        import queue
        try:
            while True:
                message_data = self.app.response_queue.get_nowait()
                
                # Handle tuple unpacking
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
                    self.add_chat_message("Assistant", "", "assistant")
                
                elif status == "stream_chunk":
                    self.streaming_text += message
                    # Real-time update not implemented for simplicity
                
                elif status == "stream_end" or status == "stream_interrupted":
                    self.stop_button.config(state=tk.DISABLED)
                    self.app.set_generating_status(False)
                    
                    # Update message history with final content
                    if self.message_history:
                        for msg in reversed(self.message_history):
                            if msg["sender"] == "Assistant" and msg.get("content") == "":
                                msg["content"] = self.streaming_text
                                break
                    
                    # Trigger TTS if enabled
                    if self.app.tts_enabled_var.get() and self.streaming_text and status != "stream_interrupted":
                        self.app.speak_response(self.streaming_text)
                    
                    # Add "You:" prompt
                    self.chat_display.config(state=tk.NORMAL)
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.chat_display.insert(tk.END, f"\n\n({timestamp})", "user")
                    self.chat_display.insert(tk.END, f" You: ", "user")
                    self.chat_display.see(tk.END)
                    self.chat_display.config(state=tk.DISABLED)
                    
                    self.save_message_history()
                
                elif status == "success":
                    self.app.set_generating_status(False)
                    self.add_chat_message("Assistant", message, "assistant")
                    
                    if self.app.tts_enabled_var.get():
                        self.app.speak_response(message)
                    
                    self.save_message_history()
                
                else:  # Error status
                    self.add_chat_message("System", message, "error")
                    self.stop_button.config(state=tk.DISABLED)
        
        except queue.Empty:
            pass
        
        # Schedule next check
        self.app.root.after(100, self.check_responses)
