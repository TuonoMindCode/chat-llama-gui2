"""
Persistent Whisper Worker Process
Stays alive and processes multiple transcription requests
Model is loaded once and reused for all requests
"""

import sys
import json
import os
import traceback
from pathlib import Path

try:
    import whisper
except ImportError:
    pass


def log_error(message):
    """Log error to stderr"""
    print(f"[PERSISTENT_WORKER_ERROR] {message}", file=sys.stderr)
    sys.stderr.flush()


def log_info(message):
    """Log info to stderr"""
    print(f"[PERSISTENT_WORKER] {message}", file=sys.stderr)
    sys.stderr.flush()


class PersistentWorker:
    """Worker that keeps model in memory"""
    
    def __init__(self):
        self.model = None
        self.current_model_name = None
        self.current_device = None
    
    def load_model(self, model_name, device):
        """Load model if not already loaded"""
        if self.model and self.current_model_name == model_name and self.current_device == device:
            return  # Already loaded
        
        log_info(f"Loading Whisper {model_name} model on {device}...")
        self.model = whisper.load_model(model_name, device=device)
        self.current_model_name = model_name
        self.current_device = device
        log_info(f"✅ Model loaded and ready for transcription")
    
    def transcribe(self, audio_file, language=None, task="transcribe", 
                   temperature=0.0, no_speech_threshold=0.6, logprob_threshold=-1.0):
        """Transcribe with loaded model"""
        if not os.path.exists(audio_file):
            raise FileNotFoundError(f"Audio file not found: {audio_file}")
        
        if not self.model:
            raise RuntimeError("Model not loaded")
        
        log_info(f"Transcribing: {audio_file}")
        
        # Prepare options
        options = {
            "language": language,
            "task": task,
            "temperature": temperature,
            "no_speech_threshold": no_speech_threshold,
            "logprob_threshold": logprob_threshold,
        }
        
        # Transcribe
        result = self.model.transcribe(audio_file, **options)
        
        log_info(f"✅ Transcription complete. Text: {len(result['text'])} chars")
        
        return {
            "text": result["text"],
            "language": result.get("language"),
            "detected_language": result.get("language"),
        }
    
    def shutdown(self):
        """Free model memory"""
        if self.model:
            log_info(f"Freeing model memory...")
            del self.model
            self.model = None
            self.current_model_name = None
            self.current_device = None
            log_info(f"✅ Model freed - 10GB memory released")


def main():
    """Main worker loop - stays alive and processes requests"""
    try:
        # Check if whisper is available
        if 'whisper' not in sys.modules:
            try:
                import whisper as whisper_module
            except ImportError:
                log_error("Whisper library not installed. Install with: pip install openai-whisper")
                sys.exit(1)
        
        worker = PersistentWorker()
        log_info("Persistent worker started. Waiting for commands...")
        
        # Process requests
        while True:
            try:
                # Read JSON request from stdin
                line = sys.stdin.readline()
                if not line:
                    break  # EOF
                
                request = json.loads(line)
                action = request.get("action")
                
                if action == "init":
                    # Initialize with model and device
                    model = request.get("model", "base")
                    device = request.get("device", "cpu")
                    worker.load_model(model, device)
                    
                    # Send success response
                    response = {"success": True, "result": {"status": "Model loaded"}}
                    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
                
                elif action == "transcribe":
                    # Transcribe audio
                    audio_file = request.get("audio_file")
                    language = request.get("language")
                    temperature = request.get("temperature", 0.0)
                    no_speech_threshold = request.get("no_speech_threshold", 0.6)
                    logprob_threshold = request.get("logprob_threshold", -1.0)
                    
                    result = worker.transcribe(
                        audio_file,
                        language=language,
                        temperature=temperature,
                        no_speech_threshold=no_speech_threshold,
                        logprob_threshold=logprob_threshold
                    )
                    
                    response = {"success": True, "result": result}
                    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
                
                elif action == "shutdown":
                    # Graceful shutdown
                    worker.shutdown()
                    response = {"success": True, "result": {"status": "Shutdown"}}
                    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                    sys.stdout.flush()
                    break
                
                else:
                    raise ValueError(f"Unknown action: {action}")
            
            except json.JSONDecodeError as e:
                log_error(f"Invalid JSON: {e}")
                response = {"success": False, "error": f"Invalid JSON: {e}"}
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
            
            except Exception as e:
                log_error(f"Error processing request: {e}")
                traceback.print_exc(file=sys.stderr)
                response = {"success": False, "error": str(e)}
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
    
    except Exception as e:
        log_error(f"Worker fatal error: {e}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
