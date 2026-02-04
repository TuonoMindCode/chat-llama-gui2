"""
Chat worker thread for non-blocking message generation
Supports conversation history and memory context
Supports streaming responses for real-time chat updates
"""

from PyQt5.QtCore import QThread, pyqtSignal
import json
from pathlib import Path
from debug_config import DebugConfig
from ollama_request_manager import OllamaRequestManager
from response_cleaner import ResponseCleaner


class ChatWorkerThread(QThread):
    """Worker thread for sending chat messages without blocking UI"""
    
    message_received = pyqtSignal(str)  # Full response when complete
    message_chunk = pyqtSignal(str)  # Streaming chunk as it arrives
    error_occurred = pyqtSignal(str)
    token_info = pyqtSignal(int, int)  # (prompt_tokens, generated_tokens)
    generation_stopped = pyqtSignal()  # Emitted when generation is stopped by user
    finished = pyqtSignal()
    
    def __init__(self, client, prompt, model, system_prompt, 
                 conversation_history=None, memory_context=None, timeout=120, 
                 enable_streaming=True, temperature=0.9, top_p=0.99, top_k=60, 
                 max_tokens=128, max_context_messages=None, chat_folder=None, prepend_enabled=False, keep_alive=120):
        super().__init__()
        self.client = client
        self.prompt = prompt
        self.model = model
        self.system_prompt = system_prompt
        self.conversation_history = conversation_history or []
        self.memory_context = memory_context or ""
        self.timeout = timeout
        self.keep_alive = keep_alive  # Model unload timeout in seconds
        self.should_stop = False
        self.enable_streaming = enable_streaming
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_tokens = max_tokens
        self.max_context_messages = max_context_messages  # NEW: limit conversation history to this many messages
        self.chat_folder = chat_folder or Path("saved_chats_ollama/default")  # NEW: Store chat folder for debug file
        self.prepend_enabled = prepend_enabled  # NEW: Whether to prepend system prompt to user message
        
        if DebugConfig.chat_enabled:
            print(f"[DEBUG-WORKER] ChatWorkerThread initialized with chat_folder: {self.chat_folder}")
    
    def run(self):
        try:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-STREAM] Worker thread started")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Timeout received in worker: {self.timeout} (type: {type(self.timeout).__name__})")
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-WORKER-RUN] ===== WORKER RUN STARTED - conversation_history has {len(self.conversation_history)} messages")
            
            # Always build messages array (even if conversation_history is empty)
            # An empty list [] is valid - it means first message with no conversation history
            # Build messages array with memory context prepended
            messages = []
            
            # Add memory context as a system message if available
            if self.memory_context:
                messages.append({
                    "role": "system",
                    "content": f"Previous conversation context:\n{self.memory_context}"
                })
            
            # Add conversation history (limited by max_context_messages if set)
            history_to_send = self.conversation_history
            if self.max_context_messages is not None and self.max_context_messages > 0:
                # Limit to the last N messages
                history_to_send = self.conversation_history[-self.max_context_messages:]
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-LIMIT] Limiting conversation history: {len(self.conversation_history)} messages → {len(history_to_send)} messages (max={self.max_context_messages})")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-LIMIT] Using all {len(self.conversation_history)} messages (no limit set)")
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-CONVERSATION] conversation_history has {len(self.conversation_history)} messages")
                if self.conversation_history:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-CONVERSATION] Last message: {self.conversation_history[-1].get('role')}: {self.conversation_history[-1].get('content', '')[:50]}")
            
            messages.extend(history_to_send)
            
            # Add system prompt as first message for Llama-server (OpenAI-compatible format)
            # Ollama will also receive it this way but primarily uses the system parameter
            if self.system_prompt:
                # Insert system message at the beginning (after any memory context)
                system_message_index = 1 if messages and messages[0].get("role") == "system" else 0
                messages.insert(system_message_index, {
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # Prepend critical system instructions to the user message
            # (Workaround for Ollama models that don't respect system prompt)
            user_message_content = self.prompt
            if self.prepend_enabled and self.system_prompt:
                # Extract just the critical instructions from system prompt
                # Focus on time and behavior instructions that must be followed
                critical_section = self._extract_critical_instructions(self.system_prompt)
                if critical_section:
                    user_message_content = f"{critical_section}\n\nUser message: {self.prompt}"
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-WORKER] Prepended critical instructions to user message")
            elif DebugConfig.chat_enabled and self.system_prompt:
                print(f"[DEBUG-WORKER] Prepend disabled (prepend_enabled={self.prepend_enabled})")
            
            # Add current message
            messages.append({
                "role": "user",
                "content": user_message_content
            })
            
            # ALWAYS use streaming if enabled and client supports it - even for first message
            # This ensures n_predict and other parameters are properly passed
            # Use the new chat_stream method which uses Ollama's /api/chat endpoint
            if self.enable_streaming and hasattr(self.client, 'chat_stream'):
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Using STREAMING mode (enable_streaming={self.enable_streaming})")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-WORKER-RUN] ===== ABOUT TO ACQUIRE MAJOR REQUEST LOCK FOR STREAMING")
                # Acquire major request lock for streaming
                if OllamaRequestManager.start_major_request("streaming_generation"):
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-WORKER-RUN] ===== LOCK ACQUIRED, CALLING _handle_streaming_response")
                    try:
                        self._handle_streaming_response(messages)
                    finally:
                        OllamaRequestManager.end_major_request("streaming_generation")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-WORKER-RUN] ===== STREAMING RESPONSE COMPLETED")
                else:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-WORKER-RUN] ===== LOCK NOT ACQUIRED - SERVER BUSY")
                    self.error_occurred.emit("Ollama server busy - another request in progress")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Using NON-STREAMING mode (enable_streaming={self.enable_streaming}, has_method={hasattr(self.client, 'chat_stream')})")
                
                # Save system + user prompt to debug file (same as streaming path)
                self._save_prompt_debug(messages)
                
                # Acquire major request lock for generation
                if OllamaRequestManager.start_major_request("generation"):
                    try:
                        # Use non-streaming chat endpoint with proper Ollama API
                        response = self.client.chat(
                            messages,
                            model=self.model,
                            system=self.system_prompt,
                            temperature=self.temperature,
                            top_p=self.top_p,
                            top_k=self.top_k,
                            n_predict=self.max_tokens,
                            timeout=self.timeout,
                            keep_alive=self.keep_alive
                        )
                        if response:
                            # Clean response before emitting
                            cleaned_response = ResponseCleaner.clean_response(response)
                            self.message_received.emit(cleaned_response)
                        else:
                            self.error_occurred.emit("No response from model")
                    finally:
                        OllamaRequestManager.end_major_request("generation")
                else:
                    self.error_occurred.emit("Ollama server busy - another request in progress")
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()
    
    def _handle_streaming_response(self, messages):
        """Handle streaming response from Ollama"""
        try:
            full_response = ""
            prompt_tokens = 0
            generated_tokens = 0
            if DebugConfig.connection_requests:
                print(f"[DEBUG-STREAM] Starting streaming response with timeout={self.timeout}")
            
            # Save system + user prompt to debug file
            self._save_prompt_debug(messages)
            
            if DebugConfig.connection_requests:
                print(f"[DEBUG-STREAM] About to call chat_stream with timeout={self.timeout}s and keep_alive={self.keep_alive}s")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] ChatWorkerThread.max_tokens = {self.max_tokens} (n_predict)")
            
            # Get streaming generator with LLM parameters using Ollama's /api/chat endpoint
            for chunk in self.client.chat_stream(
                messages,
                model=self.model,
                system=self.system_prompt,
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                n_predict=self.max_tokens,
                timeout=self.timeout,  # Pass timeout to streaming
                keep_alive=self.keep_alive  # Pass model unload timeout to streaming
            ):
                if self.should_stop:
                    if DebugConfig.connection_requests:
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG-STREAM] Streaming stopped by user")
                    self.generation_stopped.emit()
                    break
                
                if chunk:
                    # Check if this is token info message
                    if "__TOKEN_INFO__" in chunk:
                        # Extract token info
                        try:
                            import ast
                            start_idx = chunk.find("{")
                            end_idx = chunk.find("}", start_idx) + 1
                            if start_idx >= 0 and end_idx > start_idx:
                                token_dict_str = chunk[start_idx:end_idx]
                                token_dict = ast.literal_eval(token_dict_str)
                                prompt_tokens = token_dict.get("prompt_tokens", 0)
                                generated_tokens = token_dict.get("generated_tokens", 0)
                                if DebugConfig.token_count_details:
                                    print(f"[DEBUG-STREAM] Token counts: prompt={prompt_tokens}, generated={generated_tokens}")
                                # Emit token counts
                                self.token_info.emit(prompt_tokens, generated_tokens)
                        except Exception as e:
                            if DebugConfig.connection_requests:
                                print(f"[DEBUG-STREAM] Error parsing token info: {e}")
                    else:
                        # Regular message chunk
                        full_response += chunk
                        # Emit each chunk for real-time display
                        self.message_chunk.emit(chunk)
            
            if DebugConfig.connection_requests:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Streaming complete. Total response: {len(full_response)} chars")
            
            # Model unload timeout is now handled by qt_chat_tab_base.py after response completes
            # via on_response_generated() -> _start_model_unload_timer()
            # This respects the user's configured timeout setting (immediate, 5/15/30 min, or never)
            
            # Emit full response when done - after cleaning
            if full_response:
                # Clean response before emitting
                cleaned_response = ResponseCleaner.clean_response(full_response)
                self.message_received.emit(cleaned_response)
            else:
                self.error_occurred.emit("No response from model")
        except Exception as e:
            if DebugConfig.connection_requests:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-STREAM] Error during streaming: {str(e)}")
            self.error_occurred.emit(f"Streaming error: {str(e)}")
    
    def _save_prompt_debug(self, messages):
        """Save the actual payload being sent to Ollama for debugging"""
        try:
            from pathlib import Path
            import json as json_module
            
            # Build the messages array for /api/chat payload
            messages_for_debug = []
            conversation_context = ""  # Extract memory/semantic search results
            system_already_added = False
            
            # Process all incoming messages
            for msg in messages:
                role = msg.get("role", "").lower()
                content = msg.get("content", "")
                
                # Capture memory context but don't include in messages array
                if role == "system" and "Previous conversation context" in content:
                    # Extract just the context part (remove the prefix)
                    conversation_context = content.replace("Previous conversation context:\n", "").strip()
                    continue
                
                # Track if we already have a system message
                if role == "system":
                    system_already_added = True
                
                messages_for_debug.append({
                    "role": role,
                    "content": content
                })
            
            # If no system message was in the incoming messages, add it from self
            # (This handles cases where system prompt wasn't included in messages)
            if not system_already_added and self.system_prompt:
                # Insert system message at the beginning
                messages_for_debug.insert(0, {
                    "role": "system",
                    "content": self.system_prompt
                })
            
            # Build the debug file to match the actual /api/chat payload structure
            debug_data = {
                "model": self.model,
                "messages": messages_for_debug,
                "stream": True,
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "num_predict": self.max_tokens,
                "keep_alive": self.keep_alive,
                "options": {
                    "stop": ["\nUser:", "\nYou:", "\nHuman:"]
                }
            }
            
            # Add conversation_context field showing what was extracted from memory/semantic search
            if conversation_context:
                debug_data["conversation_context"] = conversation_context
            
            # Save to debug file (in current chat folder, not always default)
            debug_folder = Path(self.chat_folder)

            debug_folder.mkdir(parents=True, exist_ok=True)
            
            debug_file = debug_folder / "system_user_prompt_debug.json"
            
            import json
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, ensure_ascii=False)
            
            # Get file size
            file_size_kb = debug_file.stat().st_size / 1024
            if DebugConfig.token_count_details:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-PROMPT] Chat folder: {self.chat_folder}")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-PROMPT] Debug file path: {debug_file}")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-PROMPT] Saved actual /api/chat payload to: {debug_file} ({file_size_kb:.1f} KB)")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG-PROMPT] Messages count: {len(debug_data['messages'])}, Model: {debug_data['model']}")
            
        except Exception as e:
            if DebugConfig.token_counting_enabled:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-PROMPT] Error saving prompt debug: {e}")
            self.error_occurred.emit(f"Streaming error: {str(e)}")
    
    def _extract_critical_instructions(self, system_prompt):
        """
        Extract critical instructions from system prompt that must be followed.
        This is a workaround for Ollama models that don't respect the system prompt.
        We extract the most important parts and prepend them to the user message.
        """
        if not system_prompt:
            return ""
        
        # Look for the critical section (marked with [IMPORTANT, [TEMPORAL CONTEXT, or NEVER]
        lines = system_prompt.split('\n')
        critical_lines = []
        capture = False
        
        for i, line in enumerate(lines):
            # Start capturing at IMPORTANT, TEMPORAL CONTEXT, or NEVER markers
            if '[IMPORTANT' in line or '[TEMPORAL CONTEXT' in line or 'NEVER' in line:
                capture = True
            
            if capture:
                # Stop before the persona/role description starts (check for various patterns)
                if i > 0 and ('Persona:' in line or 'Voice +' in line or 'User Information' in line):
                    # Don't include this line, we've reached the role definition
                    break
                critical_lines.append(line)
        
        # If nothing captured with markers, just take first few critical lines
        if not critical_lines and len(lines) > 0:
            # At minimum, include first 2-3 lines which often contain critical instructions
            for i in range(min(3, len(lines))):
                if 'NEVER' in lines[i] or 'IMPORTANT' in lines[i] or '[' in lines[i]:
                    critical_lines.append(lines[i])
        
        critical_text = '\n'.join(critical_lines).strip()
        return critical_text if critical_text else ""
