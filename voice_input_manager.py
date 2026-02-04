"""
Voice Input Manager - Manages mutually exclusive voice input across chat tabs
Keeps Whisper model loaded in memory when switching between tabs
"""

import threading
import tempfile
from pathlib import Path
from debug_config import DebugConfig


class VoiceInputManager:
    """
    Manages voice input across multiple chat tabs.
    Only ONE tab can have voice input active at a time.
    Keeps Whisper model loaded in memory when switching tabs.
    """
    
    _instance = None  # Singleton
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
        """Initialize voice input manager"""
        if self._initialized:
            return
        
        self._initialized = True
        self.active_tab = None  # Which tab has voice input active: "ollama" or "llama"
        self.callbacks = {}  # Dict to store checkbox callbacks: {"ollama": callback, "llama": callback}
        self.whisper_subprocess = None  # Keep subprocess alive to keep model in memory
        
        if DebugConfig.chat_memory_operations:
            print("[VOICE_INPUT] Manager initialized - only one tab can have voice input active")
    
    def register_tab(self, server_type, checkbox_callback):
        """
        Register a chat tab's voice input checkbox
        
        Args:
            server_type: "ollama" or "llama"
            checkbox_callback: Function to call when checkbox state changes
        """
        self.callbacks[server_type] = checkbox_callback
        if DebugConfig.chat_memory_operations:
            print(f"[VOICE_INPUT] Registered {server_type} tab")
    
    def set_active_tab(self, server_type):
        """
        Set which tab has voice input active
        Automatically deactivates the other tab
        
        Args:
            server_type: "ollama" or "llama" (or None to deactivate all)
        """
        if server_type is None:
            # Deactivate all - UNLOAD WHISPER MODEL FROM MEMORY
            if self.active_tab:
                print(f"[DEBUG-STT] Deactivating speech input - unloading Whisper model...")
                if DebugConfig.chat_memory_operations:
                    print(f"[VOICE_INPUT] Deactivating {self.active_tab}")
                self.active_tab = None
                # Unload Whisper model
                self.unload_whisper_model()
        else:
            # Activate this tab, deactivate others
            if self.active_tab != server_type:
                old_tab = self.active_tab
                self.active_tab = server_type
                
                if DebugConfig.chat_memory_operations:
                    print(f"[VOICE_INPUT] Switching from {old_tab} to {server_type}")
                
                # Uncheck the other tab
                if old_tab and old_tab in self.callbacks:
                    self.callbacks[old_tab](False)  # Call callback with False to uncheck
                
                # Keep Whisper model in memory (don't clean up subprocess)
                if DebugConfig.chat_memory_operations:
                    print(f"[VOICE_INPUT] Keeping Whisper model loaded in memory for faster switching")
    
    def is_active_for_tab(self, server_type):
        """
        Check if voice input is active for this tab
        
        Args:
            server_type: "ollama" or "llama"
        
        Returns:
            True if voice input is active for this tab
        """
        return self.active_tab == server_type
    
    def get_active_tab(self):
        """Get which tab has voice input active"""
        return self.active_tab
    
    def unload_whisper_model(self):
        """
        Force unload the Whisper model from memory by terminating the subprocess.
        This frees up ~10GB of memory when speech input is disabled.
        """
        if self.whisper_subprocess is None:
            print("[DEBUG-STT] Whisper model already unloaded")
            if DebugConfig.chat_memory_operations:
                print("[VOICE_INPUT] No whisper subprocess to unload")
            return
        
        try:
            import psutil
            import os
            
            print(f"[DEBUG-STT] Unloading Whisper model (terminating subprocess PID: {self.whisper_subprocess.pid})...")
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Terminating whisper subprocess (PID: {self.whisper_subprocess.pid})...")
            
            # Terminate the subprocess process tree
            try:
                # Use psutil to terminate process tree (children too)
                process = psutil.Process(self.whisper_subprocess.pid)
                children = process.children(recursive=True)
                
                # Terminate children first
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                
                # Terminate parent
                process.terminate()
                
                # Wait for termination
                try:
                    process.wait(timeout=3)
                except psutil.TimeoutExpired:
                    # Force kill if terminate didn't work
                    process.kill()
                
                print("[DEBUG-STT] ✓ Whisper model unloaded successfully - memory freed")
                if DebugConfig.chat_memory_operations:
                    print("[VOICE_INPUT] ✓ Whisper subprocess terminated - memory freed")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Process already dead or can't access, try direct kill
                try:
                    self.whisper_subprocess.terminate()
                    self.whisper_subprocess.wait(timeout=2)
                except:
                    self.whisper_subprocess.kill()
            
            self.whisper_subprocess = None
        except Exception as e:
            print(f"[DEBUG-STT] Error unloading Whisper model: {e}")
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Error terminating whisper subprocess: {e}")
            self.whisper_subprocess = None
