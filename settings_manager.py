"""
Settings Manager for Llama Chat application
Handles saving and loading user settings to/from JSON file
"""

import json
import os
from pathlib import Path
from debug_config import DebugConfig


SETTINGS_FILE = "chat_settings.json"
_settings_cache = None  # In-memory cache to avoid repeated file reads
_cache_loaded = False


def load_settings():
    """Load settings from file (cached in memory after first load)
    
    Returns:
        dict: Settings dictionary, or empty dict if file doesn't exist
    """
    global _settings_cache, _cache_loaded
    
    # Return cached version if already loaded
    if _cache_loaded and _settings_cache is not None:
        return _settings_cache
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                _settings_cache = json.load(f)
            _cache_loaded = True
            if DebugConfig.settings_changes:
                print(f"[DEBUG-SETTINGS] load_settings: Loaded {len(_settings_cache)} settings from file, chat_template_selection = {_settings_cache.get('chat_template_selection', 'NOT FOUND')}")
        except Exception as e:
            print(f"[ERROR-SETTINGS] Error loading settings: {e}")
    else:
        _cache_loaded = True
        _settings_cache = {}
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] load_settings: File {SETTINGS_FILE} does not exist")
    
    # Ensure timeout settings always exist with sensible defaults
    if 'request_timeout' not in _settings_cache:
        _settings_cache['request_timeout'] = 120  # Default 120 seconds for chat requests
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] Added missing request_timeout setting (default 120s)")
    
    if 'request_infinite_timeout' not in _settings_cache:
        _settings_cache['request_infinite_timeout'] = False
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] Added missing request_infinite_timeout setting (default False)")
    
    # Ensure n_predict (max tokens) has sensible default
    if 'n_predict' not in _settings_cache:
        _settings_cache['n_predict'] = 8192  # Default 8k tokens
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] Added missing n_predict setting (default 8192 tokens)")
    
    # Ensure model unload timeout settings exist with sensible defaults
    defaults_added = False
    if 'ollama_model_unload_timeout' not in _settings_cache:
        _settings_cache['ollama_model_unload_timeout'] = 0  # Default: immediate unload
        defaults_added = True
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] Added missing ollama_model_unload_timeout setting (default 0 = immediate)")
    
    if 'llama-server_model_unload_timeout' not in _settings_cache:
        _settings_cache['llama-server_model_unload_timeout'] = 0  # Default: immediate unload
        defaults_added = True
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] Added missing llama-server_model_unload_timeout setting (default 0 = immediate)")
    
    # If we added defaults, save them to file so they persist
    if defaults_added:
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(_settings_cache, f, indent=2, ensure_ascii=False)
                f.flush()
            if DebugConfig.settings_changes:
                print(f"[DEBUG-SETTINGS] Saved defaults to {SETTINGS_FILE}")
        except Exception as e:
            if DebugConfig.settings_changes:
                print(f"[DEBUG-SETTINGS] Could not save defaults: {e}")
    
    return _settings_cache


def save_settings(settings):
    """Save settings to file and clear cache
    
    Args:
        settings: Dictionary of settings to save
    """
    global _settings_cache, _cache_loaded
    
    try:
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] save_settings called, writing to {SETTINGS_FILE}")
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.flush()  # Ensure data is written to disk
        
        # Update cache after successful save
        _settings_cache = settings.copy()
        _cache_loaded = True
        
        if DebugConfig.settings_changes:
            print(f"[DEBUG-SETTINGS] Successfully wrote {len(settings)} settings to {SETTINGS_FILE}")
        
        # VERIFY: Read back immediately to confirm
        if DebugConfig.settings_changes:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                verify_data = json.load(f)
            verify_value = verify_data.get("chat_template_selection", "NOT FOUND")
            if DebugConfig.settings_enabled:
                print(f"[DEBUG-SETTINGS] VERIFY: chat_template_selection in file = {verify_value}")
        
        if DebugConfig.settings_save_load:
            print(f"[DEBUG] Settings saved to {SETTINGS_FILE}")
    except Exception as e:
        print(f"[ERROR-SETTINGS] Error saving settings: {e}")
        import traceback
        traceback.print_exc()


def get_setting(key, default=None):
    """Get a specific setting
    
    Args:
        key: Setting key
        default: Default value if key doesn't exist
        
    Returns:
        Setting value or default
    """
    settings = load_settings()
    result = settings.get(key, default)
    if DebugConfig.settings_changes:
        print(f"[DEBUG-SETTINGS] get_setting({key}) = {result} (default would be {default})")
    return result


def set_setting(key, value):
    """Set a specific setting
    
    Args:
        key: Setting key
        value: Setting value
    """
    if DebugConfig.settings_changes:
        print(f"[DEBUG-SETTINGS] set_setting called: {key} = {value}")
    settings = load_settings()
    if DebugConfig.settings_changes:
        print(f"[DEBUG-SETTINGS] Loaded settings, current value of {key} = {settings.get(key, 'NOT IN DICT')}")
    settings[key] = value
    if DebugConfig.settings_changes:
        print(f"[DEBUG-SETTINGS] After setting: {key} = {settings.get(key)}")
        if DebugConfig.settings_enabled:
            print(f"[DEBUG-SETTINGS] About to save settings with {len(settings)} total settings")
        if DebugConfig.settings_enabled:
            print(f"[DEBUG-SETTINGS] Dict value before save: {key} = {settings[key]}")
    save_settings(settings)
    if DebugConfig.settings_changes:
        print(f"[DEBUG-SETTINGS] Saved successfully")
