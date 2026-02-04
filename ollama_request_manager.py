"""
Ollama Request Manager - Global throttling and concurrency control
Prevents multiple concurrent Ollama API requests that spawn excessive runners
"""

import threading
import time
from typing import Callable, Any, Optional
from debug_config import DebugConfig


class OllamaRequestManager:
    """
    Centralized manager for Ollama requests to prevent concurrent API calls.
    Uses a request queue with serialization to ensure only one API call at a time.
    """
    
    # Class-level lock - shared across all instances
    _request_lock = threading.Lock()
    
    # Tracks if a major request (streaming/generation) is in progress
    _active_request = None
    _request_start_time = None
    
    # Queue for pending minor requests (extraction, etc.)
    _pending_requests = []
    
    # Configuration
    MIN_REQUEST_GAP = 0.5  # Minimum gap (seconds) between Ollama requests
    
    @classmethod
    def start_major_request(cls, request_name: str) -> bool:
        """
        Start a major request (streaming generation, non-streaming generation).
        Returns True if allowed, False if another request is already active.
        
        Major requests block all other operations.
        """
        with cls._request_lock:
            if cls._active_request is not None:
                if DebugConfig.chat_enabled:
                    elapsed = time.time() - cls._request_start_time
                    print(f"[OLLAMA-THROTTLE] ⚠️ BLOCKED: Tried to start '{request_name}' but '{cls._active_request}' active ({elapsed:.2f}s)")
                return False
            
            cls._active_request = request_name
            cls._request_start_time = time.time()
            if DebugConfig.chat_enabled:
                print(f"[OLLAMA-THROTTLE] ✓ START major request: {request_name}")
            return True
    
    @classmethod
    def end_major_request(cls, request_name: str) -> None:
        """End a major request and process pending minor requests."""
        with cls._request_lock:
            if cls._active_request == request_name:
                elapsed = time.time() - cls._request_start_time
                cls._active_request = None
                if DebugConfig.chat_enabled:
                    print(f"[OLLAMA-THROTTLE] ✓ END major request: {request_name} ({elapsed:.2f}s)")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[OLLAMA-THROTTLE] ⚠️ end_major_request called for '{request_name}' but active is '{cls._active_request}'")
    
    @classmethod
    def can_start_minor_request(cls, request_name: str, force: bool = False) -> bool:
        """
        Check if a minor request (extraction, etc.) can proceed.
        
        Minor requests wait for major requests to finish + minimum gap.
        If force=True, will return True but log a warning.
        
        Returns: True if allowed, False if blocked.
        """
        with cls._request_lock:
            # If a major request is active, block
            if cls._active_request is not None:
                if DebugConfig.chat_enabled:
                    print(f"[OLLAMA-THROTTLE] ⚠️ BLOCKED minor: '{request_name}' - major request '{cls._active_request}' active")
                return False
            
            # Check minimum gap from last request
            if cls._request_start_time is not None:
                time_since_last = time.time() - cls._request_start_time
                if time_since_last < cls.MIN_REQUEST_GAP:
                    if DebugConfig.chat_enabled:
                        print(f"[OLLAMA-THROTTLE] ⚠️ BLOCKED minor: '{request_name}' - wait {cls.MIN_REQUEST_GAP - time_since_last:.2f}s ({time_since_last:.2f}s elapsed)")
                    return False
            
            if DebugConfig.chat_enabled:
                print(f"[OLLAMA-THROTTLE] ✓ ALLOWED minor: {request_name}")
            return True
    
    @classmethod
    def acquire_minor_request(cls, request_name: str) -> bool:
        """
        Acquire a lock for a minor request. Waits briefly if needed.
        
        Returns True if lock acquired, False if timeout.
        Used by extraction and other secondary operations.
        """
        # Wait up to 2 seconds for the lock to become available
        for attempt in range(20):  # 20 * 0.1s = 2 second timeout
            if cls.can_start_minor_request(request_name):
                with cls._request_lock:
                    # Double-check after acquiring lock
                    if cls._active_request is None:
                        cls._request_start_time = time.time()
                        if DebugConfig.chat_enabled:
                            print(f"[OLLAMA-THROTTLE] 🔒 LOCKED minor: {request_name}")
                        return True
            
            time.sleep(0.1)
        
        if DebugConfig.chat_enabled:
            print(f"[OLLAMA-THROTTLE] ⏱️ TIMEOUT waiting for {request_name}")
        return False
    
    @classmethod
    def release_minor_request(cls, request_name: str) -> None:
        """Release a minor request lock."""
        with cls._request_lock:
            if DebugConfig.chat_enabled:
                print(f"[OLLAMA-THROTTLE] 🔓 UNLOCKED minor: {request_name}")
    
    @classmethod
    def get_status(cls) -> str:
        """Get current request status for debugging."""
        with cls._request_lock:
            if cls._active_request:
                elapsed = time.time() - cls._request_start_time
                return f"Active: {cls._active_request} ({elapsed:.2f}s)"
            else:
                return "Idle"
    
    @classmethod
    def reset(cls) -> None:
        """Reset all state (for testing or shutdown)."""
        with cls._request_lock:
            cls._active_request = None
            cls._request_start_time = None
            cls._pending_requests = []
            if DebugConfig.chat_enabled:
                print("[OLLAMA-THROTTLE] Reset complete")
