"""
Image Settings Right Tab - Image Generation and Display Panel
Handles: image generation, extraction testing, image gallery navigation, display
"""
# pylint: disable=no-name-in-module

import threading
import traceback
from pathlib import Path

from debug_config import DebugConfig
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QScrollArea, QMessageBox, QCheckBox, QRadioButton, QButtonGroup, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap


class ResizableImageLabel(QLabel):
    """Custom QLabel that scales images dynamically when resized"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = None
        self.fit_to_area = True
        self.scroll_area = None  # Reference to parent scroll area (set after creation)
        # Start centered (fit_to_area is True by default)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("border: 1px solid #cccccc; padding: 10px; background-color: #f9f9f9;")
        self.setMinimumHeight(300)
        # Allow full expansion to available space - resizing is controlled by debounce timer
        # Set size policy to expand and fill available space
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Debounce timer to defer scaling during resize drag
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._scale_and_display)
        self.resize_timer.setInterval(100)
    
    def set_pixmap_with_fit(self, pixmap, fit_to_area=True):
        """Set the pixmap and store original for rescaling"""
        if pixmap and not pixmap.isNull():
            self.original_pixmap = pixmap
            self.fit_to_area = fit_to_area
            self._scale_and_display()
    
    def set_fit_mode(self, fit_to_area):
        """Change fit mode and rescale"""
        self.fit_to_area = fit_to_area
        # Update alignment: center when fit_to_area, top-left when not fit
        if fit_to_area:
            self.setAlignment(Qt.AlignCenter)
        else:
            self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        if self.original_pixmap:
            self._scale_and_display()
    
    def _scale_and_display(self):
        """Scale and display the image based on current size and fit mode"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            return
        
        if self.fit_to_area and self.scroll_area:
            # Use scroll area's viewport size (the visible area) as constraint
            # This ensures image fits completely without creating scroll bars
            viewport = self.scroll_area.viewport()
            # Use larger buffer to prevent any horizontal/vertical scroll bar
            display_width = viewport.width() - 40
            display_height = viewport.height() - 40
        else:
            # Get label's own size
            display_width = self.width() - 20
            display_height = self.height() - 20
        
        if display_width <= 0 or display_height <= 0:
            return
        
        if self.fit_to_area:
            # Scale to fit within available area while maintaining aspect ratio
            scaled = self.original_pixmap.scaledToWidth(display_width, Qt.SmoothTransformation)
            if scaled.height() > display_height:
                scaled = self.original_pixmap.scaledToHeight(display_height, Qt.SmoothTransformation)
        else:
            # Non-fit mode: scale to fixed width but respect maximum
            target_width = min(600, display_width)
            scaled = self.original_pixmap.scaledToWidth(target_width, Qt.SmoothTransformation)
        
        QLabel.setPixmap(self, scaled)
    
    def resizeEvent(self, event):
        """Defer scaling during resize drag to avoid sluggish performance"""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.resize_timer.stop()
            self.resize_timer.start()


class QtImageSettingsRightTab(QWidget):
    """Right panel for image generation and display"""
    
    # Signal to refresh image list from background thread
    image_generation_complete = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Connect signal to refresh handler
        self.image_generation_complete.connect(self._on_image_generation_complete)
        
        # Image navigation tracking
        self.generated_images = []
        self.current_image_index = -1
        self.generated_images_folder = Path(__file__).parent.parent / "generated_images"
        self.current_pixmap = None
        
        # Pending data from background thread generation
        self._pending_pixmap = None
        self._pending_fit_mode = False
        
        # Extraction mode tracking
        self.current_extracted_prompt = ""
        
        # Settings references from left panel (will be set via setter methods)
        self.comfyui_url = "http://127.0.0.1:8188"
        self.resolution_combo = None
        self.steps_spinbox = None
        self.cfg_scale_spinbox = None
        self.sampler_combo = None
        self.scheduler_combo = None
        self.generation_timeout_spinbox = None
        self.model_combo = None
        self.vae_combo = None
        self.encoder_combo = None
        self.clip_type_combo = None
        self.clip_loader_combo = None
        self.unet_weight_dtype_combo = None
        self.loader_group = None
        self.loader_standard_rb = None
        self.loader_gguf_rb = None
        self.loader_unet_rb = None
        self.loader_diffuse_rb = None
        
        # LoRA settings
        self.lora_enabled_checkbox = None
        self.lora_combo = None
        self.lora_strength_spinbox = None
        
        # Extraction settings from left panel
        self.provider_combo = None
        self.provider_url_input = None
        self.extraction_model_combo = None
        self.extraction_temperature_spinbox = None
        self.extraction_timeout_spinbox = None
        self.system_prompt_text = None
        self.user_prompt_text = None
        self.prefix_input = None
        self.suffix_input = None
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create all right panel widgets"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(layout)
        
        # Title
        test_title = QLabel("Test Image Generation")
        test_title_font = QFont()
        test_title_font.setBold(True)
        test_title_font.setPointSize(10)
        test_title.setFont(test_title_font)
        layout.addWidget(test_title)
        
        # Prompt text box
        prompt_label = QLabel("Prompt:")
        prompt_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(prompt_label)
        
        self.test_prompt_text = QTextEdit()
        self.test_prompt_text.setPlainText("4k, high quality, a busy restaurant in the city")
        self.test_prompt_text.setMinimumHeight(100)
        self.test_prompt_text.setMaximumHeight(120)
        layout.addWidget(self.test_prompt_text)
        
        # Mode selection - radio buttons
        mode_label = QLabel("Mode:")
        mode_label.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(mode_label)
        
        self.mode_group = QButtonGroup()
        self.mode_generate_rb = QRadioButton("Generate Image from Prompt Text")
        self.mode_extract_rb = QRadioButton("Test/Finetune Extraction - Show Prompt Only")
        self.mode_extract_gen_rb = QRadioButton("Test/Finetune Extraction - Show Prompt & Generate Image")
        
        self.mode_generate_rb.setChecked(True)
        
        self.mode_group.addButton(self.mode_generate_rb, 0)
        self.mode_group.addButton(self.mode_extract_rb, 1)
        self.mode_group.addButton(self.mode_extract_gen_rb, 2)
        
        self.mode_group.buttonClicked.connect(self._on_test_mode_changed)
        
        layout.addWidget(self.mode_generate_rb)
        layout.addWidget(self.mode_extract_rb)
        layout.addWidget(self.mode_extract_gen_rb)
        
        # Test/Extract button
        self.test_gen_btn = QPushButton("Generate Image")
        self.test_gen_btn.setStyleSheet("background-color: #6633ff; color: white; font-weight: bold; padding: 5px;")
        self.test_gen_btn.clicked.connect(self.test_image_generation)
        layout.addWidget(self.test_gen_btn)
        
        # Status label
        self.test_status_label = QLabel("Ready to test")
        self.test_status_label.setStyleSheet("color: #666666; font-size: 8pt; padding: 5px;")
        layout.addWidget(self.test_status_label)
        
        # Extracted Prompt section
        extracted_title = QLabel("Extracted Prompt:")
        extracted_title.setFont(QFont("Arial", 9, QFont.Bold))
        layout.addWidget(extracted_title)
        
        self.extracted_prompt_text = QTextEdit()
        self.extracted_prompt_text.setReadOnly(True)
        self.extracted_prompt_text.setPlainText("(Extracted prompt will appear here)")
        self.extracted_prompt_text.setMinimumHeight(60)
        self.extracted_prompt_text.setMaximumHeight(80)
        layout.addWidget(self.extracted_prompt_text)
        
        # Generate from extracted button
        self.generate_from_extracted_btn = QPushButton("Generate Image from Extracted")
        self.generate_from_extracted_btn.setStyleSheet("background-color: #00aa44; color: white; font-weight: bold; padding: 5px;")
        self.generate_from_extracted_btn.clicked.connect(self.generate_from_extracted_prompt)
        layout.addWidget(self.generate_from_extracted_btn)
        
        # Image display area header
        image_header_layout = QHBoxLayout()
        
        self.prev_image_btn = QPushButton("◀ Previous")
        self.prev_image_btn.setMaximumWidth(100)
        self.prev_image_btn.clicked.connect(self._show_previous_image)
        image_header_layout.addWidget(self.prev_image_btn)
        
        self.image_counter_label = QLabel("No images")
        self.image_counter_label.setAlignment(Qt.AlignCenter)
        self.image_counter_label.setMinimumWidth(100)
        image_header_layout.addWidget(self.image_counter_label)
        
        self.next_image_btn = QPushButton("Next ▶")
        self.next_image_btn.setMaximumWidth(100)
        self.next_image_btn.clicked.connect(self._show_next_image)
        image_header_layout.addWidget(self.next_image_btn)
        
        self.delete_image_btn = QPushButton("🗑️ Delete")
        self.delete_image_btn.setMaximumWidth(80)
        self.delete_image_btn.setStyleSheet("background-color: #cc3333; color: white;")
        self.delete_image_btn.clicked.connect(self._delete_current_image)
        image_header_layout.addWidget(self.delete_image_btn)
        
        self.fit_image_checkbox = QCheckBox("Fit to area")
        self.fit_image_checkbox.setChecked(True)
        self.fit_image_checkbox.stateChanged.connect(self._on_fit_image_changed)
        image_header_layout.addWidget(self.fit_image_checkbox)
        
        image_header_layout.addStretch()
        layout.addLayout(image_header_layout)
        
        # Image scroll area
        self.image_scroll = QScrollArea()
        # Enable widget resizing so label fills available space
        # Debounced resize timer prevents cascading zoom events
        self.image_scroll.setWidgetResizable(True)
        self.image_display = ResizableImageLabel()
        self.image_display.setText("(Generated images will display here)")
        # Set scroll area reference so image label can use viewport size for fitting
        self.image_display.scroll_area = self.image_scroll
        self.image_scroll.setWidget(self.image_display)
        layout.addWidget(self.image_scroll, 1)
        
        # Don't auto-refresh on startup - only refresh when user explicitly interacts
        # This prevents auto-loading and displaying previous images when app starts
    
    def set_generation_settings(self, comfyui_url_input, resolution_combo, steps_spinbox, 
                                cfg_scale_spinbox, sampler_combo, scheduler_combo, 
                                model_combo, generation_timeout_spinbox):
        """Store references to generation settings from main tab"""
        self.comfyui_url_input = comfyui_url_input
        self.resolution_combo = resolution_combo
        self.steps_spinbox = steps_spinbox
        self.cfg_scale_spinbox = cfg_scale_spinbox
        self.sampler_combo = sampler_combo
        self.scheduler_combo = scheduler_combo
        self.model_combo = model_combo
        self.generation_timeout_spinbox = generation_timeout_spinbox
        # Store the URL for direct access (get from widget)
        if hasattr(comfyui_url_input, 'text'):
            self.comfyui_url = comfyui_url_input.text()
        else:
            self.comfyui_url = str(comfyui_url_input)
    
    def set_extraction_settings(self, provider_combo, provider_url_input, extraction_model_combo,
                                extraction_model_unload_combo,
                                extraction_temperature_spinbox,
                                extraction_timeout_spinbox, system_prompt_text, user_prompt_text,
                                prefix_input, suffix_input, min_response_length_spinbox):
        """Store references to extraction settings from main tab"""
        self.provider_combo = provider_combo
        self.provider_url_input = provider_url_input
        self.extraction_model_combo = extraction_model_combo
        self.extraction_model_unload_combo = extraction_model_unload_combo
        self.extraction_temperature_spinbox = extraction_temperature_spinbox
        self.extraction_timeout_spinbox = extraction_timeout_spinbox
        self.system_prompt_text = system_prompt_text
        self.user_prompt_text = user_prompt_text
        self.prefix_input = prefix_input
        self.suffix_input = suffix_input
        self.min_response_length_spinbox = min_response_length_spinbox
    
    def set_lora_settings(self, lora_enabled_checkbox, lora_combo, lora_strength_spinbox):
        """Store references to LoRA settings from main tab"""
        self.lora_enabled_checkbox = lora_enabled_checkbox
        self.lora_combo = lora_combo
        self.lora_strength_spinbox = lora_strength_spinbox
    
    def _on_image_generation_complete(self):
        """Signal handler called from GUI thread when image generation completes"""
        # Display the generated image immediately if available
        if hasattr(self, '_pending_pixmap') and self._pending_pixmap:
            fit_mode = getattr(self, '_pending_fit_mode', False)
            self.image_display.set_pixmap_with_fit(self._pending_pixmap, fit_to_area=fit_mode)
            self.image_display.setText("")
            # Clear pending data
            self._pending_pixmap = None
            self._pending_fit_mode = False
        
        # Refresh image list with slight delay to ensure file is written
        QTimer.singleShot(200, lambda: self._refresh_image_list(show_newest=True))
    
    def _refresh_image_list(self, show_newest=False):
        """Refresh the list of generated images from the folder"""
        try:
            if self.generated_images_folder.exists():
                image_files = sorted(
                    self.generated_images_folder.glob("*.png"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                self.generated_images = [str(p) for p in image_files]
                
                if self.generated_images:
                    if self.current_image_index < 0 or show_newest:
                        self.current_image_index = 0
                        self._display_image_at_index(0)
                else:
                    self.current_image_index = -1
                    self.image_counter_label.setText("No images")
                
                self._update_navigation_buttons()
            else:
                self.generated_images = []
                self.current_image_index = -1
                self.image_counter_label.setText("No images")
        except Exception as e:
            print(f"[ERROR] Refreshing image list: {e}")
    
    def _update_navigation_buttons(self):
        """Update Previous/Next button states and counter"""
        if not self.generated_images:
            self.image_counter_label.setText("No images")
            self.prev_image_btn.setEnabled(False)
            self.next_image_btn.setEnabled(False)
            self.delete_image_btn.setEnabled(False)
            return
        
        total = len(self.generated_images)
        current = total - self.current_image_index
        self.image_counter_label.setText(f"{current} / {total}")
        
        self.prev_image_btn.setEnabled(self.current_image_index < len(self.generated_images) - 1)
        self.next_image_btn.setEnabled(self.current_image_index > 0)
        self.delete_image_btn.setEnabled(True)
    
    def _display_image_at_index(self, index):
        """Display image at given index"""
        if not self.generated_images or index < 0 or index >= len(self.generated_images):
            return
        
        try:
            img_path = self.generated_images[index]
            pixmap = QPixmap(img_path)
            
            if pixmap.isNull():
                print(f"[IMAGE] Failed to load image: {img_path}")
                self.image_display.setText(f"Failed to load image")
                return
            
            self.current_pixmap = pixmap
            fit_mode = self.fit_image_checkbox.isChecked()
            self.image_display.set_pixmap_with_fit(pixmap, fit_to_area=fit_mode)
            self.image_display.setText("")
            self.current_image_index = index
            self._update_navigation_buttons()
            # Console message uses same numbering as UI (oldest to newest)
            display_number = len(self.generated_images) - index
            print(f"[IMAGE] Displaying image {display_number}/{len(self.generated_images)}: {Path(img_path).name}")
        except Exception as e:
            print(f"[IMAGE] Error displaying image at index {index}: {e}")
            self.image_display.setText(f"Error loading image")
    
    def _show_previous_image(self):
        """Show previous image (older)"""
        if self.current_image_index < len(self.generated_images) - 1:
            self._display_image_at_index(self.current_image_index + 1)
    
    def _show_next_image(self):
        """Show next image (newer)"""
        if self.current_image_index > 0:
            self._display_image_at_index(self.current_image_index - 1)
    
    def _delete_current_image(self):
        """Delete current image with confirmation"""
        if self.current_image_index < 0 or not self.generated_images:
            return
        
        img_path = self.generated_images[self.current_image_index]
        img_name = Path(img_path).name
        
        reply = QMessageBox.question(
            self,
            "Delete Image",
            f"Are you sure you want to delete:\n\n{img_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                Path(img_path).unlink()
                print(f"[IMAGE] Deleted: {img_path}")
                
                self._refresh_image_list()
                
                if self.generated_images:
                    if self.current_image_index >= len(self.generated_images):
                        self.current_image_index = len(self.generated_images) - 1
                    self._display_image_at_index(self.current_image_index)
                else:
                    self.image_display.setText("(Generated images will display here)")
                    self.image_counter_label.setText("No images")
                
                self.test_status_label.setText(f"✅ Image deleted: {img_name}")
                self.test_status_label.setStyleSheet("color: #009900;")
            except Exception as e:
                print(f"[IMAGE] Error deleting image: {e}")
                self.test_status_label.setText(f"❌ Error deleting image: {str(e)}")
                self.test_status_label.setStyleSheet("color: #cc0000;")
    
    def _on_fit_image_changed(self):
        """Handle fit image checkbox change"""
        is_fit = self.fit_image_checkbox.isChecked()
        self.image_display.set_fit_mode(is_fit)
    
    def _on_test_mode_changed(self):
        """Handle test mode radio button change"""
        if self.mode_generate_rb.isChecked():
            self.test_gen_btn.setText("Generate Image")
        elif self.mode_extract_rb.isChecked():
            self.test_gen_btn.setText("Extract Prompt Only")
        elif self.mode_extract_gen_rb.isChecked():
            self.test_gen_btn.setText("Extract & Generate Image")
    
    def test_image_generation(self):
        """Test image generation or extraction based on selected mode"""
        if self.mode_generate_rb.isChecked():
            self._generate_image_from_prompt(self.test_prompt_text.toPlainText().strip())
        elif self.mode_extract_rb.isChecked():
            self._extract_prompt_only()
        elif self.mode_extract_gen_rb.isChecked():
            self._extract_prompt_and_generate()
    
    def generate_from_extracted_prompt(self):
        """Generate image from the extracted prompt text"""
        extracted_text = self.extracted_prompt_text.toPlainText().strip()
        if not extracted_text:
            self.test_status_label.setText("Error: No extracted prompt available")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            return
        self._generate_image_from_prompt(extracted_text)
    
    def _clean_extracted_prompt(self, extracted_text):
        """Remove common template text from extracted prompt"""
        if not extracted_text:
            return extracted_text
        
        prefixes_to_remove = [
            "Convert the LLM response into a single text-to-image prompt:",
            "Convert this LLM response into a single text-to-image prompt.",
            "Given this LLM response, output ONLY the image generation prompt:",
            "IMAGE PROMPT:",
            "Image prompt:",
            "Final prompt:",
            "FINAL PROMPT:",
        ]
        
        cleaned = extracted_text.strip()
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()
                break
        
        if "Optional constraints:" in cleaned:
            cleaned = cleaned.split("Optional constraints:")[0].strip()
        
        if "- setting:" in cleaned:
            cleaned = cleaned.split("- setting:")[0].strip()
        
        if "- character:" in cleaned:
            cleaned = cleaned.split("- character:")[0].strip()
        
        return cleaned.strip()
    
    def _display_extracted_prompt(self):
        """Display extracted prompt in UI - thread-safe method"""
        if hasattr(self, '_pending_extracted_prompt'):
            prompt_text = self._pending_extracted_prompt
            cleaned_prompt = self._clean_extracted_prompt(prompt_text)
            print(f"[UI_UPDATE] Updating extracted prompt display: {cleaned_prompt[:50]}...")
            self.extracted_prompt_text.setPlainText(cleaned_prompt)
            self.test_status_label.setText("✅ Prompt extracted successfully!")
            self.test_status_label.setStyleSheet("color: #009900;")
            print(f"[UI_UPDATE] ✅ UI updated with extracted prompt")
            delattr(self, '_pending_extracted_prompt')
        else:
            print(f"[UI_UPDATE] ERROR: No pending extracted prompt found!")
    
    def _display_extraction_error(self):
        """Display extraction error in UI - thread-safe method"""
        if hasattr(self, '_pending_error_msg'):
            error_msg = self._pending_error_msg
            print(f"[UI_UPDATE] Displaying error: {error_msg}")
            self.test_status_label.setText(f"❌ {error_msg}")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            delattr(self, '_pending_error_msg')
        else:
            print(f"[UI_UPDATE] ERROR: No pending error message found!")
    
    def _extract_prompt_only(self):
        """Extract prompt and display result (no generation)"""
        input_text = self.test_prompt_text.toPlainText().strip()
        if not input_text:
            self.test_status_label.setText("Error: Input text is empty")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            return
        
        # Validate model is selected
        model = self.extraction_model_combo.currentText()
        if not model or model.startswith("(click"):
            self.test_status_label.setText("❌ Error: No extraction model selected. Click 'Refresh' first.")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            return
        
        self.test_status_label.setText("Extracting prompt...")
        self.test_status_label.setStyleSheet("color: #0066cc;")
        
        def extract_text():
            try:
                from ollama_client import OllamaClient
                from llama_client import LlamaServerClient
                
                provider = self.provider_combo.currentText()
                url = self.provider_url_input.text()
                model = self.extraction_model_combo.currentText()
                temperature = self.extraction_temperature_spinbox.value()
                
                system_prompt = self.system_prompt_text.toPlainText()
                user_prompt = self.user_prompt_text.toPlainText()
                final_user_prompt = user_prompt.replace("{response}", input_text)
                
                if provider == "ollama":
                    client = OllamaClient(url)
                else:
                    client = LlamaServerClient(url)
                
                if DebugConfig.extraction_enabled:
                    print(f"\n[EXTRACT] Extracting prompt...")
                if DebugConfig.extraction_enabled:
                    print(f"[EXTRACT] Provider: {provider}")
                if DebugConfig.extraction_enabled:
                    print(f"[EXTRACT] Model: {model}")
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_user_prompt}
                ]
                
                extracted = client.generate_with_context(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    num_predict=512
                )
                extracted = extracted.strip() if extracted else ""
                
                if extracted:
                    if DebugConfig.extraction_enabled:
                        print(f"[EXTRACT] ✅ Extracted: {extracted}")
                    
                    prefix = self.prefix_input.text()
                    suffix = self.suffix_input.text()
                    final_prompt = f"{prefix}{extracted}{suffix}".strip()
                    
                    # Add realistic keywords only for "Persons" built-in prompt style
                    from settings_manager import load_settings
                    settings = load_settings()
                    builtin_style = getattr(self.parent_tab, 'builtin_prompt_combo', None)
                    current_style = builtin_style.currentText() if builtin_style else "Generic"
                    
                    if settings.get("add_realistic_keywords", True) and current_style == "Persons":
                        realistic_keywords = ["photorealistic", "realistic", "8k", "detailed", "high quality"]
                        has_keywords = any(keyword in final_prompt.lower() for keyword in realistic_keywords)
                        if not has_keywords:
                            final_prompt = f"photorealistic, detailed, 8k, high quality, {final_prompt}"
                            if DebugConfig.extraction_enabled:
                                print(f"[EXTRACT] Added realistic keywords (Persons mode)")
                    
                    self.current_extracted_prompt = final_prompt
                    self._pending_extracted_prompt = final_prompt
                    QTimer.singleShot(0, self._display_extracted_prompt)
                else:
                    if DebugConfig.extraction_enabled:
                        print(f"[EXTRACT] ❌ Extraction returned empty")
                    self._pending_error_msg = "Extraction failed - empty result"
                    QTimer.singleShot(0, self._display_extraction_error)
                    
            except Exception as e:
                if DebugConfig.extraction_enabled:
                    print(f"[EXTRACT] ❌ Error: {e}")
                traceback.print_exc()
                self._pending_error_msg = f"Error: {str(e)}"
                QTimer.singleShot(0, self._display_extraction_error)
        
        thread = threading.Thread(target=extract_text, daemon=True)
        thread.start()
    
    def _extract_prompt_and_generate(self):
        """Extract prompt and generate image from it"""
        input_text = self.test_prompt_text.toPlainText().strip()
        if not input_text:
            self.test_status_label.setText("Error: Input text is empty")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            return
        
        # Validate model is selected
        model = self.extraction_model_combo.currentText()
        if not model or model.startswith("(click"):
            self.test_status_label.setText("❌ Error: No extraction model selected. Click 'Refresh' first.")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            return
        
        self.test_status_label.setText("Extracting prompt...")
        self.test_status_label.setStyleSheet("color: #0066cc;")
        
        def extract_and_gen():
            try:
                from ollama_client import OllamaClient
                from llama_client import LlamaServerClient
                
                provider = self.provider_combo.currentText()
                url = self.provider_url_input.text()
                model = self.extraction_model_combo.currentText()
                temperature = self.extraction_temperature_spinbox.value()
                
                system_prompt = self.system_prompt_text.toPlainText()
                user_prompt = self.user_prompt_text.toPlainText()
                final_user_prompt = user_prompt.replace("{response}", input_text)
                
                if provider == "ollama":
                    client = OllamaClient(url)
                else:
                    client = LlamaServerClient(url)
                
                print(f"\n[EXTRACT-GEN] Extracting prompt...")
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_user_prompt}
                ]
                
                extracted = client.generate_with_context(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    num_predict=512
                )
                extracted = extracted.strip() if extracted else ""
                
                if extracted:
                    print(f"[EXTRACT-GEN] ✅ Extracted: {extracted}")
                    
                    prefix = self.prefix_input.text()
                    suffix = self.suffix_input.text()
                    final_prompt = f"{prefix}{extracted}{suffix}".strip()
                    
                    # Add realistic keywords only for "Persons" built-in prompt style
                    from settings_manager import load_settings
                    settings = load_settings()
                    builtin_style = getattr(self.parent_tab, 'builtin_prompt_combo', None)
                    current_style = builtin_style.currentText() if builtin_style else "Generic"
                    
                    if settings.get("add_realistic_keywords", True) and current_style == "Persons":
                        realistic_keywords = ["photorealistic", "realistic", "8k", "detailed", "high quality"]
                        has_keywords = any(keyword in final_prompt.lower() for keyword in realistic_keywords)
                        if not has_keywords:
                            final_prompt = f"photorealistic, detailed, 8k, high quality, {final_prompt}"
                            print(f"[EXTRACT-GEN] Added realistic keywords (Persons mode)")
                    
                    self.current_extracted_prompt = final_prompt
                    self._pending_extracted_prompt = final_prompt
                    QTimer.singleShot(0, self._display_extracted_prompt)
                    QTimer.singleShot(50, lambda: self.test_status_label.setText("✅ Prompt extracted! Now generating image..."))
                    QTimer.singleShot(50, lambda: self.test_status_label.setStyleSheet("color: #0066cc;"))
                    
                    self._generate_image_from_prompt(final_prompt)
                else:
                    print(f"[EXTRACT-GEN] ❌ Extraction returned empty")
                    self._pending_error_msg = "Extraction failed - empty result"
                    QTimer.singleShot(0, self._display_extraction_error)
                    
            except Exception as e:
                print(f"[EXTRACT-GEN] ❌ Error: {e}")
                traceback.print_exc()
                self._pending_error_msg = f"Error: {str(e)}"
                QTimer.singleShot(0, self._display_extraction_error)
        
        thread = threading.Thread(target=extract_and_gen, daemon=True)
        thread.start()
    
    def _generate_image_from_prompt(self, prompt):
        """Generate image from given prompt"""
        if not prompt:
            self.test_status_label.setText("Error: Prompt is empty")
            self.test_status_label.setStyleSheet("color: #cc0000;")
            return
        
        def generate_test():
            try:
                from image_client import ComfyUIClient
                
                url = self.comfyui_url
                resolution = self.resolution_combo.currentText()
                steps = self.steps_spinbox.value()
                cfg_scale = self.cfg_scale_spinbox.value()
                sampler = self.sampler_combo.currentText()
                scheduler = self.scheduler_combo.currentText()
                timeout = self.generation_timeout_spinbox.value()
                
                model_display = self.model_combo.currentText()
                checkpoint_model = model_display
                if " " in model_display and model_display.startswith("["):
                    checkpoint_model = model_display.split("] ")[1]
                
                self.test_status_label.setText("Generating image...")
                self.test_status_label.setStyleSheet("color: #0066cc;")
                
                if DebugConfig.extraction_enabled:
                    print(f"\n[TEST] Generating test image...")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] Prompt: {prompt}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] Resolution: {resolution}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] Steps: {steps}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] Model: {checkpoint_model}")
                
                # Initialize ComfyUI client and generate image
                client = ComfyUIClient(url)
                
                # Resolution parsing
                width, height = map(int, resolution.split("x"))
                
                # Get loader type - try to detect from model extension
                loader_type = "standard"
                if checkpoint_model.endswith(".gguf"):
                    loader_type = "gguf"
                elif checkpoint_model.endswith(".safetensors") and "unet" in checkpoint_model.lower():
                    loader_type = "unet"
                else:
                    loader_type = "standard"  # Default to standard for most checkpoints
                
                # For UNet/GGUF models, we need compatible VAE - try to auto-detect or use None
                vae_model = self.vae_combo.currentText() if self.vae_combo else None
                if vae_model == "(auto)":
                    vae_model = None
                
                # Get CLIP loader and text encoder selections
                clip_loader = self.clip_loader_combo.currentText() if self.clip_loader_combo else "CLIPLoader"
                clip_name1 = self.clip_name1_combo.currentText() if self.clip_name1_combo else None
                clip_name2 = self.clip_name2_combo.currentText() if self.clip_name2_combo else None
                
                # Handle auto and dual loader defaults
                if clip_name1 == "(auto)":
                    clip_name1 = None
                if clip_name2 in ["(same as CLIP Name 1)", "(auto)"]:
                    clip_name2 = clip_name1  # Use same as clip_name1 if not specified
                
                # For single loaders (CLIPLoader), don't pass clip_name2
                if clip_loader == "CLIPLoader":
                    clip_name2 = None
                
                clip_type = self.clip_type_combo.currentText() if self.clip_type_combo else "stable_diffusion"
                weight_dtype = self.unet_weight_dtype_combo.currentText() if self.unet_weight_dtype_combo else "default"
                
                # Get LoRA settings
                lora_enabled = self.lora_enabled_checkbox.isChecked() if self.lora_enabled_checkbox else False
                lora_name = self.lora_combo.currentText() if self.lora_combo else "(none)"
                lora_strength = self.lora_strength_spinbox.value() if self.lora_strength_spinbox else 1.0
                
                if lora_name == "(none)":
                    lora_name = None
                    lora_enabled = False
                
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] Loader Type: {loader_type} (detected from model: {checkpoint_model})")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] VAE: {vae_model if vae_model else '(auto)'}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] CLIP Loader: {clip_loader}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] CLIP Name 1: {clip_name1 if clip_name1 else '(auto)'}")
                # Only show CLIP Name 2 for dual loaders
                if clip_loader in ["DualCLIPLoader", "DualCLIPLoaderGGUF"]:
                    if DebugConfig.extraction_enabled:
                        print(f"[TEST] CLIP Name 2: {clip_name2 if clip_name2 else '(same as 1)'}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] CLIP Type: {clip_type}")
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] Weight DType: {weight_dtype}")
                if lora_enabled:
                    if DebugConfig.extraction_enabled:
                        print(f"[TEST] LoRA: {lora_name} (strength: {lora_strength})")
                
                # Generate image using the correct method
                result = client.generate_from_text(
                    text_prompt=prompt,
                    resolution=resolution,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    sampler=sampler,
                    scheduler=scheduler,
                    checkpoint_model=checkpoint_model,
                    loader_type=loader_type,
                    vae_model=vae_model,
                    text_encoder_model=clip_name1,  # CLIP Name 1 is the primary encoder
                    text_encoder_model_2=clip_name2,  # CLIP Name 2 is the secondary encoder (for dual loaders)
                    clip_type=clip_type,
                    clip_loader=clip_loader,
                    weight_dtype=weight_dtype,
                    lora_enabled=lora_enabled,
                    lora_name=lora_name,
                    lora_strength=lora_strength,
                    timeout=timeout
                )
                
                if result:
                    if DebugConfig.extraction_enabled:
                        print(f"[TEST] ✅ Image generated successfully")
                    fit_mode = self.fit_image_checkbox.isChecked()
                    pixmap = QPixmap(result)
                    self.current_pixmap = pixmap
                    self._pending_fit_mode = fit_mode
                    self._pending_pixmap = pixmap
                    # Emit signal from GUI thread (not QTimer from background thread)
                    self.image_generation_complete.emit()
                else:
                    self.test_status_label.setText("❌ Image generation failed - check terminal for details")
                    self.test_status_label.setStyleSheet("color: #cc0000;")
                    
            except Exception as e:
                if DebugConfig.extraction_enabled:
                    print(f"[TEST] ❌ Error: {e}")
                traceback.print_exc()
                error_msg = str(e)
                if "tuple index out of range" in error_msg or "VAE" in error_msg or "decode" in error_msg:
                    self.test_status_label.setText("❌ Model/VAE mismatch - try different VAE or model")
                else:
                    self.test_status_label.setText(f"❌ Error: {error_msg[:50]}")
                self.test_status_label.setStyleSheet("color: #cc0000;")
        
        thread = threading.Thread(target=generate_test, daemon=True)
        thread.start()
