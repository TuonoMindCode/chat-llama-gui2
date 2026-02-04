"""
Text-to-Speech module for Llama Chat application
Supports multiple TTS engines: pyttsx3 and Piper
"""

import threading
import os
import subprocess
import json
import unicodedata
from pathlib import Path
import tempfile
from debug_config import DebugConfig

# Try to import pyttsx3
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

# Try to import pygame for audio playback
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

# Try to import gradio_client for F5-TTS
try:
    from gradio_client import Client as GradioClient, handle_file
    F5TTS_AVAILABLE = True
except ImportError:
    F5TTS_AVAILABLE = False


class TTSManager:
    """Manages Text-to-Speech using multiple engines"""
    
    def __init__(self, engine="pyttsx3", piper_exe=None, piper_model=None, f5tts_url=None, f5tts_ref_audio=None, 
                 f5tts_cross_fade=0.15, f5tts_nfe=16, f5tts_speed=0.9, f5tts_remove_silence=False, f5tts_randomize_seed=True, f5tts_seed=0):
        """Initialize TTS Manager
        
        Args:
            engine: TTS engine to use ("pyttsx3", "piper", or "f5tts")
            piper_exe: Path to Piper executable (for Piper engine)
            piper_model: Path to Piper model file .onnx (for Piper engine)
            f5tts_url: URL to F5-TTS server (for F5-TTS engine)
            f5tts_ref_audio: Path to reference audio file (for F5-TTS engine)
            f5tts_cross_fade: Cross fade duration for F5-TTS (default 0.15)
            f5tts_nfe: NFE slider value for F5-TTS (default 16)
            f5tts_speed: Speed slider value for F5-TTS (default 0.9)
            f5tts_remove_silence: Remove silence for F5-TTS (default False)
            f5tts_randomize_seed: Randomize seed for F5-TTS (default True)
            f5tts_seed: Seed value for F5-TTS (default 0)
        """
        self.engine = engine
        self.piper_exe = piper_exe
        self.piper_model = piper_model
        self.f5tts_url = f5tts_url or "http://127.0.0.1:7860"
        self.f5tts_ref_audio = f5tts_ref_audio
        self.f5tts_cross_fade = f5tts_cross_fade
        self.f5tts_nfe = f5tts_nfe
        self.f5tts_speed = f5tts_speed
        self.f5tts_remove_silence = f5tts_remove_silence
        self.f5tts_randomize_seed = f5tts_randomize_seed
        self.f5tts_seed = f5tts_seed
        self.pyttsx3_engine = None
        self.is_speaking = False
        self.should_stop = False  # Flag to stop current playback
        self.current_process = None  # Reference to Piper subprocess
        self.current_sound = None  # Reference to current pygame sound for stopping
        self.last_audio_file = None  # Track the last audio file generated/played
        
        if engine == "pyttsx3" and PYTTSX3_AVAILABLE:
            self.pyttsx3_engine = pyttsx3.init()
    
    def get_voices_pyttsx3(self):
        """Get available voices for pyttsx3"""
        if not PYTTSX3_AVAILABLE:
            return []
        
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            return [{"id": v.id, "name": v.name} for v in voices]
        except Exception as e:
            print(f"Error getting pyttsx3 voices: {e}")
            return []
    
    def get_voices_piper(self):
        """Get available voices from Piper model"""
        if not self.piper_model or not os.path.exists(self.piper_model):
            return []
        
        try:
            # Piper model directory
            model_dir = os.path.dirname(self.piper_model)
            model_name = os.path.basename(self.piper_model).replace('.onnx', '')
            
            # Look for corresponding .json file with voice info
            json_file = os.path.join(model_dir, f"{model_name}.json")
            
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    speakers = data.get('speaker_id_map', {})
                    return list(speakers.keys())
            else:
                # Default voice if no json found
                return ["default"]
        except Exception as e:
            print(f"Error getting Piper voices: {e}")
            return []
    
    def speak(self, text, speed=1.0, volume=1.0, voice=None, callback=None):
        """Speak text using selected engine
        
        Args:
            text: Text to speak
            speed: Speech speed (0.5-2.0, 1.0 = normal)
            volume: Volume (0.0-1.0)
            voice: Voice to use (engine-specific)
            callback: Function to call when done (success, message)
        """
        if not text or not text.strip():
            if callback:
                callback(False, "No text to speak")
            return
        
        # Reset stop flag
        self.should_stop = False
        
        def speak_thread():
            try:
                self.is_speaking = True
                
                if self.engine == "pyttsx3":
                    self._speak_pyttsx3(text, speed, volume, voice)
                elif self.engine == "piper":
                    self._speak_piper(text, speed, volume, voice)
                elif self.engine == "f5tts":
                    self._speak_f5tts(text, speed, voice)
                else:
                    raise ValueError(f"Unknown TTS engine: {self.engine}")
                
                self.is_speaking = False
                if callback and not self.should_stop:
                    callback(True, "Speech completed")
                    
            except Exception as e:
                self.is_speaking = False
                error_msg = f"TTS error: {str(e)}"
                print(error_msg)
                if callback:
                    callback(False, error_msg)
        
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop current TTS playback"""
        self.should_stop = True
        self.is_speaking = False
        
        # Stop any current audio playback
        if self.current_sound:
            try:
                self.current_sound.stop()
                self.current_sound = None
            except:
                pass
        
        # Stop all pygame mixer sounds
        if PYGAME_AVAILABLE:
            try:
                import pygame
                pygame.mixer.stop()
            except:
                pass
        
        # For pyttsx3, stop the engine
        if self.engine == "pyttsx3" and PYTTSX3_AVAILABLE:
            try:
                if self.pyttsx3_engine:
                    self.pyttsx3_engine.stop()
            except:
                pass
        
        # For Piper, terminate the subprocess
        if self.engine == "piper" and self.current_process:
            try:
                # First try terminate
                self.current_process.terminate()
                # Wait a bit for graceful shutdown
                try:
                    self.current_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    # Force kill if terminate doesn't work
                    self.current_process.kill()
                    self.current_process.wait()
                self.current_process = None
            except:
                pass
    
    def _speak_pyttsx3(self, text, speed, volume, voice):
        """Speak using pyttsx3"""
        if not PYTTSX3_AVAILABLE:
            raise RuntimeError("pyttsx3 not installed. Install with: pip install pyttsx3")
        
        # Sanitize text: remove emoji and problematic unicode characters
        text = ''.join(c for c in text if unicodedata.category(c)[0] != 'S' or c in '.,!?-')  # Remove symbols except punctuation
        
        engine = self.pyttsx3_engine
        
        # Set voice if specified
        if voice:
            engine.setProperty('voice', voice)
        
        # Set rate (speed)
        base_rate = engine.getProperty('rate')
        engine.setProperty('rate', base_rate * speed)
        
        # Set volume
        engine.setProperty('volume', min(max(volume, 0.0), 1.0))
        
        # Speak
        engine.say(text)
        engine.runAndWait()
    
    def _speak_piper(self, text, speed, volume, voice):
        """Speak using Piper"""
        if not self.piper_exe or not os.path.exists(self.piper_exe):
            raise RuntimeError(f"Piper executable not found: {self.piper_exe}")
        
        if not self.piper_model or not os.path.exists(self.piper_model):
            raise RuntimeError(f"Piper model not found: {self.piper_model}")
        
        # Sanitize text: remove emoji and problematic unicode characters
        text = ''.join(c for c in text if unicodedata.category(c)[0] != 'S' or c in '.,!?-')  # Remove symbols except punctuation
        
        # Create temporary WAV file (delete=False so we can keep it after playing)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            output_file = tmp.name
        
        try:
            # Build Piper command
            cmd = [
                self.piper_exe,
                "--model", self.piper_model,
                "--output-file", output_file
            ]
            
            # Add voice/speaker if specified
            if voice and voice != "default":
                cmd.extend(["--speaker", voice])
            
            # Run Piper with UTF-8 encoding
            self.current_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            stdout, stderr = self.current_process.communicate(input=text)
            
            # Check if we were asked to stop before playing
            if self.should_stop:
                return
            
            if self.current_process.returncode != 0:
                raise RuntimeError(f"Piper error: {stderr}")
            
            # Store audio file path BEFORE playing - keep it for callback to copy
            self.last_audio_file = output_file
            
            # DON't play here - the callback will play the file via pygame after copying it
            # This ensures consistent playback and proper stopping behavior
            
        finally:
            # DON'T delete the temp file - let the callback copy it to tts_audio/
            # The cleanup will happen after the file is saved and played
            pass
    
    def _speak_f5tts(self, text, speed, voice):
        """Speak using F5-TTS"""
        if not F5TTS_AVAILABLE:
            raise RuntimeError("gradio_client not installed. Install with: pip install gradio_client")
        
        # Sanitize text: remove emoji and problematic unicode characters
        text = ''.join(c for c in text if unicodedata.category(c)[0] != 'S' or c in '.,!?-')  # Remove symbols except punctuation
        
        if not self.f5tts_ref_audio:
            raise RuntimeError("F5-TTS reference audio not configured")
        
        try:
            # Connect to F5-TTS server
            client = GradioClient(self.f5tts_url)
            
            # Read reference text from the corresponding .txt file
            txt_path = self.f5tts_ref_audio.replace(".wav", ".txt")
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    ref_text = f.read().strip()
            else:
                raise RuntimeError(f"Reference text file not found: {txt_path}")
            
            # Call F5-TTS API
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] F5-TTS API calling with ref_audio={self.f5tts_ref_audio}, text length={len(text)}")
            result = client.predict(
                ref_audio_input=handle_file(self.f5tts_ref_audio),
                ref_text_input=ref_text,
                gen_text_input=text,
                remove_silence=self.f5tts_remove_silence,
                randomize_seed=self.f5tts_randomize_seed,
                seed_input=self.f5tts_seed,
                cross_fade_duration_slider=self.f5tts_cross_fade,
                nfe_slider=self.f5tts_nfe,
                speed_slider=self.f5tts_speed,
                api_name="/basic_tts"
            )
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] F5-TTS result: {result} (type: {type(result)})")
            
            # Check if we were asked to stop before playing
            if self.should_stop:
                return
            
            # result should be a tuple (audio_path, sr) or just the path
            audio_path = result[0] if isinstance(result, tuple) else result
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] F5-TTS audio_path: {audio_path}")
            
            # Store the audio file path for later reference
            self.last_audio_file = audio_path
            
            # Don't play here - the callback will play the file via pygame after copying it
            # This ensures consistent playback and proper stopping behavior
        except Exception as e:
            raise RuntimeError(f"F5-TTS error: {str(e)}")

    def _play_audio(self, filepath):
        """Play audio file using pygame (supports stopping)"""
        try:
            # Use pygame if available
            if PYGAME_AVAILABLE:
                try:
                    # STOP any currently playing audio first
                    if self.current_sound:
                        try:
                            self.current_sound.stop()
                        except:
                            pass
                        self.current_sound = None
                    
                    # Also stop any pygame mixer music that might be playing
                    if pygame.mixer.music.get_busy():
                        pygame.mixer.music.stop()
                    
                    self.current_sound = pygame.mixer.Sound(filepath)
                    self.current_sound.play()
                    return
                except Exception as e:
                    print(f"pygame playback error: {e}")
                    self.current_sound = None
                    # Fall back to winsound
            
            # Fallback to platform-specific players
            import platform
            system = platform.system()
            
            if system == "Windows":
                import winsound
                winsound.PlaySound(filepath, winsound.SND_FILENAME)
            elif system == "Darwin":
                os.system(f"afplay {filepath}")
            else:
                # Linux
                os.system(f"aplay {filepath}")
        except Exception as e:
            print(f"Error playing audio: {e}")
            self.current_sound = None
    
    @staticmethod
    def get_available_engines():
        """Get list of available TTS engines"""
        engines = []
        
        if PYTTSX3_AVAILABLE:
            engines.append("pyttsx3")
        
        engines.append("piper")  # Piper is optional, user can install
        
        if F5TTS_AVAILABLE:
            engines.append("f5tts")  # F5-TTS is optional, user can install
        
        return engines
