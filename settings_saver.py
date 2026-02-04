"""
Centralized Settings Manager - Only saves on explicit button click
Tracks changes in memory, writes to disk only when user clicks "Save Settings"

Usage:
    saver = SettingsSaver()
    saver.set("temperature", 0.7)  # Changes in memory only
    saver.save()  # Only writes to disk when called
"""

import threading
from settings_manager import load_settings, save_settings
from debug_config import DebugConfig


class SettingsSaver:
    """
    Centralized settings manager that only saves to disk on explicit button click
    All changes are tracked in memory until save() is called
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize settings saver"""
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.settings = load_settings()
        self.pending_changes = {}  # Track what's changed
        self.save_lock = threading.Lock()
        
        if DebugConfig.chat_enabled:
            print("[SETTINGS_SAVER] Initialized - changes only saved on explicit save()")
    
    def set(self, key, value):
        """
        Set a setting value (in memory only, not saved to disk yet)
        
        Args:
            key: Setting key (e.g., "temperature")
            value: New value
        """
        with self.save_lock:
            self.settings[key] = value
            self.pending_changes[key] = value
        
        if DebugConfig.settings_changes:
            print(f"[SETTINGS_SAVER] Set in memory: {key} = {value}")
    
    def set_nested(self, section, key, value):
        """
        Set a nested setting value (in memory only)
        
        Args:
            section: Section key (e.g., "ollama_")
            key: Setting key (e.g., "temperature")
            value: New value
        """
        full_key = f"{section}{key}"
        self.set(full_key, value)
    
    def get(self, key, default=None):
        """
        Get a setting value from memory
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value
        """
        with self.save_lock:
            return self.settings.get(key, default)
    
    def has_pending_changes(self):
        """Check if there are unsaved changes"""
        with self.save_lock:
            return len(self.pending_changes) > 0
    
    def get_pending_changes(self):
        """Get count of pending changes"""
        with self.save_lock:
            return len(self.pending_changes)
    
    def save(self):
        """
        Save all changes to disk
        This is called ONLY when user clicks "Save Settings" button
        
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            with self.save_lock:
                # CRITICAL: Reload from disk first to get any changes made by set_setting()
                print("[SETTINGS_SAVER] Reloading from disk before save to preserve set_setting() changes")
                current_disk_settings = load_settings()
                
                # Merge: keep all disk settings, but override with our pending changes
                for key, value in self.pending_changes.items():
                    current_disk_settings[key] = value
                
                self.settings = current_disk_settings
                
                if not self.pending_changes:
                    if DebugConfig.settings_changes:
                        print("[SETTINGS_SAVER] No pending changes to save")
                    return True
                
                # Save to disk
                save_settings(self.settings)
                
                changed_keys = list(self.pending_changes.keys())
                self.pending_changes = {}  # Clear pending changes
                
                if DebugConfig.settings_changes:
                    print(f"[SETTINGS_SAVER] ✅ Saved {len(changed_keys)} settings: {changed_keys}")
                
                return True
        
        except Exception as e:  # pylint: disable=broad-except
            if DebugConfig.settings_changes:
                print(f"[SETTINGS_SAVER] ❌ Error saving settings: {e}")
            return False
    
    def discard_changes(self):
        """
        Discard all pending changes (reload from disk)
        """
        with self.save_lock:
            self.settings = load_settings()
            self.pending_changes = {}
        
        if DebugConfig.settings_changes:
            print("[SETTINGS_SAVER] Discarded all pending changes")
    
    def reload(self):
        """Reload settings from disk (discarding any unsaved changes)"""
        self.discard_changes()
    
    def sync_from_ui_dict(self, ui_dict):
        """
        Sync settings from a UI settings dictionary
        (useful for updating multiple settings at once)
        
        Args:
            ui_dict: Dictionary of key -> value pairs to update
        """
        with self.save_lock:
            for key, value in ui_dict.items():
                self.settings[key] = value
                self.pending_changes[key] = value
        
        if DebugConfig.settings_changes:
            print(f"[SETTINGS_SAVER] Synced {len(ui_dict)} settings from UI")


def get_settings_saver():
    """Get the global settings saver instance"""
    return SettingsSaver()
