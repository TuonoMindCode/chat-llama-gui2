"""
Image Manager - Handles image generation, extraction, display, and navigation
"""

import threading
from pathlib import Path
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from settings_manager import load_settings
from debug_config import DebugConfig
from ollama_request_manager import OllamaRequestManager


class ImageSignals(QObject):
    """Qt signals for thread-safe image operations"""
    image_ready = pyqtSignal(str)  # Emits image path
    image_error = pyqtSignal(str)  # Emits error message


class ImageManager:
    """Manages image generation, display, and navigation"""
    
    def __init__(self, chat_tab):
        """
        Initialize image manager
        
        Args:
            chat_tab: Parent chat tab instance
        """
        self.chat_tab = chat_tab
        self.image_label = chat_tab.image_label
        self.image_widget = chat_tab.image_widget
        self.image_counter_label = chat_tab.image_counter_label
        self.fit_image_checkbox = chat_tab.fit_image_checkbox
        self.generating_images_checkbox = chat_tab.generating_images_checkbox
        # NOTE: Do NOT cache image_folder - always access via self.chat_tab.image_folder
        # This ensures we use the current chat's image folder when chats are switched
        self.server_type = chat_tab.server_type
        self.client = chat_tab.client
        
        # Lock to prevent concurrent extraction requests
        self.extraction_lock = threading.Lock()
        
        # Hash tracking for duplicate prevention
        self._last_generation_hash = None
        
        # Create instance-specific signals (not global) - prevents image showing in both tabs
        self.signals = ImageSignals()
        
        # Connect signals for thread-safe image display
        self.signals.image_ready.connect(self._on_image_ready)
        self.signals.image_error.connect(self._on_image_error)
    
    @property
    def image_folder(self):
        """Get current chat's image folder from chat_tab"""
        return self.chat_tab.image_folder
    
    def _on_image_ready(self, image_path):
        """Handle image ready - called from main thread via signal"""
        print(f"[DEBUG-IMAGES] Image ready signal received: {image_path}")
        self._display_image_in_chat(image_path)
    
    def _on_image_error(self, error_msg):
        """Handle image error - called from main thread via signal"""
        print(f"[DEBUG-IMAGES] Image error signal received: {error_msg}")
        
    def toggle_image_view(self, state):
        """Toggle image viewer visibility with min/max size constraints"""
        is_visible = state == Qt.Checked
        self.image_widget.setVisible(is_visible)
        self.chat_tab.image_viewer_hidden = not is_visible
        
        if is_visible:
            # When showing images, load all images from the current chat's image folder
            self.load_chat_images()
            # When showing images, set min/max constraints so panel can't collapse
            # Minimum size: 300px width, 250px height - prevents disappearing
            self.image_widget.setMinimumSize(300, 250)
            # Maximum size: reasonable limits to prevent taking over entire view
            self.image_widget.setMaximumSize(2000, 2000)
        else:
            # When hiding images, remove constraints
            self.image_widget.setMinimumSize(0, 0)
            self.image_widget.setMaximumSize(16777215, 16777215)  # Qt default max
    
    def load_chat_images(self):
        """Load all images from the current chat's image folder"""
        try:
            # Save the current image path if one is selected (to preserve selection)
            current_image_path = None
            if (self.chat_tab.current_image_list and 
                0 <= self.chat_tab.current_image_index < len(self.chat_tab.current_image_list)):
                current_image_path = self.chat_tab.current_image_list[self.chat_tab.current_image_index]
            
            # Clear existing image list
            self.chat_tab.current_image_list = []
            self.chat_tab.current_image_index = 0
            
            # Check if image folder exists
            if not self.image_folder:
                self.image_counter_label.setText("0/0")
                self.image_label.setText("(No images yet)")
                return
            
            folder = Path(self.image_folder)
            if not folder.exists():
                self.image_counter_label.setText("0/0")
                self.image_label.setText("(No images yet)")
                return
            
            # Get all image files (jpg, png, gif, bmp, etc.)
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            image_files = []
            
            for item in folder.rglob('*'):
                if item.is_file() and item.suffix.lower() in image_extensions:
                    image_files.append(item)
            
            if not image_files:
                self.image_counter_label.setText("0/0")
                self.image_label.setText("(No images yet)")
                return
            
            # Sort by modification time (oldest first, so newest is last)
            image_files.sort(key=lambda x: x.stat().st_mtime)
            
            # Convert to strings
            self.chat_tab.current_image_list = [str(img) for img in image_files]
            
            # Try to restore the previously selected image, otherwise start with newest
            if current_image_path and current_image_path in self.chat_tab.current_image_list:
                self.chat_tab.current_image_index = self.chat_tab.current_image_list.index(current_image_path)
            else:
                self.chat_tab.current_image_index = len(self.chat_tab.current_image_list) - 1  # Start with newest
            
            # Display the current image
            if self.chat_tab.current_image_list:
                self.update_image_display()
            
        except Exception as e:
            print(f"[DEBUG] Error loading chat images: {e}")
            self.image_counter_label.setText("0/0")
            self.image_label.setText("(Error loading images)")
    
    def show_previous_image(self):
        """Show previous image"""
        if self.chat_tab.current_image_list:
            self.chat_tab.current_image_index = max(0, self.chat_tab.current_image_index - 1)
            self.update_image_display()
            self._sync_text_to_image()
    
    def show_next_image(self):
        """Show next image"""
        if self.chat_tab.current_image_list:
            self.chat_tab.current_image_index = min(
                len(self.chat_tab.current_image_list) - 1,
                self.chat_tab.current_image_index + 1
            )
            self.update_image_display()
            self._sync_text_to_image()
    
    def _sync_text_to_image(self):
        """If sync checkbox is checked, scroll chat to show the message that created this image"""
        try:
            # Check if sync checkbox exists and is checked
            if not hasattr(self.chat_tab, 'sync_image_text_checkbox'):
                return
            if not self.chat_tab.sync_image_text_checkbox.isChecked():
                return
            
            # Get current image filename
            if not (self.chat_tab.current_image_list and 
                    0 <= self.chat_tab.current_image_index < len(self.chat_tab.current_image_list)):
                return
            
            image_path = self.chat_tab.current_image_list[self.chat_tab.current_image_index]
            from pathlib import Path
            filename = Path(image_path).stem  # e.g., "2026-01-03_12-56-56_image"
            
            # Extract timestamp from filename (format: YYYY-MM-DD_HH-MM-SS_*)
            import re
            match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})', filename)
            if match:
                date_part = match.group(1)  # 2026-01-03
                time_part = match.group(2)  # 12-56-56
                # Convert to display format: 2026-01-03 12:56:56
                timestamp = f"{date_part} {time_part.replace('-', ':')}"
                self.chat_tab.scroll_to_timestamp(timestamp)
        except Exception as e:
            print(f"[DEBUG] Error syncing text to image: {e}")
    
    def zoom_in_image(self):
        """Zoom in on image"""
        self.chat_tab.current_zoom = min(3.0, self.chat_tab.current_zoom + 0.2)
        self.update_image_display()
    
    def zoom_out_image(self):
        """Zoom out from image"""
        self.chat_tab.current_zoom = max(0.5, self.chat_tab.current_zoom - 0.2)
        self.update_image_display()
    
    def fit_image(self):
        """Fit image to window"""
        self.chat_tab.current_zoom = 1.0
        if hasattr(self.image_label, 'set_fit_mode'):
            self.image_label.set_fit_mode(True)
        self.update_image_display()
    
    def on_fit_image_toggled(self, state):
        """Handle fit image checkbox toggle"""
        if hasattr(self.image_label, 'set_fit_mode'):
            self.image_label.set_fit_mode(state == Qt.Checked)
        if state == Qt.Checked:
            self.fit_image()
    
    def update_image_display(self):
        """Update image display with current zoom level and index"""
        if not self.chat_tab.current_image_list:
            return
        
        try:
            image_path = self.chat_tab.current_image_list[self.chat_tab.current_image_index]
            
            # Update counter label
            self.image_counter_label.setText(
                f"{self.chat_tab.current_image_index + 1}/{len(self.chat_tab.current_image_list)}"
            )
            
            pixmap = QPixmap(str(image_path))
            
            if not pixmap.isNull():
                # Use ResizableImageLabel's dynamic scaling
                fit_mode = self.fit_image_checkbox.isChecked()
                if hasattr(self.image_label, 'set_pixmap_with_fit'):
                    self.image_label.set_pixmap_with_fit(pixmap, fit_to_area=fit_mode)
                else:
                    # Fallback for regular QLabel
                    zoom = self.chat_tab.current_zoom
                    scaled = pixmap.scaledToHeight(int(300 * zoom), Qt.SmoothTransformation)
                    self.image_label.setPixmap(scaled)
                self.image_label.setVisible(True)
                self.chat_tab.current_image_pixmap = pixmap
        except Exception as e:
            print(f"[DEBUG] Error updating image display: {e}")
    
    def trigger_image_generation_if_needed(self, response_text, timestamp=None):
        """Check if 'Generate Image' is enabled and extract + generate image"""
        try:
            settings = load_settings()
            
            # Guard against duplicate triggers for the same response
            response_hash = hash(response_text[:100]) if response_text else 0
            if hasattr(self, '_last_generation_hash') and self._last_generation_hash == response_hash:
                print(f"[IMAGE-GEN] Skipping duplicate image generation (hash={response_hash})")
                return
            self._last_generation_hash = response_hash
            
            # Check if prompt extraction is enabled
            enable_extraction = settings.get("enable_prompt_extraction", False)
            
            # Get extraction settings from image_settings
            extraction_model = settings.get("extraction_model", "dolphin-2.1:2.4b")
            extraction_provider = settings.get("extraction_model_provider", "ollama")
            extraction_url = settings.get("extraction_provider_url", "http://localhost:11434")
            
            # Get system and user prompts from image_settings
            system_prompt = settings.get("extraction_system_prompt", "")
            user_prompt = settings.get("extraction_user_prompt", "")
            
            if not system_prompt or not user_prompt:
                print("[DEBUG] System or user prompt not configured in image settings")
                return
            
            print(f"[DEBUG] Image generation triggered with timestamp: {timestamp}")
            print(f"[DEBUG] Prompt extraction enabled: {enable_extraction}")
            
            if enable_extraction:
                # Extract prompt using LLM then generate image
                thread = threading.Thread(
                    target=self._extract_and_generate_image,
                    args=(response_text, extraction_model, extraction_provider, extraction_url, system_prompt, user_prompt, timestamp),
                    daemon=True
                )
                thread.start()
            else:
                # Use full LLM response as the prompt directly
                thread = threading.Thread(
                    target=self._generate_image_from_response,
                    args=(response_text, timestamp),
                    daemon=True
                )
                thread.start()
            
        except Exception as e:
            print(f"[DEBUG] Could not trigger image generation: {e}")
    
    def _generate_image_from_response(self, response_text, timestamp=None):
        """Generate image directly from full LLM response without extraction"""
        try:
            print("[DEBUG] Generating image from full LLM response (extraction disabled)...")
            print(f"[DEBUG] Using response as image prompt: {response_text[:150]}...")
            
            # Use the full response as the image prompt
            image_prompt = response_text.strip()
            
            if not image_prompt:
                print("[DEBUG] ❌ Response text is empty, cannot generate image")
                return
            
            print(f"[DEBUG] Image prompt length: {len(image_prompt)} chars")
            
            # Generate image with the response as prompt
            self._generate_and_display_image(image_prompt, timestamp)
            
        except Exception as e:
            print(f"[DEBUG] Error generating image from response: {e}")
    
    def _extract_and_generate_image(self, response_text, extraction_model, extraction_provider, extraction_url, system_prompt, user_prompt, timestamp=None):
        """Extract image prompt using custom prompts and generate image"""
        # Use lock to prevent concurrent extraction requests
        if not self.extraction_lock.acquire(blocking=False):
            print("[IMAGE-GEN] Extraction already in progress, skipping this request")
            return
        
        try:
            # Request Ollama throttle for image extraction (minor request)
            if not OllamaRequestManager.acquire_minor_request("image_extraction"):
                print("[IMAGE-GEN] ⚠️ Skipped extraction - Ollama server busy with generation")
                return
            
            try:
                print("[DEBUG] Extracting image prompt from LLM response...")
                print(f"[DEBUG] Extraction settings: provider={extraction_provider}, url={extraction_url}, model={extraction_model}")
                
                # Validate extraction model is set
                if not extraction_model or extraction_model == "(click Refresh Models)":
                    print("[DEBUG] ❌ Extraction model not set. Go to Image Settings and click 'Refresh' to load models.")
                    return
                
                # Use the extraction settings to get clean prompt
                from ollama_client import OllamaClient
                from llama_client import LlamaServerClient
                
                if extraction_provider == "ollama":
                    client = OllamaClient(extraction_url)
                else:
                    client = LlamaServerClient(extraction_url)
                
                # Build the extraction prompt by combining system + user prompt
                # Format user prompt with the response
                formatted_user_prompt = user_prompt.format(response=response_text)
                
                # Combine system prompt and formatted user prompt into single prompt for Ollama
                # Ollama uses a single prompt, so we format it as: [INST]system\n\nuser_prompt[/INST]
                combined_prompt = f"[INST]{system_prompt}\n\n{formatted_user_prompt}[/INST]"
                
                print(f"[DEBUG] Calling {extraction_provider} for prompt extraction with model: {extraction_model}")
                print(f"[DEBUG] System prompt length: {len(system_prompt)} chars")
                print(f"[DEBUG] System prompt START: {system_prompt[:150]}...")
                print(f"[DEBUG] User prompt length: {len(user_prompt)} chars")
                print(f"[DEBUG] User prompt START: {user_prompt[:150]}...")
                
                # Call generate with system parameter for better context
                extracted_prompt = client.generate(
                    combined_prompt,
                    model=extraction_model,
                    system=system_prompt,
                    timeout=120  # Give extraction enough time
                )
                
                if not extracted_prompt or not extracted_prompt.strip():
                    if DebugConfig.extraction_full_result:
                        print("[DEBUG] Could not extract valid prompt from response")
                    return
                
                if DebugConfig.extraction_full_result:
                    print(f"[DEBUG] ✅ Full extracted prompt:\n{extracted_prompt}")
                
                # Generate image from extracted prompt
                self._generate_and_display_image(extracted_prompt, timestamp)
                
            except Exception as e:
                error_msg = str(e)
                print(f"[DEBUG] ❌ Error during image extraction: {e}")
                print(f"[DEBUG] Make sure the extraction model is available in {extraction_provider}")
                print(f"[DEBUG] If using Ollama, you may need to run: ollama pull {extraction_model}")
                import traceback
                traceback.print_exc()
                
                # Provide user-friendly error message in chat tab
                if "No connection could be made" in error_msg or "refused" in error_msg:
                    # Server not running
                    user_message = f"❌ **Image Generation Failed**\n\n"
                    user_message += f"Cannot reach the extraction model server ({extraction_provider.upper()} at {extraction_url}).\n\n"
                    user_message += f"**To fix this:**\n"
                    if extraction_provider == "ollama":
                        user_message += f"1. Make sure Ollama is running\n"
                        user_message += f"2. Check Settings → Image Settings → Extraction Model Provider\n"
                        user_message += f"3. Verify the extraction model '{extraction_model}' is installed\n"
                    else:
                        user_message += f"1. Start your llama-server at {extraction_url}\n"
                        user_message += f"2. Check Settings → Image Settings → Extraction Model Provider\n"
                        user_message += f"3. Verify the extraction model '{extraction_model}' is available\n"
                    user_message += f"\nTry again once the server is running."
                elif "model" in error_msg.lower() and "not found" in error_msg.lower():
                    # Model not found
                    user_message = f"❌ **Image Generation Failed**\n\n"
                    user_message += f"The extraction model '{extraction_model}' is not available in {extraction_provider.upper()}.\n\n"
                    user_message += f"**To fix this:**\n"
                    user_message += f"1. Go to Settings → Image Settings tab\n"
                    user_message += f"2. Click 'Refresh Models' to load available models\n"
                    user_message += f"3. Select a different extraction model from the dropdown\n"
                    user_message += f"\n**Or install the model:**\n"
                    if extraction_provider == "ollama":
                        user_message += f"Run: `ollama pull {extraction_model}`"
                    else:
                        user_message += f"Make sure the model is loaded in your llama-server"
                else:
                    # Generic error
                    user_message = f"❌ **Image Generation Failed**\n\n"
                    user_message += f"Error: {error_msg}\n\n"
                    user_message += f"**To fix this:**\n"
                    user_message += f"1. Check Settings → Image Settings\n"
                    user_message += f"2. Verify the extraction model provider ({extraction_provider}) is configured correctly\n"
                    user_message += f"3. Make sure the extraction model '{extraction_model}' is available\n"
                
                # Add system message to chat history to show user
                if hasattr(self, 'chat_tab') and self.chat_tab:
                    self.chat_tab.add_system_message(user_message)
            finally:
                OllamaRequestManager.release_minor_request("image_extraction")
        finally:
            # Always release the lock when extraction completes
            self.extraction_lock.release()
    
    def _generate_and_display_image(self, prompt, timestamp=None):
        """Generate image from prompt and save/display with timestamp"""
        try:
            from image_client import ComfyUIClient
            
            settings = load_settings()
            comfyui_url = settings.get("comfyui_url", "http://127.0.0.1:8188")
            
            print(f"[DEBUG] Generating image from prompt: {prompt[:50]}...")
            
            # Initialize ComfyUI client with chat-specific image folder
            client = ComfyUIClient(comfyui_url, output_folder=self.image_folder)
            
            # Get model name and remove folder prefix if present
            model_display = settings.get("checkpoint_model", "")
            checkpoint_model = model_display
            if model_display and " " in model_display and model_display.startswith("["):
                checkpoint_model = model_display.split("] ", 1)[1]
            
            # Get loader type
            loader_type = settings.get("loader_type", "standard")
            
            # Get VAE and text encoder
            vae_model = settings.get("vae_model", "(auto)")
            text_encoder_model = settings.get("clip_name1", "(auto)")
            text_encoder_model_2 = settings.get("clip_name2", "(same as CLIP Name 1)")
            
            # Get CLIP loader settings
            clip_loader = settings.get("clip_loader", "CLIPLoader")
            clip_type = settings.get("clip_type", "stable_diffusion")
            weight_dtype = settings.get("unet_weight_dtype", "default")
            
            # Get scheduler
            scheduler = settings.get("image_scheduler", "normal")
            
            # Get LoRA settings
            # Convert to proper types - JSON might store as strings
            lora_enabled_raw = settings.get("lora_enabled", False)
            if isinstance(lora_enabled_raw, str):
                lora_enabled = lora_enabled_raw.lower() in ('true', '1', 'yes')
            else:
                lora_enabled = bool(lora_enabled_raw)
            
            lora_name = settings.get("lora_name", "(none)")
            lora_strength = float(settings.get("lora_strength", "1.0"))
            
            result = client.generate_from_text(
                prompt,
                resolution=settings.get("image_resolution", "768x768"),
                steps=int(settings.get("image_steps", "20")),
                cfg_scale=float(settings.get("image_cfg_scale", "7.5")),
                sampler=settings.get("image_sampler", "euler"),
                scheduler=scheduler,
                checkpoint_model=checkpoint_model,
                loader_type=loader_type,
                vae_model=vae_model,
                text_encoder_model=text_encoder_model,
                text_encoder_model_2=text_encoder_model_2,
                clip_type=clip_type,
                clip_loader=clip_loader,
                weight_dtype=weight_dtype,
                lora_enabled=lora_enabled,
                lora_name=lora_name,
                lora_strength=lora_strength,
                timeout=int(settings.get("generation_timeout", "300"))
            )
            
            if not result:
                print("[DEBUG] Image generation failed")
                return
            
            print(f"[DEBUG] Image generated: {result}")
            
            # If we have a timestamp, rename image to timestamp format
            if timestamp:
                try:
                    # Convert timestamp HH:MM:SS to filename format (same as TTS: HH-MM-SS)
                    filename_timestamp = str(timestamp).replace(":", "-").replace(" ", "_").replace(".", "-")
                    
                    # Source image path (already in the correct folder)
                    source_path = Path(result).absolute()
                    
                    # Destination: same timestamp name as TTS, but with .png extension
                    dest_filename = f"{filename_timestamp}.png"
                    dest_path = source_path.parent / dest_filename
                    
                    # Rename image with timestamp
                    if source_path.exists() and source_path != dest_path:
                        source_path.rename(dest_path)
                        print(f"[DEBUG] Image renamed to: {dest_path}")
                        self.signals.image_ready.emit(str(dest_path))
                    else:
                        # Already has correct name or file not found
                        self.signals.image_ready.emit(result)
                except Exception as rename_error:
                    print(f"[DEBUG] Error renaming image: {rename_error}")
                    # Still try to display from original path
                    self.signals.image_ready.emit(result)
            else:
                # No timestamp, just display as-is
                self.signals.image_ready.emit(result)
            
        except Exception as e:
            print(f"[DEBUG] Error generating/displaying image: {e}")
            self.signals.image_error.emit(str(e))
    
    def _display_image_in_chat(self, image_path):
        """Display image in the chat image area"""
        try:
            path = Path(image_path)
            if not path.exists():
                print(f"[DEBUG] Image file not found: {image_path}")
                return
            
            # Add to image list if not already there
            image_path_str = str(path)
            if image_path_str not in self.chat_tab.current_image_list:
                self.chat_tab.current_image_list.append(image_path_str)
            
            # Set to display the last added image
            self.chat_tab.current_image_index = len(self.chat_tab.current_image_list) - 1
            
            # Load pixmap
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                print(f"[DEBUG] Failed to load image: {image_path}")
                return
            
            # Store reference to prevent garbage collection
            self.chat_tab.current_image_pixmap = pixmap
            
            # Update counter label
            self.image_counter_label.setText(
                f"{self.chat_tab.current_image_index + 1}/{len(self.chat_tab.current_image_list)}"
            )
            
            # Display using ResizableImageLabel's dynamic scaling
            fit_mode = self.fit_image_checkbox.isChecked()
            if hasattr(self.image_label, 'set_pixmap_with_fit'):
                self.image_label.set_pixmap_with_fit(pixmap, fit_to_area=fit_mode)
            else:
                # Fallback for regular QLabel
                scaled_pixmap = pixmap.scaledToWidth(400, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
            
            print(f"[DEBUG] Image displayed in chat: {image_path}")
            
        except Exception as e:
            print(f"[DEBUG] Error displaying image: {e}")
            import traceback
            traceback.print_exc()
