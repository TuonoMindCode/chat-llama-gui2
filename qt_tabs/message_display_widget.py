"""
Message display widget with clickable timestamps for audio and image interaction
"""
# pylint: disable=no-name-in-module

import re
from pathlib import Path

from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from debug_config import DebugConfig


class ClickableTextEdit(QTextEdit):
    """Custom text edit that detects clicks on timestamps to play audio"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent  # Reference to QtBaseChatTab parent
        self.timestamp_audio = {}  # Maps timestamp to audio file path
        self.timestamp_image = {}  # Maps timestamp to image file path
        self.setReadOnly(True)
    
    def mousePressEvent(self, event):
        """Handle mouse press to detect timestamp clicks"""
        if event.button() == Qt.LeftButton:
            # Get the text position
            cursor = self.cursorForPosition(event.pos())
            block = cursor.block()
            block_text = block.text()
            pos_in_block = cursor.positionInBlock()
            
            # Look for timestamp pattern [YYYY-MM-DD HH:MM:SS]
            timestamp_pattern = r'\[(\d{4})-(\d{2})-(\d{2})\s(\d{2}):(\d{2}):(\d{2})\]'
            
            for match in re.finditer(timestamp_pattern, block_text):
                start, end = match.span()
                if start <= pos_in_block <= end:
                    timestamp = match.group(0)  # e.g., "[2026-01-03 15:24:24]"
                    self.on_timestamp_clicked(timestamp)
                    return
        
        super().mousePressEvent(event)
    
    def on_timestamp_clicked(self, timestamp):
        """Handle timestamp click - play audio if available or show images"""
        if not self.parent_widget:
            return
        
        timestamp_clean = timestamp.strip('[]')
        
        # First, check if this is a user message by looking at the message
        is_user_message = self.is_user_message_at_timestamp(timestamp_clean)
        
        print(f"[DEBUG-CLICK] Timestamp clicked: {timestamp_clean}, is_user={is_user_message}")
        
        # Only play audio for assistant messages, not user messages
        if not is_user_message:
            # Try to play audio using TTS manager if available
            if hasattr(self.parent_widget, 'tts_manager') and self.parent_widget.tts_manager:
                # Try through manager's timestamp_audio mapping
                if timestamp_clean in self.parent_widget.tts_manager.timestamp_audio:
                    audio_file = self.parent_widget.tts_manager.timestamp_audio[timestamp_clean]
                    print(f"[DEBUG-CLICK] Found audio in TTS manager: {audio_file}")
                    self.play_audio(audio_file)
                else:
                    print(f"[DEBUG-CLICK] No audio in TTS manager for: {timestamp_clean}")
                    print(f"[DEBUG-CLICK] Available timestamps in TTS manager: {list(self.parent_widget.tts_manager.timestamp_audio.keys())}")
                    # Try to find audio file by searching audio folder
                    self.play_audio_for_timestamp(timestamp_clean)
            # Fallback to direct timestamp_audio mapping
            elif timestamp_clean in self.timestamp_audio:
                audio_file = self.timestamp_audio[timestamp_clean]
                print(f"[DEBUG-CLICK] Found audio in direct mapping: {audio_file}")
                self.play_audio(audio_file)
            else:
                print(f"[DEBUG-CLICK] No audio found in mappings, searching audio folder...")
                # Try to find audio file by searching audio folder
                self.play_audio_for_timestamp(timestamp_clean)
            
            # Try to show images for this timestamp (only for assistant messages)
            self.show_images_for_timestamp(timestamp_clean)
    
    def is_user_message_at_timestamp(self, timestamp):
        """Check if message at timestamp is a user message"""
        if not self.parent_widget:
            return False
        for msg in self.parent_widget.message_history:
            if msg.get("timestamp") == timestamp or msg.get("timestamp", "").startswith(timestamp):
                # Handle both old format ("sender") and new format ("role")
                if "sender" in msg:
                    return msg.get("sender") == "You"
                else:
                    return msg.get("role") == "user"
        return False
    
    def show_images_for_timestamp(self, timestamp):
        """Show images associated with a timestamp"""
        if not self.parent_widget:
            return
        
        # First check if we have a timestamp_image mapping
        if timestamp in self.timestamp_image:
            image_file = self.timestamp_image[timestamp]
            image_path = Path(image_file) if isinstance(image_file, str) else image_file
            if image_path.exists():
                self.display_image(image_path)
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] Displaying image for timestamp: {timestamp}")
                return
        
        # Check for image in images folder (with timestamp-based naming)
        try:
            # Convert timestamp to filename format (YYYY-MM-DD HH:MM:SS -> YYYY-MM-DD_HH-MM-SS)
            filename_timestamp = str(timestamp).replace(":", "-").replace(" ", "_").replace(".", "-").replace("[", "").replace("]", "")
            
            # Check in images folder directly (not in chat_images subfolder)
            if hasattr(self.parent_widget, 'image_folder') and self.parent_widget.image_folder:
                image_folder = self.parent_widget.image_folder
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] show_images_for_timestamp: parent_widget.image_folder = {image_folder}")
                    print(f"[DEBUG] parent_widget type: {type(self.parent_widget)}")
                    print(f"[DEBUG] parent_widget.current_chat_name: {getattr(self.parent_widget, 'current_chat_name', 'NOT SET')}")
                if image_folder.exists():
                    # Try exact filename match - CHECK .PNG FIRST
                    for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                        image_path = image_folder / f"{filename_timestamp}{ext}"
                        if image_path.exists():
                            self.display_image(image_path)
                            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                                print(f"[DEBUG] Displaying image from images folder: {image_path}")
                            return
        except Exception as e:
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                print(f"[DEBUG] Error checking images folder: {e}")
        
        # Fallback: Try to match by filename in image_folder
        if not hasattr(self.parent_widget, 'image_folder') or not self.parent_widget.image_folder:
            return
        
        try:
            image_folder = Path(self.parent_widget.image_folder)
            if not image_folder.exists():
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] Image folder not found: {image_folder}")
                return
            
            # Get all images sorted by modification time
            images = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp']:
                images.extend(image_folder.glob(ext))
                images.extend(image_folder.glob(ext.upper()))
            
            if not images:
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] No images found in {image_folder}")
                return
            
            # Remove duplicates and sort by modification time (newest first)
            images = sorted(set(images), key=lambda x: x.stat().st_mtime, reverse=True)
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                print(f"[DEBUG] Found {len(images)} images. Timestamp: {timestamp}")
            
            # Try to find image matching the timestamp in filename
            matching_images = []
            for img in images:
                # Check if image filename contains the timestamp
                if timestamp in img.name or timestamp.replace(":", "") in img.name:
                    matching_images.append(img)
            
            if matching_images:
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] Found {len(matching_images)} images matching timestamp {timestamp}")
                self.display_image(matching_images[0])
            else:
                # No match - don't show any image
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] No image found for timestamp {timestamp}")
        except Exception as e:
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                print(f"[DEBUG] Error showing images: {e}")
    
    def display_image(self, image_path):
        """Display image in the image viewer"""
        if not self.parent_widget:
            return
        
        try:
            if isinstance(image_path, str):
                image_path = Path(image_path)
            
            if not image_path.exists():
                return
            
            # Load all images from folder to enable navigation
            try:
                image_folder = image_path.parent
                all_images = []
                for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp']:
                    all_images.extend(image_folder.glob(ext))
                    all_images.extend(image_folder.glob(ext.upper()))
                
                # Remove duplicates and sort by modification time (oldest first, newest last)
                unique_images = list(set(all_images))
                unique_images.sort(key=lambda x: x.stat().st_mtime)
                self.parent_widget.current_image_list = [str(img) for img in unique_images]
                
                # Find current image index
                image_path_str = str(image_path)
                if image_path_str in self.parent_widget.current_image_list:
                    self.parent_widget.current_image_index = self.parent_widget.current_image_list.index(image_path_str)
                else:
                    self.parent_widget.current_image_index = 0
                
                # Update the counter label
                if hasattr(self.parent_widget, 'image_counter_label'):
                    self.parent_widget.image_counter_label.setText(
                        f"{self.parent_widget.current_image_index + 1}/{len(self.parent_widget.current_image_list)}"
                    )
            except:
                self.parent_widget.current_image_list = [str(image_path)]
                self.parent_widget.current_image_index = 0
                if hasattr(self.parent_widget, 'image_counter_label'):
                    self.parent_widget.image_counter_label.setText("1/1")
            
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                # Use ResizableImageLabel's dynamic scaling with fit mode
                fit_mode = self.parent_widget.fit_image_checkbox.isChecked() if hasattr(self.parent_widget, 'fit_image_checkbox') else True
                if hasattr(self.parent_widget.image_label, 'set_pixmap_with_fit'):
                    self.parent_widget.image_label.set_pixmap_with_fit(pixmap, fit_to_area=fit_mode)
                else:
                    # Fallback for non-ResizableImageLabel
                    max_size = 300
                    scaled_pixmap = pixmap.scaledToHeight(max_size, Qt.SmoothTransformation)
                    self.parent_widget.image_label.setPixmap(scaled_pixmap)
                self.parent_widget.image_label.setVisible(True)
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                    print(f"[DEBUG] Displaying image: {image_path.name}")
        except Exception as e:
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_images:
                print(f"[DEBUG] Error displaying image: {e}")
    
    def play_audio_for_timestamp(self, timestamp):
        """Search audio folder for matching audio file and play it"""
        try:
            if not hasattr(self.parent_widget, 'audio_folder') or not self.parent_widget.audio_folder:
                print(f"[DEBUG-CLICK] No audio folder configured")
                return
            
            audio_folder = Path(self.parent_widget.audio_folder)
            if not audio_folder.exists():
                print(f"[DEBUG-CLICK] Audio folder does not exist: {audio_folder}")
                return
            
            # Convert timestamp to filename format (YYYY-MM-DD HH:MM:SS -> YYYY-MM-DD_HH-MM-SS)
            filename_timestamp = str(timestamp).replace(":", "-").replace(" ", "_").replace(".", "-")
            
            # Look for audio files matching this timestamp
            for audio_file in audio_folder.glob("*.wav"):
                if filename_timestamp in audio_file.name:
                    print(f"[DEBUG-CLICK] Found matching audio file: {audio_file}")
                    self.play_audio(str(audio_file))
                    return
            
            print(f"[DEBUG-CLICK] No audio file found for timestamp: {timestamp} (searched for: {filename_timestamp})")
            # List available files for debugging
            wav_files = list(audio_folder.glob("*.wav"))
            if wav_files:
                print(f"[DEBUG-CLICK] Available audio files in folder:")
                for f in wav_files[:10]:  # Show first 10
                    print(f"  - {f.name}")
        
        except Exception as e:
            print(f"[DEBUG-CLICK] Error searching for audio: {e}")
    
    def play_audio(self, audio_file):
        """Play audio file using centralized audio player"""
        try:
            from pathlib import Path
            import sys
            # Add parent directory to path for local module import
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from audio_player import get_audio_player
            
            audio_path = Path(audio_file)
            if not audio_path.exists():
                if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
                    print(f"[DEBUG] Audio file not found: {audio_file}")
                return
            
            # Use centralized audio player (only one audio at a time)
            player = get_audio_player()
            player.play(str(audio_path), auto_stop_current=True)
        
        except Exception as e:
            if DebugConfig.media_playback_enabled and DebugConfig.media_playback_audio:
                print(f"[DEBUG] Error playing audio: {e}")
