"""
Chat Persistence Manager - Handles chat loading, saving, file management, and cleanup
"""

import shutil
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from settings_manager import load_settings
from settings_saver import get_settings_saver
from chat_manager import ChatManager
from debug_config import DebugConfig


class ChatPersistenceManager:
    """Manages chat persistence - loading, saving, and deletion"""
    
    def __init__(self, chat_tab):
        """
        Initialize chat persistence manager
        
        Args:
            chat_tab: Parent chat tab instance
        """
        self.chat_tab = chat_tab
        self.message_history = chat_tab.message_history
        self.message_display = chat_tab.message_display
        # NOTE: Do NOT cache current_chat_name, audio_folder, or image_folder
        # Always use chat_tab.current_chat_name, chat_tab.audio_folder, chat_tab.image_folder
        # These are now dynamic properties that return current chat's values
        self.server_type = chat_tab.server_type
        self.chat_manager = ChatManager(self.server_type)
        self.app = chat_tab.app
        self.memory = chat_tab.memory
    
    def _update_chat_folders(self):
        """Update chat context in ChatManager - chat_tab folders are now dynamic properties"""
        try:
            chat_name = self.chat_tab.current_chat_name
            
            # Load the chat in ChatManager to set the current_chat_folder context
            # This ensures that chat_tab.audio_folder and chat_tab.image_folder properties
            # will return the correct folders (they dynamically call chat_manager.load_chat)
            self.chat_manager.load_chat(chat_name)
            
            # Get the folders for logging/verification
            audio_folder = self.chat_manager.get_audio_folder()
            image_folder = self.chat_manager.get_image_folder()
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Chat folders updated for '{chat_name}':")
                print(f"  Image folder: {image_folder}")
                print(f"  Audio folder: {audio_folder}")
        except Exception as e:
            print(f"[DEBUG] Error updating chat folders: {e}")
    
    def _save_last_chat_to_settings(self):
        """Save current chat name to settings for restoration on next app start"""
        try:
            chat_key = f"last_used_{self.server_type}_chat"
            saver = get_settings_saver()
            saver.set(chat_key, self.chat_tab.current_chat_name)
            saver.save()
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Saved last used chat: {self.chat_tab.current_chat_name}")
        except Exception as e:
            print(f"[DEBUG] Error saving last chat: {e}")
    
    def save_message_history(self):
        """Save message history to ChatManager"""
        try:
            self.chat_manager.save_chat(self.chat_tab.current_chat_name, self.message_history)
            if DebugConfig.chat_message_history:
                print(f"[DEBUG] Saved {len(self.message_history)} messages to {self.chat_tab.current_chat_name}.json")
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def save_chat_as_dialog(self):
        """Save chat with a new name"""
        self.save_message_history()
        self.chat_manager.save_chat(self.chat_tab.current_chat_name, self.message_history)
        chat_name = self.chat_tab.current_chat_name or "default"
        QMessageBox.information(self.chat_tab, "Chat Saved", f"Chat saved as '{chat_name}")
    
    def load_message_history(self):
        """Load chat history from ChatManager"""
        try:
            messages = self.chat_manager.load_chat(self.chat_tab.current_chat_name)
            
            self.message_history.clear()
            self.message_display.clear()
            
            # Display all messages using response manager if available
            for msg in messages:
                if hasattr(self.chat_tab, 'response_manager'):
                    self.chat_tab.response_manager.display_message(
                        msg.get("content", ""),
                        is_user=msg.get("role") == "user",
                        timestamp=msg.get("timestamp")
                    )
                self.message_history.append(msg)
            
            if DebugConfig.chat_message_history:
                print(f"[DEBUG] Loaded {len(messages)} messages from {self.chat_tab.current_chat_name}.json")
        except Exception as e:
            print(f"Error loading message history: {e}")
    
    def load_timestamp_audio_files(self):
        """Scan audio folder, map filenames to timestamps"""
        try:
            self.chat_tab.timestamp_audio = {}
            
            # Use current chat's folder from chat_tab, not cached
            current_audio_folder = self.chat_tab.audio_folder
            if not current_audio_folder or not current_audio_folder.exists():
                return
            
            for audio_file in current_audio_folder.glob("*.wav"):
                # Filename format: HH-MM-SS_tts.wav -> extract timestamp
                filename = audio_file.stem  # Remove .wav extension
                # Split on _tts to get the timestamp part
                if "_tts" in filename:
                    timestamp_part = filename.split("_tts")[0]
                    # Convert HH-MM-SS back to HH:MM:SS
                    timestamp = timestamp_part.replace("-", ":", 2)  # Replace first 2 hyphens
                    self.chat_tab.timestamp_audio[timestamp] = str(audio_file)
                    
            if DebugConfig.tts_operations:
                print(f"[DEBUG] Loaded {len(self.chat_tab.timestamp_audio)} audio files")
        except Exception as e:
            print(f"Error loading timestamp audio files: {e}")
    
    def clear_chat(self):
        """Clear all chat messages and TTS files"""
        reply = QMessageBox.question(
            self.chat_tab,
            "Clear Chat",
            f"Are you sure you want to clear all {self.server_type} chat history?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.message_history.clear()
            self.message_display.clear()
            self.save_message_history()
            QMessageBox.information(self.chat_tab, "Success", "Chat cleared")
    
    def update_chat_info_display(self):
        """Update chat info label with file sizes"""
        if not hasattr(self.chat_tab, 'chat_info_label'):
            return
        
        try:
            # Ensure ChatManager is pointing to current chat
            self.chat_manager.load_chat(self.chat_tab.current_chat_name)
            
            # Calculate JSON file size using ChatManager's method
            json_size = 0
            json_file = self.chat_manager.get_chat_file_path()
            if json_file and json_file.exists():
                json_size = json_file.stat().st_size
            
            # Get audio folder from ChatManager (ensures correct chat context)
            audio_size = 0
            current_audio_folder = self.chat_manager.get_audio_folder()
            if current_audio_folder and current_audio_folder.exists():
                for audio_file in current_audio_folder.glob("*"):
                    if audio_file.is_file():
                        audio_size += audio_file.stat().st_size
            
            # Get image folder from ChatManager (ensures correct chat context)
            image_size = 0
            current_image_folder = self.chat_manager.get_image_folder()
            if current_image_folder and current_image_folder.exists():
                for img_file in current_image_folder.rglob("*"):  # Use rglob to get all files recursively
                    if img_file.is_file():
                        image_size += img_file.stat().st_size
            
            # Format sizes
            def format_size(size_bytes):
                """Format bytes to human readable size"""
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size_bytes < 1024:
                        return f"{size_bytes:.1f}{unit}"
                    size_bytes /= 1024
                return f"{size_bytes:.1f}GB"
            
            # Update label
            json_str = format_size(json_size)
            audio_str = format_size(audio_size)
            image_str = format_size(image_size)
            
            label_text = f"📄 {self.chat_tab.current_chat_name}.json  |  JSON: {json_str}  |  Audio: {audio_str}  |  Images: {image_str}"
            self.chat_tab.chat_info_label.setText(label_text)
            
        except Exception as e:
            print(f"[DEBUG] Error updating chat info: {e}")
            # Fallback to simple label
            self.chat_tab.chat_info_label.setText(f"📄 {self.chat_tab.current_chat_name}.json")
    
    def delete_chat_with_confirmation(self):
        """Delete chat, images, and audio with double confirmation"""
        try:
            # First confirmation dialog
            reply1 = QMessageBox.question(
                self.chat_tab,
                "Delete Chat Session",
                f"This will delete EVERYTHING for this chat session:\n\n"
                f"• All messages\n"
                f"• All generated images\n"
                f"• All audio files\n\n"
                f"Are you sure you want to delete?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply1 != QMessageBox.Yes:
                return
            
            # Calculate file sizes
            try:
                # Calculate image size - use current chat's folder from chat_tab, not cached
                image_size_mb = 0
                current_image_folder = self.chat_tab.image_folder
                if current_image_folder and current_image_folder.exists():
                    for img_file in current_image_folder.rglob("*"):  # Use rglob to get all files recursively
                        if img_file.is_file():
                            image_size_mb += img_file.stat().st_size
                    image_size_mb = image_size_mb / (1024 * 1024)  # Convert to MB
                
                # Calculate audio size - use current chat's folder from chat_tab, not cached
                audio_size_mb = 0
                current_audio_folder = self.chat_tab.audio_folder
                if current_audio_folder and current_audio_folder.exists():
                    for audio_file in current_audio_folder.glob("*"):
                        if audio_file.is_file():
                            audio_size_mb += audio_file.stat().st_size
                    audio_size_mb = audio_size_mb / (1024 * 1024)  # Convert to MB
            except:
                image_size_mb = 0
                audio_size_mb = 0
            
            # Second confirmation with file sizes
            reply2 = QMessageBox.question(
                self.chat_tab,
                "Final Confirmation - Delete Everything",
                f"Are you REALLY REALLY sure you want to delete all files for this session?\n\n"
                f"📁 Chat Files: {self.chat_tab.current_chat_name}.json\n"
                f"🖼️ Images: {image_size_mb:.2f} MB\n"
                f"🔊 Audio Files: {audio_size_mb:.2f} MB\n\n"
                f"Total: {(image_size_mb + audio_size_mb):.2f} MB\n\n"
                f"This action CANNOT be undone!",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply2 != QMessageBox.Yes:
                return
            
            # Delete the files
            deleted_items = []
            
            try:
                # Delete chat message file using ChatManager's method
                chat_json = self.chat_manager.get_chat_file_path()
                if chat_json and chat_json.exists():
                    chat_json.unlink()
                    deleted_items.append("Chat JSON file")
                    print(f"[DEBUG] Deleted chat JSON: {chat_json}")
            except Exception as e:
                print(f"[DEBUG] Error deleting chat file: {e}")
            
            try:
                # Delete images folder - use current chat's folder from chat_tab, not cached
                current_image_folder = self.chat_tab.image_folder
                if current_image_folder and current_image_folder.exists():
                    shutil.rmtree(current_image_folder)
                    deleted_items.append(f"Images folder ({image_size_mb:.2f} MB)")
            except Exception as e:
                print(f"[DEBUG] Error deleting images: {e}")
            
            try:
                # Delete audio folder - use current chat's folder from chat_tab, not cached
                current_audio_folder = self.chat_tab.audio_folder
                if current_audio_folder and current_audio_folder.exists():
                    shutil.rmtree(current_audio_folder)
                    deleted_items.append(f"Audio folder ({audio_size_mb:.2f} MB)")
            except Exception as e:
                print(f"[DEBUG] Error deleting audio: {e}")
            
            # Clear UI
            self.message_history.clear()
            self.message_display.clear()
            self.chat_tab.image_label.setText("(No images yet)")
            
            # Update file sizes display after deletion
            self.update_chat_info_display()
            
            # Show success message
            deleted_text = "\\n".join(deleted_items) if deleted_items else "No files found to delete"
            QMessageBox.information(
                self.chat_tab,
                "Deletion Complete",
                f"Successfully deleted:\\n{deleted_text}"
            )
            
        except Exception as e:
            QMessageBox.critical(self.chat_tab, "Error", f"Error during deletion: {str(e)}")
            print(f"[DEBUG] Error in delete_chat_with_confirmation: {e}")
            import traceback
            traceback.print_exc()
    
    def load_chat_dialog(self):
        """Load saved chat from list"""
        try:
            chat_list = self.chat_manager.list_chats()
            
            if not chat_list:
                QMessageBox.information(self.chat_tab, "No Chats", f"No saved {self.server_type} chats found")
                return
            
            # Sort chat names
            chat_list.sort()
            
            # Show selection dialog
            chat_name, ok = QInputDialog.getItem(
                self.chat_tab,
                "Load Chat",
                f"Select a {self.server_type} chat to load:",
                chat_list,
                0,
                False
            )
            
            if not ok or not chat_name:
                return
            
            # Save current chat first
            self.save_message_history()
            
            # Load new chat
            self.current_chat_name = chat_name
            self.chat_tab.current_chat_name = chat_name
            self.chat_manager = ChatManager(self.server_type)
            
            # UPDATE FOLDERS TO NEW CHAT
            self._update_chat_folders()
            
            # Save this chat as the last used one
            self._save_last_chat_to_settings()
            
            # Clear and reload images for loaded chat
            if hasattr(self.chat_tab, 'current_image_list'):
                self.chat_tab.current_image_list = []
                self.chat_tab.current_image_index = 0
            if hasattr(self.chat_tab, 'image_manager'):
                self.chat_tab.image_manager.load_chat_images()
            
            # Update memory if available
            if self.memory:
                try:
                    if self.server_type == "ollama":
                        self.memory.set_ollama_chat_name(chat_name)
                    else:
                        self.memory.set_llama_chat_name(chat_name)
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Updated {self.server_type} chat context to: {chat_name}")
                except Exception as e:
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Error updating chat context: {e}")
            
            self.load_message_history()
            self.load_timestamp_audio_files()
            self.update_chat_info_display()
            # NOTE: update_chat_info_display() already sets the label with full info including sizes
            # Do NOT overwrite it here
            
            QMessageBox.information(self.chat_tab, "Chat Loaded", f"Loaded chat: {chat_name}")
            
        except Exception as e:
            QMessageBox.critical(self.chat_tab, "Error", f"Error loading chat: {e}")
            print(f"[DEBUG] Error in load_chat_dialog: {e}")
    
    def new_chat_dialog(self):
        """Create new chat"""
        try:
            # First, save current chat
            self.save_message_history()
            
            # Prompt for new chat name
            chat_name, ok = QInputDialog.getText(
                self.chat_tab,
                "New Chat",
                f"Enter name for new {self.server_type} chat:",
                text="default"
            )
            
            if not ok or not chat_name:
                return
            
            # Create new chat
            self.current_chat_name = chat_name
            self.chat_tab.current_chat_name = chat_name
            self.chat_manager = ChatManager(self.server_type)
            
            # UPDATE FOLDERS TO NEW CHAT
            self._update_chat_folders()
            
            # Save this chat as the last used one
            self._save_last_chat_to_settings()
            
            # Clear UI
            self.message_history.clear()
            self.message_display.clear()
            
            # Clear and reload images for new chat
            if hasattr(self.chat_tab, 'current_image_list'):
                self.chat_tab.current_image_list = []
                self.chat_tab.current_image_index = 0
            if hasattr(self.chat_tab, 'image_manager'):
                self.chat_tab.image_manager.load_chat_images()
            
            # Update memory if available
            if self.memory:
                try:
                    if self.server_type == "ollama":
                        self.memory.set_ollama_chat_name(chat_name)
                    else:
                        self.memory.set_llama_chat_name(chat_name)
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Updated {self.server_type} chat context to: {chat_name}")
                except Exception as e:
                    if DebugConfig.chat_memory_operations:
                        print(f"[MEMORY] Error updating chat context: {e}")
            
            self.load_timestamp_audio_files()
            self.update_chat_info_display()
            # NOTE: update_chat_info_display() already sets the label with full info including sizes
            # Do NOT overwrite it here
            
            QMessageBox.information(self.chat_tab, "New Chat", f"Created new chat: {chat_name}")
            
        except Exception as e:
            QMessageBox.critical(self.chat_tab, "Error", f"Error creating new chat: {e}")
            print(f"[DEBUG] Error in new_chat_dialog: {e}")
