"""
Debug Configuration Module
Centralized debug settings for all components
"""

class DebugConfig:
    """Global debug configuration - controls what debug info is printed to console"""
    
    # Extraction (Image prompt extraction)
    extraction_enabled = False  # Disable by default
    extraction_system_prompt = False
    extraction_user_prompt = False
    extraction_response_snippet = False  # Shows first 100 chars of response
    extraction_full_result = False  # Shows full extracted prompt
    
    # ComfyUI Image Generation
    comfyui_enabled = False  # Disable by default
    comfyui_workflow = False  # Show workflow parameters
    comfyui_generation_settings = False  # Show resolution, steps, sampler, scheduler
    comfyui_copy_operations = False  # Show file copy operations
    comfyui_queue_operations = False  # Show queue/prompt operations
    
    # System & User Prompts
    system_prompt_enabled = False  # Disable verbose output by default
    system_prompt_full = False  # Show full system prompt
    user_prompt_enabled = False  # Disable verbose output by default
    user_prompt_full = False  # Show full user prompt
    
    # Chat Templates
    chat_template_enabled = False
    chat_template_selection = False  # Show template selection
    chat_template_formatting = False  # Show template formatting
    
    # Chat & Memory
    chat_enabled = False  # Disable verbose chat debug by default
    chat_memory_operations = False  # Show memory operations
    chat_message_history = False  # Show message history operations
    
    # TTS (Text-to-Speech)
    tts_enabled = False
    tts_operations = False  # Show TTS generation
    
    # Media Playback (Audio & Image Display)
    media_playback_enabled = False
    media_playback_audio = False  # Show audio playback operations
    media_playback_images = False  # Show image display operations
    
    # STT (Speech-to-Text)
    stt_enabled = False
    stt_operations = False  # Show STT operations
    
    # Connection & Network
    connection_enabled = False  # Disable verbose connection debug by default
    connection_requests = False  # Show API requests
    connection_responses = False  # Show API responses
    connection_status = False  # Show status updates (ollama/llama-server online/offline)
    
    # Settings & Config
    settings_enabled = False  # Disable verbose output by default
    settings_save_load = False  # Show settings save/load operations
    settings_changes = False  # Show pending settings changes
    
    # Model Loading & Management
    model_loading_enabled = False  # Disable verbose output by default
    model_scanning = False  # Show directory scanning for models
    model_discovery = False  # Show discovered models
    model_restore = False  # Show profile restoration
    
    # Token counting
    token_counting_enabled = False  # Disable verbose output by default
    token_count_details = False  # Show token count breakdowns
    
    @classmethod
    def enable_all(cls):
        """Enable all debug output"""
        for attr in dir(cls):
            if not attr.startswith('_') and isinstance(getattr(cls, attr), bool):
                setattr(cls, attr, True)
    
    @classmethod
    def disable_all(cls):
        """Disable all debug output"""
        for attr in dir(cls):
            if not attr.startswith('_') and isinstance(getattr(cls, attr), bool):
                setattr(cls, attr, False)
    
    @classmethod
    def get_all_settings(cls):
        """Get all debug settings as a dictionary"""
        settings = {}
        for attr in sorted(dir(cls)):
            if not attr.startswith('_') and attr not in ['disable_all', 'enable_all', 'get_all_settings']:
                value = getattr(cls, attr)
                if isinstance(value, bool):
                    settings[attr] = value
        return settings
    
    @classmethod
    def set_from_dict(cls, settings_dict):
        """Set debug settings from a dictionary"""
        for key, value in settings_dict.items():
            if hasattr(cls, key) and isinstance(value, bool):
                setattr(cls, key, value)
