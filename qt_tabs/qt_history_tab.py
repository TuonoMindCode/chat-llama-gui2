"""
History Tab for PyQt5
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTextEdit, QSplitter, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from pathlib import Path
import json


class QtHistoryTab(QWidget):
    """History tab implementation - shows saved chats"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        self.create_widgets()
        self.load_chat_list()
    
    def create_widgets(self):
        """Create history tab widgets"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Title
        title = QLabel("📚 Chat History")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title.setFont(title_font)
        main_layout.addWidget(title)
        
        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT: Chat list
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        
        left_layout.addWidget(QLabel("Saved Chats:"))
        
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.on_chat_selected)
        left_layout.addWidget(self.chat_list)
        
        # List control buttons
        list_button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_chat_list)
        list_button_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self.export_chat)
        list_button_layout.addWidget(export_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_chat)
        list_button_layout.addWidget(delete_btn)
        
        left_layout.addLayout(list_button_layout)
        
        # RIGHT: Chat preview
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)
        
        right_layout.addWidget(QLabel("Preview:"))
        
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        right_layout.addWidget(self.preview_text)
        
        # Preview control buttons
        preview_button_layout = QHBoxLayout()
        
        load_btn = QPushButton("📂 Load Chat")
        load_btn.clicked.connect(self.load_selected_chat)
        preview_button_layout.addWidget(load_btn)
        
        copy_btn = QPushButton("📋 Copy")
        copy_btn.clicked.connect(self.copy_preview)
        preview_button_layout.addWidget(copy_btn)
        
        right_layout.addLayout(preview_button_layout)
        
        # Add widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter, 1)
        
        # Status bar
        self.bottom_status_label = QLabel("Ready")
        self.bottom_status_label.setStyleSheet("color: #666666; font-size: 9pt; padding: 3px 5px; border-top: 1px solid #cccccc;")
        main_layout.addWidget(self.bottom_status_label)
    
    def load_chat_list(self):
        """Load list of saved chats from saved_chats folders"""
        self.chat_list.clear()
        
        try:
            # Check saved_chats folders (primary source)
            for chat_folder in sorted(Path(".").glob("saved_chats_*/")):
                # Iterate through each chat in the folder
                for chat_subfolder in sorted(chat_folder.glob("*/")):
                    if chat_subfolder.is_dir():
                        # Look for chat JSON file
                        chat_name = chat_subfolder.name
                        chat_file = chat_subfolder / f"{chat_name}.json"
                        
                        if chat_file.exists():
                            try:
                                with open(chat_file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                
                                messages = data.get("messages", []) if isinstance(data, dict) else data
                                msg_count = len(messages) if isinstance(messages, list) else 0
                                
                                # Format: server_type/chat_name (msg_count messages)
                                server_type = chat_folder.name.replace("saved_chats_", "")
                                item_text = f"{chat_name} - {server_type} ({msg_count} messages)"
                                item = QListWidgetItem(item_text)
                                item.setData(Qt.UserRole, str(chat_file))
                                self.chat_list.addItem(item)
                            except Exception as e:
                                print(f"[DEBUG] Error loading {chat_file}: {e}")
        
        except Exception as e:
            print(f"[DEBUG] Error loading chat list: {e}")
    
    def on_chat_selected(self, item):
        """Handle chat selection"""
        file_path = item.data(Qt.UserRole)
        self.preview_chat(file_path)
    
    def preview_chat(self, file_path):
        """Preview selected chat"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            messages = data.get("messages", []) if isinstance(data, dict) else data
            
            # Build preview text
            preview_lines = [f"Chat: {Path(file_path).stem}\n"]
            preview_lines.append(f"Messages: {len(messages)}\n")
            preview_lines.append("-" * 50 + "\n\n")
            
            # Show first few messages
            for i, msg in enumerate(messages[:10]):
                if isinstance(msg, dict):
                    role = msg.get("role", "unknown")
                    content = msg.get("content", "")[:100]
                    timestamp = msg.get("timestamp", "")
                    
                    preview_lines.append(f"[{role.upper()}] {content}...\n")
                else:
                    preview_lines.append(f"{str(msg)[:100]}...\n")
            
            if len(messages) > 10:
                preview_lines.append(f"\n... and {len(messages) - 10} more messages")
            
            self.preview_text.setText("".join(preview_lines))
            self.current_preview_file = file_path
            
        except Exception as e:
            self.preview_text.setText(f"Error loading preview: {e}")
    
    def load_selected_chat(self):
        """Load the selected chat into the chat window"""
        try:
            if not hasattr(self, 'current_preview_file'):
                QMessageBox.warning(self, "Warning", "Please select a chat first")
                return
            
            # TODO: Load chat into active chat tab
            file_path = self.current_preview_file
            QMessageBox.information(self, "Load Chat", f"Loading: {Path(file_path).name}\n\nThis feature will load the chat into the active tab.")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load chat: {e}")
    
    def copy_preview(self):
        """Copy preview text to clipboard"""
        try:
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = self.preview_text.toPlainText()
            if text:
                clipboard.setText(text)
                QMessageBox.information(self, "Success", "Preview copied to clipboard")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not copy: {e}")
    
    def export_chat(self):
        """Export selected chat to file"""
        try:
            if not hasattr(self, 'current_preview_file'):
                QMessageBox.warning(self, "Warning", "Please select a chat first")
                return
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Chat",
                f"{Path(self.current_preview_file).stem}_export.txt",
                "Text Files (*.txt);;JSON Files (*.json)"
            )
            
            if file_path:
                with open(self.current_preview_file, "r", encoding="utf-8") as src:
                    data = json.load(src)
                
                # Export as readable text
                with open(file_path, "w", encoding="utf-8") as dst:
                    messages = data.get("messages", []) if isinstance(data, dict) else data
                    
                    for msg in messages:
                        if isinstance(msg, dict):
                            role = msg.get("role", "unknown").upper()
                            content = msg.get("content", "")
                            timestamp = msg.get("timestamp", "")
                            
                            dst.write(f"[{timestamp}] {role}:\n{content}\n\n")
                
                QMessageBox.information(self, "Success", f"Chat exported to {file_path}")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not export: {e}")
    
    def delete_chat(self):
        """Delete selected chat"""
        try:
            if not hasattr(self, 'current_preview_file'):
                QMessageBox.warning(self, "Warning", "Please select a chat first")
                return
            
            reply = QMessageBox.question(
                self,
                "Delete Chat",
                "Are you sure you want to delete this chat?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                Path(self.current_preview_file).unlink()
                self.preview_text.clear()
                self.load_chat_list()
                QMessageBox.information(self, "Success", "Chat deleted")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not delete: {e}")

