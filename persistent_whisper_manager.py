"""
Persistent Whisper Manager - Keeps Whisper model in memory between calls
Perfect for continuous voice input recording with 5-second chunks
"""

import subprocess
import json
import sys
import os
import threading
from typing import Optional, Dict, Any
from debug_config import DebugConfig


class PersistentWhisperManager:
    """
    Manages a persistent Whisper worker process.
    Keeps the model in memory between calls for fast transcription.
    Perfect for continuous voice input.
    
    Usage:
        manager = PersistentWhisperManager(model="base", device="cpu")
        result = manager.transcribe(audio_file, language="en")
        manager.shutdown()  # When done, unload model
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton per configuration"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize persistent manager (singleton)"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._initialized = True
        self.worker_script = os.path.join(os.path.dirname(__file__), "persistent_whisper_worker.py")
        self.process = None
        self.model = None
        self.device = None
        self.is_running = False
        
        if not os.path.exists(self.worker_script):
            raise FileNotFoundError(f"Worker script not found: {self.worker_script}")
        
        if DebugConfig.chat_memory_operations:
            print(f"[PERSISTENT_WHISPER] Initialized (will keep model in memory)")
    
    def start(self, model: str = "base", device: str = "cpu"):
        """
        Start the persistent worker process
        
        Args:
            model: Model size (tiny, base, small, medium, large)
            device: Device to use (cpu, cuda, mps)
        """
        if self.is_running and self.model == model and self.device == device:
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] Already running with {model} on {device}")
            return
        
        # Shutdown previous instance if different config
        if self.is_running:
            self.shutdown()
        
        try:
            self.model = model
            self.device = device
            
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] Starting worker with {model} model on {device}...")
            
            # Spawn persistent worker process
            python_exe = sys.executable
            
            self.process = subprocess.Popen(
                [python_exe, self.worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1,  # Line buffering
            )
            
            # Send initialization request
            init_request = {
                "action": "init",
                "model": model,
                "device": device,
            }
            
            init_json = json.dumps(init_request, ensure_ascii=False) + "\n"
            self.process.stdin.write(init_json)
            self.process.stdin.flush()
            
            # Read initialization response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("Worker process failed to initialize")
            
            response = json.loads(response_line)
            if not response.get("success"):
                raise RuntimeError(f"Worker init failed: {response.get('error', 'Unknown error')}")
            
            self.is_running = True
            
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] ✅ Worker started - model loaded in memory")
            
            # Start thread to monitor stderr
            self._stderr_thread = threading.Thread(target=self._log_stderr, daemon=True)
            self._stderr_thread.start()
            
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] Error starting worker: {e}")
            self.is_running = False
            if self.process:
                self.process.kill()
            raise
    
    def transcribe(self, audio_file: str, language: Optional[str] = None, 
                   temperature: float = 0.0, no_speech_threshold: float = 0.6,
                   logprob_threshold: float = -1.0) -> Dict[str, Any]:
        """
        Transcribe audio using persistent worker
        
        Args:
            audio_file: Path to audio file
            language: Language code or None for auto-detect
            temperature: Temperature setting
            no_speech_threshold: Silence threshold
            logprob_threshold: Confidence threshold
        
        Returns:
            Dictionary with transcription result
        """
        if not self.is_running:
            raise RuntimeError("Worker not running. Call start() first.")
        
        try:
            # Send transcription request
            request = {
                "action": "transcribe",
                "audio_file": audio_file,
                "language": language,
                "temperature": temperature,
                "no_speech_threshold": no_speech_threshold,
                "logprob_threshold": logprob_threshold,
            }
            
            request_json = json.dumps(request, ensure_ascii=False) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("Worker process crashed")
            
            response = json.loads(response_line)
            
            if not response.get("success"):
                raise RuntimeError(f"Transcription failed: {response.get('error', 'Unknown error')}")
            
            return response.get("result", {})
        
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] Transcription error: {e}")
            raise
    
    def shutdown(self):
        """Shutdown worker and free model memory"""
        if not self.is_running:
            return
        
        try:
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] Shutting down - freeing 10GB model memory...")
            
            # Send shutdown request
            shutdown_request = {"action": "shutdown"}
            shutdown_json = json.dumps(shutdown_request, ensure_ascii=False) + "\n"
            self.process.stdin.write(shutdown_json)
            self.process.stdin.flush()
            
            # Wait for process to exit
            self.process.wait(timeout=5)
            
        except subprocess.TimeoutExpired:
            self.process.kill()
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[PERSISTENT_WHISPER] Error during shutdown: {e}")
            if self.process:
                self.process.kill()
        
        self.is_running = False
        self.process = None
        
        if DebugConfig.chat_memory_operations:
            print(f"[PERSISTENT_WHISPER] ✅ Shutdown complete - model freed")
    
    def _log_stderr(self):
        """Monitor stderr for debug output"""
        try:
            while self.is_running:
                line = self.process.stderr.readline()
                if not line:
                    break
                if line.strip():
                    print(f"[WORKER_LOG] {line.rstrip()}")
        except:
            pass
    
    def __del__(self):
        """Cleanup on deletion"""
        if self.is_running:
            try:
                self.shutdown()
            except:
                pass
