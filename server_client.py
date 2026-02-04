"""
Abstract base class for LLM server clients (llama-server, Ollama, etc)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from debug_config import DebugConfig


class ServerClient(ABC):
    """Abstract base class for LLM server clients"""
    
    def __init__(self, server_url: str, timeout: int = 60):
        """Initialize server client
        
        Args:
            server_url: Base URL of the server (e.g., http://localhost:8080)
            timeout: Request timeout in seconds (default 60)
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        # Debug output for timeout configuration
        if DebugConfig.connection_enabled:
            if self.timeout is None:
                print(f"[DEBUG-CLIENT] ServerClient initialized with INFINITE timeout (None)")
            else:
                print(f"[DEBUG-CLIENT] ServerClient initialized with timeout={self.timeout}s")
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if server is reachable
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models
        
        Returns:
            List of model names
        """
        pass
    
    @abstractmethod
    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """Generate text from prompt
        
        Args:
            prompt: The prompt to send
            model: Model name to use
            **kwargs: Additional parameters (temperature, top_p, top_k, n_predict, etc)
        
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def generate_stream(self, prompt: str, model: str, **kwargs):
        """Generate text from prompt with streaming
        
        Args:
            prompt: The prompt to send
            model: Model name to use
            **kwargs: Additional parameters (temperature, top_p, top_k, n_predict, etc)
        
        Yields:
            Text chunks as they arrive
        """
        pass
