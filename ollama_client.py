"""
Ollama API client implementation
"""

import requests
import json
from typing import List, Dict, Optional
from server_client import ServerClient
from chat_template_manager import template_manager
from settings_manager import get_setting
from debug_config import DebugConfig

class OllamaClient(ServerClient):
    """Client for Ollama API"""
    
    def test_connection(self) -> bool:
        """Test if Ollama server is reachable"""
        try:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-CONNECTION] Testing Ollama connection to: {self.server_url}/api/tags (timeout={self.timeout}s)")
            response = requests.get(f"{self.server_url}/api/tags", timeout=self.timeout)
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-CONNECTION] Ollama response status: {response.status_code}")
            if response.status_code == 200:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-CONNECTION] Ollama connection successful")
                return True
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-CONNECTION] Ollama connection failed - status code: {response.status_code}")
                return False
        except requests.exceptions.Timeout as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-CONNECTION] Ollama connection timeout: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-CONNECTION] Ollama connection error (can't reach server): {e}")
            return False
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-CONNECTION] Ollama connection error: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama
        
        Returns:
            List of model names
        """
        try:
            response = requests.get(f"{self.server_url}/api/tags", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                return [model["name"] for model in models]
            return []
        except Exception as e:
            print(f"Error fetching Ollama models: {e}")
            return []
    
    def get_loaded_models_info(self) -> Dict:
        """Get information about models currently loaded in Ollama memory
        
        Returns:
            Dict with loaded models info
        """
        try:
            # Try to get PS API which shows loaded models
            response = requests.get(f"{self.server_url}/api/ps", timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                if DebugConfig.chat_memory_operations:
                    print(f"\n[DEBUG-MODELS] ========================================")
                    print(f"[DEBUG-MODELS] Models currently loaded in Ollama memory:")
                
                total_size = 0
                for model in models:
                    model_name = model.get("name", "unknown")
                    size_bytes = model.get("size", 0)
                    size_gb = size_bytes / (1024 * 1024 * 1024)
                    total_size += size_gb
                    expires_at = model.get("expires_at", "unknown")
                    if DebugConfig.chat_memory_operations:
                        print(f"[DEBUG-MODELS]   - {model_name}: {size_gb:.2f} GB (expires: {expires_at})")
                
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-MODELS] Total VRAM used by models: {total_size:.2f} GB")
                    print(f"[DEBUG-MODELS] ========================================\n")
                return data
            else:
                if DebugConfig.chat_memory_operations:
                    print(f"\n[DEBUG-MODELS] Could not query loaded models (status {response.status_code})")
                    print(f"[DEBUG-MODELS] The /api/ps endpoint may not be available in this Ollama version\n")
                return {}
        except requests.exceptions.Timeout:
            if DebugConfig.chat_memory_operations:
                print(f"\n[DEBUG-MODELS] Timeout querying loaded models - Ollama may be slow\n")
            return {}
        except Exception as e:
            print(f"\n[DEBUG-MODELS] Error getting loaded models: {e}\n")
            return {}
    
    def unload_model(self, model: str = None) -> bool:
        """Unload a model from Ollama memory to free up VRAM
        
        Args:
            model: Model name to unload (if None, unloads all models)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if model is None:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-UNLOAD] Unloading all models from Ollama...")
            else:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-UNLOAD] Unloading model: {model}")
            
            # To unload a model, send a request with keep_alive=0
            payload = {
                "model": model if model else "ollama",  # Use any model name to trigger unload
                "keep_alive": 0,  # 0 means unload immediately
                "stream": False,
            }
            
            response = requests.post(
                f"{self.server_url}/api/generate",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-UNLOAD] Successfully triggered model unload")
                # Give it a moment to unload
                import time
                time.sleep(0.5)
                return True
            else:
                if DebugConfig.chat_memory_operations:
                    print(f"[DEBUG-UNLOAD] Unload request failed: {response.status_code}")
                return False
        except Exception as e:
            if DebugConfig.chat_memory_operations:
                print(f"[DEBUG-UNLOAD] Error unloading model: {e}")
            return False
    
    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """Generate text using Ollama
        
        Args:
            prompt: The prompt to send
            model: Model name (e.g., "llama2", "neural-chat")
            **kwargs: Additional parameters:
                - system: str (system prompt/context)
                - temperature: float (default 0.7)
                - top_p: float (default 0.95)
                - top_k: int (default 40)
                - n_predict: int (default 8192) - preferred parameter name
                - num_predict: int (default 8192) - legacy parameter name (falls back to n_predict)
                - timeout: int (default self.timeout)
                - keep_alive: int (model unload timeout in seconds)
        
        Returns:
            Generated text response
        """
        try:
            # Get timeout from kwargs or use default
            timeout = kwargs.get("timeout", self.timeout)
            
            # Get keep_alive timeout setting (unload timeout in seconds)
            # Try n_predict first (new name), fall back to num_predict (old name)
            max_tokens = kwargs.get("n_predict", kwargs.get("num_predict", 8192))
            keep_alive = kwargs.get("keep_alive", 120)  # Default 120 seconds (2 min)
            
            # Ollama parameters mapping
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,  # Non-streaming for simplicity
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
                "num_predict": max_tokens,
                "keep_alive": keep_alive,
            }
            
            # Debug: Print all Ollama request parameters
            if DebugConfig.chat_enabled:
                print(f"\n[DEBUG-OLLAMA-REQUEST] =====================================")
                print(f"[DEBUG-OLLAMA-REQUEST] Model: {payload['model']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Temperature: {payload['temperature']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Top P: {payload['top_p']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Top K: {payload['top_k']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Max Tokens (num_predict): {payload['num_predict']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Keep Alive: {payload['keep_alive']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Streaming: {payload['stream']}")
                print(f"[DEBUG-OLLAMA-REQUEST] =====================================\n")
            
            # Add system prompt if provided
            if "system" in kwargs and kwargs["system"]:
                payload["system"] = kwargs["system"]
                if DebugConfig.system_prompt_enabled:
                    print(f"[DEBUG] Ollama system prompt length: {len(kwargs['system'])} chars")
                    print(f"[DEBUG] Ollama system prompt START: {kwargs['system'][:100]}...")
            
            response = requests.post(
                f"{self.server_url}/api/generate",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "No response generated").strip()
            else:
                raise Exception(f"Server error: {response.status_code}")
        
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach Ollama server")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")
    
    def generate_with_context(self, messages: List[Dict], model: str, **kwargs) -> str:
        """Generate text using conversation history/context
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name
            **kwargs: Additional parameters (system, temperature, etc.)
        
        Returns:
            Generated text response
        """
        # Get selected template from settings (default: "auto")
        selected_template = get_setting("chat_template_selection", "auto")
        
        # Extract system prompt and user message
        system_prompt = kwargs.get("system", "")
        user_message = ""
        
        # Find the last user message
        for msg in reversed(messages):
            if msg.get("role", "").lower() == "user":
                user_message = msg.get("content", "")
                break
        
        # Format based on selected template
        if selected_template == "auto":
            # Auto mode: Build simple prompt from messages
            # Include full conversation but add clear boundary to prevent hallucination
            prompt_parts = []
            
            # Add system prompt if available
            if system_prompt:
                prompt_parts.append(f"{system_prompt}\n\n")
            
            # Add conversation history without explicit "USER:" and "ASSISTANT:" labels
            # This provides context while avoiding the model copying these labels
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    continue  # Already added
                elif role == "user":
                    prompt_parts.append(f"{content}\n\n")
                elif role == "assistant":
                    # Include assistant responses but without role label
                    prompt_parts.append(f"{content}\n\n")
            
            # Add clear boundary marker and response directive
            prompt_parts.append("---\nRespond only with your next message:\n")
            
            full_prompt = "".join(prompt_parts)
        
        else:
            # Template mode: Use template manager to format
            full_prompt = template_manager.format_prompt(
                selected_template,
                system_prompt,
                user_message
            )
            
            if full_prompt is None:
                # Fallback to auto if template failed
                prompt_parts = []
                if system_prompt:
                    prompt_parts.append(f"SYSTEM: {system_prompt}\n")
                for msg in messages:
                    role = msg.get("role", "").lower()
                    content = msg.get("content", "")
                    if role != "system":
                        prompt_parts.append(f"{role.upper()}: {content}\n")
                full_prompt = "".join(prompt_parts)
        
        if DebugConfig.chat_template_formatting:
            print(f"[DEBUG-TEMPLATE] Using template: {selected_template}")
        
        return self.generate(
            full_prompt,
            model=model,
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p", 0.95),
            top_k=kwargs.get("top_k", 40),
            n_predict=kwargs.get("n_predict", 8192),  # Changed from num_predict and 128 to n_predict and 8192
            timeout=kwargs.get("timeout", self.timeout),
            keep_alive=kwargs.get("keep_alive", 120)  # Added keep_alive parameter
        )
    
    def generate_stream(self, prompt: str, model: str, **kwargs):
        """Generate text using Ollama with streaming
        
        Args:
            prompt: The prompt to send
            model: Model name (e.g., "llama2", "neural-chat")
            **kwargs: Additional parameters (timeout, temperature, etc.)
        
        Yields:
            Text chunks as they arrive
        """
        try:
            # Get keep_alive timeout setting (unload timeout in seconds)
            keep_alive = kwargs.get("keep_alive", 120)  # Default 120 seconds (2 min)
            
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,  # Enable streaming
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.95),
                "top_k": kwargs.get("top_k", 40),
                "num_predict": kwargs.get("n_predict", 128),
                "keep_alive": keep_alive,  # Controls model unload timeout
            }
            
            # Debug: Print all Ollama request parameters
            if DebugConfig.chat_enabled:
                print(f"\n[DEBUG-OLLAMA-REQUEST] =====================================")
                print(f"[DEBUG-OLLAMA-REQUEST] Model: {payload['model']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Temperature: {payload['temperature']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Top P: {payload['top_p']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Top K: {payload['top_k']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Max Tokens (num_predict): {payload['num_predict']}")
                print(f"[DEBUG-OLLAMA-REQUEST] Streaming: {payload['stream']}")
                print(f"[DEBUG-OLLAMA-REQUEST] =====================================\n")
            
            # Check what models are currently loaded in Ollama
            self.get_loaded_models_info()
            
            # Use timeout from kwargs if provided, otherwise use instance default
            # For infinite timeout (None), use a very large number (24 hours in seconds)
            timeout = kwargs.get("timeout", self.timeout)
            if timeout is None:
                timeout = 86400  # 24 hours - effectively infinite for practical purposes
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Infinite timeout detected - converting None to {timeout}s (24 hours)")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Using finite timeout: {timeout}s")
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-STREAM] Sending request to: {self.server_url}/api/generate")
                print(f"[DEBUG-STREAM] Prompt length: {len(prompt)} characters")
                print(f"[DEBUG-STREAM] Awaiting Ollama response...")
            
            response = requests.post(
                f"{self.server_url}/api/generate",
                json=payload,
                timeout=timeout,
                stream=True
            )
            
            print(f"[DEBUG-STREAM] Ollama responded with status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"[DEBUG-STREAM] Starting to receive streaming chunks...")
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                            # Yield token counts from final response
                            if data.get("done", False):
                                prompt_count = data.get("prompt_eval_count", 0)
                                generated_count = data.get("eval_count", 0)
                                token_info = {
                                    "prompt_tokens": prompt_count,
                                    "generated_tokens": generated_count
                                }
                                print(f"\n[DEBUG-TOKENS] Final response received:")
                                print(f"[DEBUG-TOKENS] Prompt tokens: {prompt_count}")
                                print(f"[DEBUG-TOKENS] Generated tokens: {generated_count}")
                                print(f"[DEBUG-TOKENS] Total: {prompt_count + generated_count}")
                                yield f"__TOKEN_INFO__{token_info}__END_TOKEN_INFO__"
                        except json.JSONDecodeError:
                            pass  # Skip malformed lines
            else:
                print(f"[DEBUG-STREAM] ERROR: Server error: {response.status_code} - {response.text}")
                raise Exception(f"Server error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach Ollama server")
        except Exception as e:
            raise Exception(f"Error: {str(e)}")
    
    def generate_stream_with_context(self, messages: List[Dict], model: str, **kwargs):
        """Generate text using conversation history/context with streaming
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name
            **kwargs: Additional parameters (system, temperature, timeout, etc.)
        
        Yields:
            Text chunks as they arrive from Ollama
        """
        import time
        start_time = time.time()
        
        # Get selected template from settings (default: "auto")
        selected_template = get_setting("chat_template_selection", "auto")
        
        # Extract system prompt and user message
        system_prompt = kwargs.get("system", "")
        user_message = ""
        
        # Find the last user message
        for msg in reversed(messages):
            if msg.get("role", "").lower() == "user":
                user_message = msg.get("content", "")
                break
        
        # Format based on selected template
        if selected_template == "auto":
            # Auto mode: Build prompt with explicit role labels for clarity
            # This helps model understand conversation structure and respond appropriately
            prompt_parts = []
            
            # Add system prompt if available
            if system_prompt:
                prompt_parts.append(f"{system_prompt}\n\n")
            
            # Add conversation history WITH explicit "User:" and "Assistant:" labels
            # This provides clear context that the model can understand
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    continue  # Already added as system prompt
                elif role == "user":
                    prompt_parts.append(f"User: {content}\n\n")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}\n\n")
            
            # Add response directive
            # This tells the model: respond as Assistant with only the next message
            prompt_parts.append("Assistant:")
            
            full_prompt = "".join(prompt_parts)
            if DebugConfig.chat_template_formatting:
                print(f"[DEBUG-TEMPLATE] Using: auto (with full context and response boundary)")
                print(f"[DEBUG-TEMPLATE] Messages count: {len(messages)}")
                if messages:
                    print(f"[DEBUG-TEMPLATE] Last message: role={messages[-1].get('role')}, content={messages[-1].get('content', '')[:100]}")
                print(f"[DEBUG-TEMPLATE] Full prompt length: {len(full_prompt)} chars")
                print(f"[DEBUG-TEMPLATE] Full prompt (last 400 chars):\n...{full_prompt[-400:]}")
        
        else:
            # Template mode: Use template manager to format
            full_prompt = template_manager.format_prompt(
                selected_template,
                system_prompt,
                user_message
            )
            
            if full_prompt is None:
                # Fallback to auto if template failed
                print(f"[DEBUG-TEMPLATE] Template failed, falling back to auto")
                prompt_parts = []
                if system_prompt:
                    prompt_parts.append(f"SYSTEM: {system_prompt}\n")
                for msg in messages:
                    role = msg.get("role", "").lower()
                    content = msg.get("content", "")
                    if role != "system":
                        prompt_parts.append(f"{role.upper()}: {content}\n")
                full_prompt = "".join(prompt_parts)
        
        print(f"[DEBUG-TEMPLATE] Selected template: {selected_template}")
        print(f"[DEBUG-TEMPLATE] Full prompt (first 300 chars):\n{full_prompt[:300]}...\n")
        template_time = time.time() - start_time
        print(f"[DEBUG-TIMING] Template formatting took: {template_time:.2f}s")
        
        # Use streaming generate with the formatted prompt
        for chunk in self.generate_stream(
            full_prompt,
            model=model,
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p", 0.95),
            top_k=kwargs.get("top_k", 40),
            n_predict=kwargs.get("n_predict", 128),
            timeout=kwargs.get("timeout", self.timeout),
            keep_alive=kwargs.get("keep_alive", 120)
        ):
            yield chunk    
    def chat_stream(self, messages: List[Dict], model: str, **kwargs):
        """Generate text using Ollama's /api/chat endpoint with streaming
        
        Uses Ollama's native chat API with proper role handling and stop sequences
        to prevent hallucination. This is the recommended approach for conversations.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name
            **kwargs: Additional parameters (system, temperature, timeout, etc.)
        
        Yields:
            Text chunks as they arrive from Ollama
        """
        try:
            keep_alive = kwargs.get("keep_alive", 120)
            
            # Filter out system messages from messages list - system goes in separate field
            filtered_messages = []
            system_content = kwargs.get("system", "")
            
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    # Use the first system message found
                    if not system_content:
                        system_content = content
                    continue
                
                # Only add user and assistant messages
                filtered_messages.append({
                    "role": role,
                    "content": content
                })
            
            # Build the messages array with system prompt as first message
            # (Ollama /api/chat expects system as a message role, not top-level field)
            messages_with_system = []
            
            # Add system prompt as first message if provided
            if system_content:
                messages_with_system.append({
                    "role": "system",
                    "content": system_content
                })
            
            # Add all other messages
            messages_with_system.extend(filtered_messages)
            
            # Build the payload for /api/chat
            # Note: All sampling parameters go inside options, not at top level
            payload = {
                "model": model,
                "messages": messages_with_system,
                "stream": True,
                "keep_alive": keep_alive,
                "options": {
                    "temperature": kwargs.get("temperature", 0.9),
                    "top_p": kwargs.get("top_p", 0.99),
                    "top_k": kwargs.get("top_k", 60),
                    "num_predict": kwargs.get("n_predict", 8192),
                    "stop": [
                        "\nUser:", "\nYou:", "\nHuman:",  # Prevent role prefixes
                        "[INST]", "\n[INST]",            # Llama instruction tokens
                        "[/INST]", "\n[/INST]",          # Llama closing tokens
                        "<|user|>", "\n<|user|>"         # Other model formats
                    ]
                }
            }
            
            if DebugConfig.connection_requests:
                print(f"\n[DEBUG-CHAT-API] Using /api/chat endpoint")
                print(f"[DEBUG-CHAT-API] Model: {payload['model']}")
                print(f"[DEBUG-CHAT-API] Messages count: {len(messages_with_system)}")
                print(f"[DEBUG-CHAT-API] Temperature: {payload['options']['temperature']}")
                print(f"[DEBUG-CHAT-API] Top P: {payload['options']['top_p']}")
                print(f"[DEBUG-CHAT-API] Top K: {payload['options']['top_k']}")
                print(f"[DEBUG-CHAT-API] Max Tokens: {payload['options']['num_predict']}")
                print(f"[DEBUG-CHAT-API] Stop sequences: {payload['options']['stop']}")
                print(f"[DEBUG-CHAT-API] =====================================")
            
            # Print the FULL JSON payload being sent to Ollama
            import json as json_module
            payload_json = json_module.dumps(payload, indent=2, ensure_ascii=False)
            if DebugConfig.connection_requests:
                print(f"[DEBUG-CHAT-API-PAYLOAD] Full JSON payload sent to /api/chat:")
                print(payload_json)
                print(f"[DEBUG-CHAT-API-PAYLOAD] =====================================\n")
            
            timeout = kwargs.get("timeout", self.timeout)
            if timeout is None:
                timeout = 86400  # 24 hours
            
            response = requests.post(
                f"{self.server_url}/api/chat",
                json=payload,
                timeout=timeout,
                stream=True
            )
            
            if DebugConfig.connection_responses:
                print(f"[DEBUG-CHAT-API] Ollama responded with status: {response.status_code}")
            
            if response.status_code == 200:
                if DebugConfig.connection_responses:
                    print(f"[DEBUG-CHAT-API] Starting to receive streaming chunks...")
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            chunk = data.get("message", {}).get("content", "")
                            if chunk:
                                full_response += chunk
                                yield chunk
                            
                            # Yield token counts from final response
                            if data.get("done", False):
                                prompt_count = data.get("prompt_eval_count", 0)
                                generated_count = data.get("eval_count", 0)
                                token_info = {
                                    "prompt_tokens": prompt_count,
                                    "generated_tokens": generated_count
                                }
                                if DebugConfig.token_counting_enabled:
                                    print(f"\n[DEBUG-CHAT-TOKENS] Final response received:")
                                    print(f"[DEBUG-CHAT-TOKENS] Prompt tokens: {prompt_count}")
                                    print(f"[DEBUG-CHAT-TOKENS] Generated tokens: {generated_count}")
                                    print(f"[DEBUG-CHAT-TOKENS] Total: {prompt_count + generated_count}")
                                yield f"__TOKEN_INFO__{token_info}__END_TOKEN_INFO__"
                        except json.JSONDecodeError:
                            pass
            else:
                if DebugConfig.connection_responses:
                    print(f"[DEBUG-CHAT-API] ERROR: Server error: {response.status_code} - {response.text}")
                raise Exception(f"Server error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach Ollama server")
        except Exception as e:
            raise Exception(f"Chat stream error: {str(e)}")
    
    def chat(self, messages: List[Dict], model: str, **kwargs) -> str:
        """Generate text using Ollama's /api/chat endpoint (non-streaming)
        
        Uses Ollama's native chat API with proper role handling and stop sequences.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            model: Model name
            **kwargs: Additional parameters (system, temperature, timeout, etc.)
        
        Returns:
            Generated text response
        """
        try:
            keep_alive = kwargs.get("keep_alive", 120)
            
            # Filter out system messages from messages list - system goes in separate field
            filtered_messages = []
            system_content = kwargs.get("system", "")
            
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    if not system_content:
                        system_content = content
                    continue
                
                filtered_messages.append({
                    "role": role,
                    "content": content
                })
            
            # Build the payload for /api/chat
            payload = {
                "model": model,
                "messages": filtered_messages,
                "stream": False,
                "temperature": kwargs.get("temperature", 0.9),
                "top_p": kwargs.get("top_p", 0.99),
                "top_k": kwargs.get("top_k", 60),
                "num_predict": kwargs.get("n_predict", 8192),
                "keep_alive": keep_alive,
                "options": {
                    "stop": ["\nUser:", "\nYou:", "\nHuman:"],
                }
            }
            
            if system_content:
                payload["system"] = system_content
            
            print(f"\n[DEBUG-CHAT] Using /api/chat endpoint (non-streaming)")
            print(f"[DEBUG-CHAT] Messages count: {len(filtered_messages)}")
            
            # Print the FULL JSON payload being sent to Ollama
            import json as json_module
            payload_json = json_module.dumps(payload, indent=2, ensure_ascii=False)
            print(f"[DEBUG-CHAT-PAYLOAD] Full JSON payload sent to Ollama:")
            print(payload_json)
            print(f"[DEBUG-CHAT-PAYLOAD] =====================================")
            
            timeout = kwargs.get("timeout", self.timeout)
            if timeout is None:
                timeout = 86400
            
            response = requests.post(
                f"{self.server_url}/api/chat",
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                raise Exception(f"Server error: {response.status_code} - {response.text}")
        
        except requests.exceptions.Timeout:
            raise Exception("Request timeout - server took too long to respond")
        except requests.exceptions.ConnectionError:
            raise Exception("Connection error - unable to reach Ollama server")
        except Exception as e:
            raise Exception(f"Chat error: {str(e)}")