"""
Image Settings Tab - Configure image generation and extraction settings
"""

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
from pathlib import Path


class ImageSettingsTab:
    """Image generation and extraction settings UI"""
    
    def __init__(self, parent, app):
        """Initialize image settings tab"""
        self.parent = parent
        self.app = app
        
        self.create_widgets()
        self.load_settings()
    
    def create_widgets(self):
        """Create all image settings widgets"""
        
        # Create split layout using PanedWindow for proper resizable split
        split_container = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        split_container.pack(fill=tk.BOTH, expand=True)
        
        # LEFT SIDE: Settings scrollable area
        left_container = tk.Frame(split_container, bg="#f0f0f0")
        split_container.add(left_container, weight=1)  # Weight allows resizing
        
        canvas = tk.Canvas(left_container, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f0f0f0")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind canvas resize to expand scrollable_frame width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Store reference for scrollable frame (for button placement at top)
        self.scrollable_frame = scrollable_frame
        
        # RIGHT SIDE: Image viewer
        image_frame = tk.Frame(split_container, bg="#f0f0f0")
        split_container.add(image_frame, weight=1)  # Weight allows resizing
        
        # Import and create image viewer
        from ui.image_viewer import ImageViewerWidget
        self.image_viewer = ImageViewerWidget(image_frame, width=250, height=600)
        self.app.image_viewer = self.image_viewer  # Also store in app for access
        
        # ===== ACTION BUTTONS (at top) =====
        self._create_action_buttons()
        
        # ===== COMFYUI SECTION =====
        comfyui_frame = tk.LabelFrame(scrollable_frame, text="ComfyUI Server", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        comfyui_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # ComfyUI URL
        tk.Label(comfyui_frame, text="ComfyUI Server URL:", bg="#f0f0f0").pack(anchor="w")
        url_frame = tk.Frame(comfyui_frame, bg="#f0f0f0")
        url_frame.pack(fill=tk.X, pady=5)
        
        self.comfyui_url_var = tk.StringVar(value="http://127.0.0.1:8188")
        tk.Entry(url_frame, textvariable=self.comfyui_url_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(url_frame, text="Test Connection", command=self.test_comfyui_connection, bg="#0066cc", fg="white").pack(side=tk.LEFT, padx=5)
        
        self.comfyui_status_label = tk.Label(comfyui_frame, text="", bg="#f0f0f0", fg="#009900")
        self.comfyui_status_label.pack(anchor="w", pady=5)
        
        # ComfyUI Root Folder (for model discovery)
        tk.Label(comfyui_frame, text="ComfyUI Root Folder:", bg="#f0f0f0").pack(anchor="w")
        root_folder_frame = tk.Frame(comfyui_frame, bg="#f0f0f0")
        root_folder_frame.pack(fill=tk.X, pady=5)
        
        self.comfyui_root_var = tk.StringVar(value="")
        root_folder_entry = tk.Entry(root_folder_frame, textvariable=self.comfyui_root_var, width=50)
        root_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Button(root_folder_frame, text="Browse", command=self.browse_comfyui_folder, bg="#666666", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        
        tk.Label(comfyui_frame, text="(e.g., C:\\ComfyUI) - Used to find checkpoint, diffusion_models, and other model directories", bg="#f0f0f0", fg="#666666", font=("Arial", 9)).pack(anchor="w", padx=5)
        
        # ===== IMAGE GENERATION OPTIONS =====
        gen_options_frame = tk.LabelFrame(scrollable_frame, text="Image Generation Options", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        gen_options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Generation status label
        self.generation_status_label = tk.Label(gen_options_frame, text="", bg="#f0f0f0", fg="#009900", wraplength=400, justify=tk.LEFT)
        self.generation_status_label.pack(anchor="w", pady=5)
        
        # Resolution
        res_frame = tk.Frame(gen_options_frame, bg="#f0f0f0")
        res_frame.pack(fill=tk.X, pady=5)
        tk.Label(res_frame, text="Resolution:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.resolution_var = tk.StringVar(value="768x768")
        resolution_combo = ttk.Combobox(res_frame, textvariable=self.resolution_var, state="readonly", width=15)
        resolution_combo['values'] = ["512x512", "640x640", "768x768", "1024x1024", "512x768", "768x512"]
        resolution_combo.pack(side=tk.LEFT, padx=10)
        
        # Steps
        steps_frame = tk.Frame(gen_options_frame, bg="#f0f0f0")
        steps_frame.pack(fill=tk.X, pady=5)
        tk.Label(steps_frame, text="Inference Steps:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.steps_var = tk.StringVar(value="20")
        tk.Spinbox(steps_frame, from_=1, to=100, textvariable=self.steps_var, width=15).pack(side=tk.LEFT, padx=10)
        
        # CFG Scale (guidance scale)
        cfg_frame = tk.Frame(gen_options_frame, bg="#f0f0f0")
        cfg_frame.pack(fill=tk.X, pady=5)
        tk.Label(cfg_frame, text="CFG Scale (Guidance):", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.cfg_scale_var = tk.StringVar(value="7.5")
        tk.Spinbox(cfg_frame, from_=1.0, to=20.0, increment=0.5, textvariable=self.cfg_scale_var, width=15).pack(side=tk.LEFT, padx=10)
        
        # Sampler
        sampler_frame = tk.Frame(gen_options_frame, bg="#f0f0f0")
        sampler_frame.pack(fill=tk.X, pady=5)
        tk.Label(sampler_frame, text="Sampler:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.sampler_var = tk.StringVar(value="euler")
        sampler_combo = ttk.Combobox(sampler_frame, textvariable=self.sampler_var, state="readonly", width=15)
        sampler_combo['values'] = ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", "dpmpp_sde", "dpmpp_sde_gpu", "dpmpp_2m"]
        sampler_combo.pack(side=tk.LEFT, padx=10)
        
        # ===== COMFYUI MODEL SELECTION SECTION =====
        model_selection_frame = tk.LabelFrame(scrollable_frame, text="ComfyUI Model Selection", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        model_selection_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Checkpoint Model
        checkpoint_frame = tk.Frame(model_selection_frame, bg="#f0f0f0")
        checkpoint_frame.pack(fill=tk.X, pady=5)
        tk.Label(checkpoint_frame, text="Checkpoint:", bg="#f0f0f0", width=25, anchor="w").pack(side=tk.LEFT)
        self.checkpoint_model_var = tk.StringVar(value="sd_xl_base_1.0.safetensors")
        self.checkpoint_combo = ttk.Combobox(checkpoint_frame, textvariable=self.checkpoint_model_var, width=30)
        self.checkpoint_combo['values'] = ["(click Refresh to load models)"]
        self.checkpoint_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.checkpoint_size_label = tk.Label(checkpoint_frame, text="", bg="#f0f0f0", fg="#666666", font=("Arial", 8))
        self.checkpoint_size_label.pack(side=tk.LEFT, padx=5)
        
        # Has built-in CLIP and VAE checkbox
        builtin_frame = tk.Frame(model_selection_frame, bg="#f0f0f0")
        builtin_frame.pack(fill=tk.X, pady=5, padx=25)
        self.checkpoint_has_builtin_var = tk.BooleanVar(value=True)
        builtin_cb = tk.Checkbutton(
            builtin_frame,
            text="☑ Checkpoint includes built-in CLIP and VAE",
            variable=self.checkpoint_has_builtin_var,
            bg="#f0f0f0",
            font=("Arial", 9),
            command=self._on_builtin_changed
        )
        builtin_cb.pack(anchor="w")
        
        # VAE dropdown (enabled only if checkbox is unchecked)
        vae_frame = tk.Frame(model_selection_frame, bg="#f0f0f0")
        vae_frame.pack(fill=tk.X, pady=5)
        tk.Label(vae_frame, text="VAE (external):", bg="#f0f0f0", width=25, anchor="w").pack(side=tk.LEFT)
        self.vae_var = tk.StringVar(value="")
        self.vae_combo = ttk.Combobox(vae_frame, textvariable=self.vae_var, width=30, state="disabled")
        self.vae_combo['values'] = ["(none)"]
        self.vae_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.vae_size_label = tk.Label(vae_frame, text="", bg="#f0f0f0", fg="#666666", font=("Arial", 8))
        self.vae_size_label.pack(side=tk.LEFT, padx=5)
        
        # Text Encoder dropdown (enabled only if checkbox is unchecked)
        encoder_frame = tk.Frame(model_selection_frame, bg="#f0f0f0")
        encoder_frame.pack(fill=tk.X, pady=5)
        tk.Label(encoder_frame, text="Text Encoder:", bg="#f0f0f0", width=25, anchor="w").pack(side=tk.LEFT)
        self.text_encoder_var = tk.StringVar(value="")
        self.text_encoder_combo = ttk.Combobox(encoder_frame, textvariable=self.text_encoder_var, width=30, state="disabled")
        self.text_encoder_combo['values'] = ["(none)"]
        self.text_encoder_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.encoder_size_label = tk.Label(encoder_frame, text="", bg="#f0f0f0", fg="#666666", font=("Arial", 8))
        self.encoder_size_label.pack(side=tk.LEFT, padx=5)
        
        # Refresh button
        refresh_frame = tk.Frame(model_selection_frame, bg="#f0f0f0")
        refresh_frame.pack(fill=tk.X, pady=10)
        tk.Button(refresh_frame, text="Refresh Models", command=self.refresh_comfyui_models, bg="#0099cc", fg="white", width=20, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        
        # Loader Type Selection (Radio buttons)
        loader_frame = tk.LabelFrame(model_selection_frame, text="Loader Type", bg="#f0f0f0", padx=10, pady=5)
        loader_frame.pack(fill=tk.X, pady=10)
        
        self.loader_type_var = tk.StringVar(value="standard")
        
        loader_options = [
            ("Standard Checkpoint", "standard"),
            ("GGUF (Quantized)", "gguf"),
            ("UNet (Standalone)", "unet"),
            ("Diffusion Model", "diffuse")
        ]
        
        for text, value in loader_options:
            rb = tk.Radiobutton(
                loader_frame,
                text=text,
                variable=self.loader_type_var,
                value=value,
                bg="#f0f0f0",
                font=("Arial", 9),
                command=self._on_loader_type_changed
            )
            rb.pack(anchor="w", pady=2)
        
        # Model type specific dropdowns (initially hidden)
        self.loader_models_frame = tk.Frame(model_selection_frame, bg="#f0f0f0")
        self.loader_models_frame.pack(fill=tk.X, pady=10)
        
        # GGUF model dropdown
        gguf_frame = tk.Frame(self.loader_models_frame, bg="#f0f0f0")
        gguf_frame.pack(fill=tk.X, pady=5)
        tk.Label(gguf_frame, text="GGUF Model:", bg="#f0f0f0", width=25, anchor="w").pack(side=tk.LEFT)
        self.gguf_model_var = tk.StringVar(value="")
        self.gguf_combo = ttk.Combobox(gguf_frame, textvariable=self.gguf_model_var, width=30)
        self.gguf_combo['values'] = ["(none)"]
        self.gguf_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.gguf_size_label = tk.Label(gguf_frame, text="", bg="#f0f0f0", fg="#666666", font=("Arial", 8))
        self.gguf_size_label.pack(side=tk.LEFT, padx=5)
        gguf_frame.pack_forget()  # Hide initially
        self.gguf_frame = gguf_frame
        
        # UNet model dropdown
        unet_frame = tk.Frame(self.loader_models_frame, bg="#f0f0f0")
        unet_frame.pack(fill=tk.X, pady=5)
        tk.Label(unet_frame, text="UNet Model:", bg="#f0f0f0", width=25, anchor="w").pack(side=tk.LEFT)
        self.unet_model_var = tk.StringVar(value="")
        self.unet_combo = ttk.Combobox(unet_frame, textvariable=self.unet_model_var, width=30)
        self.unet_combo['values'] = ["(none)"]
        self.unet_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.unet_size_label = tk.Label(unet_frame, text="", bg="#f0f0f0", fg="#666666", font=("Arial", 8))
        self.unet_size_label.pack(side=tk.LEFT, padx=5)
        unet_frame.pack_forget()  # Hide initially
        self.unet_frame = unet_frame
        
        # Diffusion model dropdown
        diffusion_frame = tk.Frame(self.loader_models_frame, bg="#f0f0f0")
        diffusion_frame.pack(fill=tk.X, pady=5)
        tk.Label(diffusion_frame, text="Diffusion Model:", bg="#f0f0f0", width=25, anchor="w").pack(side=tk.LEFT)
        self.diffusion_model_var = tk.StringVar(value="")
        self.diffusion_combo = ttk.Combobox(diffusion_frame, textvariable=self.diffusion_model_var, width=30)
        self.diffusion_combo['values'] = ["(none)"]
        self.diffusion_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.diffusion_size_label = tk.Label(diffusion_frame, text="", bg="#f0f0f0", fg="#666666", font=("Arial", 8))
        self.diffusion_size_label.pack(side=tk.LEFT, padx=5)
        diffusion_frame.pack_forget()  # Hide initially
        self.diffusion_frame = diffusion_frame
        
        # Store old image generation options frame reference
        self.gen_options_frame = gen_options_frame
        
        # ===== PROMPT EXTRACTION SETTINGS =====
        extraction_frame = tk.LabelFrame(scrollable_frame, text="Prompt Extraction (LLM)", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        extraction_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Local Model Provider (Ollama or Llama Server)
        provider_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        provider_frame.pack(fill=tk.X, pady=5)
        tk.Label(provider_frame, text="Model Provider:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.model_provider_var = tk.StringVar(value="ollama")
        provider_combo = ttk.Combobox(provider_frame, textvariable=self.model_provider_var, state="readonly", width=15)
        provider_combo['values'] = ["ollama", "llama_server"]
        provider_combo.pack(side=tk.LEFT, padx=10)
        provider_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_available_models())
        
        # Provider URL
        provider_url_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        provider_url_frame.pack(fill=tk.X, pady=5)
        tk.Label(provider_url_frame, text="Provider URL:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.provider_url_var = tk.StringVar(value="http://localhost:11434")
        tk.Entry(provider_url_frame, textvariable=self.provider_url_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Local Model selection
        model_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        model_frame.pack(fill=tk.X, pady=5)
        tk.Label(model_frame, text="Local Model:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.extraction_model_var = tk.StringVar(value="dolphin-2.1:2.4b")
        self.extraction_model_combo = ttk.Combobox(model_frame, textvariable=self.extraction_model_var, state="readonly", width=30)
        self.extraction_model_combo['values'] = ["(click Refresh Models)"]
        self.extraction_model_combo.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        refresh_btn = tk.Button(model_frame, text="Refresh Models", command=self.refresh_available_models, bg="#0099cc", fg="white", width=15)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Response length threshold
        response_len_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        response_len_frame.pack(fill=tk.X, pady=5)
        tk.Label(response_len_frame, text="Min Response Length:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        tk.Label(response_len_frame, text="Skip image generation if response is shorter than (chars):", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.min_response_length_var = tk.StringVar(value="100")
        tk.Spinbox(response_len_frame, from_=0, to=1000, textvariable=self.min_response_length_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Extraction temperature
        temp_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        temp_frame.pack(fill=tk.X, pady=5)
        tk.Label(temp_frame, text="Extraction Temperature:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.extraction_temperature_var = tk.StringVar(value="0.3")
        tk.Spinbox(temp_frame, from_=0.0, to=1.0, increment=0.1, textvariable=self.extraction_temperature_var, width=10).pack(side=tk.LEFT, padx=10)
        tk.Label(temp_frame, text="(Lower = more focused)", bg="#f0f0f0", fg="#666666").pack(side=tk.LEFT, padx=5)
        
        # Extraction timeout
        timeout_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        timeout_frame.pack(fill=tk.X, pady=5)
        tk.Label(timeout_frame, text="Extraction Timeout:", bg="#f0f0f0", width=20, anchor="w").pack(side=tk.LEFT)
        self.extraction_timeout_var = tk.StringVar(value="120")
        tk.Spinbox(timeout_frame, from_=10, to=600, increment=10, textvariable=self.extraction_timeout_var, width=10).pack(side=tk.LEFT, padx=10)
        tk.Label(timeout_frame, text="seconds (default: 120)", bg="#f0f0f0", fg="#666666").pack(side=tk.LEFT, padx=5)
        
        # ===== ADD REALISTIC KEYWORDS CHECKBOX =====
        realistic_frame = tk.Frame(extraction_frame, bg="#f0f0f0")
        realistic_frame.pack(fill=tk.X, pady=10)
        self.add_realistic_keywords_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            realistic_frame,
            text="✓ Auto-add realistic keywords to prompts (photorealistic, 8k, detailed)",
            variable=self.add_realistic_keywords_var,
            bg="#f0f0f0",
            font=("Arial", 10)
        ).pack(anchor="w")
        
        # ===== EXTRACTION PROMPT PROFILES (unified system) =====
        profiles_frame = tk.LabelFrame(scrollable_frame, text="Extraction Prompt Profiles (System + User + Prefix/Suffix)", bg="#f0f0f0", font=("Arial", 11, "bold"), padx=10, pady=10)
        profiles_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        # Profile management controls
        profile_mgmt_frame = tk.Frame(profiles_frame, bg="#f0f0f0")
        profile_mgmt_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(profile_mgmt_frame, text="Profile:", bg="#f0f0f0", font=("Arial", 9)).pack(side=tk.LEFT)
        self.profile_var = tk.StringVar(value="default")
        self.profile_combo = ttk.Combobox(profile_mgmt_frame, textvariable=self.profile_var, state="readonly", width=25)
        self.profile_combo['values'] = ["default"]
        self.profile_combo.pack(side=tk.LEFT, padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)
        
        tk.Button(profile_mgmt_frame, text="Load", command=self.load_prompt_profile, bg="#0099cc", fg="white", width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(profile_mgmt_frame, text="Save As", command=self.save_prompt_profile, bg="#00cc66", fg="white", width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(profile_mgmt_frame, text="Reset", command=self.reset_prompt_profile, bg="#ff9900", fg="white", width=8).pack(side=tk.LEFT, padx=2)
        tk.Button(profile_mgmt_frame, text="Delete", command=self.delete_prompt_profile, bg="#ff3333", fg="white", width=8).pack(side=tk.LEFT, padx=2)
        
        # System Prompt section
        tk.Label(profiles_frame, text="System Prompt (instructions for extraction model):", bg="#f0f0f0", font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 2))
        self.system_prompt_text = scrolledtext.ScrolledText(
            profiles_frame,
            wrap=tk.WORD,
            height=5,
            width=80,
            bg="white",
            fg="#333333",
            font=("Courier", 10)
        )
        self.system_prompt_text.pack(fill=tk.BOTH, expand=False, pady=2)
        
        # User Prompt section
        tk.Label(profiles_frame, text="User Prompt Template (use {response} placeholder):", bg="#f0f0f0", font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 2))
        self.user_prompt_text = scrolledtext.ScrolledText(
            profiles_frame,
            wrap=tk.WORD,
            height=5,
            width=80,
            bg="white",
            fg="#333333",
            font=("Courier", 10)
        )
        self.user_prompt_text.pack(fill=tk.BOTH, expand=False, pady=2)
        
        # Prefix section
        prefix_frame = tk.Frame(profiles_frame, bg="#f0f0f0")
        prefix_frame.pack(fill=tk.X, pady=(5, 2))
        tk.Label(prefix_frame, text="Prefix (prepended to prompt):", bg="#f0f0f0", font=("Arial", 9, "bold")).pack(anchor="w")
        self.prefix_text = tk.Entry(prefix_frame, width=80, font=("Courier", 10), bg="white", fg="#333333")
        self.prefix_text.pack(fill=tk.X, pady=2)
        
        # Suffix section
        suffix_frame = tk.Frame(profiles_frame, bg="#f0f0f0")
        suffix_frame.pack(fill=tk.X, pady=(5, 10))
        tk.Label(suffix_frame, text="Suffix (appended to prompt):", bg="#f0f0f0", font=("Arial", 9, "bold")).pack(anchor="w")
        self.suffix_text = tk.Entry(suffix_frame, width=80, font=("Courier", 10), bg="white", fg="#333333")
        self.suffix_text.pack(fill=tk.X, pady=2)
        
        # Load default profile on startup
        self._load_profiles_from_file()

    
    
    def _create_action_buttons(self):
        """Create action buttons at the top of the settings (above ComfyUI section)"""
        button_frame = tk.Frame(self.scrollable_frame, bg="#f0f0f0", relief=tk.FLAT)
        button_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Button(
            button_frame,
            text="Save All",
            command=self.save_all_settings,
            bg="#00cc66",
            fg="white",
            font=("Arial", 9, "bold"),
            width=12,
            padx=5,
            pady=4
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_frame,
            text="Reset",
            command=self.reset_to_defaults,
            bg="#ff9900",
            fg="white",
            font=("Arial", 9, "bold"),
            width=12,
            padx=5,
            pady=4
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            button_frame,
            text="Test Generation",
            command=self.test_image_generation,
            bg="#6633ff",
            fg="white",
            font=("Arial", 9, "bold"),
            width=14,
            padx=5,
            pady=4
        ).pack(side=tk.LEFT, padx=3)
    
    def browse_comfyui_folder(self):
        """Browse for ComfyUI root folder"""
        try:
            from tkinter import filedialog
            folder = filedialog.askdirectory(title="Select ComfyUI Root Folder")
            if folder:
                self.comfyui_root_var.set(folder)
                self.save_all_settings()
                print(f"[DEBUG] Set ComfyUI root to: {folder}")
        except Exception as e:
            print(f"[ERROR] Error browsing folder: {e}")
    
    def refresh_comfyui_models(self):
        """Fetch available models from ComfyUI - populates checkpoints, VAE, and text encoder dropdowns"""
        try:
            import requests
            from pathlib import Path
            url = self.comfyui_url_var.get()
            
            print(f"[DEBUG] Fetching models from ComfyUI at {url}")
            
            checkpoints = []
            vaes = []
            text_encoders = []
            
            # Try API first for checkpoints
            try:
                response = requests.get(f"{url}/api/models/checkpoints", timeout=5)
                if response.status_code == 200:
                    api_models = response.json() if isinstance(response.json(), list) else []
                    if api_models:
                        checkpoints.extend(api_models)
                        print(f"[DEBUG] API returned models: {api_models}")
            except Exception as e:
                print(f"[DEBUG] API call failed: {e}")
            
            # Scan directory for models organized by type
            try:
                comfyui_root = self.comfyui_root_var.get()
                
                if not comfyui_root:
                    raise Exception("ComfyUI Root Folder not set")
                
                root_path = Path(comfyui_root)
                
                # ===== SCAN CHECKPOINTS =====
                checkpoint_dir = root_path / "models" / "checkpoints"
                if checkpoint_dir.exists():
                    print(f"[DEBUG] Scanning checkpoints: {checkpoint_dir}")
                    for ext in ["*.safetensors", "*.gguf", "*.ckpt"]:
                        for model_file in checkpoint_dir.glob(ext):
                            model_name = model_file.name
                            if model_name not in checkpoints:
                                checkpoints.append(model_name)
                                print(f"[DEBUG] Found checkpoint: {model_name}")
                
                # Also check diffusion_models folder for image models
                diffusion_dir = root_path / "models" / "diffusion_models"
                if diffusion_dir.exists():
                    print(f"[DEBUG] Scanning diffusion_models: {diffusion_dir}")
                    for ext in ["*.safetensors", "*.gguf"]:
                        for model_file in diffusion_dir.glob(ext):
                            model_name = model_file.name
                            if model_name not in checkpoints:
                                checkpoints.append(model_name)
                                print(f"[DEBUG] Found diffusion model: {model_name}")
                
                # ===== SCAN VAE =====
                vae_dir = root_path / "models" / "vae"
                if vae_dir.exists():
                    print(f"[DEBUG] Scanning VAE: {vae_dir}")
                    for ext in ["*.safetensors", "*.ckpt"]:
                        for model_file in vae_dir.glob(ext):
                            model_name = model_file.name
                            if model_name not in vaes:
                                vaes.append(model_name)
                                print(f"[DEBUG] Found VAE: {model_name}")
                else:
                    print(f"[DEBUG] VAE directory not found: {vae_dir}")
                
                # ===== SCAN TEXT ENCODERS (CLIP) =====
                # Scan both models/clip and models/text_encoders
                clip_dir = root_path / "models" / "clip"
                text_encoders_dir = root_path / "models" / "text_encoders"
                
                if clip_dir.exists():
                    print(f"[DEBUG] Scanning CLIP/Text Encoders: {clip_dir}")
                    for ext in ["*.safetensors", "*.gguf"]:
                        for model_file in clip_dir.glob(ext):
                            model_name = model_file.name
                            if model_name not in text_encoders:
                                text_encoders.append(model_name)
                                print(f"[DEBUG] Found text encoder (clip): {model_name}")
                else:
                    print(f"[DEBUG] CLIP directory not found: {clip_dir}")
                
                if text_encoders_dir.exists():
                    print(f"[DEBUG] Scanning text_encoders folder: {text_encoders_dir}")
                    for ext in ["*.safetensors", "*.gguf"]:
                        for model_file in text_encoders_dir.glob(ext):
                            model_name = model_file.name
                            if model_name not in text_encoders:
                                text_encoders.append(model_name)
                                print(f"[DEBUG] Found text encoder (text_encoders): {model_name}")
                else:
                    print(f"[DEBUG] text_encoders directory not found: {text_encoders_dir}")
                
            except Exception as e:
                print(f"[DEBUG] Directory scan error: {e}")
            
            # Update dropdowns with sorted results
            if checkpoints:
                checkpoints = sorted(list(set(checkpoints)))
                self.checkpoint_combo['values'] = checkpoints
                print(f"[DEBUG] ✓ Populated checkpoint dropdown with {len(checkpoints)} models")
            
            if vaes:
                vaes = sorted(list(set(vaes)))
                self.vae_combo['values'] = vaes
                print(f"[DEBUG] ✓ Populated VAE dropdown with {len(vaes)} models")
            else:
                print(f"[DEBUG] ✗ No VAE models found")
                self.vae_combo['values'] = []
            
            if text_encoders:
                text_encoders = sorted(list(set(text_encoders)))
                self.text_encoder_combo['values'] = text_encoders
                print(f"[DEBUG] ✓ Populated text encoder dropdown with {len(text_encoders)} models")
            else:
                print(f"[DEBUG] ✗ No text encoder models found")
                self.text_encoder_combo['values'] = []
            
            total_found = len(checkpoints) + len(vaes) + len(text_encoders)
            if total_found > 0:
                self.app.show_status(f"✅ Found {len(checkpoints)} checkpoints, {len(vaes)} VAEs, {len(text_encoders)} encoders", 2000)
            else:
                self.app.show_status(f"❌ No models found. Check ComfyUI Root Folder path.", 2000)
            
        except Exception as e:
            print(f"[ERROR] Error fetching models: {e}")
            self.app.show_status(f"❌ Error: {str(e)}", 2000)
    
    def _on_builtin_changed(self):
        """Handle checkbox change for 'has built-in CLIP and VAE'"""
        has_builtin = self.checkpoint_has_builtin_var.get()
        
        if has_builtin:
            # Disable VAE and Text Encoder dropdowns
            self.vae_combo.config(state="disabled")
            self.text_encoder_combo.config(state="disabled")
        else:
            # Enable VAE and Text Encoder dropdowns
            self.vae_combo.config(state="readonly")
            self.text_encoder_combo.config(state="readonly")
    
    def _on_loader_type_changed(self):
        """Handle loader type radio button change"""
        loader_type = self.loader_type_var.get()
        
        # Hide all loader-specific dropdowns
        self.gguf_frame.pack_forget()
        self.unet_frame.pack_forget()
        self.diffusion_frame.pack_forget()
        
        # Show only the selected loader's dropdown
        if loader_type == "gguf":
            self.gguf_frame.pack(fill=tk.X, pady=5)
        elif loader_type == "unet":
            self.unet_frame.pack(fill=tk.X, pady=5)
        elif loader_type == "diffuse":
            self.diffusion_frame.pack(fill=tk.X, pady=5)
        # "standard" shows no additional dropdown
    
    def load_all_models(self):
        """Load all models from ComfyUIModelManager and populate dropdowns"""
        try:
            from comfyui_model_manager import ComfyUIModelManager
            
            comfyui_root = self.comfyui_root_var.get()
            if not comfyui_root:
                self.app.show_status("❌ Please set ComfyUI Root Folder first", 2000)
                return
            
            # Initialize model manager
            manager = ComfyUIModelManager(comfyui_root)
            all_models = manager.get_all_models()
            
            # Populate checkpoint dropdown with file sizes
            checkpoints = all_models.get("checkpoints", {})
            if checkpoints:
                self.checkpoint_combo['values'] = list(checkpoints.keys())
                print(f"[DEBUG] Loaded {len(checkpoints)} checkpoints")
            
            # Populate VAE dropdown with file sizes
            vaes = all_models.get("vaes", [])
            if vaes:
                self.vae_combo['values'] = vaes
                print(f"[DEBUG] Loaded {len(vaes)} VAEs")
            
            # Populate Text Encoder dropdown
            text_encoders = all_models.get("text_encoders", [])
            if text_encoders:
                self.text_encoder_combo['values'] = text_encoders
                print(f"[DEBUG] Loaded {len(text_encoders)} text encoders")
            
            # Populate GGUF dropdown
            gguf_models = all_models.get("gguf_models", [])
            if gguf_models:
                self.gguf_combo['values'] = gguf_models
                print(f"[DEBUG] Loaded {len(gguf_models)} GGUF models")
            
            # Populate UNet dropdown
            unets = all_models.get("unets", [])
            if unets:
                self.unet_combo['values'] = unets
                print(f"[DEBUG] Loaded {len(unets)} UNet models")
            
            # Populate Diffusion dropdown
            diffusion = all_models.get("diffusion_models", [])
            if diffusion:
                self.diffusion_combo['values'] = diffusion
                print(f"[DEBUG] Loaded {len(diffusion)} diffusion models")
            
            # Update file size displays
            self._update_model_sizes(checkpoints)
            
            self.app.show_status(f"✅ Loaded all ComfyUI models", 2000)
        
        except Exception as e:
            print(f"[DEBUG] Error loading models: {e}")
            self.app.show_status(f"❌ Error: {str(e)}", 2000)
    
    def _update_model_sizes(self, checkpoints):
        """Update file size labels for checkpoints"""
        try:
            from comfyui_model_manager import ComfyUIModelManager
            from pathlib import Path
            comfyui_root = self.comfyui_root_var.get()
            if not comfyui_root:
                return
            
            manager = ComfyUIModelManager(comfyui_root)
            
            # Update checkpoint size on selection change
            def on_checkpoint_changed(event=None):
                selected = self.checkpoint_model_var.get()
                if selected and selected in checkpoints:
                    size = checkpoints[selected]["size"]
                    size_str = manager.format_size(size)
                    self.checkpoint_size_label.config(text=size_str)
                    
                    # Auto-detect if checkpoint has built-in CLIP/VAE
                    has_clip = checkpoints[selected]["has_clip"]
                    has_vae = checkpoints[selected]["has_vae"]
                    self.checkpoint_has_builtin_var.set(has_clip and has_vae)
                    self._on_builtin_changed()
            
            self.checkpoint_combo.bind("<<ComboboxSelected>>", on_checkpoint_changed)
            
            # Bind other dropdowns to update sizes
            def on_vae_changed(event=None):
                selected = self.vae_var.get()
                if selected and selected != "(none)":
                    vae_path = Path(comfyui_root) / "models" / "vae" / selected
                    if vae_path.exists():
                        size_str = manager.format_size(vae_path.stat().st_size)
                        self.vae_size_label.config(text=size_str)
            
            def on_encoder_changed(event=None):
                selected = self.text_encoder_var.get()
                if selected and selected != "(none)":
                    encoder_path = Path(comfyui_root) / "models" / "text_encoders" / selected
                    if encoder_path.exists():
                        size_str = manager.format_size(encoder_path.stat().st_size)
                        self.encoder_size_label.config(text=size_str)
            
            def on_gguf_changed(event=None):
                selected = self.gguf_model_var.get()
                if selected and selected != "(none)":
                    # Search for GGUF in multiple locations
                    gguf_path = Path(comfyui_root) / "models" / "gguf" / selected
                    if not gguf_path.exists():
                        gguf_path = Path(comfyui_root) / "models" / "checkpoints" / selected
                    if gguf_path.exists():
                        size_str = manager.format_size(gguf_path.stat().st_size)
                        self.gguf_size_label.config(text=size_str)
            
            def on_unet_changed(event=None):
                selected = self.unet_model_var.get()
                if selected and selected != "(none)":
                    unet_path = Path(comfyui_root) / "models" / "unet" / selected
                    if unet_path.exists():
                        size_str = manager.format_size(unet_path.stat().st_size)
                        self.unet_size_label.config(text=size_str)
            
            def on_diffusion_changed(event=None):
                selected = self.diffusion_model_var.get()
                if selected and selected != "(none)":
                    diffusion_path = Path(comfyui_root) / "models" / "diffusion_models" / selected
                    if diffusion_path.exists():
                        size_str = manager.format_size(diffusion_path.stat().st_size)
                        self.diffusion_size_label.config(text=size_str)
            
            self.vae_combo.bind("<<ComboboxSelected>>", on_vae_changed)
            self.text_encoder_combo.bind("<<ComboboxSelected>>", on_encoder_changed)
            self.gguf_combo.bind("<<ComboboxSelected>>", on_gguf_changed)
            self.unet_combo.bind("<<ComboboxSelected>>", on_unet_changed)
            self.diffusion_combo.bind("<<ComboboxSelected>>", on_diffusion_changed)
            
        except Exception as e:
            print(f"[DEBUG] Error updating model sizes: {e}")
    
    def test_comfyui_connection(self):
        """Test ComfyUI connection with improved debugging"""
        try:
            import requests
            url = self.comfyui_url_var.get()
            
            self.comfyui_status_label.config(text="⏳ Testing...", fg="#0066cc")
            self.app.root.update()
            
            print(f"[DEBUG] Testing ComfyUI at: {url}")
            
            # Test basic connection to ComfyUI via system_stats endpoint (most reliable)
            try:
                response = requests.get(f"{url}/system_stats", timeout=5)
                if response.status_code == 200:
                    self.comfyui_status_label.config(text="✅ Connected to ComfyUI", fg="#009900")
                    print(f"[DEBUG] ComfyUI connection successful!")
                    return
                else:
                    print(f"[DEBUG] Unexpected response code: {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"[DEBUG] Connection refused - ComfyUI may not be running")
            except requests.exceptions.Timeout:
                print(f"[DEBUG] Connection timeout - ComfyUI not responding")
            except Exception as e:
                print(f"[DEBUG] Connection error: {e}")
            
            self.comfyui_status_label.config(
                text="❌ Cannot connect to ComfyUI\nEnsure:\n1. ComfyUI is running\n2. URL is correct", 
                fg="#cc0000",
                justify=tk.LEFT
            )
            print(f"[DEBUG] ComfyUI connection failed at {url}")
            
        except Exception as e:
            print(f"[DEBUG] Error in test_comfyui_connection: {e}")
            self.comfyui_status_label.config(text=f"❌ Error: {str(e)}", fg="#cc0000")
    
    def test_image_generation(self):
        """Test image generation with current settings"""
        import threading
        
        def generate_test():
            try:
                from image_client import ComfyUIClient
                
                test_prompt = "a beautiful red apple on a white table, 8k, highly detailed"
                url = self.comfyui_url_var.get()
                resolution = self.resolution_var.get()
                steps = int(self.steps_var.get())
                cfg_scale = float(self.cfg_scale_var.get())
                sampler = self.sampler_var.get()
                
                print(f"\n[TEST] Generating test image...")
                print(f"[TEST] Prompt: {test_prompt}")
                print(f"[TEST] Resolution: {resolution}")
                print(f"[TEST] Steps: {steps}")
                print(f"[TEST] CFG Scale: {cfg_scale}")
                print(f"[TEST] Sampler: {sampler}")
                
                client = ComfyUIClient(url)
                result = client.generate_from_text(
                    test_prompt, 
                    resolution=resolution,
                    steps=steps,
                    cfg_scale=cfg_scale,
                    sampler=sampler
                )
                
                if result:
                    print(f"[TEST] ✅ Image generated successfully!")
                    # Try to display in image viewer if available
                    if hasattr(self.app, 'image_viewer'):
                        self.app.image_viewer.add_image(result)
                        print(f"[TEST] Image displayed in viewer")
                    self.generation_status_label.config(
                        text="✅ Test image generated! Check the image viewer.",
                        fg="#009900"
                    )
                else:
                    print(f"[TEST] ❌ Generation failed - no result returned")
                    self.generation_status_label.config(
                        text="❌ Generation failed - check terminal for errors",
                        fg="#cc0000"
                    )
                    
            except Exception as e:
                print(f"[TEST] ❌ Error: {e}")
                import traceback
                traceback.print_exc()
                self.generation_status_label.config(
                    text=f"❌ Error: {str(e)}",
                    fg="#cc0000"
                )
        
        # Show status
        self.generation_status_label.config(text="⏳ Generating test image...", fg="#0066cc")
        self.app.root.update()
        
        # Run in background thread
        thread = threading.Thread(target=generate_test, daemon=True)
        thread.start()
    
    def refresh_available_models(self):
        """Refresh list of available models from provider"""
        try:
            provider = self.model_provider_var.get()
            url = self.provider_url_var.get()
            
            if provider == "ollama":
                from ollama_client import OllamaClient
                client = OllamaClient(url)
                models = client.get_available_models()
            else:  # llama_server
                from llama_client import LlamaServerClient
                client = LlamaServerClient(url)
                models = client.get_available_models()
            
            if models:
                self.extraction_model_combo['values'] = models
                self.app.show_status(f"✅ Found {len(models)} models", 2000)
            else:
                self.app.show_status("❌ No models found", 2000)
        except Exception as e:
            self.app.show_status(f"❌ Error refreshing models: {str(e)}", 2000)
            print(f"[ERROR] {e}")
    
    def _load_profiles_from_file(self):
        """Load profiles from prompt_profiles.json"""
        try:
            from pathlib import Path
            import json
            profiles_file = Path(__file__).parent.parent / "prompt_profiles.json"
            if profiles_file.exists():
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    self.profiles = json.load(f)
                    profile_names = list(self.profiles.keys())
                    self.profile_combo['values'] = profile_names
                    if "default" in self.profiles:
                        self.profile_var.set("default")
                        self._load_profile_to_ui("default")
        except Exception as e:
            print(f"[ERROR] Failed to load profiles: {e}")
            self.profiles = {"default": {}}
    
    def _save_profiles_to_file(self):
        """Save all profiles to prompt_profiles.json"""
        try:
            from pathlib import Path
            import json
            profiles_file = Path(__file__).parent.parent / "prompt_profiles.json"
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=2, ensure_ascii=False)
            print(f"[DEBUG] Profiles saved to {profiles_file}")
        except Exception as e:
            print(f"[ERROR] Failed to save profiles: {e}")
    
    def _on_profile_changed(self, event=None):
        """Load profile when selection changes"""
        profile_name = self.profile_var.get()
        if profile_name in self.profiles:
            self._load_profile_to_ui(profile_name)
    
    def _load_profile_to_ui(self, profile_name):
        """Load profile data into UI fields"""
        if profile_name not in self.profiles:
            return
        
        profile = self.profiles[profile_name]
        
        # Load all four components
        self.system_prompt_text.delete("1.0", tk.END)
        self.system_prompt_text.insert("1.0", profile.get("system_prompt", ""))
        
        self.user_prompt_text.delete("1.0", tk.END)
        self.user_prompt_text.insert("1.0", profile.get("user_prompt", ""))
        
        self.prefix_text.delete(0, tk.END)
        self.prefix_text.insert(0, profile.get("prefix", ""))
        
        self.suffix_text.delete(0, tk.END)
        self.suffix_text.insert(0, profile.get("suffix", ""))
        
        print(f"[DEBUG] Loaded profile: {profile_name}")
    
    def load_prompt_profile(self):
        """Load selected profile from file"""
        self._load_profiles_from_file()
        profile_name = self.profile_var.get()
        self._load_profile_to_ui(profile_name)
        self.app.show_status(f"✅ Loaded profile: {profile_name}", 2000)
    
    def save_prompt_profile(self):
        """Save current UI values as a new profile"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("Save Profile As")
        dialog.geometry("400x150")
        dialog.grab_set()
        
        tk.Label(dialog, text="Profile Name:", font=("Arial", 10)).pack(pady=10)
        name_entry = tk.Entry(dialog, width=40, font=("Arial", 10))
        name_entry.pack(pady=5, padx=20, fill=tk.X)
        
        def save():
            profile_name = name_entry.get().strip()
            if not profile_name:
                messagebox.showerror("Error", "Profile name cannot be empty")
                return
            
            # Save current UI values as profile
            self.profiles[profile_name] = {
                "system_prompt": self.system_prompt_text.get("1.0", tk.END).strip(),
                "user_prompt": self.user_prompt_text.get("1.0", tk.END).strip(),
                "prefix": self.prefix_text.get().strip(),
                "suffix": self.suffix_text.get().strip()
            }
            
            self._save_profiles_to_file()
            
            # Update dropdown
            current_values = list(self.profile_combo['values'])
            if profile_name not in current_values:
                current_values.append(profile_name)
                self.profile_combo['values'] = current_values
            
            self.profile_var.set(profile_name)
            self.app.show_status(f"✅ Profile saved: {profile_name}", 2000)
            dialog.destroy()
        
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="Save", command=save, bg="#00cc66", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy, bg="#cc0000", fg="white", width=10).pack(side=tk.LEFT, padx=5)
    
    def reset_prompt_profile(self):
        """Reset current profile to default"""
        if messagebox.askyesno("Confirm", "Reset to default profile? This will overwrite current settings."):
            self.profile_var.set("default")
            self._load_profiles_from_file()
            self._load_profile_to_ui("default")
            self.app.show_status("✅ Profile reset to default", 2000)
    
    def delete_prompt_profile(self):
        """Delete selected profile"""
        profile_name = self.profile_var.get()
        if profile_name == "default":
            messagebox.showerror("Error", "Cannot delete the default profile")
            return
        
        if messagebox.askyesno("Confirm", f"Delete profile '{profile_name}'?"):
            if profile_name in self.profiles:
                del self.profiles[profile_name]
                self._save_profiles_to_file()
                
                # Update dropdown
                current_values = list(self.profile_combo['values'])
                current_values.remove(profile_name)
                self.profile_combo['values'] = current_values
                
                self.profile_var.set("default")
                self._load_profile_to_ui("default")
                self.app.show_status(f"✅ Profile deleted: {profile_name}", 2000)
    
    def save_all_settings(self):
        """Save all image settings"""
        try:
            from settings_manager import load_settings, save_settings
            
            settings = load_settings()
            
            # ComfyUI settings
            settings["comfyui_url"] = self.comfyui_url_var.get()
            settings["comfyui_root_folder"] = self.comfyui_root_var.get()
            
            # Image generation settings
            settings["image_resolution"] = self.resolution_var.get()
            settings["image_steps"] = self.steps_var.get()
            settings["image_cfg_scale"] = self.cfg_scale_var.get()
            settings["image_sampler"] = self.sampler_var.get()
            settings["checkpoint_model"] = self.checkpoint_model_var.get()
            settings["checkpoint_has_builtin"] = self.checkpoint_has_builtin_var.get()
            settings["vae_model"] = self.vae_var.get()
            settings["text_encoder_model"] = self.text_encoder_var.get()
            
            # Extraction settings
            settings["extraction_model_provider"] = self.model_provider_var.get()
            settings["extraction_provider_url"] = self.provider_url_var.get()
            settings["extraction_model"] = self.extraction_model_var.get()
            settings["extraction_temperature"] = self.extraction_temperature_var.get()
            settings["extraction_timeout"] = self.extraction_timeout_var.get()
            settings["min_response_length"] = self.min_response_length_var.get()
            
            # Prompts
            settings["extraction_system_prompt"] = self.system_prompt_text.get("1.0", tk.END).strip()
            settings["extraction_user_prompt"] = self.user_prompt_text.get("1.0", tk.END).strip()
            
            # Prefix/Suffix and realistic keywords
            settings["extraction_prefix"] = self.prefix_text.get().strip()
            settings["extraction_suffix"] = self.suffix_text.get().strip()
            settings["add_realistic_keywords"] = self.add_realistic_keywords_var.get()
            
            save_settings(settings)
            self.app.show_status("✅ Image settings saved", 2000)
        except Exception as e:
            self.app.show_status(f"❌ Error saving settings: {str(e)}", 2000)
            print(f"[ERROR] {e}")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            from settings_manager import load_settings
            settings = load_settings()
            
            # ComfyUI
            self.comfyui_url_var.set(settings.get("comfyui_url", "http://127.0.0.1:8188"))
            self.comfyui_root_var.set(settings.get("comfyui_root_folder", ""))
            
            # Image generation
            self.resolution_var.set(settings.get("image_resolution", "768x768"))
            self.steps_var.set(settings.get("image_steps", "20"))
            self.cfg_scale_var.set(settings.get("image_cfg_scale", "7.5"))
            self.sampler_var.set(settings.get("image_sampler", "euler"))
            self.checkpoint_model_var.set(settings.get("checkpoint_model", "sd_xl_base_1.0.safetensors"))
            self.checkpoint_has_builtin_var.set(settings.get("checkpoint_has_builtin", True))
            self.vae_var.set(settings.get("vae_model", "(none)"))
            self.text_encoder_var.set(settings.get("text_encoder_model", "(none)"))
            
            # Extraction
            self.model_provider_var.set(settings.get("extraction_model_provider", "ollama"))
            self.provider_url_var.set(settings.get("extraction_provider_url", "http://localhost:11434"))
            self.extraction_model_var.set(settings.get("extraction_model", "dolphin-2.1:2.4b"))
            self.extraction_temperature_var.set(settings.get("extraction_temperature", "0.3"))
            self.extraction_timeout_var.set(settings.get("extraction_timeout", "120"))
            self.min_response_length_var.set(settings.get("min_response_length", "100"))
            
            # Prompts
            system_prompt = settings.get("extraction_system_prompt")
            if system_prompt:
                self.system_prompt_text.delete("1.0", tk.END)
                self.system_prompt_text.insert("1.0", system_prompt)
            
            user_prompt = settings.get("extraction_user_prompt")
            if user_prompt:
                self.user_prompt_text.delete("1.0", tk.END)
                self.user_prompt_text.insert("1.0", user_prompt)
            
            # Prefix/Suffix and realistic keywords
            self.prefix_text.delete(0, tk.END)
            self.prefix_text.insert(0, settings.get("extraction_prefix", ""))
            
            self.suffix_text.delete(0, tk.END)
            self.suffix_text.insert(0, settings.get("extraction_suffix", ""))
            
            self.add_realistic_keywords_var.set(settings.get("add_realistic_keywords", True))
        except Exception as e:
            print(f"[ERROR] Loading image settings: {e}")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Reset to Defaults", "Reset all image settings to defaults?"):
            self.comfyui_url_var.set("http://127.0.0.1:8188")
            self.comfyui_root_var.set("")
            self.resolution_var.set("768x768")
            self.steps_var.set("20")
            self.cfg_scale_var.set("7.5")
            self.sampler_var.set("euler")
            self.checkpoint_model_var.set("sd_xl_base_1.0.safetensors")
            self.checkpoint_has_builtin_var.set(True)
            self.vae_var.set("(none)")
            self.text_encoder_var.set("(none)")
            self.model_provider_var.set("ollama")
            self.provider_url_var.set("http://localhost:11434")
            self.extraction_model_var.set("dolphin-2.1:2.4b")
            self.extraction_temperature_var.set("0.3")
            self.extraction_timeout_var.set("120")
            self.min_response_length_var.set("100")
            
            self.system_prompt_text.delete("1.0", tk.END)
            self.system_prompt_text.insert("1.0", """You are an expert at extracting image generation prompts for Stable Diffusion XL.
Extract a SINGLE, CONCISE image prompt from the given text.
Output ONLY the prompt itself - NO explanations, NO commentary, NO extra text.
Requirements:
- Start directly with the prompt
- Include: photorealistic, detailed, 8k, high quality keywords
- Avoid: cartoon, illustration, painting, stylized, anime
- Keep it 1-2 sentences maximum
- Output NOTHING except the image prompt""")
            
            self.user_prompt_text.delete("1.0", tk.END)
            self.user_prompt_text.insert("1.0", """Extract ONLY the image prompt from this response. Output NOTHING else.

{response}

IMAGE PROMPT (ONLY THE PROMPT, NO EXPLANATION):""")
            
            self.save_all_settings()
