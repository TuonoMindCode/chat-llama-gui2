"""
ChatManager - Handles saving, loading, and managing chat files
Organizes chats with per-chat audio folders
"""

import json
from pathlib import Path
from datetime import datetime


class ChatManager:
    """Manages chat files and folders for a specific server"""
    
    def __init__(self, server_type):
        """
        Initialize ChatManager
        
        Args:
            server_type: "ollama" or "llama-server"
        """
        self.server_type = server_type
        self.base_folder = Path(f"saved_chats_{server_type.replace('-', '_')}")
        self.base_folder.mkdir(exist_ok=True)
        self.current_chat_name = None
        self.current_chat_folder = None
    
    def get_default_chat(self):
        """Get or create default chat"""
        return self._ensure_chat_folder("default")
    
    def _ensure_chat_folder(self, chat_name):
        """Ensure chat folder exists with proper structure"""
        chat_folder = self.base_folder / chat_name
        chat_folder.mkdir(exist_ok=True)
        
        audio_folder = chat_folder / "audio"
        audio_folder.mkdir(exist_ok=True)
        
        image_folder = chat_folder / "images"
        image_folder.mkdir(exist_ok=True)
        
        return chat_folder
    
    def load_chat(self, chat_name):
        """Load a chat by name"""
        chat_folder = self._ensure_chat_folder(chat_name)
        chat_file = chat_folder / f"{chat_name}.json"
        
        self.current_chat_name = chat_name
        self.current_chat_folder = chat_folder
        
        if chat_file.exists():
            with open(chat_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_chat(self, chat_name, messages):
        """Save chat messages"""
        chat_folder = self._ensure_chat_folder(chat_name)
        chat_file = chat_folder / f"{chat_name}.json"
        
        self.current_chat_name = chat_name
        self.current_chat_folder = chat_folder
        
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
    
    def rename_chat(self, old_name, new_name):
        """Rename a chat and its audio folder"""
        old_folder = self.base_folder / old_name
        new_folder = self.base_folder / new_name
        
        if old_folder.exists() and not new_folder.exists():
            old_folder.rename(new_folder)
            self.current_chat_name = new_name
            self.current_chat_folder = new_folder
            
            # Rename the JSON file
            old_json = new_folder / f"{old_name}.json"
            new_json = new_folder / f"{new_name}.json"
            if old_json.exists():
                old_json.rename(new_json)
            
            return True
        return False
    
    def new_chat(self, chat_name="default"):
        """Create a new chat"""
        chat_folder = self._ensure_chat_folder(chat_name)
        chat_file = chat_folder / f"{chat_name}.json"
        
        # Clear any existing chat file
        if chat_file.exists():
            chat_file.unlink()
        
        self.current_chat_name = chat_name
        self.current_chat_folder = chat_folder
        
        # Create empty chat file
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        return chat_folder
    
    def list_chats(self):
        """List all available chats"""
        chats = []
        for folder in self.base_folder.iterdir():
            if folder.is_dir():
                chats.append(folder.name)
        return sorted(chats)
    
    def get_chat_size(self, chat_name):
        """Get size of chat JSON file only (not audio)"""
        chat_folder = self.base_folder / chat_name
        chat_file = chat_folder / f"{chat_name}.json"
        
        if chat_file.exists():
            return chat_file.stat().st_size
        return 0
    
    def get_all_tts_size(self):
        """Get total size of all TTS files for both servers"""
        total_size = 0
        
        # Ollama TTS
        ollama_tts = Path("tts_audio_ollama")
        if ollama_tts.exists():
            for file in ollama_tts.rglob("*"):
                if file.is_file():
                    total_size += file.stat().st_size
        
        # Llama TTS
        llama_tts = Path("tts_audio_llama")
        if llama_tts.exists():
            for file in llama_tts.rglob("*"):
                if file.is_file():
                    total_size += file.stat().st_size
        
        return total_size
    
    def format_size(self, size_bytes):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def get_current_size_formatted(self):
        """Get formatted size of current chat"""
        if not self.current_chat_name:
            return "0 B"
        size = self.get_chat_size(self.current_chat_name)
        return self.format_size(size)
    
    def get_audio_folder(self):
        """Get path to current chat's audio folder"""
        if not self.current_chat_folder:
            self.load_chat("default")
        return self.current_chat_folder / "audio"
    
    def get_image_folder(self):
        """Get path to current chat's image folder"""
        if not self.current_chat_folder:
            self.load_chat("default")
        return self.current_chat_folder / "images"
    
    def get_chat_file_path(self):
        """Get path to current chat JSON file"""
        if not self.current_chat_folder or not self.current_chat_name:
            return None
        return self.current_chat_folder / f"{self.current_chat_name}.json"
