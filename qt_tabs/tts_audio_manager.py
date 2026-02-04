"""
TTS Manager - Handles text-to-speech playback and audio file management
"""

import subprocess
import os
import shutil
import time as time_module
from pathlib import Path
from settings_manager import load_settings
from debug_config import DebugConfig


class TTSAudioManager:
    """Manages text-to-speech audio playback and file management"""
    
    def __init__(self, chat_tab):
        """
        Initialize TTS audio manager
        
        Args:
            chat_tab: Parent chat tab instance
        """
        self.chat_tab = chat_tab
        # NOTE: Do NOT cache audio_folder - always access via self.chat_tab.audio_folder
        # This ensures we use the current chat's audio folder when chats are switched
        self.server_type = chat_tab.server_type
        self.timestamp_audio = chat_tab.timestamp_audio
        self.current_tts = None
        self.current_audio_player = None
        self.current_audio_process = None
    
    @property
    def audio_folder(self):
        """Get current chat's audio folder from chat_tab"""
        return self.chat_tab.audio_folder
    
    def speak_response(self, response_text, timestamp=None):
        """Speak the response using TTS and associate audio with timestamp"""
        try:
            if DebugConfig.tts_operations:
                print("[DEBUG] TTS: speak_response() called")
                print(f"[DEBUG] TTS: response_text length={len(response_text)}, timestamp={timestamp}")
            from tts_manager import TTSManager
            from text_utils import clean_text_for_tts
            
            settings = load_settings()
            # Use global TTS engine setting (same for all servers)
            tts_engine = settings.get("tts_engine", "piper")
            if DebugConfig.tts_operations:
                print(f"[DEBUG] TTS: engine={tts_engine}")
            
            # Check if text should be cleaned for TTS
            should_clean = self.chat_tab.clean_text_for_tts_checkbox.isChecked() if hasattr(self.chat_tab, 'clean_text_for_tts_checkbox') else False
            if DebugConfig.tts_operations:
                print(f"[DEBUG] TTS: Clean text for TTS: {should_clean}")
            
            # Clean the text if checkbox is enabled
            if should_clean:
                response_text = clean_text_for_tts(response_text)
                if DebugConfig.tts_operations:
                    print(f"[DEBUG] TTS: Cleaned text: {response_text[:100]}...")
            
            # Get engine-specific settings (global keys)
            piper_exe = settings.get("tts_piper_exe", "")
            piper_model = settings.get("tts_piper_model", "")
            f5tts_url = settings.get("tts_f5tts_url", "")
            f5tts_ref_audio = settings.get("tts_f5tts_ref_audio", "")
            f5tts_cross_fade = settings.get("tts_f5tts_cross_fade_duration", 0.15)
            f5tts_nfe = settings.get("tts_f5tts_nfe_slider", 16)
            f5tts_speed = settings.get("tts_f5tts_speed_slider", 0.9)
            f5tts_remove_silence = settings.get("tts_f5tts_remove_silence", False)
            f5tts_randomize_seed = settings.get("tts_f5tts_randomize_seed", True)
            f5tts_seed = settings.get("tts_f5tts_seed_input", 0)
            tts_volume = settings.get("tts_volume", 1.0)  # Get volume setting (0.0-1.0)
            
            if DebugConfig.tts_operations:
                print(f"[DEBUG] TTS: piper_exe={piper_exe}")
                print(f"[DEBUG] TTS: piper_model={piper_model}")
                print(f"[DEBUG] TTS: f5tts_url={f5tts_url}")
                print(f"[DEBUG] TTS: f5tts_ref_audio={f5tts_ref_audio}")
                print(f"[DEBUG] TTS: volume={tts_volume}")
            
            # Map "python-tts" to "pyttsx3" for TTSManager
            if tts_engine == "python-tts":
                tts_engine = "pyttsx3"
            
            # Initialize TTS with settings
            tts = TTSManager(
                engine=tts_engine,
                piper_exe=piper_exe,
                piper_model=piper_model,
                f5tts_url=f5tts_url,
                f5tts_ref_audio=f5tts_ref_audio,
                f5tts_cross_fade=f5tts_cross_fade,
                f5tts_nfe=f5tts_nfe,
                f5tts_speed=f5tts_speed,
                f5tts_remove_silence=f5tts_remove_silence,
                f5tts_randomize_seed=f5tts_randomize_seed,
                f5tts_seed=int(f5tts_seed)
            )
            
            # Define callback for when TTS completes
            def on_tts_complete(success, message):
                """Called when TTS finishes - copy audio file to chat folder"""
                if DebugConfig.tts_operations:
                    print(f"[DEBUG] TTS: callback fired - success={success}, message={message}")
                if success and hasattr(tts, 'last_audio_file') and tts.last_audio_file:
                    if DebugConfig.tts_operations:
                        print(f"[DEBUG] TTS: audio file ready: {tts.last_audio_file}")
                    self._handle_tts_audio(tts.last_audio_file, timestamp, tts_volume)
                elif not success:
                    if DebugConfig.tts_operations:
                        print(f"[DEBUG] TTS: FAILED - {message}")
            
            # Call speak with callback - when callback is invoked, audio is ready
            if DebugConfig.tts_operations:
                print(f"[DEBUG] TTS: calling tts.speak() with volume={tts_volume}, timestamp={timestamp}")
            tts.speak(response_text, volume=tts_volume, callback=on_tts_complete)
            self.current_tts = tts
            
        except Exception as e:
            print(f"[DEBUG] Could not speak response: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_tts_audio(self, audio_file_path, timestamp=None, volume=1.0):
        """Handle TTS audio file - copy to chat folder and associate with message"""
        try:
            print(f"[DEBUG] _handle_tts_audio called with audio_file_path={audio_file_path}, timestamp={timestamp}, volume={volume}")
            
            # Make sure we have an audio folder
            if not self.audio_folder:
                print(f"[DEBUG] No audio folder set! Cannot save TTS file. Will play from temp location.")
                self._play_audio_file(audio_file_path, volume)
                return
            
            # If TTS returned a file path, copy it to the chat's audio folder
            if audio_file_path:
                try:
                    source_path = Path(audio_file_path)
                    print(f"[DEBUG] Checking if source exists: {source_path.exists()}")
                    
                    if source_path.exists():
                        # Create audio folder if it doesn't exist
                        self.audio_folder.mkdir(parents=True, exist_ok=True)
                        if DebugConfig.tts_operations:
                            print(f"[DEBUG] Audio folder created/verified: {self.audio_folder}")
                        
                        # Generate filename based on timestamp or use generic name
                        if timestamp:
                            # Format: 2026-01-03 12:33:15 -> 2026-01-03_12-33-15_tts.wav
                            timestamp_str = str(timestamp).replace(":", "-").replace(" ", "_").replace(".", "-").replace("[", "").replace("]", "")
                            dest_filename = f"{timestamp_str}_tts.wav"
                        else:
                            dest_filename = f"tts_{int(time_module.time())}.wav"
                        
                        dest_path = self.audio_folder / dest_filename
                        
                        print(f"[DEBUG] Copying TTS file from {source_path} to {dest_path}")
                        
                        # Copy the file
                        shutil.copy2(str(source_path), str(dest_path))
                        
                        if DebugConfig.tts_operations:
                            print(f"[DEBUG] ✓ Audio copied to chat folder: {dest_path}")
                        
                        # Verify the copy worked
                        if dest_path.exists():
                            print(f"[DEBUG] ✓ Verified: file exists at destination: {dest_path}")
                            
                            # Store mapping of timestamp -> audio file
                            if timestamp:
                                timestamp_clean = str(timestamp).replace("[", "").replace("]", "")
                                self.timestamp_audio[timestamp_clean] = str(dest_path)
                                print(f"[DEBUG] Stored mapping: {timestamp_clean} -> {dest_path}")
                            
                            # Auto-play the COPIED audio file (not the temp file!)
                            self._play_audio_file(str(dest_path), volume)
                        else:
                            print(f"[DEBUG] ERROR: Destination file not found after copy! {dest_path}")
                            # Try to play from source as fallback
                            self._play_audio_file(str(source_path), volume)
                    else:
                        print(f"[DEBUG] Source audio file not found: {source_path}")
                        # Still try to play from temp location as fallback
                        self._play_audio_file(audio_file_path, volume)
                        
                except Exception as e:
                    print(f"[DEBUG] Error copying TTS audio: {e}")
                    import traceback
                    traceback.print_exc()
                    # Still try to play from original location as fallback
                    self._play_audio_file(audio_file_path, volume)
            else:
                print(f"[DEBUG] No audio file path provided")
                    
        except Exception as e:
            print(f"[DEBUG] Error in _handle_tts_audio: {e}")
            import traceback
            traceback.print_exc()
    
    def _play_audio_file(self, filepath, volume=1.0):
        """Play audio file after TTS completes - using centralized audio player"""
        try:
            import sys
            # Add parent directory to path for local module import
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from audio_player import get_audio_player
            
            filepath = str(filepath)
            if not os.path.exists(filepath):
                if DebugConfig.tts_operations:
                    print(f"[DEBUG] Audio file does not exist: {filepath}")
                return
            
            if DebugConfig.tts_operations:
                print(f"[DEBUG] Auto-playing audio: {filepath} at volume {volume}")
            
            # Use centralized audio player (only one audio at a time)
            player = get_audio_player()
            player.play(filepath, auto_stop_current=True, volume=volume)
            
        except Exception as e:
            if DebugConfig.tts_operations:
                print(f"[DEBUG] Error playing audio: {e}")
    
    def stop_tts(self):
        """Stop TTS playback using centralized audio player"""
        try:
            import sys
            # Add parent directory to path for local module import
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from audio_player import get_audio_player
            
            # Stop current TTS object if it exists
            if self.current_tts:
                try:
                    self.current_tts.stop()
                except:
                    pass
                self.current_tts = None
            
            # Use centralized audio player to stop all audio
            player = get_audio_player()
            player.stop()
            if DebugConfig.tts_operations:
                print("[DEBUG-TTS] ✅ Audio stopped via centralized player")
            
            # Clear any TTS queues/flags
            if hasattr(self.chat_tab, 'app') and hasattr(self.chat_tab.app, 'tts_is_playing'):
                self.chat_tab.app.tts_is_playing = False
            if hasattr(self.chat_tab, 'app') and hasattr(self.chat_tab.app, 'tts_queue'):
                self.chat_tab.app.tts_queue = []
            
            if DebugConfig.tts_operations:
                print("[DEBUG-TTS] ✅ TTS stopped")
        except Exception as e:
            if DebugConfig.tts_operations:
                print(f"[DEBUG-TTS] Could not stop TTS: {e}")
