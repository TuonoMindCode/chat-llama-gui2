"""
Speech-to-Text module for Llama Chat application
Uses OpenAI's Whisper for speech recognition
"""

import threading
import numpy as np
import tempfile
import os

# Lazy loading of heavy libraries to avoid torch DLL errors on Windows
STT_AVAILABLE = False
CUDA_AVAILABLE = False
COMPUTE_DEVICE = "cpu"
whisper = None
sd = None
sf = None
torch = None


def _initialize_stt_libraries():
    """Lazily initialize STT libraries on first use"""
    global STT_AVAILABLE, CUDA_AVAILABLE, COMPUTE_DEVICE, whisper, sd, sf, torch
    
    if STT_AVAILABLE:
        return  # Already initialized
    
    try:
        import whisper as _whisper
        import sounddevice as _sd
        import soundfile as _sf
        import torch as _torch
        
        whisper = _whisper
        sd = _sd
        sf = _sf
        torch = _torch
        
        STT_AVAILABLE = True
        # Auto-detect GPU availability
        CUDA_AVAILABLE = torch.cuda.is_available()
        if CUDA_AVAILABLE:
            COMPUTE_DEVICE = "cuda"
        else:
            COMPUTE_DEVICE = "cpu"
    except (ImportError, OSError) as e:
        # Catch both ImportError and OSError (DLL loading errors on Windows)
        STT_AVAILABLE = False
        CUDA_AVAILABLE = False
        COMPUTE_DEVICE = "cpu"
        error_msg = str(e)
        if "c10.dll" in error_msg or "DLL" in error_msg:
            print(f"[VOICE_INPUT] PyTorch DLL loading error on Windows: {e}")
            print("[VOICE_INPUT] Voice input disabled. PyTorch libraries may be corrupted.")
        else:
            print(f"[VOICE_INPUT] STT libraries not available: {e}")
        raise


# Global model cache to avoid reloading the same model multiple times
_model_cache = {}
_cache_lock = threading.Lock()


def clear_all_models():
    """Clear all models from cache to free all memory"""
    import gc
    import sys
    global _model_cache
    
    try:
        print("[CLEANUP] Starting comprehensive model cleanup...")
        
        with _cache_lock:
            for cache_key in list(_model_cache.keys()):
                try:
                    model = _model_cache[cache_key]
                    print(f"[CLEANUP] Clearing {cache_key}...")
                    
                    # Explicitly delete model internals for Whisper
                    try:
                        if hasattr(model, 'encoder'):
                            model.encoder = None
                        if hasattr(model, 'decoder'):
                            model.decoder = None
                        if hasattr(model, 'dims'):
                            model.dims = None
                        if hasattr(model, 'tokenizer'):
                            model.tokenizer = None
                        if hasattr(model, '__dict__'):
                            model.__dict__.clear()
                    except Exception as e:
                        print(f"[CLEANUP] Error clearing internals: {e}")
                    
                    del model
                    del _model_cache[cache_key]
                    print(f"✓ Deleted {cache_key} from cache")
                except Exception as e:
                    print(f"Error clearing {cache_key}: {e}")
        
        # Aggressive garbage collection for CPU models
        print("[CLEANUP] Running aggressive garbage collection...")
        for i in range(10):
            collected = gc.collect()
            if i < 3 or collected > 0:
                print(f"[CLEANUP] GC pass {i+1}: freed {collected} objects")
        
        # Clear CUDA cache if available
        try:
            import torch
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            print("[CLEANUP] CUDA cache cleared and synchronized")
        except:
            pass
        
        print("✓ All models cleared from memory - RAM should be freed now")
    except Exception as e:
        print(f"Error clearing all models: {e}")


class SpeechToText:
    """Handles speech-to-text conversion using Whisper"""
    
    def __init__(self, model="base", device=None, compute_device="auto"):
        """Initialize speech-to-text
        
        Args:
            model: Whisper model size (tiny, base, small, medium, large)
            device: Audio device index to use (None = default)
            compute_device: Where to run Whisper: "auto" (GPU if available), "cpu", or "cuda"
            
        Raises:
            RuntimeError: If STT libraries failed to load (e.g., PyTorch DLL error)
        """
        # Lazy initialize torch and whisper on first use (avoid DLL errors at import time)
        _initialize_stt_libraries()
        
        if not STT_AVAILABLE:
            raise RuntimeError("Speech-to-text libraries not available. Check PyTorch installation.")
        
        self.model = None
        self.model_name = model
        self.device = device
        self.compute_device = compute_device if compute_device in ["auto", "cpu", "cuda"] else "auto"
        self.is_recording = False
        self.audio_data = None
        self.sample_rate = 16000  # Will be detected at recording time
        self.recording_complete = False  # Flag to indicate recording finished
        self.stop_recording_flag = False  # Flag to stop recording early
        self.last_audio_file = None  # Path to last recorded audio file
        
        if STT_AVAILABLE:
            self.load_model(model)
    
    @staticmethod
    def _get_supported_sample_rates(device):
        """Get supported sample rates for a device by testing"""
        preferred_rates = [16000, 44100, 48000, 22050, 32000]
        supported = []
        
        for rate in preferred_rates:
            try:
                # Try to open a stream with this sample rate
                test_stream = sd.InputStream(
                    samplerate=rate, 
                    channels=1, 
                    device=device, 
                    blocksize=1024
                )
                test_stream.close()
                supported.append(rate)
            except:
                pass
        
        return supported if supported else [16000]
    
    def load_model(self, model_name):
        """Load whisper model with caching to avoid reloading
        
        Args:
            model_name: Model size to load
        """
        try:
            # Determine which device to use
            if self.compute_device == "auto":
                device = COMPUTE_DEVICE
            else:
                device = self.compute_device
            
            # Check if CUDA is requested but not available
            if device == "cuda" and not CUDA_AVAILABLE:
                print(f"⚠ CUDA requested but not available. Falling back to CPU.")
                device = "cpu"
            
            # Create cache key
            cache_key = f"{model_name}_{device}"
            
            # DISABLED CACHING - Load fresh model each time for clean memory
            # This ensures we can properly clean up after transcription
            # Caching was causing memory issues
            print(f"Loading Whisper model '{model_name}' on {device}...")
            self.model = whisper.load_model(model_name, device=device)
            self.model_name = model_name
            self.device = device  # Store the actual compute device for unload
            
            if device == "cuda":
                print(f"✓ Loaded Whisper model '{model_name}' on GPU (CUDA)")
            else:
                print(f"✓ Loaded Whisper model '{model_name}' on CPU")
            return True
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            # Try falling back to CPU if there was an error
            try:
                print(f"Attempting fallback to CPU...")
                cache_key = f"{model_name}_cpu"
                with _cache_lock:
                    if cache_key not in _model_cache:
                        self.model = whisper.load_model(model_name, device="cpu")
                        _model_cache[cache_key] = self.model
                    else:
                        self.model = _model_cache[cache_key]
                self.model_name = model_name
                self.device = "cpu"  # Store the actual compute device for unload
                print(f"✓ Loaded Whisper model '{model_name}' on CPU (fallback)")
                return True
            except Exception as fallback_error:
                print(f"Fallback failed: {fallback_error}")
                return False
    
    def record_audio(self, duration=5, callback=None, level_callback=None, gain=1.0):
        """Record audio from microphone
        
        Args:
            duration: Recording duration in seconds
            callback: Function to call with (success, message) when recording completes
            level_callback: Function to call with (level) for real-time level updates
            gain: Input gain multiplier (1.0 = normal, >1.0 = louder, <1.0 = quieter)
        """
        self.stop_recording_flag = False  # Reset stop flag
        
        def record_thread():
            try:
                self.recording_complete = False  # Reset flag
                
                # Detect supported sample rate for this device
                supported_rates = self._get_supported_sample_rates(self.device)
                sample_rate = supported_rates[0] if supported_rates else 16000
                self.sample_rate = sample_rate
                
                # Record audio
                sample_count = int(sample_rate * duration)
                
                audio = sd.rec(
                    sample_count, 
                    samplerate=sample_rate, 
                    channels=1, 
                    dtype=np.float32, 
                    device=self.device
                )
                
                # Update level during recording
                for i in range(duration * 10):  # Update 10 times per second
                    import time
                    time.sleep(0.1)
                    
                    # Check if stop was requested
                    if self.stop_recording_flag:
                        print("[DEBUG SpeechToText] Stop flag detected, stopping recording")
                        sd.stop()
                        break
                    
                    current_samples = int((i + 1) * sample_rate * 0.1)
                    current_samples = min(current_samples, len(audio))
                    
                    if current_samples > 0:
                        try:
                            chunk = audio[:current_samples]
                            level = float(np.max(np.abs(chunk))) if len(chunk) > 0 else 0.0
                            if level_callback:
                                level_callback(level)
                        except:
                            pass
                
                sd.wait()
                
                # Flatten and apply gain
                self.audio_data = audio.flatten() if audio is not None else np.array([])
                if len(self.audio_data) > 0:
                    self.audio_data = self.audio_data * gain
                    self.audio_data = np.clip(self.audio_data, -1.0, 1.0)
                
                if self.audio_data is not None and len(self.audio_data) > 0:
                    # Calculate final audio level
                    max_level = float(np.max(np.abs(self.audio_data)))
                    rms_level = float(np.sqrt(np.mean(self.audio_data ** 2)))
                    
                    # Save audio to file in recordings folder
                    try:
                        from pathlib import Path
                        recordings_dir = Path("whisper_recordings")
                        recordings_dir.mkdir(exist_ok=True)
                        
                        # Generate filename with timestamp
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        audio_file = recordings_dir / f"recording_{timestamp}.wav"
                        
                        # Save audio
                        sf.write(str(audio_file), self.audio_data, self.sample_rate)
                        self.last_audio_file = str(audio_file)
                        print(f"[DEBUG] Audio saved to: {audio_file}")
                    except Exception as e:
                        print(f"[DEBUG] Error saving audio file: {e}")
                    
                    # Mark recording as complete
                    self.recording_complete = True
                    
                    if callback:
                        callback(True, f"Max Level: {max_level:.4f} | RMS: {rms_level:.4f}")
                else:
                    self.recording_complete = True
                    if callback:
                        callback(False, "No audio data recorded")
            except Exception as e:
                self.recording_complete = True
                if callback:
                    callback(False, str(e))
        
        thread = threading.Thread(target=record_thread, daemon=True)
        thread.start()
    
    def stop_recording(self):
        """Stop recording immediately"""
        print("[DEBUG SpeechToText] Stop recording called")
        self.stop_recording_flag = True
    
    def detect_language(self):
        """Detect language of recorded audio (first pass)
        
        Returns:
            Language code (e.g., 'sv', 'en', 'de') or None if failed
        """
        if self.audio_data is None or len(self.audio_data) == 0:
            return None
        
        try:
            if self.model is None:
                self.load_model(self.model_name)
            
            if self.model is None:
                return None
            
            # Save audio to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_file = tmp.name
            
            sf.write(temp_file, self.audio_data, self.sample_rate)
            
            # Suppress warnings and progress output
            import warnings
            import sys
            import io
            
            warnings.filterwarnings('ignore')
            
            # Redirect stderr to suppress progress bar
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            
            try:
                # Run Whisper without specifying language - it will detect and return language
                result = self.model.transcribe(
                    temp_file,
                    verbose=False,
                    fp16=False,
                    temperature=0.0,
                    no_speech_threshold=0.6,
                    logprob_threshold=-1.0
                )
            finally:
                sys.stderr = old_stderr
            
            detected_language = result.get("language", "unknown")
            
            # Clean up
            try:
                os.remove(temp_file)
            except:
                pass
            
            print(f"[DEBUG LANGUAGE DETECTION] Detected language: {detected_language}")
            return detected_language
        
        except Exception as e:
            print(f"[DEBUG LANGUAGE DETECTION] Error: {e}")
            return None
    
    def transcribe(self, language=None, temperature=None, no_speech_threshold=None, logprob_threshold=None, rms_threshold=None):
        """Transcribe recorded audio with optional language hint (second pass)
        
        Args:
            language: Language code (e.g., 'sv', 'en', 'de') to use for transcription.
                     If None, language will be auto-detected.
            temperature: Temperature value (0.0-1.0) to control randomness/repetition
            no_speech_threshold: Threshold for detecting silence (0.0-1.0)
            logprob_threshold: Log probability threshold for confidence (-5.0-0.0)
            rms_threshold: RMS amplitude threshold for rejecting audio as too quiet (0.001-0.1)
        
        Returns:
            Dict with 'text' and 'language' keys, or None if failed
        """
        if self.audio_data is None or len(self.audio_data) == 0:
            return None
        
        # Check minimum audio duration (at least 0.5 seconds of actual content)
        # This helps prevent hallucinations from very short audio or silence
        audio_duration = len(self.audio_data) / self.sample_rate
        min_duration = 0.5
        
        # Check if audio has meaningful content (not just silence/noise)
        max_amplitude = float(np.max(np.abs(self.audio_data)))
        rms_level = float(np.sqrt(np.mean(self.audio_data ** 2)))
        
        # Get thresholds from parameters or environment or use defaults
        import os
        # MUCH lower threshold to avoid rejecting real audio - 0.001 instead of 0.01
        if rms_threshold is None:
            rms_threshold = float(os.environ.get('WHISPER_RMS_THRESHOLD', 0.001))
        else:
            rms_threshold = float(rms_threshold)
        
        # Use passed parameters if provided, otherwise use environment/defaults
        if no_speech_threshold is None:
            no_speech_threshold = float(os.environ.get('WHISPER_NO_SPEECH_THRESHOLD', 0.6))
        else:
            no_speech_threshold = float(no_speech_threshold)
            
        if logprob_threshold is None:
            logprob_threshold = float(os.environ.get('WHISPER_LOG_PROB_THRESHOLD', -1.0))
        else:
            logprob_threshold = float(logprob_threshold)
            
        if temperature is None:
            temperature = float(os.environ.get('WHISPER_TEMPERATURE', 0.0))
        else:
            temperature = float(temperature)
        
        # Debug: log the RMS level
        print(f"[DEBUG TRANSCRIBE] Audio RMS: {rms_level:.6f}, Threshold: {rms_threshold:.6f}, Duration: {audio_duration:.2f}s")
        print(f"[DEBUG TRANSCRIBE] Settings - Temp: {temperature}, NoSpeech: {no_speech_threshold}, LogProb: {logprob_threshold}")
        
        # If audio is too quiet, it's likely just noise or silence
        if rms_level < rms_threshold:
            print(f"[DEBUG TRANSCRIBE] Audio rejected - too quiet (RMS {rms_level:.6f} < {rms_threshold:.6f})")
            return None
        
        try:
            if self.model is None:
                self.load_model(self.model_name)
            
            if self.model is None:
                return None
            
            # Save audio to temporary file  
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                temp_file = tmp.name
            
            sf.write(temp_file, self.audio_data, self.sample_rate)
            
            # Suppress warnings and progress output
            import warnings
            import sys
            import io
            
            warnings.filterwarnings('ignore')
            
            # Redirect stderr to suppress progress bar
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            
            try:
                # Transcribe with language hint if provided (second pass with detected language)
                transcribe_kwargs = {
                    "verbose": False,
                    "fp16": False,  # Use FP32 for better accuracy, less hallucination
                    "temperature": temperature,  # Lower temperature = more deterministic, less hallucination
                    "no_speech_threshold": no_speech_threshold,  # Threshold for detecting speech
                    "logprob_threshold": logprob_threshold  # Threshold for log probability
                }
                
                # Add language parameter if provided (not auto-detection, using selected language)
                if language:
                    transcribe_kwargs["language"] = language
                    print(f"[DEBUG TRANSCRIBE] Using selected language: {language}")
                
                result = self.model.transcribe(temp_file, **transcribe_kwargs)
            finally:
                sys.stderr = old_stderr
            
            text = result.get("text", "").strip()
            detected_language = result.get("language", "unknown")
            
            # Filter out likely hallucinations:
            # - Common hallucination patterns (empty transcripts, generic phrases)
            # - Very short results when audio is longer (sign of hallucination)
            # - Repetitive phrases (Whisper can get stuck repeating the same phrase)
            hallucination_keywords = [
                "thank you for watching",
                "thanks for watching", 
                "subscribe",
                "don't forget to like",
                "hit the like button",
                "please like",
                "thank you for listening",
                "thank you"  # Also catch standalone "thank you"
            ]
            
            if text:
                text_lower = text.lower()
                # Check for known hallucination patterns
                for keyword in hallucination_keywords:
                    if keyword in text_lower:
                        return None
                
                # Check for repetitive phrase hallucination (e.g., same sentence repeated many times)
                # Split into sentences
                import re
                sentences = re.split(r'[.!?]+', text)
                sentences = [s.strip() for s in sentences if s.strip()]
                
                if len(sentences) > 0:
                    # Check if more than 70% of sentences are identical (hallucination threshold)
                    if len(sentences) > 3:
                        sentence_counts = {}
                        for sent in sentences:
                            sent_lower = sent.lower().strip()
                            sentence_counts[sent_lower] = sentence_counts.get(sent_lower, 0) + 1
                        
                        # Find the most repeated sentence
                        max_repeats = max(sentence_counts.values()) if sentence_counts else 0
                        repeat_ratio = max_repeats / len(sentences) if sentences else 0
                        
                        # If > 70% of text is the same sentence, it's likely hallucination
                        if repeat_ratio > 0.7:
                            print(f"[DEBUG TRANSCRIBE] Detected repetitive hallucination: {repeat_ratio*100:.0f}% repeated sentences")
                            # Return only the first occurrence of the repeated sentence
                            # This preserves some content instead of returning None
                            first_unique = []
                            seen = set()
                            for sent in sentences:
                                sent_lower = sent.lower().strip()
                                if sent_lower not in seen:
                                    first_unique.append(sent)
                                    seen.add(sent_lower)
                            
                            cleaned_text = ". ".join(first_unique) + "."
                            return {
                                "text": cleaned_text,
                                "language": detected_language
                            }
                
                # If audio is long but transcription is generic, likely hallucination
                if audio_duration > 2.0 and len(text) < 20:
                    # Probably hallucination from silence
                    if text_lower in ["thanks for watching.", "thank you for watching.", "", "thank you."]:
                        return None
            
            # Clean up
            try:
                os.remove(temp_file)
            except:
                pass
            
            self.audio_data = None
            return {
                "text": text if text else None,
                "language": detected_language
            } if text else None
        except Exception as e:
            return None
    
    def get_available_models(self):
        """Get list of available Whisper models"""
        return ["tiny", "base", "small", "medium", "large"]
    
    def unload_model(self):
        """Unload model from memory to free VRAM/RAM"""
        import gc
        import sys
        
        try:
            print(f"[UNLOAD] Starting model unload for {self.model_name}...")
            
            if self.model is None:
                print(f"[UNLOAD] Model already None, skipping")
                return
            
            # Find all references to the model
            referrers = gc.get_referrers(self.model)
            print(f"[UNLOAD] Found {len(referrers)} references to model")
            
            # Try to break circular references
            try:
                if hasattr(self.model, 'encoder'):
                    print(f"[UNLOAD] Deleting encoder...")
                    if hasattr(self.model.encoder, 'conv1'):
                        self.model.encoder.conv1 = None
                    self.model.encoder = None
                
                if hasattr(self.model, 'decoder'):
                    print(f"[UNLOAD] Deleting decoder...")
                    if hasattr(self.model.decoder, 'token_embedding'):
                        self.model.decoder.token_embedding = None
                    self.model.decoder = None
                
                if hasattr(self.model, 'dims'):
                    self.model.dims = None
                
                if hasattr(self.model, 'tokenizer'):
                    self.model.tokenizer = None
                
                # Clear the model dict
                if hasattr(self.model, '__dict__'):
                    self.model.__dict__.clear()
                    
            except Exception as e:
                print(f"[UNLOAD] Error clearing internals: {e}")
            
            # Delete model reference
            del self.model
            self.model = None
            
            # Delete audio data if exists
            if hasattr(self, 'audio_data') and self.audio_data is not None:
                self.audio_data = None
            
            print(f"[UNLOAD] Deleted model reference")
            
            # Aggressive garbage collection - multiple passes
            print(f"[UNLOAD] Running garbage collection (multiple passes)...")
            for i in range(10):
                collected = gc.collect()
                if i < 3 or collected > 0:
                    print(f"[UNLOAD] GC pass {i+1}: {collected} objects freed")
            
            # Clear CUDA cache if on GPU
            if self.device == "cuda":
                try:
                    import torch
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    print(f"[UNLOAD] CUDA cache cleared and synchronized")
                except Exception as e:
                    print(f"[UNLOAD] Error clearing CUDA: {e}")
            
            print(f"[UNLOAD] Model unload complete")
                    
        except Exception as e:
            print(f"[UNLOAD] Error in unload_model: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def get_available_devices():
        """Get list of available audio input devices
        
        Returns:
            List of (device_id, device_name) tuples
        """
        if not STT_AVAILABLE:
            return []
        
        try:
            devices = sd.query_devices()
            input_devices = []
            
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    input_devices.append((i, f"{i}: {device['name']}"))
            
            return input_devices
        except Exception as e:
            print(f"Error querying devices: {e}")
            return []
    
    def test_microphone(self, duration=3, device=None, callback=None):
        """Test microphone and save recording to file for inspection
        
        Args:
            duration: Recording duration in seconds
            device: Device ID to test
            callback: Function to call with (success, message, filename)
        """
        def test_thread():
            try:
                test_device = device if device is not None else self.device
                
                # Detect supported sample rate
                supported_rates = self._get_supported_sample_rates(test_device)
                sample_rate = supported_rates[0] if supported_rates else 16000
                
                print(f"\n{'='*60}")
                print(f"MICROPHONE TEST")
                print(f"{'='*60}")
                print(f"Device: {test_device}")
                print(f"Supported rates: {supported_rates}")
                print(f"Using rate: {sample_rate}Hz")
                print(f"Recording for {duration} seconds...")
                print(f"Please speak clearly into the microphone!")
                print(f"{'='*60}\n")
                
                # Record audio
                sample_count = int(sample_rate * duration)
                audio = sd.rec(
                    sample_count,
                    samplerate=sample_rate,
                    channels=1,
                    dtype=np.float32,
                    device=test_device
                )
                
                # Wait and show progress
                for i in range(duration):
                    import time
                    time.sleep(1)
                    print(f"  {i+1}/{duration}s")
                
                sd.wait()
                audio_data = audio.flatten() if audio is not None else np.array([])
                
                if len(audio_data) == 0:
                    if callback:
                        callback(False, "No audio data recorded", "")
                    return
                
                # Save to test file
                test_file = "microphone_test.wav"
                sf.write(test_file, audio_data, sample_rate)
                
                # Analyze
                max_level = float(np.max(np.abs(audio_data)))
                rms_level = float(np.sqrt(np.mean(audio_data ** 2)))
                mean_level = float(np.mean(np.abs(audio_data)))
                
                print(f"\n{'='*60}")
                print(f"RECORDING ANALYSIS")
                print(f"{'='*60}")
                print(f"File saved: {test_file}")
                print(f"Duration: {len(audio_data) / sample_rate:.2f}s")
                print(f"Samples: {len(audio_data)}")
                print(f"Sample rate: {sample_rate}Hz")
                print(f"Peak level: {max_level:.6f}")
                print(f"RMS level: {rms_level:.6f}")
                print(f"Mean level: {mean_level:.6f}")
                
                # Diagnostics
                print(f"\nDIAGNOSTICS:")
                if max_level < 0.001:
                    print(f"  ⚠️  PROBLEM: Audio level is VERY LOW (< 0.001)")
                    print(f"     - Microphone may not be working")
                    print(f"     - Try a different microphone device")
                    print(f"     - Check if microphone is muted")
                    print(f"     - Speak louder and closer to mic")
                elif max_level < 0.01:
                    print(f"  ⚠️  WARNING: Audio level is low (0.001-0.01)")
                    print(f"     - Increase microphone gain in settings")
                    print(f"     - Speak louder")
                else:
                    print(f"  ✓ Audio level looks good!")
                    print(f"     - Microphone is working properly")
                
                print(f"\nTo listen to the recording, open: {test_file}")
                print(f"{'='*60}\n")
                
                if callback:
                    callback(True, f"Max: {max_level:.6f} | RMS: {rms_level:.6f} | Samples: {len(audio_data)}", test_file)
                    
            except Exception as e:
                print(f"Test error: {e}")
                import traceback
                traceback.print_exc()
                if callback:
                    callback(False, str(e), "")
        
        thread = threading.Thread(target=test_thread, daemon=True)
        thread.start()
