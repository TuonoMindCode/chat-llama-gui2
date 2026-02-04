"""
Llama Server API client for interacting with llama-server
"""

import requests
import json
from typing import Dict, Any, Optional, List
from server_client import ServerClient
from debug_config import DebugConfig


class LlamaServerClient(ServerClient):
    """Client for communicating with llama-server (inherits from ServerClient base class)"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080", timeout: int = 60):
        super().__init__(server_url, timeout)
    
    def test_connection(self) -> bool:
        """Test if llama-server is reachable using the /v1/chat/completions endpoint"""
        try:
            # Try the /v1/chat/completions endpoint (OpenAI-compatible format)
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "test"}],
                    "temperature": 0.1,
                    "max_tokens": 10
                },
                timeout=3
            )
            # If we got any response (200, 400, etc), server is reachable
            print(f"[OK] Connected to llama-server at {self.server_url}")
            return True
        except requests.exceptions.Timeout:
            print(f"[WARN] Timeout - server at {self.server_url} is slow to respond")
            return True  # Server is there, just slow
        except requests.exceptions.ConnectionError:
            print(f"[ERR] Cannot reach llama-server at {self.server_url} - server not running (default: 127.0.0.1:8080)")
            return False
        except Exception as e:
            print(f"[WARN] Connection warning: {e}")
            # If we got here, something responded (even if with an error)
            return True
    
    def get_available_models(self) -> List[str]:
        """Get list of available models
        
        Note: llama-server typically runs one model at a time,
        so this returns a generic model name or empty list
        """
        # llama-server doesn't have a direct API to list models
        # It's configured at startup with one model
        return ["default"]
    
    def generate(self, prompt: str, model: str = None, **kwargs) -> str:
        """Generate text from prompt (model parameter ignored for llama-server)
        
        Args:
            prompt: The prompt to send
            model: Ignored (llama-server runs one model)
            **kwargs: Additional parameters:
                - temperature: float
                - top_p: float
                - top_k: int
                - n_predict: int (max_tokens)
                - timeout: int (default self.timeout)
        
        Returns:
            Generated text response
        """
        try:
            # Get timeout from kwargs or use default
            timeout = kwargs.get("timeout", self.timeout)
            
            # Use OpenAI-compatible /v1/chat/completions endpoint
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
                "max_tokens": kwargs.get("n_predict", 128),
                "stop": ["\nUser:", "\nYou:", "\nHuman:", "[INST]", "[/INST]"],
            }
            
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract message from OpenAI-compatible response format
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    return "No response generated"
            else:
                raise Exception(f"Server error: {response.status_code}")
        
        except requests.exceptions.Timeout:
            raise Exception(f"Request timeout - {self.server_url} took too long to respond (>{timeout}s)")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot reach llama-server at {self.server_url}\nMake sure it's running on that address and port (default is localhost:8000)")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")
    
    def generate_with_context(self, messages: List[Dict], model: str = None, **kwargs) -> str:
        """Generate text using conversation history/context (OpenAI-compatible)
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Ignored (llama-server runs one model)
            **kwargs: Additional parameters (system, temperature, etc.)
        
        Returns:
            Generated text response
        """
        try:
            # Get timeout from kwargs or use default
            timeout = kwargs.get("timeout", self.timeout)
            
            # Filter out system messages if present and use as context
            # (llama-server /v1/chat/completions doesn't have a separate system role handling)
            payload = {
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
                "max_tokens": kwargs.get("num_predict", 128),
                "stop": ["\nUser:", "\nYou:", "\nHuman:", "[INST]", "[/INST]"],
            }
            
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract message from OpenAI-compatible response format
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    return "No response generated"
            else:
                raise Exception(f"Server error: {response.status_code}")
        
        except requests.exceptions.Timeout:
            raise Exception(f"Request timeout - {self.server_url} took too long to respond (>{timeout}s)")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Cannot reach llama-server at {self.server_url}\nMake sure it's running on that address and port (default is localhost:8000)")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")
    
    def tokenize(self, text: str) -> Dict[str, Any]:
        """Tokenize text"""
        payload = {"content": text}
        response = requests.post(
            f"{self.server_url}/api/tokenize",
            json=payload,
            timeout=self.timeout
        )
        return response.json()
    
    def get_embeddings(self, text: str) -> Dict[str, Any]:
        """Get embeddings for text"""
        payload = {"content": text}
        response = requests.post(
            f"{self.server_url}/api/embeddings",
            json=payload,
            timeout=self.timeout
        )
        return response.json()
    
    def generate_stream(self, prompt: str, model: str = None, **kwargs):
        """Generate text from prompt with streaming (model parameter ignored for llama-server)
        
        Args:
            prompt: The prompt to send
            model: Ignored (llama-server runs one model)
            **kwargs: Additional parameters
        
        Yields:
            Text chunks as they arrive
        """
        try:
            # Use OpenAI-compatible /v1/chat/completions endpoint with streaming
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,  # Enable streaming
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
                "max_tokens": kwargs.get("n_predict", 128),
                "stop": ["\nUser:", "\nYou:", "\nHuman:", "[INST]", "[/INST]"],
            }
            
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            # OpenAI-compatible SSE format with "data: " prefix
                            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                            if line_str.startswith('data: '):
                                line_str = line_str[6:]  # Remove "data: " prefix
                            
                            # Skip [DONE] marker
                            if line_str.strip() == '[DONE]':
                                continue
                            
                            data = json.loads(line_str)
                            # Extract delta content from OpenAI-compatible format
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    yield chunk
                        except json.JSONDecodeError:
                            # Skip lines that aren't valid JSON
                            continue
            else:
                raise Exception(f"Server error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach llama-server")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")
    
    def generate_stream_with_context(self, messages: List[Dict], model: str, **kwargs):
        """Generate text using conversation history/context with streaming and token counts
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (ignored for llama-server)
            **kwargs: Additional parameters (system, temperature, timeout, etc.)
        
        Yields:
            Text chunks as they arrive from llama-server
            Token info as special marker when done
        """
        try:
            # Get timeout from kwargs or use default
            timeout = kwargs.get("timeout", self.timeout)
            if timeout is None:
                timeout = 86400  # 24 hours - effectively infinite for practical purposes
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Infinite timeout detected - converting None to {timeout}s (24 hours)")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Using finite timeout: {timeout}s")
            
            # Calculate prompt tokens by concatenating all messages and tokenizing
            # This gives us accurate token count for the input
            prompt_text = ""
            for msg in messages:
                prompt_text += msg.get("content", "") + " "
            
            prompt_tokens = 0
            try:
                # Try to get actual token count from llama-server tokenize endpoint
                tokenize_response = requests.post(
                    f"{self.server_url}/tokenize",
                    json={"content": prompt_text},
                    timeout=5
                )
                if tokenize_response.status_code == 200:
                    token_data = tokenize_response.json()
                    prompt_tokens = len(token_data.get("tokens", []))
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-TOKENS] Prompt tokens from tokenize: {prompt_tokens}")
                else:
                    # Fallback: estimate as ~4 chars per token
                    prompt_tokens = len(prompt_text) // 4
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-TOKENS] Prompt tokens (estimated): {prompt_tokens}")
            except Exception as e:
                # Fallback: estimate as ~4 chars per token
                prompt_tokens = len(prompt_text) // 4
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-TOKENS] Prompt tokens (estimated, fallback): {prompt_tokens}")
            
            # Use OpenAI-compatible /v1/chat/completions endpoint with streaming
            payload = {
                "messages": messages,
                "stream": True,  # Enable streaming
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
                "max_tokens": kwargs.get("n_predict", 128),
                "stop": ["\nUser:", "\nYou:", "\nHuman:", "[INST]", "[/INST]"],
            }
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-STREAM] Sending request to: {self.server_url}/v1/chat/completions")
                print(f"[DEBUG-STREAM] Messages: {len(messages)} total")
                print(f"[DEBUG-STREAM] Awaiting llama-server response...")
            
            response = requests.post(
                f"{self.server_url}/v1/chat/completions",
                json=payload,
                timeout=timeout,
                stream=True
            )
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-STREAM] llama-server responded with status: {response.status_code}")
            
            if response.status_code == 200:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Starting to receive streaming chunks...")
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            # OpenAI-compatible SSE format with "data: " prefix
                            line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                            if line_str.startswith('data: '):
                                line_str = line_str[6:]  # Remove "data: " prefix
                            
                            # Skip [DONE] marker but use it to detect end
                            if line_str.strip() == '[DONE]':
                                # End of stream - yield token info
                                # generated_tokens: estimate as ~4 chars per token
                                generated_tokens = len(full_response) // 4
                                token_info = {
                                    "prompt_tokens": prompt_tokens,
                                    "generated_tokens": generated_tokens
                                }
                                print(f"\n[DEBUG-TOKENS] Final response received:")
                                if DebugConfig.chat_enabled:
                                    print(f"[DEBUG-TOKENS] Prompt tokens: {prompt_tokens}")
                                    print(f"[DEBUG-TOKENS] Generated tokens (estimated): {generated_tokens}")
                                    print(f"[DEBUG-TOKENS] Total: {prompt_tokens + generated_tokens}")
                                yield f"__TOKEN_INFO__{token_info}__END_TOKEN_INFO__"
                                continue
                            
                            data = json.loads(line_str)
                            # Extract delta content from OpenAI-compatible format
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                chunk = delta.get("content", "")
                                if chunk:
                                    full_response += chunk
                                    yield chunk
                        except json.JSONDecodeError:
                            # Skip lines that aren't valid JSON
                            continue
            else:
                raise Exception(f"Server error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach llama-server")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")
    
    def chat_stream(self, messages: List[Dict], model: str = None, **kwargs):
        """Alias for generate_stream_with_context for API compatibility with OllamaClient
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (ignored for llama-server, it runs one model)
            **kwargs: Additional parameters (system, temperature, timeout, etc.)
        
        Yields:
            Text chunks as they arrive from llama-server
        """
        # Use generate_stream_with_context which already handles streaming properly
        yield from self.generate_stream_with_context(messages, model or "default", **kwargs)
    
    def chat(self, messages: List[Dict], model: str = None, **kwargs) -> str:
        """Non-streaming chat for API compatibility with OllamaClient
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name (ignored for llama-server)
            **kwargs: Additional parameters (system, temperature, timeout, etc.)
        
        Returns:
            Complete response text
        """
        # Collect all chunks from streaming into one response
        full_response = ""
        for chunk in self.generate_stream_with_context(messages, model or "default", **kwargs):
            # Skip token info markers (they would start with a special format)
            if isinstance(chunk, str) and not chunk.startswith("TOKEN_INFO:"):
                full_response += chunk
        return full_response


# Keep old class name for backwards compatibility
class LlamaClient(LlamaServerClient):
    """Backwards compatibility wrapper for LlamaServerClient"""
    pass
