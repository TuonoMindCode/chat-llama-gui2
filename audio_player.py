"""
Centralized Audio Player - Single point for all audio playback
Ensures only one audio plays at a time, no overlapping audio
Thread-safe implementation to prevent GUI freezing
"""

import os
import subprocess
import threading
from pathlib import Path
from debug_config import DebugConfig

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


class AudioPlayer:
    """
    Global audio player - single instance for entire app
    Only plays one audio at a time (media player style)
    THREAD-SAFE: Uses lock to ensure pygame is only called from safe context
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioPlayer, cls).__new__(cls)
            # Initialize the _initialized flag
            object.__setattr__(cls._instance, '_initialized', False)
        return cls._instance
    
    def __init__(self):
        """Initialize audio player (singleton)"""
        # Use getattr with default to safely check initialization status
        if getattr(self, '_initialized', False):
            return
        
        self._initialized = True
        self.current_sound = None  # pygame.mixer.Sound
        self.current_process = None  # subprocess for fallback players
        self.current_file = None  # path to currently playing file
        self.is_playing = False
        self.lock = threading.Lock()  # Thread-safe lock for pygame access
        
        if PYGAME_AVAILABLE:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
            except Exception:  # pylint: disable=broad-except
                pass
        
        if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
            print("[AUDIO_PLAYER] Initialized - centralized audio player (thread-safe)")
    
    def play(self, filepath, auto_stop_current=True, volume=1.0):
        """
        Play audio file (thread-safe)
        
        Args:
            filepath: Path to audio file to play
            auto_stop_current: If True, stops any currently playing audio
            volume: Volume level (0.0-1.0), default 1.0 (full volume)
        
        Returns:
            bool: True if playback started, False otherwise
        """
        try:
            filepath = str(filepath)
            
            if not os.path.exists(filepath):
                print(f"[AUDIO_PLAYER] ✗ ERROR: File not found: {filepath}")
                return False
            
            print(f"[AUDIO_PLAYER] ► Attempting to play: {filepath} (volume={volume})")
            
            # Use lock to ensure thread-safe access to pygame
            with self.lock:
                # Stop currently playing audio if requested
                if auto_stop_current:
                    self._stop_internal()
                
                # Try pygame first
                if PYGAME_AVAILABLE:
                    return self._play_with_pygame(filepath, volume)
                else:
                    # Fallback to system player
                    return self._play_with_system(filepath)
        
        except Exception as e:  # pylint: disable=broad-except
            print(f"[AUDIO_PLAYER] ✗ Error playing audio: {e}")
            return False
    
    def _play_with_pygame(self, filepath, volume=1.0):
        """Play audio using pygame (assumes lock is held)"""
        try:
            self.current_sound = pygame.mixer.Sound(filepath)
            # Clamp volume to 0.0-1.0 range
            volume = min(max(volume, 0.0), 1.0)
            self.current_sound.set_volume(volume)
            self.current_sound.play()
            self.current_file = filepath
            self.is_playing = True
            
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
                print(f"[AUDIO_PLAYER] ✓ Playing with pygame: {Path(filepath).name} (volume={volume})")
            return True
        except Exception as e:  # pylint: disable=broad-except
            print(f"[AUDIO_PLAYER] pygame error: {e}, trying system player...")
            return self._play_with_system(filepath)
    
    def _play_with_system(self, filepath):
        """Play audio using system player (assumes lock is held)"""
        try:
            import sys
            if sys.platform == 'win32':
                # Windows: use powershell to play audio
                self.current_process = subprocess.Popen(
                    ['powershell', '-Command', f'(New-Object Media.SoundPlayer "{filepath}").PlaySync()'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif sys.platform == 'darwin':
                # macOS: use afplay
                self.current_process = subprocess.Popen(
                    ['afplay', filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Linux: try ffplay or other players
                self.current_process = subprocess.Popen(
                    ['ffplay', '-nodisp', '-autoexit', filepath],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            self.current_file = filepath
            self.is_playing = True
            
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
                print(f"[AUDIO_PLAYER] ✓ Playing with system player: {Path(filepath).name}")
            return True
        except Exception as e:  # pylint: disable=broad-except
            print(f"[AUDIO_PLAYER] ✗ System player error: {e}")
            return False
    
    def _stop_internal(self):
        """Stop audio (assumes lock is held)"""
        try:
            if self.current_sound:
                try:
                    self.current_sound.stop()
                except Exception:  # pylint: disable=broad-except
                    pass
                self.current_sound = None
            
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=0.5)
                except Exception:  # pylint: disable=broad-except
                    try:
                        self.current_process.kill()
                    except Exception:  # pylint: disable=broad-except
                        pass
                self.current_process = None
            
            self.is_playing = False
        except Exception:  # pylint: disable=broad-except
            pass
    
    def stop(self):
        """Stop currently playing audio (thread-safe)"""
        try:
            with self.lock:
                self._stop_internal()
            
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
                print("[AUDIO_PLAYER] ⏹ Stopped playback")
        
        except Exception as e:  # pylint: disable=broad-except
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
                print(f"[AUDIO_PLAYER] ERROR stopping: {e}")
    
    def is_audio_playing(self):
        """Check if any audio is currently playing"""
        return self.is_playing
    
    def get_current_file(self):
        """Get path to currently playing file"""
        return self.current_file


# Get singleton instance
def get_audio_player():
    """Get the global audio player instance"""
    return AudioPlayer()
