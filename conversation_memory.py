"""
Conversation Memory System with Semantic Search
Supports both Ollama and Llama-server with nomic-embed-text-v1.5 embeddings

IMPORTANT: Embeddings ALWAYS use Ollama
- Llama-server doesn't support embeddings, only chat endpoints
- When using Llama-server for chat, embeddings are fetched from Ollama
- This allows running both servers in parallel: Llama-server for chat, Ollama for embeddings
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
from debug_config import DebugConfig

class Message:
    """Represents a single message in conversation"""
    def __init__(self, role: str, content: str, embedding: Optional[List[float]] = None):
        self.role = role  # "user" or "assistant"
        self.content = content
        self.embedding = embedding
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "embedding": self.embedding,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data):
        # Handle both old format (sender) and new format (role)
        role = data.get("role") or data.get("sender")
        # Map old "You"/"Assistant" to new "user"/"assistant"
        if role == "You":
            role = "user"
        elif role == "Assistant":
            role = "assistant"
        
        content = data.get("content", "")
        msg = cls(role, content, data.get("embedding"))
        msg.timestamp = data.get("timestamp", datetime.now().isoformat())
        return msg


class ConversationMemory:
    """
    Base conversation memory class with semantic search using nomic-embed-text-v1.5
    """
    
    def __init__(self, 
                 session_id: str = "default",
                 max_context_messages: int = 20,
                 semantic_search_limit: int = 5,
                 enable_memory: bool = True):
        """
        Initialize conversation memory.
        
        Args:
            session_id: Unique identifier for this conversation session
            max_context_messages: How many recent messages to include in context
            semantic_search_limit: How many semantically similar facts to retrieve
            enable_memory: Whether memory is enabled
        """
        self.session_id = session_id
        self.max_context_messages = max_context_messages
        self.semantic_search_limit = semantic_search_limit
        self.enable_memory = enable_memory
        self.messages: List[Message] = []
        self.embedder = None
        
    def set_embedder(self, embedder):
        """Set the embedder (should be OllamaEmbedder or LlamaServerEmbedder)"""
        self.embedder = embedder
    
    def add_message(self, role: str, content: str, embedding: Optional[List[float]] = None):
        """Add a message to memory, optionally with pre-computed embedding"""
        if not self.enable_memory:
            return
        
        # Compute embedding if not provided
        if embedding is None and self.embedder:
            embedding = self.embedder.embed(content)
        
        message = Message(role, content, embedding)
        self.messages.append(message)
    
    def get_context_for_prompt(self, user_query: str) -> str:
        """
        Get conversation context for the LLM prompt.
        Includes: recent messages + semantically relevant facts.
        
        Args:
            user_query: Current user message to base semantic search on
            
        Returns:
            Formatted context string for LLM
        """
        if not self.enable_memory or not self.messages:
            return ""
        
        context_parts = []
        
        # Get recent messages (last N messages)
        recent_messages = self.messages[-self.max_context_messages:]
        
        # Get semantically similar messages (for facts)
        relevant_messages = self._semantic_search(user_query, limit=self.semantic_search_limit)
        
        # Combine both (avoid duplicates)
        all_relevant = recent_messages.copy()
        recent_indices = set(self.messages.index(msg) for msg in recent_messages)
        
        for msg in relevant_messages:
            if msg not in all_relevant and self.messages.index(msg) not in recent_indices:
                all_relevant.append(msg)
        
        # Format as context
        if all_relevant:
            context_parts.append("## Conversation Context:")
            for msg in all_relevant:
                prefix = "User:" if msg.role == "user" else "Assistant:"
                context_parts.append(f"{prefix} {msg.content}")
        
        return "\n".join(context_parts)
    
    def _semantic_search(self, query: str, limit: int = 5) -> List[Message]:
        """
        Search for semantically similar messages in conversation history.
        
        Args:
            query: Query text to search for
            limit: Maximum number of results
            
        Returns:
            List of most similar messages
        """
        if not self.embedder or not self.messages:
            return []
        
        # Embed the query
        query_embedding = self.embedder.embed(query)
        if query_embedding is None:
            return []
        
        # Calculate similarity scores
        similarities = []
        for msg in self.messages:
            if msg.embedding is not None:
                # Cosine similarity
                similarity = self._cosine_similarity(query_embedding, msg.embedding)
                similarities.append((msg, similarity))
        
        # Sort by similarity and return top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [msg for msg, _ in similarities[:limit]]
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        arr1 = np.array(vec1)
        arr2 = np.array(vec2)
        
        dot_product = np.dot(arr1, arr2)
        norm1 = np.linalg.norm(arr1)
        norm2 = np.linalg.norm(arr2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def save_to_file(self, filepath: str):
        """Save conversation to JSON file"""
        data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(self.messages),
            "messages": [msg.to_dict() for msg in self.messages]
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        if DebugConfig.chat_memory_operations:
            if DebugConfig.chat_memory_operations:
                print(f"[MEMORY] Saved {len(self.messages)} messages to {filepath}")
    
    def load_from_file(self, filepath: str):
        """Load conversation from JSON file"""
        file_path = Path(filepath)
        if not file_path.exists():
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-FILE] File not found: {filepath}")
            return False
        
        # Check file size and modification time
        file_size = file_path.stat().st_size
        import time
        mod_time = time.ctime(file_path.stat().st_mtime)
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-FILE] Loading from: {filepath}")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-FILE] File size: {file_size} bytes | Modified: {mod_time}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both old format (list) and new format (dict with "messages" key)
        if isinstance(data, list):
            # Old format: just a list of messages
            messages_data = data
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-FILE] Format detected: OLD (array)")
        elif isinstance(data, dict):
            # New format: dict with "messages" key
            messages_data = data.get("messages", [])
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-FILE] Format detected: NEW (dict with 'messages' key)")
        else:
            messages_data = []
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-FILE] Format unknown, using empty list")
        
        self.messages = [Message.from_dict(msg) for msg in messages_data]
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-FILE] Loaded {len(self.messages)} messages from {filepath}")
        
        # Show first and last message content
        if self.messages and DebugConfig.chat_memory_operations:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-FILE] First message: {self.messages[0].content[:50]}...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-FILE] Last message: {self.messages[-1].content[:50]}...")
        
        return True
    
    def save_facts_cache(self, facts_dict: Dict, cache_filepath: str):
        """Save extracted facts to cache file next to chat file
        
        Args:
            facts_dict: Dictionary with extracted facts
            cache_filepath: Path to facts.json file
        """
        try:
            cache_path = Path(cache_filepath)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_filepath, 'w', encoding='utf-8') as f:
                json.dump(facts_dict, f, indent=2, ensure_ascii=False)
            
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-CACHE] Saved facts cache to: {cache_filepath}")
            return True
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-CACHE] Failed to save facts cache: {e}")
            return False
    
    def load_facts_cache(self, cache_filepath: str) -> Optional[Dict]:
        """Load cached facts from file
        
        Args:
            cache_filepath: Path to facts.json file
            
        Returns:
            Dictionary with cached facts, or None if not found/invalid
        """
        cache_path = Path(cache_filepath)
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                facts = json.load(f)
            
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-CACHE] Loaded facts cache from: {cache_filepath}")
            return facts
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-CACHE] Failed to load facts cache: {e}")
            return None
    
    def clear(self):
        """Clear all messages from memory"""
        self.messages = []
        if DebugConfig.chat_memory_operations:
            if DebugConfig.chat_memory_operations:
                print(f"[MEMORY] Conversation cleared ({self.session_id})")
    
    def get_full_history(self) -> List[Dict]:
        """Get full message history as list of dicts (for API calls)"""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in self.messages
        ]
    
    def extract_personal_facts_with_cache(self, cache_filepath: str = None, max_scan_messages: int = 50,
                                         enabled_categories: List[str] = None, 
                                         custom_keywords: str = None) -> str:
        """Extract personal facts with smart cache invalidation
        
        Args:
            cache_filepath: Path to facts.json cache file (beside chat file)
            max_scan_messages: Max recent messages to scan (0 = scan all)
            enabled_categories: Categories to track
            custom_keywords: Custom keywords to track
            
        Returns:
            Formatted string of personal facts
        """
        # Try to load cached facts first
        if cache_filepath:
            cached_facts = self.load_facts_cache(cache_filepath)
            if cached_facts:
                # Check if cache is still valid (no new messages since last extraction)
                last_scanned_idx = cached_facts.get('last_scanned_message_index', 0)
                current_msg_count = len(self.messages)
                
                # If no new messages added, use cached facts
                if last_scanned_idx >= current_msg_count:
                    facts_list = []
                    for category, value in cached_facts.items():
                        if value and category not in ['last_updated', 'last_scanned_message_index']:
                            facts_list.append(f"{category}: {value}")
                    
                    if facts_list:
                        if DebugConfig.chat_memory_operations:
                            print(f"[DEBUG-CACHE] Using cached facts for [nomic] (message count: {current_msg_count}, cached at: {last_scanned_idx})")
                        return " | ".join(facts_list)
                else:
                    # New messages added since cache - invalidate and re-extract
                    new_msg_count = current_msg_count - last_scanned_idx
                    if DebugConfig.chat_memory_operations:
                        print(f"[DEBUG-CACHE] Cache invalidated: {new_msg_count} new messages found (had {last_scanned_idx}, now {current_msg_count})")
        
        # Cache doesn't exist, is empty, or is stale - extract fresh facts
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-CACHE] Extracting fresh facts from messages")
        
        # If max_scan_messages is 0, scan all messages
        if max_scan_messages == 0:
            scan_messages = self.messages
        else:
            # Only scan the newest N messages
            scan_messages = self.messages[-max_scan_messages:] if self.messages else []
        
        # Extract facts with category mapping (returns dict of category -> value)
        extracted_facts_dict = self.extract_personal_facts_with_categories(
            enabled_categories=enabled_categories,
            custom_keywords=custom_keywords,
            messages_to_scan=scan_messages
        )
        
        # Also get the formatted text version for display
        extracted_facts_text = self.extract_personal_facts(
            enabled_categories=enabled_categories,
            custom_keywords=custom_keywords,
            messages_to_scan=scan_messages
        )
        
        # Save to cache if cache_filepath provided
        if cache_filepath and extracted_facts_dict:
            # Build facts_dict with all possible fields (defaults + custom keywords)
            facts_dict = {}
            
            # Add default categories
            default_categories = enabled_categories or ['name', 'job', 'pet', 'family', 'location', 'age']
            for category in default_categories:
                facts_dict[category] = ""
            
            # Add custom keywords
            if custom_keywords and custom_keywords.strip():
                import re
                for item in re.split(r'[,\n]', custom_keywords):
                    item = item.strip()
                    if item and len(item) > 1:  # Skip empty and single char items
                        facts_dict[item.lower()] = ""
            
            # Populate with extracted facts
            for key, value in extracted_facts_dict.items():
                if key in facts_dict or key.lower() in facts_dict:
                    # Use lowercase key for matching
                    facts_dict[key.lower()] = value
            
            # Remove empty fields before saving (only keep populated ones)
            facts_dict_filtered = {k: v for k, v in facts_dict.items() if v}
            
            # Always add metadata
            facts_dict_filtered["last_updated"] = datetime.now().isoformat()
            facts_dict_filtered["last_scanned_message_index"] = len(self.messages)
            
            self.save_facts_cache(facts_dict_filtered, cache_filepath)
        
        return extracted_facts_text
    
    def extract_personal_facts(self, enabled_categories: List[str] = None, custom_keywords: str = None,
                              messages_to_scan: List[Message] = None) -> str:
        """Extract key personal facts that should always be available
        
        Looks for messages containing personal information keywords
        and returns them formatted for always-on inclusion.
        
        Args:
            enabled_categories: List of category names to search for.
                              If None, uses defaults: name, job, pet, family, location, age
            custom_keywords: Custom keywords string (comma or newline separated)
                           Example: "my hobby:, interested in:, my project:"
            messages_to_scan: Specific messages to scan (if None, uses last 200)
        
        Returns:
            Formatted string of personal facts
        """
        if not self.messages:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-MEMORY] No messages loaded, returning empty facts")
            return ""
        
        # Use provided messages_to_scan or default to last 200
        if messages_to_scan is None:
            messages_to_scan = self.messages[-200:] if len(self.messages) > 200 else self.messages
        
        if DebugConfig.chat_memory_operations:
            print(f"\n[DEBUG-MEMORY] ===== STARTING PERSONAL FACTS EXTRACTION =====")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Total messages in memory: {len(self.messages)}")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Scanning: {len(messages_to_scan)} messages")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Message list details:")
            for i, msg in enumerate(messages_to_scan[-5:]):  # Show last 5 messages being scanned
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-MEMORY]   [{i}] ({msg.role}): {msg.content[:60]}...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] ========================================\n")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Extracting personal facts from {len(messages_to_scan)} messages")
        
        # Define keyword mappings for each category
        category_keywords = {
            'name': ['my name', 'call me', 'i am', "i'm", 'name is', "i'm named", "i'm alex", "name's", 'alex', 'my name is'],
            'job': ['my job', 'work as', 'profession', 'career', 'i work', 'employed', 'work for'],
            'pet': ['my dog', 'my pet', 'my cat', 'my rabbit', 'my bird', 'i have a dog', 'i have a cat', 'north', 'named north'],
            'family': ['my family', 'my wife', 'my husband', 'my kids', 'my children', 'my brother', 'my sister', 'my parent'],
            'location': ['i live', 'from', 'born', 'city', 'state', 'country', 'located', 'live in'],
            'age': ['age', 'years old', 'i am [0-9]+ years old', 'born in', 'im 35', 'i am 35', '35 years', 'i am'],
            'interests': ['i like', 'i love', 'my hobby', 'into', 'interested in', 'passionate about'],
            'education': ['graduated', 'studied', 'university', 'college', 'school', 'degree']
        }
        
        # Use defaults if no categories specified
        if enabled_categories is None:
            enabled_categories = ['name', 'job', 'pet', 'family', 'location', 'age']
        
        # Collect keywords from enabled categories
        personal_keywords = []
        for category in enabled_categories:
            if category in category_keywords:
                personal_keywords.extend(category_keywords[category])
        
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-MEMORY] Enabled categories: {enabled_categories}")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Searching for keywords: {personal_keywords}")
        
        # Add custom keywords if provided
        if custom_keywords and custom_keywords.strip():
            # Parse custom keywords: split by comma or newline
            custom_list = []
            # Split by both comma and newline
            import re
            for item in re.split(r'[,\n]', custom_keywords):
                item = item.strip()
                if item and len(item) > 1:  # Skip empty and single char items
                    custom_list.append(item.lower())
            personal_keywords.extend(custom_list)
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-MEMORY] Added custom keywords: {custom_list}")
        
        facts = []
        
        # Search messages for personal info in REVERSE order (newest first)
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-MEMORY] Searching {len(messages_to_scan)} messages...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Checking in REVERSE order (newest first)...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] User messages to scan:")
            user_messages = [m for m in messages_to_scan if m.role == "user"]
            for i, um in enumerate(user_messages[-10:]):  # Show last 10 user messages
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-MEMORY]   User msg {i}: '{um.content[:80]}...'")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-MEMORY] Processing user messages (newest first)...\n")
        
        for msg in reversed(messages_to_scan):  # REVERSE ORDER: newest first
            if msg.role == "user":  # Only from user messages
                msg_lower = msg.content.lower()
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MEMORY] Checking user message: '{msg.content[:100]}...'")
                
                # Split message into lines and check each line separately
                lines = msg.content.split('\n')
                message_has_match = False
                
                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped:  # Skip empty lines
                        continue
                    
                    line_lower = line_stripped.lower()
                    
                    # Check if this specific line matches any keyword
                    if any(keyword in line_lower for keyword in personal_keywords):
                        if DebugConfig.chat_memory_operations:
                            print(f"[DEBUG-MEMORY] ✓ MATCH FOUND in line: '{line_stripped}'")
                        # Keep short lines (< 150 chars) for facts
                        if len(line_stripped) < 150:
                            facts.append(line_stripped)
                            message_has_match = True
                            if DebugConfig.chat_memory_operations:
                                print(f"[DEBUG-MEMORY] ✓ Added to facts (length: {len(line_stripped)})")
                
                if not message_has_match and DebugConfig.chat_memory_operations:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-MEMORY] ✗ No keyword match in any line")
        
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-MEMORY] Found {len(facts)} matching facts")
        
        # Return last 5 unique facts
        unique_facts = list(dict.fromkeys(facts))[-5:]
        
        if not unique_facts:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-MEMORY] No unique facts to return")
            return ""
        
        result = "User's personal facts:\n" + "\n".join(f"- {fact}" for fact in unique_facts)
        if DebugConfig.chat_memory_operations:
            print(f"[DEBUG-MEMORY] Returning facts: {result}")
        return result
    
    def extract_personal_facts_with_categories(self, enabled_categories: List[str] = None, 
                                               custom_keywords: str = None,
                                               messages_to_scan: List[Message] = None) -> Dict[str, str]:
        """Extract personal facts mapped to their categories/keywords
        
        Returns a dictionary mapping category/keyword -> matched fact value
        This is used for saving to facts.json with proper categorization.
        Extracts only the sentence/line containing the keyword, not the whole message.
        
        Args:
            enabled_categories: List of category names to search for
            custom_keywords: Custom keywords string (comma or newline separated)
            messages_to_scan: Specific messages to scan
            
        Returns:
            Dictionary of {category/keyword: fact_value}
        """
        if not self.messages:
            return {}
        
        # Use provided messages_to_scan or default to last 200
        if messages_to_scan is None:
            messages_to_scan = self.messages[-200:] if len(self.messages) > 200 else self.messages
        
        # Define keyword mappings for each category
        category_keywords = {
            'name': ['my name', 'call me', 'i am', "i'm", 'name is', "i'm named", 'my name is'],
            'job': ['my job', 'work as', 'profession', 'career', 'i work', 'employed', 'work for'],
            'pet': ['my dog', 'my pet', 'my cat', 'my rabbit', 'my bird', 'i have a dog', 'i have a cat'],
            'family': ['my family', 'my wife', 'my husband', 'my kids', 'my children', 'my brother', 'my sister', 'my parent'],
            'location': ['i live', 'from', 'born', 'city', 'state', 'country', 'located', 'live in'],
            'age': ['age', 'years old', 'i am', 'born in'],
        }
        
        # Use defaults if no categories specified
        if enabled_categories is None:
            enabled_categories = ['name', 'job', 'pet', 'family', 'location', 'age']
        
        # Build keyword -> category mapping (for reverse lookup)
        keyword_to_category = {}
        for category in enabled_categories:
            if category in category_keywords:
                for keyword in category_keywords[category]:
                    keyword_to_category[keyword.lower()] = category
        
        # Add custom keywords (they map to themselves as category)
        if custom_keywords and custom_keywords.strip():
            import re
            for item in re.split(r'[,\n]', custom_keywords):
                item = item.strip()
                if item and len(item) > 1:
                    keyword_to_category[item.lower()] = item.lower()
        
        facts_dict = {}
        
        # Search messages for personal info (newest first)
        for msg in reversed(messages_to_scan):
            if msg.role == "user":
                msg_lower = msg.content.lower()
                
                # Split message into lines and check each line separately
                lines = msg.content.split('\n')
                
                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped:  # Skip empty lines
                        continue
                    
                    line_lower = line_stripped.lower()
                    
                    # Check each keyword to see if it matches this line
                    for keyword, category in keyword_to_category.items():
                        if keyword in line_lower:
                            # Only keep if line is short enough to be a fact (< 150 chars)
                            if len(line_stripped) < 150 and category not in facts_dict:
                                facts_dict[category] = line_stripped
                                break  # Only use first matching keyword per line
        
        return facts_dict
    
    def get_stats(self) -> Dict:
        """Get memory statistics"""
        user_msgs = sum(1 for msg in self.messages if msg.role == "user")
        assistant_msgs = sum(1 for msg in self.messages if msg.role == "assistant")
        embedded_msgs = sum(1 for msg in self.messages if msg.embedding is not None)
        
        return {
            "total_messages": len(self.messages),
            "user_messages": user_msgs,
            "assistant_messages": assistant_msgs,
            "embedded_messages": embedded_msgs,
            "session_id": self.session_id,
            "memory_enabled": self.enable_memory
        }


class OllamaEmbedder:
    """Generates embeddings using Ollama with nomic-embed-text-v1.5"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.model_name = f"{model}:v1.5"  # Specify version
    
    def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding for text"""
        try:
            import requests
            
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model_name, "prompt": text},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("embedding")
            else:
                print(f"[EMBED] Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"[EMBED] Failed to embed: {e}")
            return None


class LlamaServerEmbedder:
    """
    DEPRECATED - Not currently used
    Llama-server does NOT support embeddings endpoints.
    This class is kept for reference only.
    
    All embeddings are handled by OllamaEmbedder even when using Llama-server for chat.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def embed(self, text: str) -> Optional[List[float]]:
        """Get embedding for text"""
        try:
            import requests
            
            response = requests.post(
                f"{self.base_url}/v1/embeddings",
                json={
                    "input": text,
                    "model": "nomic-embed-text-v1.5"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    return data["data"][0]["embedding"]
            else:
                print(f"[EMBED] Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"[EMBED] Failed to embed: {e}")
            return None


class OllamaConversationMemory(ConversationMemory):
    """Conversation memory specialized for Ollama"""
    
    def __init__(self, 
                 session_id: str = "ollama_session",
                 ollama_url: str = "http://localhost:11434",
                 enable_nomic: bool = True,
                 **kwargs):
        super().__init__(session_id, **kwargs)
        # Only create embedder if nomic is enabled
        if enable_nomic:
            self.embedder = OllamaEmbedder(base_url=ollama_url)
        else:
            self.embedder = None
    
    def get_conversation_file(self) -> Path:
        """Get path to save conversation"""
        return Path.cwd() / "chat_history_ollama.json"


class LlamaServerConversationMemory(ConversationMemory):
    """Conversation memory specialized for Llama Server"""
    
    def __init__(self, 
                 session_id: str = "llama_session",
                 llama_url: str = "http://localhost:8000",
                 enable_nomic: bool = True,
                 ollama_url: str = "http://localhost:11434",
                 **kwargs):
        super().__init__(session_id, **kwargs)
        # IMPORTANT: Always use Ollama for embeddings (nomic-embed-text)
        # Llama-server does NOT support embeddings
        # This allows using Llama-server for chat while Ollama handles embeddings
        if enable_nomic:
            self.embedder = OllamaEmbedder(base_url=ollama_url)
        else:
            self.embedder = None
    
    def get_conversation_file(self) -> Path:
        """Get path to save conversation"""
        return Path.cwd() / "chat_history_llama.json"
