"""
Chat Memory Integration Helper
Integrates conversation memory with existing chat managers and clients
"""

from pathlib import Path
from settings_manager import load_settings, get_setting
from conversation_memory import (
    OllamaConversationMemory, 
    LlamaServerConversationMemory
)
from debug_config import DebugConfig


class MemoryIntegration:
    """Helper to integrate memory system with chat clients"""
    
    def __init__(self, ollama_chat_name: str = "default", llama_chat_name: str = "default"):
        self.settings = load_settings()
        self.ollama_memory = None
        self.llama_memory = None
        self.ollama_chat_name = ollama_chat_name
        self.llama_chat_name = llama_chat_name
        self._init_memory_systems()
    
    def _init_memory_systems(self):
        """Initialize memory systems based on settings"""
        
        # Initialize Ollama memory if enabled
        if self.settings.get("ollama_memory_enabled", True):
            self.ollama_memory = OllamaConversationMemory(
                session_id="ollama_default",
                ollama_url=self.settings.get("ollama_url", "http://localhost:11434"),
                enable_nomic=self.settings.get("nomic_ollama_enabled", False),
                max_context_messages=self.settings.get("ollama_max_context_messages", 20),
                semantic_search_limit=self.settings.get("ollama_semantic_search_limit", 5),
                enable_memory=True
            )
            
            # Load existing history from the active chat folder
            ollama_chat_file = Path("saved_chats_ollama") / self.ollama_chat_name / f"{self.ollama_chat_name}.json"
            if ollama_chat_file.exists():
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Loading Ollama memory from: {ollama_chat_file}")
                self.ollama_memory.load_from_file(str(ollama_chat_file))
            else:
                # Fallback to old root location for backward compatibility
                ollama_history = Path("chat_history_ollama.json")
                if ollama_history.exists():
                    if DebugConfig.chat_memory_operations:
                        print(f"[DEBUG-MEMORY] Loading Ollama memory from legacy location: {ollama_history}")
                    self.ollama_memory.load_from_file(str(ollama_history))
        
        # Initialize Llama memory if enabled
        if self.settings.get("llama_memory_enabled", True):
            self.llama_memory = LlamaServerConversationMemory(
                session_id="llama_default",
                llama_url=self.settings.get("llama_url", "http://localhost:8000"),
                enable_nomic=self.settings.get("nomic_llama_enabled", False),
                ollama_url=self.settings.get("ollama_url", "http://localhost:11434"),  # For embeddings
                max_context_messages=self.settings.get("llama_max_context_messages", 20),
                semantic_search_limit=self.settings.get("llama_semantic_search_limit", 5),
                enable_memory=True
            )
            
            # Load existing history from the active chat folder
            llama_chat_file = Path("saved_chats_llama_server") / self.llama_chat_name / f"{self.llama_chat_name}.json"
            if llama_chat_file.exists():
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Loading Llama memory from: {llama_chat_file}")
                self.llama_memory.load_from_file(str(llama_chat_file))
            else:
                # Fallback to old root location for backward compatibility
                llama_history = Path("chat_history_llama.json")
                if llama_history.exists():
                    if DebugConfig.chat_memory_operations:
                        print(f"[DEBUG-MEMORY] Loading Llama memory from legacy location: {llama_history}")
                    self.llama_memory.load_from_file(str(llama_history))
    
    def get_ollama_memory(self) -> OllamaConversationMemory:
        """Get Ollama memory system"""
        return self.ollama_memory
    
    def get_llama_memory(self) -> LlamaServerConversationMemory:
        """Get Llama memory system"""
        return self.llama_memory
    
    def set_ollama_chat_name(self, chat_name: str):
        """Update Ollama chat name and reload memory from new chat file"""
        self.ollama_chat_name = chat_name
        if self.ollama_memory:
            # Reload memory from the new chat file
            ollama_chat_file = Path("saved_chats_ollama") / chat_name / f"{chat_name}.json"
            if ollama_chat_file.exists():
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Switching Ollama memory to: {ollama_chat_file}")
                self.ollama_memory.load_from_file(str(ollama_chat_file))
            else:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Ollama chat file not found: {ollama_chat_file}")
                # Clear memory if file doesn't exist
                self.ollama_memory.messages = []
    
    def set_llama_chat_name(self, chat_name: str):
        """Update Llama chat name and reload memory from new chat file"""
        self.llama_chat_name = chat_name
        if self.llama_memory:
            # Reload memory from the new chat file
            llama_chat_file = Path("saved_chats_llama_server") / chat_name / f"{chat_name}.json"
            if llama_chat_file.exists():
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Switching Llama memory to: {llama_chat_file}")
                self.llama_memory.load_from_file(str(llama_chat_file))
            else:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Llama chat file not found: {llama_chat_file}")
                # Clear memory if file doesn't exist
                self.llama_memory.messages = []
    
    def add_ollama_message(self, role: str, content: str):
        """Add message to Ollama memory"""
        if self.ollama_memory:
            self.ollama_memory.add_message(role, content)
    
    def add_llama_message(self, role: str, content: str):
        """Add message to Llama memory"""
        if self.llama_memory:
            self.llama_memory.add_message(role, content)
    
    def get_ollama_context(self, user_query: str) -> str:
        """Get conversation context for Ollama"""
        if self.ollama_memory:
            return self.ollama_memory.get_context_for_prompt(user_query)
        return ""
    
    def get_llama_context(self, user_query: str) -> str:
        """Get conversation context for Llama"""
        if self.llama_memory:
            return self.llama_memory.get_context_for_prompt(user_query)
        return ""
    
    def get_ollama_personal_facts(self, enabled_categories: list = None) -> str:
        """Get personal facts from Ollama memory with caching support"""
        # Check if nomic long term memory is enabled
        if not self.settings.get("nomic_ollama_enabled", True):
            return ""
        
        if self.ollama_memory:
            # Get enabled categories from settings or use parameter
            if enabled_categories is None:
                categories = self.settings.get("memory_track_categories", 
                                              ["name", "job", "pet", "family", "location", "age"])
            else:
                categories = enabled_categories
            
            # Get custom keywords from settings
            custom_keywords = self.settings.get("memory_custom_keywords", "")
            
            # Get cache mode and max scan messages
            fact_file_enabled = self.settings.get("nomic_ollama_fact_file_enabled", True)
            max_scan_messages = self.settings.get("nomic_ollama_max_scan_messages", 50)
            
            # Determine cache filepath based on mode
            cache_filepath = None
            if fact_file_enabled:
                # Per-chat fact file - searches only current chat's memory
                chat_dir = f"saved_chats_ollama/{self.ollama_chat_name}"
                cache_filepath = f"{chat_dir}/facts.json"
            # If disabled, cache_filepath remains None
            
            # Extract facts with caching
            return self.ollama_memory.extract_personal_facts_with_cache(
                cache_filepath=cache_filepath,
                max_scan_messages=max_scan_messages,
                enabled_categories=categories,
                custom_keywords=custom_keywords
            )
        return ""
    
    def get_llama_personal_facts(self, enabled_categories: list = None) -> str:
        """Get personal facts from Llama memory with caching support"""
        # Check if nomic long term memory is enabled
        if not self.settings.get("nomic_llama_enabled", True):
            return ""
        
        if self.llama_memory:
            # Get enabled categories from settings or use parameter
            if enabled_categories is None:
                categories = self.settings.get("memory_track_categories", 
                                              ["name", "job", "pet", "family", "location", "age"])
            else:
                categories = enabled_categories
            
            # Get custom keywords from settings
            custom_keywords = self.settings.get("memory_custom_keywords", "")
            
            # Get cache mode and max scan messages
            fact_file_enabled = self.settings.get("nomic_llama_fact_file_enabled", True)
            max_scan_messages = self.settings.get("nomic_llama_max_scan_messages", 50)
            
            # Determine cache filepath based on mode
            cache_filepath = None
            if fact_file_enabled:
                # Per-chat fact file - searches only current chat's memory
                chat_dir = f"saved_chats_llama_server/{self.llama_chat_name}"
                cache_filepath = f"{chat_dir}/facts.json"
            # If disabled, cache_filepath remains None
            
            # Extract facts with caching
            return self.llama_memory.extract_personal_facts_with_cache(
                cache_filepath=cache_filepath,
                max_scan_messages=max_scan_messages,
                enabled_categories=categories,
                custom_keywords=custom_keywords
            )
        return ""
    
    def save_ollama_memory(self):
        """Save Ollama memory to file"""
        if self.ollama_memory:
            self.ollama_memory.save_to_file("chat_history_ollama.json")
    
    def save_llama_memory(self):
        """Save Llama memory to file"""
        if self.llama_memory:
            self.llama_memory.save_to_file("chat_history_llama.json")
    
    def save_all(self):
        """Save all memory systems"""
        self.save_ollama_memory()
        self.save_llama_memory()
    
    def get_ollama_stats(self) -> dict:
        """Get Ollama memory statistics"""
        if self.ollama_memory:
            return self.ollama_memory.get_stats()
        return {}
    
    def get_llama_stats(self) -> dict:
        """Get Llama memory statistics"""
        if self.llama_memory:
            return self.llama_memory.get_stats()
        return {}
    
    def clear_ollama(self):
        """Clear Ollama memory"""
        if self.ollama_memory:
            self.ollama_memory.clear()
    
    def clear_llama(self):
        """Clear Llama memory"""
        if self.llama_memory:
            self.llama_memory.clear()
    
    def reload_from_settings(self):
        """Reload memory systems from updated settings"""
        self.settings = load_settings()
        self._init_memory_systems()
