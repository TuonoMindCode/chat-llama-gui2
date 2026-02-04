"""
OllamaChatHandler - Business logic for Ollama chat (responses, voice, audio, history)
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


class OllamaChatHandler:
    """Handles Ollama chat business logic: responses, voice input, audio playback, history"""
    
    def __init__(self, chat_tab):
        """
        Initialize handler
        
        Args:
            chat_tab: Reference to OllamaChatTab instance
        """
        self.tab = chat_tab
        self.response_queue = queue.Queue()
        self.message_history = []
        self.timestamp_audio = {}
        self.timestamp_image = {}
        self.streaming_text = ""
        self.voice_listening = False
        
        # Initialize ChatManager
        self.chat_manager = ChatManager("ollama")
        
        # Load saved current chat or default to "default"
        from settings_manager import load_settings
        settings = load_settings()
        saved_chat = settings.get("ollama_current_chat")
        
        if saved_chat and (self.chat_manager.base_folder / saved_chat).exists():
            self.current_chat_name = saved_chat
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Loaded saved ollama chat: {saved_chat}")
        else:
            self.current_chat_name = self.chat_manager.get_default_chat().name
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Using default ollama chat")
        
        # Set up file paths
        self.history_file = Path("chat_history_ollama.json")
        self.audio_folder = self.chat_manager.get_audio_folder()
        self.audio_folder.mkdir(exist_ok=True)
    
    def get_server_response(self, message):
        """Get response from server and put in queue"""
        try:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] get_server_response called for ollama with message: {message[:50]}")
            if not self.tab.app.server_client:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] No server client")
                self.response_queue.put(("error", "Server not connected"))
                return
            
            self.tab.app.stop_generation = False
            
            # Get system prompt
            system_prompt = self.tab.app.system_prompt
            
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
                    print(f"[DEBUG] Using streaming for ollama")
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
                            self.response_queue.put(("stream_interrupted",))
                            return
                        self.response_queue.put(("stream_chunk", chunk))
                    self.response_queue.put(("stream_end",))
                except Exception as e:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Streaming error for ollama: {e}")
                    self.response_queue.put(("error", f"Streaming error: {str(e)}"))
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Using non-streaming for ollama")
                generated_text = self.tab.app.server_client.generate(
                    formatted_prompt,
                    model=model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    n_predict=n_predict
                )
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Generated text from ollama: {generated_text[:100]}")
                
                lines = generated_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    if line.strip().startswith("User:"):
                        break
                    cleaned_lines.append(line)
                
                generated_text = '\n'.join(cleaned_lines).strip()
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Putting success message in queue for ollama")
                self.response_queue.put(("success", generated_text))
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Exception in get_server_response for ollama: {e}")
            self.response_queue.put(("error", f"Error: {str(e)}"))
    
    def generate_image(self, response_text):
        """
        Generate image from LLM response text using Image Settings
        
        Args:
            response_text: The LLM response text
        """
        try:
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] generate_image called, enabled: {self.tab.image_gen_enabled_var.get()}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Response text length: {len(response_text)}")
            
            if not self.tab.image_gen_enabled_var.get():
                if DebugConfig.comfyui_enabled:
                    print(f"[DEBUG] Image generation disabled, returning")
                return
            
            # Import clients
            from image_client import ComfyUIClient
            from image_prompt_extractor import ImagePromptExtractor
            
            self.tab.app.set_image_generation_status("extracting prompt", provider="ollama")
            self.tab.app.root.update()
            
            # Get all settings from Image Settings tab
            from settings_manager import load_settings
            settings = load_settings()
            
            # ComfyUI settings
            comfyui_url = settings.get("comfyui_url", "http://127.0.0.1:8188")
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] ComfyUI URL from settings: {comfyui_url}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Settings keys available: {list(settings.keys())}")
            
            # Extraction settings
            extraction_provider = settings.get("extraction_model_provider", "ollama")
            extraction_url = settings.get("extraction_provider_url", "http://localhost:11434")
            extraction_model = settings.get("extraction_model", "dolphin-2.1:2.4b")
            extraction_temperature = float(settings.get("extraction_temperature", "0.3"))
            extraction_timeout = int(settings.get("extraction_timeout", "120"))
            min_response_length = int(settings.get("min_response_length", "100"))
            extraction_system_prompt = settings.get("extraction_system_prompt")
            extraction_user_prompt = settings.get("extraction_user_prompt")
            
            # Image generation settings
            resolution = settings.get("image_resolution", "768x768")
            steps = int(settings.get("image_steps", "20"))
            cfg_scale = float(settings.get("image_cfg_scale", "7.5"))
            sampler = settings.get("image_sampler", "euler")
            
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] Image Settings loaded:")
                print(f"  Provider: {extraction_provider}, URL: {extraction_url}")
                print(f"  Model: {extraction_model}, Temp: {extraction_temperature}")
                print(f"  Min response length: {min_response_length} chars")
                print(f"  Generation: {resolution}, {steps} steps, CFG {cfg_scale}, {sampler}")
            
            # Check response length threshold
            if len(response_text) < min_response_length:
                self.tab.app.image_gen_status_label.config(
                    text=f"Response too short ({len(response_text)} < {min_response_length})", 
                    fg="#ff9900"
                )
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Response skipped (too short)")
                return
            
            # Initialize prompt extractor with custom prompts and provider
            extractor = ImagePromptExtractor(
                model=extraction_model,
                provider=extraction_provider,
                provider_url=extraction_url,
                system_prompt=extraction_system_prompt,
                user_prompt_template=extraction_user_prompt
            )
            
            # Initialize ComfyUI client with chat-specific image folder
            image_folder = self.chat_manager.get_image_folder()
            comfyui = ComfyUIClient(url=comfyui_url, output_folder=image_folder)
            
            # Skip connection test - just try to generate
            # (Test Generation in Image Settings doesn't test connection either, just generates)
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] Using ComfyUI at: {comfyui_url}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Saving images to: {image_folder}")
            
            # Extract image prompt
            image_prompt = extractor.extract_prompt(
                response_text,
                temperature=extraction_temperature,
                min_response_length=min_response_length,
                timeout=extraction_timeout
            )
            
            if not image_prompt:
                self.tab.app.image_gen_status_label.config(text="No image content detected", fg="#ff9900")
                return
            
            if DebugConfig.extraction_enabled:
                print(f"[DEBUG] Image prompt extracted: {image_prompt}")
            self.tab.app.set_image_generation_status("generating", provider="ollama")
            self.tab.app.root.update()
            
            # Get checkpoint model from settings
            from settings_manager import load_settings
            settings = load_settings()
            checkpoint_model = settings.get("checkpoint_model", "sdxl_turbo.safetensors")
            
            # Get the latest message timestamp (the assistant response just added)
            latest_timestamp = None
            if self.message_history:
                latest_msg = self.message_history[-1]
                if latest_msg.get("sender") in ("ollama", "Assistant"):
                    latest_timestamp = latest_msg.get("timestamp")
            
            # Generate image with resolution, steps, cfg_scale, sampler, and checkpoint model
            # Pass timestamp to get it back for filename and mapping
            result = comfyui.generate_from_text(
                image_prompt,
                resolution=resolution,
                steps=steps,
                cfg_scale=cfg_scale,
                sampler=sampler,
                checkpoint_model=checkpoint_model,
                timestamp=latest_timestamp
            )
            
            if result:
                # Handle both single return (str) and tuple return (str, timestamp)
                if isinstance(result, tuple):
                    image_path, timestamp = result
                else:
                    image_path = result
                    timestamp = latest_timestamp
                
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Image generated: {image_path}")
                self.tab.image_viewer.add_image(image_path)
                
                # Store timestamp with image for alignment functionality
                if timestamp:
                    self.tab.image_viewer.set_image_timestamp(image_path, timestamp)
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Stored timestamp {timestamp} for image alignment")
                
                self.tab.app.set_image_generation_status("done", provider="ollama")
                
                # Update the latest message in history with image_file and map timestamp to image
                if timestamp and self.message_history:
                    for msg in reversed(self.message_history):
                        if msg.get("timestamp") == timestamp and msg.get("sender") in ("ollama", "Assistant"):
                            msg["image_file"] = image_path
                            # Add to handler's timestamp_image mapping
                            if not hasattr(self, 'timestamp_image'):
                                self.timestamp_image = {}
                            self.timestamp_image[timestamp] = image_path
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] Mapped timestamp {timestamp} to image {image_path}")
                            break
                    
                    # Save updated message history
                    self.save_message_history()
            else:
                self.tab.app.set_image_generation_status("failed", provider="ollama")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Image generation failed")
                
        except Exception as e:
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] Error in generate_image: {e}")
            import traceback
            traceback.print_exc()
            self.tab.app.set_image_generation_status("failed", provider="ollama")
    
    def add_chat_message(self, sender, message, tag="assistant"):
        """Add message to chat display and history"""
        if DebugConfig.chat_enabled:
            if DebugConfig.chat_enabled:
                print(f"[HANDLER] add_chat_message called: sender={sender}, message_len={len(message)}, tag={tag}")
        self.tab.chat_display.config(state=tk.NORMAL)
        
        display_label = sender
        if sender == "Assistant":
            display_label = "ollama"
        
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
                    print(f"[HANDLER] Inserting assistant message: [{timestamp}] ollama: {message[:50]}")
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
            "server": "ollama" if sender == "Assistant" else None
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
            
            # Keep everything up to and including "] ollama: "
            # The format is "[HH:MM:SS] ollama: "
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
        
        # Tag assistant messages (ollama:) using search
        idx = "1.0"
        while True:
            idx = self.tab.chat_display.search("ollama:", idx, tk.END)
            if not idx:
                break
            # Find start of message content (after "ollama: ")
            msg_start = self.tab.chat_display.index(f"{idx}+8c")
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
                    self.add_chat_message("Assistant", "", "assistant")
                
                elif status == "stream_chunk":
                    self.streaming_text += message
                    self.update_streaming_message(self.streaming_text)
                
                elif status == "stream_end" or status == "stream_interrupted":
                    self.tab.stop_button.config(state=tk.DISABLED)
                    self.tab.app.set_generating_status(False)
                    
                    # Update the empty message with streaming text
                    if self.message_history:
                        for msg in reversed(self.message_history):
                            if msg["sender"] == "ollama" and msg.get("content") == "":
                                msg["content"] = self.streaming_text
                                break
                    
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Stream ended. Message length: {len(self.streaming_text)}")
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Image gen enabled: {self.tab.image_gen_enabled_var.get()}")
                    
                    if self.tab.tts_enabled_var.get() and self.streaming_text and status != "stream_interrupted":
                        self.tab.app.speak_response(self.streaming_text)
                    
                    # Trigger image generation in background if enabled
                    if self.tab.image_gen_enabled_var.get() and self.streaming_text:
                        if DebugConfig.comfyui_enabled:
                            print(f"[DEBUG] ✓ Image generation ENABLED - starting thread...")
                        thread = threading.Thread(
                            target=self.generate_image,
                            args=(self.streaming_text,),
                            daemon=True
                        )
                        thread.start()
                    
                    # Add placeholder for next input
                    self.tab.chat_display.config(state=tk.NORMAL)
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.tab.chat_display.insert(tk.END, f"({timestamp}) You: ", "user")
                    self.tab.chat_display.see(tk.END)
                    self.tab.chat_display.config(state=tk.DISABLED)
                
                elif status == "success":
                    self.tab.app.set_generating_status(False)
                    self.add_chat_message("Assistant", message, "assistant")
                    
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Response complete. Message length: {len(message)}")
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] TTS enabled: {self.tab.tts_enabled_var.get()}")
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Image gen enabled: {self.tab.image_gen_enabled_var.get()}")
                    
                    if self.tab.tts_enabled_var.get():
                        self.tab.app.speak_response(message)
                    
                    # Trigger image generation in background if enabled
                    if self.tab.image_gen_enabled_var.get():
                        if DebugConfig.comfyui_enabled:
                            print(f"[DEBUG] ✓ Image generation ENABLED - starting thread...")
                        thread = threading.Thread(
                            target=self.generate_image,
                            args=(message,),
                            daemon=True
                        )
                        thread.start()
                    else:
                        if DebugConfig.comfyui_enabled:
                            print(f"[DEBUG] ✗ Image generation DISABLED")
                    
                    self.save_message_history()
                
                else:
                    self.add_chat_message("System", message, "error")
                    self.tab.stop_button.config(state=tk.DISABLED)
        
        except queue.Empty:
            pass
    
    def save_message_history(self):
        """Save message history to JSON"""
        try:
            # Use chat manager to save
            self.chat_manager.save_chat(self.current_chat_name or "default", self.message_history)
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG SAVE] Saved {len(self.message_history)} messages to {self.current_chat_name}")
        except Exception as e:
            print(f"Error saving message history: {e}")
    
    def load_message_history(self):
        """Load message history from current chat on startup"""
        try:
            messages = self.chat_manager.load_chat(self.current_chat_name or "default")
            self.message_history = messages
            self.timestamp_audio = {}
            self.timestamp_image = {}
            
            # Parse audio and image mappings and calculate total size
            total_size = 0
            image_count = 0
            for msg in messages:
                if msg.get("audio_file"):
                    audio_file = msg.get("audio_file")
                    self.timestamp_audio[msg.get("timestamp")] = audio_file
                    try:
                        from pathlib import Path
                        total_size += Path(audio_file).stat().st_size
                    except:
                        pass
                if msg.get("image_file"):
                    image_file = msg.get("image_file")
                    self.timestamp_image[msg.get("timestamp")] = image_file
                    image_count += 1
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG LOAD INIT] Loaded image mapping: {msg.get('timestamp')} -> {image_file}")
            
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
                elif sender == "ollama" or sender == "Assistant":
                    tag = "assistant"
                else:
                    tag = "system"
                
                self.tab.chat_display.config(state=tk.NORMAL)
                if sender == "ollama" or sender == "Assistant":
                    self.tab.chat_display.insert(tk.END, f"[{timestamp}]", "timestamp")
                    self.tab.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                else:
                    self.tab.chat_display.insert(tk.END, f"({timestamp})", tag)
                    self.tab.chat_display.insert(tk.END, f" {sender}: {content}\n\n", tag)
                self.tab.chat_display.config(state=tk.DISABLED)
            
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
                                print(f"[DEBUG LOAD INIT] Added image to viewer: {image_file}")
                
                # Update image viewer display
                if self.tab.image_viewer.images_list:
                    self.tab.image_viewer.current_image_index = 0
                    self.tab.image_viewer.display_images()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG LOAD INIT] Populated image viewer with {len(self.tab.image_viewer.images_list)} images")
            
            self.tab.update_chat_info_display()
            size_mb = total_size / (1024 * 1024)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG LOAD INIT] Loaded {len(messages)} messages with {len(self.timestamp_audio)} audio files, {image_count} images ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"Error loading message history: {e}")
    
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
            
            # Update audio and image folder paths
            self.audio_folder = self.chat_manager.get_audio_folder()
            
            # Save current chat name to settings (for next app startup)
            from settings_manager import load_settings, save_settings
            settings = load_settings()
            settings["ollama_current_chat"] = chat_name
            save_settings(settings)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Saved current ollama chat: {chat_name}")
            
            # Load the messages
            self.message_history = messages
            self.timestamp_audio = {}
            self.timestamp_image = {}
            
            # Parse audio and image mappings
            image_count = 0
            for msg in messages:
                if msg.get("audio_file"):
                    self.timestamp_audio[msg.get("timestamp")] = msg.get("audio_file")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG LOAD] Loaded audio mapping: {msg.get('timestamp')} -> {msg.get('audio_file')}")
                if msg.get("image_file"):
                    self.timestamp_image[msg.get("timestamp")] = msg.get("image_file")
                    image_count += 1
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG LOAD] Loaded image mapping: {msg.get('timestamp')} -> {msg.get('image_file')}")
            
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
                elif sender == "ollama" or sender == "Assistant":
                    tag = "assistant"
                else:
                    tag = "system"
                
                self.tab.chat_display.config(state=tk.NORMAL)
                if sender == "ollama" or sender == "Assistant":
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
                                print(f"[DEBUG LOAD] Added image to viewer: {image_file}")
                
                # Update image viewer display
                if self.tab.image_viewer.images_list:
                    self.tab.image_viewer.current_image_index = 0
                    self.tab.image_viewer.display_images()
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG LOAD] Populated image viewer with {len(self.tab.image_viewer.images_list)} images")
            
            self.tab.update_chat_info_display()
            self.tab.app.show_status(f"✅ Loaded chat: {chat_name}", 2000)
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
                settings["ollama_current_chat"] = chat_name
                save_settings(settings)
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Saved new ollama chat as current: {chat_name}")
                
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
