"""
Response Display Manager - Handles message rendering, token counting, and streaming display
"""

from datetime import datetime
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt5.QtCore import Qt
from settings_manager import load_settings
from settings_saver import get_settings_saver
from chat_manager import ChatManager
from debug_config import DebugConfig
from response_cleaner import ResponseCleaner


class ResponseDisplayManager:
    """Manages display of messages, streaming chunks, and token information"""
    
    def __init__(self, chat_tab):
        """
        Initialize response display manager
        
        Args:
            chat_tab: Parent chat tab instance with message_display widget
        """
        self.chat_tab = chat_tab
        self.message_display = chat_tab.message_display
        self.server_type = chat_tab.server_type
        self.app = chat_tab.app
        self.memory = chat_tab.memory
        self.message_history = chat_tab.message_history
        
        # Hash tracking for duplicate prevention
        self._last_image_trigger_hash = None
        
    def display_message(self, text, is_user=False, timestamp=None):
        """Display message in chat window with timestamp"""
        # Skip completely empty messages
        if not text or not str(text).strip():
            if DebugConfig.chat_message_history:
                print(f"[DEBUG-UI] Skipping empty message (is_user={is_user})")
            return
        
        cursor = self.message_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Use provided timestamp or create new one
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(timestamp, str) and "T" in timestamp:
            # Convert ISO format to YYYY-MM-DD HH:MM:SS
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if is_user:
            # User message - blue
            # Add blank line before message (except for first message)
            if self.message_display.toPlainText():
                if DebugConfig.chat_message_history:
                    print(f"[DEBUG-UI] Adding blank line before user message")
                cursor.insertText("\n")
            else:
                if DebugConfig.chat_message_history:
                    print(f"[DEBUG-UI] First message - no blank line before")
            
            format_obj = QTextCharFormat()
            format_obj.setForeground(QColor("#0066cc"))
            cursor.setCharFormat(format_obj)
            text_to_add = f"[{timestamp}] You: {text}\n"
            if DebugConfig.chat_message_history:
                print(f"[DEBUG-UI] Adding user message: {repr(text_to_add[:50])}")
            cursor.insertText(text_to_add)
        else:
            # Assistant message - using server type instead of "Assistant"
            server_label = self.server_type.upper() if self.server_type != "llama-server" else "LLAMA"
            format_obj = QTextCharFormat()
            format_obj.setForeground(QColor("#009900"))
            cursor.setCharFormat(format_obj)
            cursor.insertText(f"[{timestamp}] {server_label}: ")
            
            # Reset format for message text
            format_obj = QTextCharFormat()
            format_obj.setForeground(QColor("#333333"))
            cursor.setCharFormat(format_obj)
            cursor.insertText(f"{text}\n")
        
        self.message_display.setTextCursor(cursor)
        self.message_display.ensureCursorVisible()
    
    def on_message_chunk(self, chunk):
        """Handle incoming message chunk from streaming response - display word-by-word"""
        # On first chunk, add the server label + timestamp header if not already done
        if not getattr(self, '_streaming_header_added', False):
            self._streaming_header_added = True
            self._streaming_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._streaming_word_buffer = ""
            
            cursor = self.message_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            
            # Add server label with timestamp
            server_label = self.server_type.upper() if self.server_type != "llama-server" else "LLAMA"
            format_obj = QTextCharFormat()
            format_obj.setForeground(QColor("#009900"))
            cursor.setCharFormat(format_obj)
            cursor.insertText(f"[{self._streaming_start_time}] {server_label}: ")
            
            # Reset format for message text (will be black/default)
            format_obj = QTextCharFormat()
            format_obj.setForeground(QColor("#333333"))
            cursor.setCharFormat(format_obj)
            
            self.message_display.setTextCursor(cursor)
        
        # Buffer characters until we have a complete word
        self._streaming_word_buffer += chunk
        
        # Process complete words (separated by spaces or newlines)
        words_to_display = ""
        remaining_buffer = ""
        
        for i, char in enumerate(self._streaming_word_buffer):
            if char in (" ", "\n", "\t"):
                # Found a word boundary - include the whitespace
                words_to_display += self._streaming_word_buffer[:i+1]
                remaining_buffer = self._streaming_word_buffer[i+1:]
                break
        else:
            # No word boundary found yet, keep buffering
            remaining_buffer = self._streaming_word_buffer
            words_to_display = ""
        
        # Display complete words
        if words_to_display:
            cursor = self.message_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            format_obj = QTextCharFormat()
            format_obj.setForeground(QColor("#333333"))
            cursor.setCharFormat(format_obj)
            cursor.insertText(words_to_display)
            self.message_display.setTextCursor(cursor)
        
        # Keep remaining characters in buffer for next chunk
        self._streaming_word_buffer = remaining_buffer
        
        # Auto-scroll to bottom to see latest word
        self.message_display.verticalScrollBar().setValue(
            self.message_display.verticalScrollBar().maximum()
        )
    
    def on_token_info(self, prompt_tokens, generated_tokens):
        """Handle token count information from worker thread"""
        if hasattr(self.app, 'status_panel'):
            self.app.status_panel.set_token_count(prompt_tokens, generated_tokens, self.server_type)
    
    def on_message_received(self, response):
        """Handle received message"""
        if DebugConfig.chat_enabled:
            print(f"[DEBUG-RESPONSE] on_message_received() CALLED with response: {response[:60]}...")
        
        # Clean response to remove hallucinated conversation exchanges
        cleaned_response = ResponseCleaner.clean_response(response)
        if cleaned_response != response:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG-RESPONSE] Response cleaned - before: {len(response)} chars, after: {len(cleaned_response)} chars")
        
        # Store response and timestamp for later use in on_response_generated
        self._last_response = cleaned_response
        self._last_response_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # If streaming was used, use the streaming start time instead
        if hasattr(self, '_streaming_header_added') and self._streaming_header_added:
            self._last_response_timestamp = self._streaming_start_time
        
        # If streaming was used, response was already displayed chunk-by-chunk
        # Just save to history and add empty prompt. If not streaming, display the full response.
        
        timestamp = self._last_response_timestamp
        
        if hasattr(self, '_streaming_header_added') and self._streaming_header_added:
            # Streaming was used - response already displayed
            # Use the streaming start time (when first chunk arrived) for consistency
            
            # Display any remaining buffered word fragments
            if hasattr(self, '_streaming_word_buffer') and self._streaming_word_buffer:
                cursor = self.message_display.textCursor()
                cursor.movePosition(QTextCursor.End)
                format_obj = QTextCharFormat()
                format_obj.setForeground(QColor("#333333"))
                cursor.setCharFormat(format_obj)
                cursor.insertText(self._streaming_word_buffer)
                self.message_display.setTextCursor(cursor)
                self._streaming_word_buffer = ""
            
            # Add newline at the end of the streamed response
            cursor = self.message_display.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText("\n")
            self.message_display.setTextCursor(cursor)
            # Reset streaming flag for next message
            self._streaming_header_added = False
        else:
            # Non-streaming mode - display full response
            self.display_message(cleaned_response, is_user=False, timestamp=timestamp)
        
        # Trigger persistence manager to save
        if hasattr(self.chat_tab, 'persistence_manager'):
            self.chat_tab.persistence_manager.save_message_history()
        
        # Guard against multiple image generation triggers for the same response
        # Store the response hash to detect if we're being called again with the same response
        response_hash = hash(cleaned_response[:100]) if cleaned_response else 0
        if not hasattr(self, '_last_image_trigger_hash') or self._last_image_trigger_hash != response_hash:
            self._last_image_trigger_hash = response_hash
            
            # Check if we should trigger image generation
            if hasattr(self.chat_tab, 'generating_images_checkbox') and self.chat_tab.generating_images_checkbox.isChecked():
                if hasattr(self.chat_tab, 'image_manager'):
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Triggering image generation (hash={response_hash})")
                    self.chat_tab.image_manager.trigger_image_generation_if_needed(cleaned_response, timestamp)
        else:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Skipping image generation - same response hash ({response_hash})")
        
        # Check if we should speak the response
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] ResponseDisplay: Checking TTS - has tts_enabled_checkbox={hasattr(self.chat_tab, 'tts_enabled_checkbox')}, has tts_manager={hasattr(self.chat_tab, 'tts_manager')}")
        if hasattr(self.chat_tab, 'tts_enabled_checkbox') and self.chat_tab.tts_enabled_checkbox.isChecked():
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] ResponseDisplay: TTS checkbox is CHECKED")
            if hasattr(self.chat_tab, 'tts_manager'):
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] ResponseDisplay: Calling tts_manager.speak_response()")
                self.chat_tab.tts_manager.speak_response(cleaned_response, timestamp)
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] ResponseDisplay: ERROR - tts_manager not found!")
        else:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] ResponseDisplay: TTS checkbox NOT checked or attribute missing")
        
        # Show bright green border to signal ready for input
        if hasattr(self.chat_tab, 'update_input_border_state'):
            self.chat_tab.update_input_border_state(bright=True)
    
    def on_error(self, error_msg):
        """Handle error from worker thread"""
        self.display_message(f"[ERROR] {error_msg}", is_user=False)
        self.chat_tab.send_button.setEnabled(True)
        self.chat_tab.progress_bar.setMinimumHeight(0)  # Hide with zero height
        self.chat_tab.progress_bar.setMaximumHeight(0)
        self.chat_tab.progress_bar.setVisible(False)
        self.chat_tab.is_generating = False
        
        # Resume voice listening if it was paused
        if self.chat_tab.voice_input_paused and hasattr(self.chat_tab, 'resume_voice_listening'):
            print("[VOICE_INPUT] LLM error - resuming listening")
            self.chat_tab.resume_voice_listening()
        
        # Update status panel
        if hasattr(self.app, 'status_panel'):
            self.app.status_panel.set_llm_status('idle')
        
        # Update input border - show ready for input
        if hasattr(self.chat_tab, 'update_input_border_state'):
            self.chat_tab.update_input_border_state(bright=True)
    
    def on_generation_finished(self):
        """Handle generation finished"""
        self.chat_tab.is_generating = False
        self.chat_tab.send_button.setEnabled(True)
        self.chat_tab.stop_button.setEnabled(False)
        self.chat_tab.progress_bar.setMinimumHeight(0)  # Hide with zero height
        self.chat_tab.progress_bar.setMaximumHeight(0)
        self.chat_tab.progress_bar.setVisible(False)
        
        # Resume voice listening if it was paused
        if self.chat_tab.voice_input_paused and hasattr(self.chat_tab, 'resume_voice_listening'):
            print("[VOICE_INPUT] ✅ LLM response complete - resuming listening")
            self.chat_tab.resume_voice_listening()
        else:
            if DebugConfig.chat_memory_operations:
                print(f"[VOICE_INPUT] Response finished but voice not paused (paused={self.chat_tab.voice_input_paused})")
        
        # Update status panel
        if hasattr(self.app, 'status_panel'):
            self.app.status_panel.set_llm_status('idle')
        
        # Update input border - show ready for input
        if hasattr(self.chat_tab, 'update_input_border_state'):
            self.chat_tab.update_input_border_state(bright=True)
    
    def load_message_history(self):
        """Load chat history from ChatManager"""
        try:
            chat_manager = ChatManager(self.server_type)
            messages = chat_manager.load_chat(self.chat_tab.current_chat_name)
            
            self.message_history.clear()
            self.message_display.clear()
            
            # Display all messages
            for msg in messages:
                self.display_message(
                    msg.get("content", ""),
                    is_user=msg.get("role") == "user",
                    timestamp=msg.get("timestamp")
                )
                self.message_history.append(msg)
            
            if DebugConfig.chat_message_history:
                print(f"[DEBUG] Loaded {len(messages)} messages from {self.chat_tab.current_chat_name}.json")
        except Exception as e:
            print(f"Error loading message history: {e}")
    
    def save_message_history(self):
        """Save message history to ChatManager"""
        try:
            chat_manager = ChatManager(self.server_type)
            chat_manager.save_chat(self.chat_tab.current_chat_name, self.message_history)
            if DebugConfig.chat_message_history:
                print(f"[DEBUG] Saved {len(self.message_history)} messages to {self.chat_tab.current_chat_name}.json")
        except Exception as e:
            print(f"Error saving history: {e}")
