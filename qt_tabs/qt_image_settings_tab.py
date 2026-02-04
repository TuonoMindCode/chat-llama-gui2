"""
Image Settings Tab for PyQt5 - COMPLETE WITH ALL OPTIONS
Includes: ComfyUI settings, model selection, extraction settings, prompt profiles
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QTextEdit, QFrame,
    QSplitter, QScrollArea, QMessageBox, QFileDialog, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont, QPixmap
from pathlib import Path
import threading
import json

from settings_manager import load_settings
from settings_saver import get_settings_saver
from comfyui_model_manager import ComfyUIModelManager
from chat_template_manager import template_manager
from debug_config import DebugConfig

# Image handling class imported from new modular file
from qt_tabs.qt_image_settings_right_tab import QtImageSettingsRightTab


class ModelLoadSignals(QObject):
    """Signals for model loading operations"""
    models_loaded = pyqtSignal(dict, list, list, list, list, list)  # checkpoints, vaes, encoders, gguf, unet, diffusion
    load_error = pyqtSignal(str)


class QtImageSettingsTab(QWidget):
    """Image generation and extraction settings tab - PyQt5 Version"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.settings = load_settings()
        self.profiles = {}
        
        # Built-in extractor prompt styles
        self.builtin_prompts = {
            "Generic": {
                "system_prompt": (
                    "You are an expert at extracting image generation prompts.\n"
                    "Extract a SINGLE, CONCISE image prompt from the given text.\n"
                    "Output ONLY the prompt itself - NO explanations.\n"
                    "Keep it 1-2 sentences maximum."
                ),
                "user_prompt": (
                    "Extract ONLY the image prompt from this response.\n"
                    "Output NOTHING else.\n\n"
                    "{response}\n\n"
                    "IMAGE PROMPT (ONLY THE PROMPT, NO EXPLANATION):"
                )
            },
            "Persons": {
                "system_prompt": (
                    "You are a \"visual prompt writer\" for a photorealistic text-to-image model.\n\n"
                    "CRITICAL: Output ONLY the image prompt itself. No preamble, no explanation, no extra text.\n\n"
                    "Task:\n"
                    "Given an LLM response, generate ONE photorealistic image prompt that depicts REAL ANIMALS or REAL PEOPLE in a scene that captures the speaker's tone, role, and intent.\n\n"
                    "Rules:\n"
                    "- Generate prompts for REAL, PHOTOREALISTIC animals or people - NOT cartoon, illustrated, or stylized characters\n"
                    "- For animals: use real species (e.g., \"realistic cat\", \"real dog\") with natural behavior\n"
                    "- Describe real-world locations, not fictional towns or fantasy settings\n"
                    "- Make the scene depict an ACTION that matches the intent (playing, exploring, helping, interacting)\n"
                    "- Keep it grounded in reality: show what a photographer could capture\n"
                    "- Include: subjects, real setting, natural action, mood, lighting, camera framing, and style\n"
                    "- ALWAYS specify: photorealistic, real animals/people, natural lighting, photography style\n"
                    "- Avoid text in the image (no readable signs, no subtitles)\n"
                    "- Output ONLY the final image prompt, no analysis, no bullet points\n\n"
                    "Default style (unless user requests otherwise):\n"
                    "Photorealistic, natural skin texture (for people) or real fur/feathers (for animals), realistic lighting, 35mm photography style, shallow depth of field, candid moment"
                ),
                "user_prompt": (
                    "Output ONLY the photorealistic image generation prompt for the MAIN/CLIMACTIC scene or KEY MOMENT of the story.\n"
                    "Focus on the most important action, emotion, or turning point - not just introductory scenes.\n"
                    "No preamble, no instructions, no explanations.\n\n"
                    "LLM response:\n"
                    "{response}\n\n"
                    "IMAGE PROMPT (ONLY THE MAIN SCENE):"
                )
            },
            "Storybook": {
                "system_prompt": (
                    "You are a \"visual prompt writer\" for a storybook illustration model.\n\n"
                    "CRITICAL: Output ONLY the image prompt itself. No preamble, no explanation, no extra text.\n\n"
                    "Task:\n"
                    "Given an LLM response, generate ONE image prompt depicting REAL ANIMALS or REAL PEOPLE in a scene that captures the story's tone, setting, and action.\n\n"
                    "Rules:\n"
                    "- Generate prompts for REAL, PHOTOREALISTIC animals or people - NOT cartoon, illustrated, or stylized characters\n"
                    "- For animals: use real species with natural behavior (e.g., \"realistic cat\", \"real dog\")\n"
                    "- Settings CAN be fictional towns, fantasy locations, or imaginative places - that's OK for storybook style\n"
                    "- Capture the MAIN ACTION or most important moment from the story\n"
                    "- Include: subjects, setting, action, mood, and artistic style\n"
                    "- Style: Storybook illustration, warm lighting, detail-rich, whimsical yet grounded, children's book aesthetic\n"
                    "- Make it feel like a scene from a beloved picture book\n"
                    "- Avoid text in the image (no readable signs, no subtitles)\n"
                    "- Output ONLY the final image prompt, no analysis, no bullet points"
                ),
                "user_prompt": (
                    "Output ONLY the storybook illustration prompt for the MAIN/CLIMACTIC scene or KEY MOMENT of the story.\n"
                    "Capture the most important action, emotion, or turning point.\n"
                    "Include the fictional setting if mentioned - that's part of the story!\n"
                    "No preamble, no instructions, no explanations.\n\n"
                    "LLM response:\n"
                    "{response}\n\n"
                    "IMAGE PROMPT (ONLY THE MAIN SCENE):"
                )
            },
            "Cartoon/CGI": {
                "system_prompt": (
                    "You are a \"visual prompt writer\" for a stylized cartoon/CGI illustration model.\n\n"
                    "CRITICAL: Output ONLY the image prompt itself. No preamble, no explanation, no extra text.\n\n"
                    "Task:\n"
                    "Given an LLM response, generate ONE image prompt depicting the scene in a stylized, illustrated, or CGI style.\n\n"
                    "Rules:\n"
                    "- Identify character types from the story\n"
                    "- Generate STYLIZED, ILLUSTRATED, or CGI versions of those characters (NOT photorealistic)\n"
                    "- Characters can be cartoon animals, animated people, CGI creatures, or fantastical beings\n"
                    "- Settings can be realistic, stylized, or fantastical\n"
                    "- Make the scene depict the main ACTION or key moment that conveys emotion and tone\n"
                    "- Include: subjects (specify animal/character types), setting, action, mood, lighting, and artistic style\n"
                    "- Style: Vibrant colors, expressive animation, playful or whimsical energy, professional CGI quality OR cartoon illustration\n"
                    "- Can be: Pixar-style, Disney-style, anime-inspired, or digital illustration\n"
                    "- ALWAYS start the prompt with the style descriptor (e.g., 'cartoon', 'CGI', 'illustrated', 'animated')\n"
                    "- Avoid text in the image (no readable signs, no subtitles)\n"
                    "- Output ONLY the final image prompt, no analysis, no bullet points"
                ),
                "user_prompt": (
                    "Output ONLY the cartoon/CGI illustration prompt for the MAIN/CLIMACTIC scene or KEY MOMENT of the story.\n"
                    "Focus on the most important action, emotion, or turning point.\n"
                    "Make it feel fun, energetic, and visually appealing in a stylized animated style.\n"
                    "START the prompt with a style descriptor like 'cartoon', 'CGI', 'illustrated', or 'animated'.\n"
                    "Include character types (if they're animals, specify which animals like 'cat', 'dog', etc.).\n"
                    "No preamble, no instructions, no explanations.\n\n"
                    "LLM response:\n"
                    "{response}\n\n"
                    "IMAGE PROMPT (ONLY THE MAIN SCENE, MUST START WITH STYLE DESCRIPTOR):"
                )
            },
            "Fantasy": {
                "system_prompt": (
                    "You are a \"visual prompt writer\" for a fantasy/magical illustration model.\n\n"
                    "CRITICAL: Output ONLY the image prompt itself. No preamble, no explanation, no extra text.\n\n"
                    "Task:\n"
                    "Given an LLM response, generate ONE image prompt depicting a magical, surreal, or fantastical scene.\n\n"
                    "Rules:\n"
                    "- Identify character types from the story\n"
                    "- Characters can be REAL (photorealistic humans/animals), STYLIZED/ILLUSTRATED, or FANTASTICAL (magical creatures, mythical beings)\n"
                    "- Settings MUST be magical, surreal, or fantastical (not ordinary real-world)\n"
                    "- Include magical elements: glowing auras, enchanted objects, mystical energy, dreamlike atmosphere, ethereal lighting\n"
                    "- Make the scene depict the main ACTION or key moment of the story\n"
                    "- Include: subjects (specify animal/character types), magical setting, action, mood, mystical elements, and artistic style\n"
                    "- Style: Enchanting, mystical, dreamlike, ethereal lighting, magical atmosphere, fantasy art, vibrant or moody colors\n"
                    "- Can include: Dragons, wizards, magical forests, enchanted castles, floating islands, magical portals\n"
                    "- Avoid text in the image (no readable signs, no subtitles)\n"
                    "- Output ONLY the final image prompt, no analysis, no bullet points"
                ),
                "user_prompt": (
                    "Output ONLY the fantasy/magical illustration prompt for the MAIN/CLIMACTIC scene or KEY MOMENT of the story.\n"
                    "Focus on the most important action, emotion, or turning point with magical elements.\n"
                    "Capture the wonder, mystery, and enchantment of the scene.\n"
                    "No preamble, no instructions, no explanations.\n\n"
                    "LLM response:\n"
                    "{response}\n\n"
                    "IMAGE PROMPT (ONLY THE MAIN SCENE):"
                )
            },
            "Complete Story": {
                "system_prompt": (
                    "You are a \"visual prompt writer\" for creating comprehensive story illustrations.\n\n"
                    "CRITICAL: Output ONLY the image prompt itself. No preamble, no explanation, no extra text.\n\n"
                    "Task:\n"
                    "Given an LLM response, generate ONE image prompt that captures THE ENTIRE STORY visually.\n"
                    "Not just one moment, but ALL major elements, locations, characters, and key objects from the narrative.\n\n"
                    "Rules:\n"
                    "- Identify ALL characters from the story\n"
                    "- Include ALL major locations/settings mentioned (use visual hierarchy: foreground, midground, background)\n"
                    "- Show key objects, actions, and emotional beats from the story\n"
                    "- Use depth and scale to show multiple story elements in one frame:\n"
                    "  * Foreground: Main characters or most important element\n"
                    "  * Midground: Secondary characters or supporting scenes\n"
                    "  * Background: Other locations or context from the story\n"
                    "- Style: Photo-realistic or illustrated depending on story, detailed, rich with storytelling elements\n"
                    "- Make it feel like a complete visual summary of the entire narrative\n"
                    "- Include: all characters, major settings, key objects, overall mood and theme\n"
                    "- Avoid text in the image (no readable signs, no subtitles)\n"
                    "- Output ONLY the final image prompt, no analysis, no bullet points"
                ),
                "user_prompt": (
                    "Output ONLY the comprehensive story image prompt that captures THE ENTIRE NARRATIVE.\n"
                    "Include ALL major characters and locations from the story exactly as described.\n"
                    "Use depth and visual hierarchy to show multiple story elements in one frame.\n"
                    "Create a prompt for a rich, detailed composition that visually tells the complete story.\n"
                    "No preamble, no instructions, no explanations.\n\n"
                    "LLM response:\n"
                    "{response}\n\n"
                    "IMAGE PROMPT (ONLY THE COMPLETE STORY SCENE):"
                )
            }
        }
        
        self.model_manager = ComfyUIModelManager(
            self.settings.get("comfyui_root_folder", "")
        )
        
        # Store model selections to restore after loading
        self.pending_checkpoint = None
        self.pending_vae = None
        self.pending_encoder = None
        self.pending_lora = None
        self.pending_lora_strength = 1.0
        
        # Initialize model lists
        self.lora_list = []
        
        # Initialize signals for thread-safe model loading
        self.load_signals = ModelLoadSignals()
        self.load_signals.models_loaded.connect(self._on_models_loaded)
        self.load_signals.load_error.connect(self._on_models_load_error)
        
        self.create_widgets()
        self.load_settings()
        self.load_prompt_profiles()
    
    def create_widgets(self):
        """Create all image settings widgets"""
        # Create a single scrollable area for the entire page (not double scroll)
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(main_scroll)
        
        # Content widget that holds both panels
        content_widget = QWidget()
        main_layout = QHBoxLayout()
        content_widget.setLayout(main_layout)
        main_scroll.setWidget(content_widget)
        
        # ========== LEFT SIDE: SETTINGS (no longer scrollable separately) ==========
        # Left panel - no scroll area, just layout
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        
        # === SAVE / RESET BUTTONS AT TOP ===
        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self.save_all_settings)
        button_layout.addWidget(save_btn)
        reset_btn = QPushButton("🔄 Reset to Default")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        scroll_layout.addLayout(button_layout)
        scroll_layout.addWidget(self.create_separator())
        
        # === COMFYUI SERVER SETTINGS ===
        comfyui_title = QLabel("🖼️ ComfyUI Server")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        comfyui_title.setFont(title_font)
        scroll_layout.addWidget(comfyui_title)
        
        # URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("URL:"))
        self.comfyui_url_input = QLineEdit()
        self.comfyui_url_input.setText("http://127.0.0.1:8188")
        url_layout.addWidget(self.comfyui_url_input)
        test_conn_btn = QPushButton("Test")
        test_conn_btn.setMaximumWidth(60)
        test_conn_btn.clicked.connect(self.test_comfyui_connection)
        url_layout.addWidget(test_conn_btn)
        scroll_layout.addLayout(url_layout)
        
        self.comfyui_status_label = QLabel("")
        scroll_layout.addWidget(self.comfyui_status_label)
        
        # General test/refresh status label
        self.test_status_label = QLabel("")
        scroll_layout.addWidget(self.test_status_label)
        
        # Root Folder
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Root Folder:"))
        self.comfyui_root_input = QLineEdit()
        folder_layout.addWidget(self.comfyui_root_input)
        browse_btn = QPushButton("Browse")
        browse_btn.setMaximumWidth(80)
        browse_btn.clicked.connect(self.browse_comfyui_folder)
        folder_layout.addWidget(browse_btn)
        scroll_layout.addLayout(folder_layout)
        
        scroll_layout.addWidget(self.create_separator())
        
        # === IMAGE GENERATION PARAMETERS ===
        gen_title = QLabel("🎨 Generation Parameters")
        gen_title.setFont(title_font)
        scroll_layout.addWidget(gen_title)
        
        # Resolution
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "512x512", "640x640", "768x768", "1024x1024", "512x768", "768x512"
        ])
        self.resolution_combo.setCurrentText("768x768")
        res_layout.addWidget(self.resolution_combo)
        res_layout.addStretch()
        scroll_layout.addLayout(res_layout)
        
        # Steps
        steps_layout = QHBoxLayout()
        steps_layout.addWidget(QLabel("Steps:"))
        self.steps_spinbox = QSpinBox()
        self.steps_spinbox.setRange(1, 100)
        self.steps_spinbox.setValue(20)
        steps_layout.addWidget(self.steps_spinbox)
        steps_layout.addStretch()
        scroll_layout.addLayout(steps_layout)
        
        # CFG Scale
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("CFG Scale:"))
        self.cfg_scale_spinbox = QDoubleSpinBox()
        self.cfg_scale_spinbox.setRange(1.0, 20.0)
        self.cfg_scale_spinbox.setSingleStep(0.5)
        self.cfg_scale_spinbox.setValue(7.5)
        cfg_layout.addWidget(self.cfg_scale_spinbox)
        cfg_layout.addStretch()
        scroll_layout.addLayout(cfg_layout)
        
        # Sampler
        sampler_layout = QHBoxLayout()
        sampler_layout.addWidget(QLabel("Sampler:"))
        self.sampler_combo = QComboBox()
        self.sampler_combo.addItems([
            "euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral",
            "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_sde"
        ])
        self.sampler_combo.setCurrentText("euler")
        sampler_layout.addWidget(self.sampler_combo)
        sampler_layout.addStretch()
        scroll_layout.addLayout(sampler_layout)
        
        # Scheduler
        scheduler_layout = QHBoxLayout()
        scheduler_layout.addWidget(QLabel("Scheduler:"))
        self.scheduler_combo = QComboBox()
        self.scheduler_combo.addItems([
            "normal", "karras", "exponential", "simple", "beta", "ddim_uniform"
        ])
        self.scheduler_combo.setCurrentText("normal")
        scheduler_layout.addWidget(self.scheduler_combo)
        scheduler_layout.addStretch()
        scroll_layout.addLayout(scheduler_layout)
        
        # Generation Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Generation Timeout:"))
        self.generation_timeout_spinbox = QSpinBox()
        self.generation_timeout_spinbox.setRange(30, 3600)
        self.generation_timeout_spinbox.setSingleStep(30)
        self.generation_timeout_spinbox.setValue(300)  # Default 5 minutes
        timeout_layout.addWidget(self.generation_timeout_spinbox)
        timeout_layout.addWidget(QLabel("seconds"))
        timeout_layout.addStretch()
        scroll_layout.addLayout(timeout_layout)
        
        scroll_layout.addWidget(self.create_separator())
        
        # === MODEL SELECTION ===
        model_title = QLabel("🔧 Model Selection")
        model_title.setFont(title_font)
        scroll_layout.addWidget(model_title)
        
        # Model Type radio buttons
        loader_layout = QHBoxLayout()
        loader_layout.addWidget(QLabel("Model Type:"))
        
        self.loader_group = QButtonGroup()
        self.loader_standard_rb = QRadioButton("Standard")
        self.loader_gguf_rb = QRadioButton("GGUF")
        self.loader_unet_rb = QRadioButton("UNet")
        self.loader_diffuse_rb = QRadioButton("Diffusion")
        
        self.loader_standard_rb.setChecked(True)
        
        self.loader_group.addButton(self.loader_standard_rb, 0)
        self.loader_group.addButton(self.loader_gguf_rb, 1)
        self.loader_group.addButton(self.loader_unet_rb, 2)
        self.loader_group.addButton(self.loader_diffuse_rb, 3)
        
        self.loader_group.buttonClicked.connect(self._on_loader_type_changed)
        
        loader_layout.addWidget(self.loader_standard_rb)
        loader_layout.addWidget(self.loader_gguf_rb)
        loader_layout.addWidget(self.loader_unet_rb)
        loader_layout.addWidget(self.loader_diffuse_rb)
        loader_layout.addStretch()
        scroll_layout.addLayout(loader_layout)
        
        # Model dropdown (shows all models from all folders)
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("(click Refresh to load)")
        model_layout.addWidget(self.model_combo)
        scroll_layout.addLayout(model_layout)
        
        # VAE - always visible
        vae_layout = QHBoxLayout()
        vae_layout.addWidget(QLabel("VAE:"))
        self.vae_combo = QComboBox()
        self.vae_combo.addItem("(auto)")
        vae_layout.addWidget(self.vae_combo)
        scroll_layout.addLayout(vae_layout)
        
        # CLIP Loader Type - moved up first
        clip_loader_layout = QHBoxLayout()
        clip_loader_layout.addWidget(QLabel("CLIP Loader:"))
        self.clip_loader_combo = QComboBox()
        self.clip_loader_combo.addItems([
            "CLIPLoader", "DualCLIPLoader", "DualCLIPLoaderGGUF"
        ])
        self.clip_loader_combo.setCurrentText("CLIPLoader")
        self.clip_loader_combo.currentTextChanged.connect(self._on_clip_loader_changed)
        clip_loader_layout.addWidget(self.clip_loader_combo)
        clip_loader_layout.addStretch()
        scroll_layout.addLayout(clip_loader_layout)
        
        # CLIP Name 1 (for dual loaders, this is the first CLIP/text encoder)
        clip_name1_layout = QHBoxLayout()
        clip_name1_layout.addWidget(QLabel("CLIP Name 1:"))
        self.clip_name1_combo = QComboBox()
        self.clip_name1_combo.addItem("(auto)")
        self.clip_name1_combo.setMinimumWidth(300)
        clip_name1_layout.addWidget(self.clip_name1_combo)
        clip_name1_layout.addStretch()
        scroll_layout.addLayout(clip_name1_layout)
        
        # CLIP Name 2 (for dual loaders, this is the second CLIP/text encoder)
        clip_name2_layout = QHBoxLayout()
        clip_name2_layout.addWidget(QLabel("CLIP Name 2:"))
        self.clip_name2_combo = QComboBox()
        self.clip_name2_combo.addItem("(same as CLIP Name 1)")
        self.clip_name2_combo.setMinimumWidth(300)
        self.clip_name2_combo.setVisible(False)  # Hidden by default (shown only for dual loaders)
        clip_name2_layout.addWidget(self.clip_name2_combo)
        clip_name2_layout.addStretch()
        scroll_layout.addLayout(clip_name2_layout)
        
        # CLIP Type - moved below loaders
        clip_type_layout = QHBoxLayout()
        clip_type_layout.addWidget(QLabel("CLIP Type:"))
        self.clip_type_combo = QComboBox()
        # Store different CLIP type lists for different loaders - must match ComfyUI node definitions
        self.clip_types_standard = [
            "stable_diffusion", "stable_cascade", "sd3", "stable_audio", "mochi", "ltxv", 
            "pixart", "cosmos", "lumina2", "wan", "hidream", "chroma", "ace", "omnigen2",
            "qwen_image", "hunyuan_image", "flux2"
        ]
        # DualCLIPLoader types based on ComfyUI actual node
        self.clip_types_dual = [
            "sdxl", "sd3", "flux", "hunyuan_video", "hidream", "hunyuan_image", 
            "hunyuan_video_15", "kandinsky5", "kandinsky5_image", "ltxv", "newbie"
        ]
        self.clip_types_dual_gguf = [
            "sdxl", "sd3", "flux", "hunyuan_video", "hidream", "hunyuan_image", 
            "hunyuan_video_15", "kandinsky5", "kandinsky5_image", "ltxv", "newbie", "flux2"
        ]
        self.clip_type_combo.addItems(self.clip_types_standard)
        self.clip_type_combo.setCurrentText("stable_diffusion")
        clip_type_layout.addWidget(self.clip_type_combo)
        clip_type_layout.addStretch()
        scroll_layout.addLayout(clip_type_layout)
        
        # UNet Weight DType
        unet_loader_layout = QHBoxLayout()
        unet_loader_layout.addWidget(QLabel("UNet Weight DType:"))
        self.unet_weight_dtype_combo = QComboBox()
        self.unet_weight_dtype_combo.addItems(["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"])
        self.unet_weight_dtype_combo.setCurrentText("default")
        unet_loader_layout.addWidget(self.unet_weight_dtype_combo)
        unet_loader_layout.addStretch()
        scroll_layout.addLayout(unet_loader_layout)
        
        # LoRA Settings
        lora_enabled_layout = QHBoxLayout()
        self.lora_enabled_checkbox = QCheckBox("Use LoRA")
        self.lora_enabled_checkbox.setChecked(False)
        self.lora_enabled_checkbox.stateChanged.connect(self._on_lora_enabled_changed)
        lora_enabled_layout.addWidget(self.lora_enabled_checkbox)
        lora_enabled_layout.addStretch()
        scroll_layout.addLayout(lora_enabled_layout)
        
        # LoRA model selection
        lora_model_layout = QHBoxLayout()
        lora_model_layout.addWidget(QLabel("LoRA Model:"))
        self.lora_combo = QComboBox()
        self.lora_combo.addItem("(none)")
        self.lora_combo.setEnabled(False)
        lora_model_layout.addWidget(self.lora_combo)
        scroll_layout.addLayout(lora_model_layout)
        
        # LoRA strength
        lora_strength_layout = QHBoxLayout()
        lora_strength_layout.addWidget(QLabel("LoRA Strength:"))
        self.lora_strength_spinbox = QDoubleSpinBox()
        self.lora_strength_spinbox.setMinimum(0.0)
        self.lora_strength_spinbox.setMaximum(2.0)
        self.lora_strength_spinbox.setValue(1.0)
        self.lora_strength_spinbox.setSingleStep(0.1)
        self.lora_strength_spinbox.setEnabled(False)
        lora_strength_layout.addWidget(self.lora_strength_spinbox)
        lora_strength_layout.addStretch()
        scroll_layout.addLayout(lora_strength_layout)
        
        # Refresh models button
        refresh_btn = QPushButton("🔄 Refresh Models")
        refresh_btn.clicked.connect(self.refresh_models)
        scroll_layout.addWidget(refresh_btn)
        
        scroll_layout.addWidget(self.create_separator())
        
        # === PROMPT EXTRACTION ===
        extraction_title = QLabel("📝 Prompt Extraction (LLM)")
        extraction_title.setFont(title_font)
        scroll_layout.addWidget(extraction_title)
        
        # Model Provider
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Provider:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["ollama", "llama_server"])
        self.provider_combo.setCurrentText("ollama")
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addStretch()
        scroll_layout.addLayout(provider_layout)
        
        # Provider URL
        provider_url_layout = QHBoxLayout()
        provider_url_layout.addWidget(QLabel("Provider URL:"))
        self.provider_url_input = QLineEdit()
        self.provider_url_input.setText("http://localhost:11434")
        provider_url_layout.addWidget(self.provider_url_input)
        scroll_layout.addLayout(provider_url_layout)
        
        # Extraction Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Extraction Model:"))
        self.extraction_model_combo = QComboBox()
        self.extraction_model_combo.addItem("(click Refresh Models)")
        model_layout.addWidget(self.extraction_model_combo)
        refresh_ext_btn = QPushButton("Refresh")
        refresh_ext_btn.setMaximumWidth(80)
        refresh_ext_btn.clicked.connect(self.refresh_extraction_models)
        model_layout.addWidget(refresh_ext_btn)
        scroll_layout.addLayout(model_layout)
        
        # Enable/Disable Prompt Extraction
        extraction_enabled_layout = QHBoxLayout()
        self.enable_prompt_extraction_checkbox = QCheckBox("Enable Prompt Extraction")
        self.enable_prompt_extraction_checkbox.setChecked(False)  # Disabled by default
        extraction_enabled_layout.addWidget(self.enable_prompt_extraction_checkbox)
        extraction_enabled_layout.addWidget(QLabel("(When disabled, sends full LLM reply to ComfyUI)"))
        extraction_enabled_layout.addStretch()
        scroll_layout.addLayout(extraction_enabled_layout)
        
        # Model Unload Timeout (for prompt extractor)
        unload_timeout_layout = QHBoxLayout()
        unload_timeout_layout.addWidget(QLabel("Model Unload Timeout:"))
        self.extraction_model_unload_combo = QComboBox()
        self.extraction_model_unload_combo.addItems([
            "0 (Immediate)",
            "5 minutes",
            "15 minutes",
            "30 minutes",
            "Never"
        ])
        self.extraction_model_unload_combo.setCurrentText("0 (Immediate)")
        unload_timeout_layout.addWidget(self.extraction_model_unload_combo)
        unload_timeout_layout.addWidget(QLabel("(Frees VRAM after prompt extraction)"))
        unload_timeout_layout.addStretch()
        scroll_layout.addLayout(unload_timeout_layout)
        
        # Min Response Length
        response_len_layout = QHBoxLayout()
        response_len_layout.addWidget(QLabel("Min Response Length:"))
        self.min_response_length_spinbox = QSpinBox()
        self.min_response_length_spinbox.setRange(0, 10000)
        self.min_response_length_spinbox.setValue(100)
        response_len_layout.addWidget(self.min_response_length_spinbox)
        response_len_layout.addWidget(QLabel("chars"))
        response_len_layout.addStretch()
        scroll_layout.addLayout(response_len_layout)
        
        # Temperature
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperature:"))
        self.extraction_temperature_spinbox = QDoubleSpinBox()
        self.extraction_temperature_spinbox.setRange(0.0, 1.0)
        self.extraction_temperature_spinbox.setSingleStep(0.1)
        self.extraction_temperature_spinbox.setValue(0.3)
        temp_layout.addWidget(self.extraction_temperature_spinbox)
        temp_layout.addWidget(QLabel("(Lower = focused)"))
        temp_layout.addStretch()
        scroll_layout.addLayout(temp_layout)
        
        # Timeout
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout:"))
        self.extraction_timeout_spinbox = QSpinBox()
        self.extraction_timeout_spinbox.setRange(10, 600)
        self.extraction_timeout_spinbox.setSingleStep(10)
        self.extraction_timeout_spinbox.setValue(120)
        timeout_layout.addWidget(self.extraction_timeout_spinbox)
        timeout_layout.addWidget(QLabel("seconds"))
        timeout_layout.addStretch()
        scroll_layout.addLayout(timeout_layout)
        
        # Realistic keywords checkbox
        self.realistic_keywords_checkbox = QCheckBox("✓ Auto-add realistic keywords to prompts")
        self.realistic_keywords_checkbox.setChecked(True)
        scroll_layout.addWidget(self.realistic_keywords_checkbox)
        
        scroll_layout.addWidget(self.create_separator())
        
        # === PROMPT PROFILES ===
        profiles_title = QLabel("📋 Prompt Profiles")
        profiles_title.setFont(QFont("Arial", 11, QFont.Bold))
        scroll_layout.addWidget(profiles_title)
        
        profile_mgmt_layout = QHBoxLayout()
        profile_mgmt_layout.addWidget(QLabel("Profile:"))
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("default")
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        profile_mgmt_layout.addWidget(self.profile_combo)
        
        load_profile_btn = QPushButton("Load")
        load_profile_btn.setMaximumWidth(60)
        load_profile_btn.setStyleSheet("background-color: #0099cc; color: white;")
        load_profile_btn.clicked.connect(self.load_prompt_profile)
        profile_mgmt_layout.addWidget(load_profile_btn)
        
        save_current_profile_btn = QPushButton("Save")
        save_current_profile_btn.setMaximumWidth(60)
        save_current_profile_btn.setStyleSheet("background-color: #00dd77; color: white;")
        save_current_profile_btn.clicked.connect(self.save_current_profile)
        profile_mgmt_layout.addWidget(save_current_profile_btn)
        
        save_profile_btn = QPushButton("Save As")
        save_profile_btn.setMaximumWidth(80)
        save_profile_btn.setStyleSheet("background-color: #00cc66; color: white;")
        save_profile_btn.clicked.connect(self.save_prompt_profile)
        profile_mgmt_layout.addWidget(save_profile_btn)
        
        reset_profile_btn = QPushButton("Reset")
        reset_profile_btn.setMaximumWidth(60)
        reset_profile_btn.setStyleSheet("background-color: #ff9900; color: white;")
        reset_profile_btn.clicked.connect(self.reset_prompt_profile)
        profile_mgmt_layout.addWidget(reset_profile_btn)
        
        delete_profile_btn = QPushButton("Delete")
        delete_profile_btn.setMaximumWidth(60)
        delete_profile_btn.setStyleSheet("background-color: #ff3333; color: white;")
        delete_profile_btn.clicked.connect(self.delete_prompt_profile)
        profile_mgmt_layout.addWidget(delete_profile_btn)
        
        profile_mgmt_layout.addStretch()
        scroll_layout.addLayout(profile_mgmt_layout)
        
        scroll_layout.addWidget(self.create_separator())
        
        # === RESET BUILT-IN PROMPTS ===
        reset_builtin_layout = QHBoxLayout()
        reset_builtin_label = QLabel("Built-In Prompts:")
        reset_builtin_layout.addWidget(reset_builtin_label)
        
        self.builtin_prompt_combo = QComboBox()
        self.builtin_prompt_combo.addItems(["Generic", "Persons", "Storybook", "Cartoon/CGI", "Fantasy", "Complete Story"])
        self.builtin_prompt_combo.setCurrentText("Generic")
        self.builtin_prompt_combo.currentTextChanged.connect(self._on_builtin_prompt_selected)
        reset_builtin_layout.addWidget(self.builtin_prompt_combo)
        reset_builtin_layout.addStretch()
        scroll_layout.addLayout(reset_builtin_layout)
        
        scroll_layout.addWidget(self.create_separator())
        
        # === SYSTEM PROMPT ===
        system_title = QLabel("System Prompt (for extraction model):")
        system_title.setFont(QFont("Arial", 9, QFont.Bold))
        scroll_layout.addWidget(system_title)
        
        self.system_prompt_text = QTextEdit()
        self.system_prompt_text.setPlainText(
            "You are an expert at extracting image generation prompts.\n"
            "Extract a SINGLE, CONCISE image prompt from the given text.\n"
            "Output ONLY the prompt itself - NO explanations.\n"
            "Keep it 1-2 sentences maximum."
        )
        self.system_prompt_text.setMinimumHeight(220)
        self.system_prompt_text.setMaximumHeight(300)
        scroll_layout.addWidget(self.system_prompt_text)
        
        # === USER PROMPT ===
        user_title = QLabel("User Prompt (use {response} placeholder):")
        user_title.setFont(QFont("Arial", 9, QFont.Bold))
        scroll_layout.addWidget(user_title)
        
        self.user_prompt_text = QTextEdit()
        self.user_prompt_text.setPlainText(
            "Extract ONLY the image prompt from this response.\n"
            "Output NOTHING else.\n\n"
            "{response}\n\n"
            "IMAGE PROMPT (ONLY THE PROMPT, NO EXPLANATION):"
        )
        self.user_prompt_text.setMinimumHeight(240)
        self.user_prompt_text.setMaximumHeight(320)
        scroll_layout.addWidget(self.user_prompt_text)
        
        # === PREFIX & SUFFIX ===
        prefix_label = QLabel("Prefix (prepended to prompt):")
        prefix_label.setFont(QFont("Arial", 9, QFont.Bold))
        scroll_layout.addWidget(prefix_label)
        
        self.prefix_input = QLineEdit()
        scroll_layout.addWidget(self.prefix_input)
        
        suffix_label = QLabel("Suffix (appended to prompt):")
        suffix_label.setFont(QFont("Arial", 9, QFont.Bold))
        scroll_layout.addWidget(suffix_label)
        
        self.suffix_input = QLineEdit()
        scroll_layout.addWidget(self.suffix_input)
        
        scroll_layout.addStretch()
        
        # Add left panel directly to main layout (no internal scroll area)
        main_layout.addWidget(scroll_widget, 1)  # Left panel: 1 part (33%)
        
        # ========== RIGHT SIDE: Image Generation & Display Panel ==========
        # Right panel is now a separate modular widget
        self.right_panel = QtImageSettingsRightTab()
        
        # Set parent reference so right panel can access left panel controls
        self.right_panel.parent_tab = self
        
        # Pass settings references from left panel to right panel
        self.right_panel.set_generation_settings(
            self.comfyui_url_input,  # Pass widget, not text value
            self.resolution_combo,
            self.steps_spinbox,
            self.cfg_scale_spinbox,
            self.sampler_combo,
            self.scheduler_combo,
            self.model_combo,
            self.generation_timeout_spinbox
        )
        
        self.right_panel.set_extraction_settings(
            self.provider_combo,
            self.provider_url_input,
            self.extraction_model_combo,
            self.extraction_model_unload_combo,
            self.extraction_temperature_spinbox,
            self.extraction_timeout_spinbox,
            self.system_prompt_text,
            self.user_prompt_text,
            self.prefix_input,
            self.suffix_input,
            self.min_response_length_spinbox
        )
        
        # Set LoRA settings
        self.right_panel.set_lora_settings(
            self.lora_enabled_checkbox,
            self.lora_combo,
            self.lora_strength_spinbox
        )
        
        # Also set model-related controls (VAE, encoders, etc)
        self.right_panel.vae_combo = self.vae_combo
        self.right_panel.clip_name1_combo = self.clip_name1_combo
        self.right_panel.clip_name2_combo = self.clip_name2_combo
        self.right_panel.clip_type_combo = self.clip_type_combo
        self.right_panel.clip_loader_combo = self.clip_loader_combo
        self.right_panel.unet_weight_dtype_combo = self.unet_weight_dtype_combo
        self.right_panel.loader_standard_rb = self.loader_standard_rb
        self.right_panel.loader_gguf_rb = self.loader_gguf_rb
        self.right_panel.loader_unet_rb = self.loader_unet_rb
        self.right_panel.loader_diffuse_rb = self.loader_diffuse_rb
        
        main_layout.addWidget(self.right_panel, 2)  # Right panel: 2 parts (67%)
    
    def create_separator(self):
        """Create a separator frame"""
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #cccccc;")
        return sep
    
    def _get_unload_timeout_value(self, combo_text):
        """Convert combo box text to timeout value in minutes"""
        if combo_text == "0 (Immediate)":
            return 0
        elif combo_text == "5 minutes":
            return 5
        elif combo_text == "15 minutes":
            return 15
        elif combo_text == "30 minutes":
            return 30
        elif combo_text == "Never":
            return -1
        return 0  # Default to immediate
    
    def _convert_timeout_to_combo_text(self, timeout_value):
        """Convert timeout value (in minutes) to combo box text"""
        if timeout_value == 0:
            return "0 (Immediate)"
        elif timeout_value == 5:
            return "5 minutes"
        elif timeout_value == 15:
            return "15 minutes"
        elif timeout_value == 30:
            return "30 minutes"
        elif timeout_value == -1:
            return "Never"
        return "0 (Immediate)"  # Default to immediate
    
    # NOTE: This method references self.builtin_checkbox which doesn't exist in the UI
    # Kept for reference but unused - VAE and Encoder are always enabled
    # def _on_builtin_changed(self):
    #     """Handle built-in CLIP/VAE checkbox change"""
    #     has_builtin = self.builtin_checkbox.isChecked()
    #     self.vae_combo.setEnabled(not has_builtin)
    #     self.encoder_combo.setEnabled(not has_builtin)
    
    def _on_loader_type_changed(self):
        """Handle loader type radio button change"""
        # Simply store the selected loader type - model dropdown shows all models regardless
        pass
    
    
    def _on_builtin_prompt_selected(self, style_name):
        """Handle built-in prompt selection from dropdown"""
        if style_name in self.builtin_prompts:
            prompts = self.builtin_prompts[style_name]
            self.system_prompt_text.setPlainText(prompts["system_prompt"])
            self.user_prompt_text.setPlainText(prompts["user_prompt"])
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] ✅ Loaded built-in '{style_name}' prompts")
    
    def _on_lora_enabled_changed(self):
        """Enable/disable LoRA controls based on checkbox"""
        enabled = self.lora_enabled_checkbox.isChecked()
        self.lora_combo.setEnabled(enabled)
        self.lora_strength_spinbox.setEnabled(enabled)
    
    def _on_clip_loader_changed(self):
        """Update CLIP type options and visibility based on selected CLIP loader"""
        clip_loader = self.clip_loader_combo.currentText()
        current_type = self.clip_type_combo.currentText()
        
        # Show/hide CLIP Name 2 based on loader type
        is_dual_loader = clip_loader in ["DualCLIPLoader", "DualCLIPLoaderGGUF"]
        self.clip_name2_combo.setVisible(is_dual_loader)
        
        # Clear and repopulate CLIP types based on loader type
        self.clip_type_combo.blockSignals(True)
        self.clip_type_combo.clear()
        
        if clip_loader == "DualCLIPLoaderGGUF":
            self.clip_type_combo.addItems(self.clip_types_dual_gguf)
            # Try to restore current selection or default to stable_diffusion
            if current_type in self.clip_types_dual_gguf:
                self.clip_type_combo.setCurrentText(current_type)
            else:
                self.clip_type_combo.setCurrentText("stable_diffusion")
        elif clip_loader == "DualCLIPLoader":
            self.clip_type_combo.addItems(self.clip_types_dual)
            if current_type in self.clip_types_dual:
                self.clip_type_combo.setCurrentText(current_type)
            else:
                self.clip_type_combo.setCurrentText("stable_diffusion")
        else:  # CLIPLoader
            self.clip_type_combo.addItems(self.clip_types_standard)
            if current_type in self.clip_types_standard:
                self.clip_type_combo.setCurrentText(current_type)
            else:
                self.clip_type_combo.setCurrentText("stable_diffusion")
        
        self.clip_type_combo.blockSignals(False)
        if DebugConfig.comfyui_generation_settings:
            print(f"[DEBUG] CLIP Loader changed to: {clip_loader}, dual_loader: {is_dual_loader}, available types: {self.clip_type_combo.count()}")
    
    def refresh_models(self):
        """Refresh model lists in background thread"""
        self.test_status_label.setText("Loading models...")
        thread = threading.Thread(target=self._load_models)
        thread.daemon = True
        thread.start()
    
    def _load_models(self):
        """Load models from ComfyUI root folder (runs in background thread)"""
        try:
            comfyui_root = self.comfyui_root_input.text()
            if not comfyui_root:
                if DebugConfig.model_loading_enabled:
                    print("[DEBUG] ComfyUI root folder not set")
                self.test_status_label.setText("Error: ComfyUI root folder not set")
                return
            
            if DebugConfig.model_scanning:
                print(f"[DEBUG] Loading models from: {comfyui_root}")
            
            # Reinitialize model manager with current root folder path
            self.model_manager = ComfyUIModelManager(comfyui_root)
            
            # Use the model manager to scan for models
            checkpoints = self.model_manager.scan_checkpoints()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(checkpoints)} checkpoints")
            self.checkpoints_dict = checkpoints
            
            # Load VAE models
            vaes = self.model_manager.scan_vaes()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(vaes)} VAE models")
            
            # Load text encoders
            text_encoders = self.model_manager.scan_text_encoders()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(text_encoders)} text encoders")
            
            # Load GGUF models
            gguf_models = self.model_manager.scan_gguf_models()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(gguf_models)} GGUF models")
            self.gguf_list = gguf_models
            
            # Load UNet models
            unet_models = self.model_manager.scan_unets()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(unet_models)} UNet models")
            self.unet_list = unet_models
            
            # Load diffusion models
            diffusion_models = self.model_manager.scan_diffusion_models()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(diffusion_models)} diffusion models")
            self.diffusion_list = diffusion_models
            
            # Load LoRA models
            loras = self.model_manager.scan_loras()
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(loras)} LoRA models")
            self.lora_list = loras
            
            # Emit signal with all loaded model data - will be handled in main thread
            self.load_signals.models_loaded.emit(
                checkpoints,
                vaes,
                text_encoders,
                gguf_models,
                unet_models,
                diffusion_models
            )
            total_models = len(checkpoints) + len(vaes) + len(text_encoders) + len(gguf_models) + len(unet_models) + len(diffusion_models)
            if DebugConfig.model_loading_enabled:
                print(f"[DEBUG] Model loading emitted signal - {total_models} total models")
            
        except Exception as e:
            print(f"[ERROR] Loading models: {e}")
            import traceback
            traceback.print_exc()
            self.load_signals.load_error.emit(f"Error loading models: {str(e)}")
    
    def refresh_extraction_models(self):
        """Refresh extraction model list from provider"""
        try:
            provider = self.provider_combo.currentText()
            url = self.provider_url_input.text()
            
            if provider == "ollama":
                from ollama_client import OllamaClient
                client = OllamaClient(url)
            else:
                from llama_client import LlamaServerClient
                client = LlamaServerClient(url)
            
            models = client.get_available_models()
            if models:
                # Save current selection before clearing
                current_model = self.extraction_model_combo.currentText()
                self.extraction_model_combo.clear()
                self.extraction_model_combo.addItems(models)
                
                # Restore previous selection if it still exists
                idx = self.extraction_model_combo.findText(current_model)
                if idx >= 0:
                    self.extraction_model_combo.setCurrentIndex(idx)
                else:
                    # Default to first model if previous one not found
                    self.extraction_model_combo.setCurrentIndex(0)
                
                self.test_status_label.setText(f"✅ Found {len(models)} models")
            else:
                self.test_status_label.setText("❌ No models found")
        except Exception as e:
            self.test_status_label.setText(f"❌ Error: {str(e)}")
            print(f"[ERROR] Refreshing extraction models: {e}")
    
    def _on_models_loaded(self, checkpoints, vaes, text_encoders, gguf_models, unet_models, diffusion_models):
        """Handle models loaded signal from background thread - runs in main thread"""
        try:
            if DebugConfig.chat_enabled:
                print("[DEBUG] _on_models_loaded signal received - updating UI")
            
            # Update VAE combo
            self.vae_combo.clear()
            self.vae_combo.addItem("(auto)")
            if vaes:
                self.vae_combo.addItems(vaes)
            
            # Update CLIP Name 1 and 2 combos with available text encoders
            self.clip_name1_combo.clear()
            self.clip_name1_combo.addItem("(auto)")
            if text_encoders:
                self.clip_name1_combo.addItems(text_encoders)
            
            self.clip_name2_combo.clear()
            self.clip_name2_combo.addItem("(same as CLIP Name 1)")
            if text_encoders:
                self.clip_name2_combo.addItems(text_encoders)
            
            # Update LoRA combo
            self.lora_combo.clear()
            self.lora_combo.addItem("(none)")
            if self.lora_list:
                self.lora_combo.addItems(self.lora_list)
            
            # Combine ALL models into one dropdown with folder labels
            self.model_combo.clear()
            all_models = []
            
            if checkpoints:
                sorted_checkpoints = sorted(checkpoints.keys())
                for model in sorted_checkpoints:
                    all_models.append(f"[Checkpoint] {model}")
            
            if gguf_models:
                for model in gguf_models:
                    all_models.append(f"[GGUF] {model}")
            
            if unet_models:
                for model in unet_models:
                    all_models.append(f"[UNet] {model}")
            
            if diffusion_models:
                for model in diffusion_models:
                    all_models.append(f"[Diffusion] {model}")
            
            if all_models:
                self.model_combo.addItems(all_models)
            else:
                self.model_combo.addItem("(no models found)")
                if DebugConfig.chat_enabled:
                    print("[DEBUG] No models found in any folder")
            
            # NOW restore pending model selections after models are loaded
            if self.pending_checkpoint:
                # Search through all_models for a match
                for item in all_models:
                    if self.pending_checkpoint in item:  # e.g., "flux-2-klein-9b-Q8_0.gguf" in "[UNet] flux-2-klein-9b-Q8_0.gguf"
                        idx = self.model_combo.findText(item)
                        if idx >= 0:
                            self.model_combo.setCurrentIndex(idx)
                            if DebugConfig.comfyui_generation_settings:
                                print(f"[DEBUG] Restored Model: {self.pending_checkpoint} -> {item}")
                            break
            
            # Restore VAE
            if self.pending_vae and self.pending_vae != "(auto)":
                idx = self.vae_combo.findText(self.pending_vae)
                if idx >= 0:
                    self.vae_combo.setCurrentIndex(idx)
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] Restored VAE: {self.pending_vae}")
            
            # Restore CLIP Name 1
            if self.pending_clip_name1 and self.pending_clip_name1 != "(auto)":
                idx = self.clip_name1_combo.findText(self.pending_clip_name1)
                if idx >= 0:
                    self.clip_name1_combo.setCurrentIndex(idx)
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] Restored CLIP Name 1: {self.pending_clip_name1}")
                else:
                    # CLIP Name 1 not found, set to (auto)
                    idx_auto = self.clip_name1_combo.findText("(auto)")
                    if idx_auto >= 0:
                        self.clip_name1_combo.setCurrentIndex(idx_auto)
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] CLIP Name 1 '{self.pending_clip_name1}' not found in loaded list, set to (auto)")
            
            # Restore CLIP Name 2
            if self.pending_clip_name2 and self.pending_clip_name2 != "(same as CLIP Name 1)":
                idx = self.clip_name2_combo.findText(self.pending_clip_name2)
                if idx >= 0:
                    self.clip_name2_combo.setCurrentIndex(idx)
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] Restored CLIP Name 2: {self.pending_clip_name2}")
                else:
                    # CLIP Name 2 not found, set to (same as CLIP Name 1)
                    idx_same = self.clip_name2_combo.findText("(same as CLIP Name 1)")
                    if idx_same >= 0:
                        self.clip_name2_combo.setCurrentIndex(idx_same)
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] CLIP Name 2 '{self.pending_clip_name2}' not found in loaded list, set to (same as CLIP Name 1)")
            
            # Restore CLIP Type
            if self.pending_clip_type:
                idx = self.clip_type_combo.findText(self.pending_clip_type)
                if idx >= 0:
                    self.clip_type_combo.setCurrentIndex(idx)
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] Restored CLIP Type: {self.pending_clip_type}")
                else:
                    # CLIP Type not found, set to default
                    self.clip_type_combo.setCurrentText("stable_diffusion")
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] CLIP Type '{self.pending_clip_type}' not found in loaded list, set to stable_diffusion")
            
            # Restore LoRA settings
            if self.pending_lora and self.pending_lora != "(none)":
                if self.lora_combo:
                    idx = self.lora_combo.findText(self.pending_lora)
                    if idx >= 0:
                        self.lora_combo.setCurrentIndex(idx)
                        if DebugConfig.comfyui_generation_settings:
                            print(f"[DEBUG] Restored LoRA: {self.pending_lora}")
                    else:
                        # LoRA not found, set to (none)
                        idx_none = self.lora_combo.findText("(none)")
                        if idx_none >= 0:
                            self.lora_combo.setCurrentIndex(idx_none)
                        if DebugConfig.comfyui_generation_settings:
                            print(f"[DEBUG] LoRA '{self.pending_lora}' not found in loaded list, set to (none)")
            
            # Restore LoRA strength
            if self.lora_strength_spinbox:
                self.lora_strength_spinbox.setValue(self.pending_lora_strength)
                if DebugConfig.comfyui_generation_settings:
                    print(f"[DEBUG] Restored LoRA Strength: {self.pending_lora_strength}")
            
            found_count = len(checkpoints) + len(vaes) + len(text_encoders) + len(gguf_models) + len(unet_models) + len(diffusion_models)
            self.test_status_label.setText(f"✅ Loaded {found_count} models")
            if DebugConfig.model_loading_enabled:
                print(f"[DEBUG] Model loading complete - {found_count} total models loaded")
            
        except Exception as e:
            print(f"[ERROR] Updating UI with models: {e}")
            self.test_status_label.setText(f"❌ Error updating models: {str(e)}")
    
    def _on_models_load_error(self, error_msg):
        """Handle model loading error signal from background thread - runs in main thread"""
        print(f"[ERROR] Model loading failed: {error_msg}")
        self.test_status_label.setText(f"❌ {error_msg}")
    
    def test_comfyui_connection(self):
        """Test ComfyUI connection"""
        try:
            import requests
            url = self.comfyui_url_input.text()
            response = requests.get(f"{url}/system_stats", timeout=5)
            if response.status_code == 200:
                self.comfyui_status_label.setText("✅ Connected to ComfyUI")
                self.comfyui_status_label.setStyleSheet("color: #009900;")
            else:
                self.comfyui_status_label.setText(f"❌ Connection failed (status {response.status_code})")
                self.comfyui_status_label.setStyleSheet("color: #cc0000;")
        except Exception as e:
            self.comfyui_status_label.setText(f"❌ Cannot connect to ComfyUI\nError: {str(e)}")
            self.comfyui_status_label.setStyleSheet("color: #cc0000;")
    
    def browse_comfyui_folder(self):
        """Browse for ComfyUI root folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select ComfyUI Root Folder")
        if folder:
            self.comfyui_root_input.setText(folder)
    
    
    def load_prompt_profiles(self):
        """Load prompt profiles from file"""
        try:
            profiles_file = Path(__file__).parent.parent / "prompt_profiles.json"
            if profiles_file.exists():
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
            else:
                # Create default profile if file doesn't exist
                self.profiles = {
                    "default": {
                        "system_prompt": "You are an expert at extracting image generation prompts.\nExtract a SINGLE, CONCISE image prompt from the given text.\nOutput ONLY the prompt itself - NO explanations.\nKeep it 1-2 sentences maximum.",
                        "user_prompt": "Extract ONLY the image prompt from this response.\nOutput NOTHING else.\n\n{response}\n\nIMAGE PROMPT (ONLY THE PROMPT, NO EXPLANATION):",
                        "prefix": "",
                        "suffix": ""
                    }
                }
                self._save_profiles_to_file()
            
            # Update profile combo with loaded profiles
            if hasattr(self, 'profile_combo'):
                profile_names = list(self.profiles.keys())
                self.profile_combo.clear()
                self.profile_combo.addItems(sorted(profile_names))
                
                # Restore last selected profile (don't save during init)
                last_selected = self.settings.get("last_selected_prompt_profile", "default")
                if last_selected in self.profiles:
                    self.profile_combo.setCurrentText(last_selected)
                    self._load_profile_to_ui(last_selected, should_save=False)
                    if DebugConfig.model_restore:
                        print(f"[DEBUG] Restored last profile: {last_selected}")
                else:
                    self.profile_combo.setCurrentText("default")
                    self._load_profile_to_ui("default", should_save=False)
        except Exception as e:
            print(f"[ERROR] Loading prompt profiles: {e}")
            self.profiles = {}
    
    def save_all_settings(self):
        """Save all image settings"""
        try:
            self.settings = load_settings()
            
            # ComfyUI settings
            self.settings["comfyui_url"] = self.comfyui_url_input.text()
            self.settings["comfyui_root_folder"] = self.comfyui_root_input.text()
            
            # Generation settings
            self.settings["image_resolution"] = self.resolution_combo.currentText()
            self.settings["image_steps"] = str(self.steps_spinbox.value())
            self.settings["image_cfg_scale"] = str(self.cfg_scale_spinbox.value())
            self.settings["image_sampler"] = self.sampler_combo.currentText()
            self.settings["image_scheduler"] = self.scheduler_combo.currentText()
            self.settings["generation_timeout"] = str(self.generation_timeout_spinbox.value())
            
            # Model selection - extract clean name from display (remove folder prefix)
            model_display = self.model_combo.currentText()
            if " " in model_display and model_display.startswith("["):
                checkpoint_model = model_display.split("] ", 1)[1]
            else:
                checkpoint_model = model_display
            self.settings["checkpoint_model"] = checkpoint_model
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving Model: {checkpoint_model} (display: {model_display})")
            
            vae_selected = self.vae_combo.currentText()
            self.settings["vae_model"] = vae_selected
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving VAE: {vae_selected}")
            
            # CLIP Name 1 and 2
            self.settings["clip_name1"] = self.clip_name1_combo.currentText()
            self.settings["clip_name2"] = self.clip_name2_combo.currentText()
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving CLIP Name 1: {self.clip_name1_combo.currentText()}, CLIP Name 2: {self.clip_name2_combo.currentText()}")
            
            # CLIP Type
            self.settings["clip_type"] = self.clip_type_combo.currentText()
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving CLIP Type: {self.clip_type_combo.currentText()}")
            
            # CLIP Loader type
            self.settings["clip_loader"] = self.clip_loader_combo.currentText()
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving CLIP Loader: {self.clip_loader_combo.currentText()}")
            
            # UNet Weight DType
            self.settings["unet_weight_dtype"] = self.unet_weight_dtype_combo.currentText()
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving UNet Weight DType: {self.unet_weight_dtype_combo.currentText()}")
            
            # LoRA settings
            lora_enabled = self.lora_enabled_checkbox.isChecked() if self.lora_enabled_checkbox else False
            lora_name = self.lora_combo.currentText() if self.lora_combo else "(none)"
            lora_strength = self.lora_strength_spinbox.value() if self.lora_strength_spinbox else 1.0
            
            self.settings["lora_enabled"] = lora_enabled
            self.settings["lora_name"] = lora_name
            self.settings["lora_strength"] = str(lora_strength)
            
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Saving LoRA - Enabled: {lora_enabled}, Name: {lora_name}, Strength: {lora_strength}")
            
            # Loader type (which radio button is selected)
            if self.loader_standard_rb.isChecked():
                self.settings["loader_type"] = "standard"
            elif self.loader_gguf_rb.isChecked():
                self.settings["loader_type"] = "gguf"
            elif self.loader_unet_rb.isChecked():
                self.settings["loader_type"] = "unet"
            elif self.loader_diffuse_rb.isChecked():
                self.settings["loader_type"] = "diffuse"
            
            # Extraction settings
            self.settings["extraction_model_provider"] = self.provider_combo.currentText()
            self.settings["extraction_provider_url"] = self.provider_url_input.text()
            self.settings["extraction_model"] = self.extraction_model_combo.currentText()
            self.settings["extraction_model_unload_timeout"] = self._get_unload_timeout_value(self.extraction_model_unload_combo.currentText())
            self.settings["enable_prompt_extraction"] = self.enable_prompt_extraction_checkbox.isChecked()
            self.settings["extraction_temperature"] = str(self.extraction_temperature_spinbox.value())
            self.settings["extraction_timeout"] = str(self.extraction_timeout_spinbox.value())
            self.settings["min_response_length"] = str(self.min_response_length_spinbox.value())
            self.settings["add_realistic_keywords"] = self.realistic_keywords_checkbox.isChecked()
            
            # Prompts
            self.settings["extraction_system_prompt"] = self.system_prompt_text.toPlainText()
            self.settings["extraction_user_prompt"] = self.user_prompt_text.toPlainText()
            self.settings["extraction_prefix"] = self.prefix_input.text()
            self.settings["extraction_suffix"] = self.suffix_input.text()
            
            # Image display settings
            self.settings["image_fit_to_area"] = self.right_panel.fit_image_checkbox.isChecked()
            
            # Save current profile selection
            if hasattr(self, 'profile_combo'):
                self.settings["last_selected_prompt_profile"] = self.profile_combo.currentText()
            
            saver = get_settings_saver()
            saver.sync_from_ui_dict(self.settings)
            saver.save()
            
            # Verify settings were saved by reloading
            reloaded = load_settings()
            if reloaded.get("checkpoint_model") == checkpoint_model:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] ✅ Verification: Model setting saved and verified")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] ⚠️ WARNING: Model setting NOT saved. Saved: {reloaded.get('checkpoint_model')}, Expected: {checkpoint_model}")
            
            self.test_status_label.setText("✅ Settings saved!")
            QMessageBox.information(self, "Success", "All settings saved successfully!")
            
        except Exception as e:
            self.test_status_label.setText(f"❌ Error saving settings")
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")
            print(f"[ERROR] Saving settings: {e}")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(self, "Reset to Defaults", 
                                     "Are you sure you want to reset all settings to defaults?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Reset all fields
            self.comfyui_url_input.setText("http://127.0.0.1:8188")
            self.comfyui_root_input.setText("")
            self.resolution_combo.setCurrentText("768x768")
            self.steps_spinbox.setValue(20)
            self.cfg_scale_spinbox.setValue(7.5)
            self.sampler_combo.setCurrentText("euler")
            self.generation_timeout_spinbox.setValue(300)
            self.model_combo.setCurrentIndex(0)
            self.vae_combo.setCurrentIndex(0)
            self.clip_name1_combo.setCurrentIndex(0)
            self.clip_name2_combo.setCurrentIndex(0)
            self.clip_type_combo.setCurrentText("stable_diffusion")
            self.unet_weight_dtype_combo.setCurrentText("default")
            self.loader_standard_rb.setChecked(True)
            
            self.provider_combo.setCurrentText("ollama")
            self.provider_url_input.setText("http://localhost:11434")
            # Don't reset extraction model - keep the last selected one
            # self.extraction_model_combo.setCurrentIndex(0)  # DISABLED to preserve model selection
            self.extraction_temperature_spinbox.setValue(0.3)
            self.extraction_timeout_spinbox.setValue(120)
            self.min_response_length_spinbox.setValue(100)
            self.realistic_keywords_checkbox.setChecked(True)
            
            # Reset to "Generic" prompt style
            if hasattr(self, 'builtin_prompt_combo'):
                self.builtin_prompt_combo.setCurrentText("Generic")
            prompts = self.builtin_prompts["Generic"]
            self.system_prompt_text.setPlainText(prompts["system_prompt"])
            self.user_prompt_text.setPlainText(prompts["user_prompt"])
            
            self.prefix_input.setText("")
            self.suffix_input.setText("")
            
            self.save_all_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            self.settings = load_settings()
            
            # ComfyUI
            self.comfyui_url_input.setText(self.settings.get("comfyui_url", "http://127.0.0.1:8188"))
            root_folder = self.settings.get("comfyui_root_folder", "")
            self.comfyui_root_input.setText(root_folder)
            
            # If root folder is configured, auto-load models
            if root_folder:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Root folder configured: {root_folder} - auto-loading models")
                self.refresh_models()
            else:
                if DebugConfig.chat_enabled:
                    print("[DEBUG] No root folder configured in settings")
                self.test_status_label.setText("⚠️ ComfyUI root folder not configured")
            
            # Generation
            self.resolution_combo.setCurrentText(self.settings.get("image_resolution", "768x768"))
            self.steps_spinbox.setValue(int(self.settings.get("image_steps", "20")))
            self.cfg_scale_spinbox.setValue(float(self.settings.get("image_cfg_scale", "7.5")))
            self.sampler_combo.setCurrentText(self.settings.get("image_sampler", "euler"))
            self.scheduler_combo.setCurrentText(self.settings.get("image_scheduler", "normal"))
            self.generation_timeout_spinbox.setValue(int(self.settings.get("generation_timeout", "300")))
            
            # Model selection - STORE for restoration after models are loaded
            # Don't try to restore now because models may not be loaded yet
            self.pending_checkpoint = self.settings.get("checkpoint_model", "")
            self.pending_vae = self.settings.get("vae_model", "(auto)")
            self.pending_clip_name1 = self.settings.get("clip_name1", "(auto)")
            self.pending_clip_name2 = self.settings.get("clip_name2", "(same as CLIP Name 1)")
            self.pending_clip_type = self.settings.get("clip_type", "stable_diffusion")
            self.pending_lora = self.settings.get("lora_name", "(none)")
            self.pending_lora_strength = float(self.settings.get("lora_strength", "1.0"))
            
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Stored pending restoration - Model: {self.pending_checkpoint}, VAE: {self.pending_vae}, CLIP Name 1: {self.pending_clip_name1}, CLIP Name 2: {self.pending_clip_name2}, CLIP Type: {self.pending_clip_type}, LoRA: {self.pending_lora}, LoRA Strength: {self.pending_lora_strength}")
            
            # CLIP Type
            clip_type = self.settings.get("clip_type", "stable_diffusion")
            idx = self.clip_type_combo.findText(clip_type)
            if idx >= 0:
                self.clip_type_combo.setCurrentIndex(idx)
            else:
                self.clip_type_combo.setCurrentText("stable_diffusion")
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Restored CLIP Type: {clip_type}")
            
            # CLIP Loader
            clip_loader = self.settings.get("clip_loader", "CLIPLoader")
            idx = self.clip_loader_combo.findText(clip_loader)
            if idx >= 0:
                self.clip_loader_combo.setCurrentIndex(idx)
            else:
                self.clip_loader_combo.setCurrentText("CLIPLoader")
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Restored CLIP Loader: {clip_loader}")
            
            # UNet Weight DType
            unet_weight_dtype = self.settings.get("unet_weight_dtype", "default")
            idx = self.unet_weight_dtype_combo.findText(unet_weight_dtype)
            if idx >= 0:
                self.unet_weight_dtype_combo.setCurrentIndex(idx)
            else:
                self.unet_weight_dtype_combo.setCurrentText("default")
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Restored UNet Weight DType: {unet_weight_dtype}")
            
            # LoRA settings
            if self.lora_enabled_checkbox:
                lora_enabled = self.settings.get("lora_enabled", False)
                self.lora_enabled_checkbox.setChecked(lora_enabled)
            
            if self.lora_combo:
                lora_name = self.settings.get("lora_name", "(none)")
                idx = self.lora_combo.findText(lora_name)
                if idx >= 0:
                    self.lora_combo.setCurrentIndex(idx)
                else:
                    self.lora_combo.setCurrentText("(none)")
            
            if self.lora_strength_spinbox:
                lora_strength = float(self.settings.get("lora_strength", "1.0"))
                self.lora_strength_spinbox.setValue(lora_strength)
            
            if DebugConfig.comfyui_generation_settings:
                lora_enabled = self.settings.get("lora_enabled", False)
                lora_name = self.settings.get("lora_name", "(none)")
                lora_strength = self.settings.get("lora_strength", "1.0")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Restored LoRA - Enabled: {lora_enabled}, Name: {lora_name}, Strength: {lora_strength}")
            
            # Loader type
            loader_type = self.settings.get("loader_type", "standard")
            if loader_type == "gguf":
                self.loader_gguf_rb.setChecked(True)
            elif loader_type == "unet":
                self.loader_unet_rb.setChecked(True)
            elif loader_type == "diffuse":
                self.loader_diffuse_rb.setChecked(True)
            else:
                self.loader_standard_rb.setChecked(True)
            
            # Extraction
            self.provider_combo.setCurrentText(self.settings.get("extraction_model_provider", "ollama"))
            self.provider_url_input.setText(self.settings.get("extraction_provider_url", "http://localhost:11434"))
            
            # For extraction model, use saved value OR fall back to a reasonable default
            extraction_model = self.settings.get("extraction_model", "")
            
            if not extraction_model:
                # No saved model, set to placeholder
                extraction_model = "(click Refresh Models)"
                self.extraction_model_combo.setCurrentText(extraction_model)
            else:
                # Try to set saved model - add it even if not currently in dropdown
                if self.extraction_model_combo.findText(extraction_model) >= 0:
                    self.extraction_model_combo.setCurrentText(extraction_model)
                else:
                    # Add it even if not in list - will be validated when used
                    self.extraction_model_combo.insertItem(0, extraction_model)
                    self.extraction_model_combo.setCurrentIndex(0)
            
            # Load extraction model unload timeout
            unload_timeout_value = self.settings.get("extraction_model_unload_timeout", 0)
            unload_timeout_text = self._convert_timeout_to_combo_text(unload_timeout_value)
            if self.extraction_model_unload_combo.findText(unload_timeout_text) >= 0:
                self.extraction_model_unload_combo.setCurrentText(unload_timeout_text)
            else:
                self.extraction_model_unload_combo.setCurrentText("0 (Immediate)")
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Restored Extraction Model: {extraction_model}")
            
            self.extraction_temperature_spinbox.setValue(float(self.settings.get("extraction_temperature", "0.3")))
            self.extraction_timeout_spinbox.setValue(int(self.settings.get("extraction_timeout", "120")))
            self.min_response_length_spinbox.setValue(int(self.settings.get("min_response_length", "100")))
            self.enable_prompt_extraction_checkbox.setChecked(self.settings.get("enable_prompt_extraction", False))
            self.realistic_keywords_checkbox.setChecked(self.settings.get("add_realistic_keywords", True))
            
            
            # Prompts
            system_prompt = self.settings.get("extraction_system_prompt", "")
            if system_prompt:
                self.system_prompt_text.setPlainText(system_prompt)
            
            user_prompt = self.settings.get("extraction_user_prompt", "")
            if user_prompt:
                self.user_prompt_text.setPlainText(user_prompt)
            
            self.prefix_input.setText(self.settings.get("extraction_prefix", ""))
            self.suffix_input.setText(self.settings.get("extraction_suffix", ""))
            
            # Image display settings
            fit_to_area = self.settings.get("image_fit_to_area", True)
            self.right_panel.fit_image_checkbox.setChecked(fit_to_area)
            
        except Exception as e:
            print(f"[ERROR] Loading settings: {e}")
    
    def _save_profiles_to_file(self):
        """Save all profiles to prompt_profiles.json"""
        try:
            profiles_file = Path(__file__).parent.parent / "prompt_profiles.json"
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=2, ensure_ascii=False)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Profiles saved to {profiles_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save profiles: {e}")
    
    def _on_profile_changed(self, profile_name):
        """Called when profile selection changes - just track it"""
        pass
    
    def _load_profile_to_ui(self, profile_name, should_save=True):
        """Load profile data into UI fields"""
        if profile_name not in self.profiles:
            return
        
        profile = self.profiles[profile_name]
        
        # Load all four components
        self.system_prompt_text.setPlainText(profile.get("system_prompt", ""))
        self.user_prompt_text.setPlainText(profile.get("user_prompt", ""))
        self.prefix_input.setText(profile.get("prefix", ""))
        self.suffix_input.setText(profile.get("suffix", ""))
        
        # Only save if this was user-initiated (not during init)
        if not should_save:
            return
        
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] Loaded profile: {profile_name}")
    
    def load_prompt_profile(self):
        """Load selected profile from combo box"""
        profile_name = self.profile_combo.currentText()
        self._load_profile_to_ui(profile_name, should_save=True)
        
        # Track the selected profile (will save on explicit button click)
        saver = get_settings_saver()
        saver.set("last_selected_prompt_profile", profile_name)
        
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] ✅ Loaded profile: {profile_name}")
    
    def save_current_profile(self):
        """Save/overwrite the currently selected profile"""
        profile_name = self.profile_combo.currentText()
        
        if not profile_name or profile_name == "(click Refresh Models)":
            QMessageBox.warning(self, "Error", "Please select a valid profile")
            return
        
        # Save current UI values to the selected profile
        self.profiles[profile_name] = {
            "system_prompt": self.system_prompt_text.toPlainText(),
            "user_prompt": self.user_prompt_text.toPlainText(),
            "prefix": self.prefix_input.text(),
            "suffix": self.suffix_input.text()
        }
        
        self._save_profiles_to_file()
        
        QMessageBox.information(self, "Success", f"Profile '{profile_name}' saved successfully!")
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] ✅ Profile saved/overwritten: {profile_name}")
    
    def save_prompt_profile(self):
        """Save current UI values as a new profile"""
        from PyQt5.QtWidgets import QDialog
        
        # Create dialog (use QDialog, not QWidget, and store as instance variable)
        self.save_dialog = QDialog(self)
        self.save_dialog.setWindowTitle("Save Profile As")
        self.save_dialog.setGeometry(100, 100, 400, 150)
        
        dialog_layout = QVBoxLayout()
        
        label = QLabel("Profile Name:")
        dialog_layout.addWidget(label)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter profile name...")
        dialog_layout.addWidget(name_input)
        
        button_layout = QHBoxLayout()
        
        def save():
            profile_name = name_input.text().strip()
            if not profile_name:
                QMessageBox.warning(self.save_dialog, "Error", "Profile name cannot be empty")
                return
            
            # Save current UI values as profile
            self.profiles[profile_name] = {
                "system_prompt": self.system_prompt_text.toPlainText(),
                "user_prompt": self.user_prompt_text.toPlainText(),
                "prefix": self.prefix_input.text(),
                "suffix": self.suffix_input.text()
            }
            
            self._save_profiles_to_file()
            
            # Update dropdown - maintain sorted order
            if self.profile_combo.findText(profile_name) < 0:
                # Insert in sorted position
                current_items = [self.profile_combo.itemText(i) for i in range(self.profile_combo.count())]
                current_items.append(profile_name)
                current_items.sort()
                self.profile_combo.clear()
                self.profile_combo.addItems(current_items)
            
            self.profile_combo.setCurrentText(profile_name)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] ✅ Profile saved: {profile_name}")
            self.save_dialog.close()
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("background-color: #00cc66; color: white;")
        save_btn.clicked.connect(save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("background-color: #cc0000; color: white;")
        cancel_btn.clicked.connect(self.save_dialog.close)
        button_layout.addWidget(cancel_btn)
        
        dialog_layout.addLayout(button_layout)
        
        self.save_dialog.setLayout(dialog_layout)
        self.save_dialog.exec_()
    
    def reset_prompt_profile(self):
        """Reset current profile to default"""
        reply = QMessageBox.question(self, "Confirm", "Reset to default profile? This will overwrite current settings.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.profile_combo.setCurrentText("default")
            self._load_profile_to_ui("default", should_save=True)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] ✅ Profile reset to default")
    
    def delete_prompt_profile(self):
        """Delete selected profile"""
        profile_name = self.profile_combo.currentText()
        if profile_name == "default":
            QMessageBox.warning(self, "Error", "Cannot delete the default profile")
            return
        
        reply = QMessageBox.question(self, "Confirm", f"Delete profile '{profile_name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if profile_name in self.profiles:
                del self.profiles[profile_name]
                self._save_profiles_to_file()
                
                # Update dropdown
                self.profile_combo.removeItem(self.profile_combo.findText(profile_name))
                self.profile_combo.setCurrentText("default")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] ✅ Profile deleted: {profile_name}")
    
    def showEvent(self, event):
        """Called when tab is shown - refresh image list"""
        super().showEvent(event)
        # Refresh image list when user opens the image settings tab
        if self.right_panel and hasattr(self.right_panel, '_refresh_image_list'):
            self.right_panel._refresh_image_list()
