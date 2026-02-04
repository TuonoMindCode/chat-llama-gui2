"""
System Prompts Manager Tab for PyQt5
Separate system prompts for Ollama and Llama Server
"""
# pylint: disable=no-name-in-module,too-many-locals,broad-except

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QTextEdit, QMessageBox, QInputDialog,
    QSplitter, QFrame, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from pathlib import Path
import os
from settings_manager import load_settings
from settings_saver import get_settings_saver


class QtSystemPromptsTab(QWidget):
    """Manage separate system prompts for Ollama and Llama Server"""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.prompts_dir = Path("system_prompts")
        self.prompts_dir.mkdir(exist_ok=True)
        
        # Ensure default prompts exist
        self._ensure_default_prompts()
        
        # Track current file and modifications for each server
        self.current_files = {
            "ollama": {"path": None, "modified": False},
            "llama": {"path": None, "modified": False}
        }
        
        # Checkboxes for prepending system prompt to user message
        self.ollama_prepend_checkbox = None
        self.llama_prepend_checkbox = None
        
        # Template attributes
        self.template_list = None
        self.template_editor = None
        
        self.create_widgets()
        self.load_prompts()
    
    def _ensure_default_prompts(self):
        """Ensure Default.txt exists with the friendly system prompt"""
        default_file = self.prompts_dir / "Default.txt"
        
        # If Default.txt doesn't exist, create it
        if not default_file.exists():
            from config import SYSTEM_PROMPT
            try:
                with open(default_file, 'w', encoding='utf-8') as f:
                    f.write(SYSTEM_PROMPT)
                print(f"[DEBUG] Created default system prompt: {default_file}")
            except Exception as e:
                print(f"[ERROR] Failed to create default system prompt: {e}")
    
    def create_widgets(self):
        """Create system prompts manager with dual-panel layout"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Main horizontal splitter (lists on left, editors on right)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # LEFT PANEL - File lists stacked vertically
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # LEFT TOP - Ollama list
        ollama_list_label = QLabel("Ollama System Prompt")
        ollama_font = QFont()
        ollama_font.setBold(True)
        ollama_list_label.setFont(ollama_font)
        ollama_list_label.setStyleSheet("color: #0066cc;")
        left_layout.addWidget(ollama_list_label)
        
        self.ollama_list = QListWidget()
        self.ollama_list.itemClicked.connect(lambda item: self.on_file_select("ollama", item))
        left_layout.addWidget(self.ollama_list)
        
        # LEFT BOTTOM - Llama list
        llama_list_label = QLabel("Llama Server System Prompt")
        llama_font = QFont()
        llama_font.setBold(True)
        llama_list_label.setFont(llama_font)
        llama_list_label.setStyleSheet("color: #cc6600;")
        left_layout.addWidget(llama_list_label)
        
        self.llama_list = QListWidget()
        self.llama_list.itemClicked.connect(lambda item: self.on_file_select("llama", item))
        left_layout.addWidget(self.llama_list)
        
        # RIGHT PANEL - Editors stacked vertically
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Create a splitter to stack the two editors vertically
        editors_splitter = QSplitter(Qt.Vertical)
        
        # RIGHT TOP - Ollama editor in a frame
        ollama_frame = QFrame()
        ollama_frame_layout = QVBoxLayout()
        ollama_frame_layout.setContentsMargins(0, 0, 0, 0)
        ollama_frame_layout.setSpacing(2)
        ollama_frame.setLayout(ollama_frame_layout)
        
        ollama_editor_label = QLabel("Ollama Content")
        ollama_editor_font = QFont()
        ollama_editor_font.setBold(True)
        ollama_editor_label.setFont(ollama_editor_font)
        ollama_editor_label.setStyleSheet("color: #0066cc;")
        ollama_frame_layout.addWidget(ollama_editor_label)
        
        self.ollama_text = QTextEdit()
        self.ollama_text.setFont(QFont("Courier", 9))
        self.ollama_text.textChanged.connect(lambda: self.on_text_modify("ollama"))
        ollama_frame_layout.addWidget(self.ollama_text)
        
        # Ollama buttons
        ollama_button_layout = QHBoxLayout()
        self.ollama_new_btn = QPushButton("New")
        self.ollama_new_btn.setMaximumWidth(80)
        self.ollama_new_btn.clicked.connect(lambda: self.create_new_prompt("ollama"))
        ollama_button_layout.addWidget(self.ollama_new_btn)
        
        self.ollama_save_btn = QPushButton("Save")
        self.ollama_save_btn.setMaximumWidth(80)
        self.ollama_save_btn.clicked.connect(lambda: self.save_prompt("ollama"))
        ollama_button_layout.addWidget(self.ollama_save_btn)
        
        self.ollama_delete_btn = QPushButton("Delete")
        self.ollama_delete_btn.setMaximumWidth(80)
        self.ollama_delete_btn.clicked.connect(lambda: self.delete_prompt("ollama"))
        ollama_button_layout.addWidget(self.ollama_delete_btn)
        
        self.ollama_activate_btn = QPushButton("Activate")
        self.ollama_activate_btn.setMaximumWidth(80)
        self.ollama_activate_btn.clicked.connect(lambda: self.activate_prompt("ollama"))
        ollama_button_layout.addWidget(self.ollama_activate_btn)
        
        self.ollama_add_nomic_btn = QPushButton("Add Nomic Memory")
        self.ollama_add_nomic_btn.setMaximumWidth(160)
        self.ollama_add_nomic_btn.clicked.connect(lambda: self.add_nomic_tracking("ollama"))
        ollama_button_layout.addWidget(self.ollama_add_nomic_btn)
        
        ollama_button_layout.addStretch()
        ollama_frame_layout.addLayout(ollama_button_layout)
        
        # Ollama checkbox for prepending system prompt
        self.ollama_prepend_checkbox = QCheckBox("Prepend system prompt to user message")
        self.ollama_prepend_checkbox.setToolTip("Workaround for Ollama models that ignore system prompts.\nEmbeds critical instructions in the user message.")
        self.ollama_prepend_checkbox.stateChanged.connect(lambda: self.save_prepend_setting("ollama"))
        ollama_frame_layout.addWidget(self.ollama_prepend_checkbox)
        
        editors_splitter.addWidget(ollama_frame)
        
        # RIGHT BOTTOM - Llama editor in a frame
        llama_frame = QFrame()
        llama_frame_layout = QVBoxLayout()
        llama_frame_layout.setContentsMargins(0, 0, 0, 0)
        llama_frame_layout.setSpacing(2)
        llama_frame.setLayout(llama_frame_layout)
        
        llama_editor_label = QLabel("Llama Content")
        llama_editor_font = QFont()
        llama_editor_font.setBold(True)
        llama_editor_label.setFont(llama_editor_font)
        llama_editor_label.setStyleSheet("color: #cc6600;")
        llama_frame_layout.addWidget(llama_editor_label)
        
        self.llama_text = QTextEdit()
        self.llama_text.setFont(QFont("Courier", 9))
        self.llama_text.textChanged.connect(lambda: self.on_text_modify("llama"))
        llama_frame_layout.addWidget(self.llama_text)
        
        # Llama buttons
        llama_button_layout = QHBoxLayout()
        self.llama_new_btn = QPushButton("New")
        self.llama_new_btn.setMaximumWidth(80)
        self.llama_new_btn.clicked.connect(lambda: self.create_new_prompt("llama"))
        llama_button_layout.addWidget(self.llama_new_btn)
        
        self.llama_save_btn = QPushButton("Save")
        self.llama_save_btn.setMaximumWidth(80)
        self.llama_save_btn.clicked.connect(lambda: self.save_prompt("llama"))
        llama_button_layout.addWidget(self.llama_save_btn)
        
        self.llama_delete_btn = QPushButton("Delete")
        self.llama_delete_btn.setMaximumWidth(80)
        self.llama_delete_btn.clicked.connect(lambda: self.delete_prompt("llama"))
        llama_button_layout.addWidget(self.llama_delete_btn)
        
        self.llama_activate_btn = QPushButton("Activate")
        self.llama_activate_btn.setMaximumWidth(80)
        self.llama_activate_btn.clicked.connect(lambda: self.activate_prompt("llama"))
        llama_button_layout.addWidget(self.llama_activate_btn)
        
        self.llama_add_nomic_btn = QPushButton("Add Nomic Memory")
        self.llama_add_nomic_btn.setMaximumWidth(160)
        self.llama_add_nomic_btn.clicked.connect(lambda: self.add_nomic_tracking("llama"))
        llama_button_layout.addWidget(self.llama_add_nomic_btn)
        
        llama_button_layout.addStretch()
        llama_frame_layout.addLayout(llama_button_layout)
        
        # Llama checkbox for prepending system prompt
        self.llama_prepend_checkbox = QCheckBox("Prepend system prompt to user message")
        self.llama_prepend_checkbox.setToolTip("Workaround for Llama models that ignore system prompts.\nEmbeds critical instructions in the user message.")
        self.llama_prepend_checkbox.stateChanged.connect(lambda: self.save_prepend_setting("llama"))
        llama_frame_layout.addWidget(self.llama_prepend_checkbox)
        
        editors_splitter.addWidget(llama_frame)
        editors_splitter.setStretchFactor(0, 1)
        editors_splitter.setStretchFactor(1, 1)
        
        right_layout.addWidget(editors_splitter)
        
        # Add panels to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(main_splitter)
        
        # Status bar (fixed small height at bottom)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666666; font-size: 8pt; padding: 2px 5px; border-top: 1px solid #cccccc;")
        self.status_label.setMaximumHeight(25)
        main_layout.addWidget(self.status_label)
    
    def load_prompts(self):
        """Load all system prompts from folder for both servers"""
        self.ollama_list.clear()
        self.llama_list.clear()
        
        try:
            prompt_files = sorted([f for f in os.listdir(self.prompts_dir) if f.endswith('.txt')])
            
            settings = load_settings()
            saved_ollama_prompt = settings.get("selected_system_prompt_ollama", None)
            saved_llama_prompt = settings.get("selected_system_prompt_llama", None)
            
            for filename in prompt_files:
                # Add to both lists
                ollama_item = QListWidgetItem(filename[:-4])
                ollama_item.setData(Qt.UserRole, str(self.prompts_dir / filename))
                self.ollama_list.addItem(ollama_item)
                
                llama_item = QListWidgetItem(filename[:-4])
                llama_item.setData(Qt.UserRole, str(self.prompts_dir / filename))
                self.llama_list.addItem(llama_item)
            
            # Restore saved selections
            if saved_ollama_prompt:
                for i in range(self.ollama_list.count()):
                    item = self.ollama_list.item(i)
                    if item.text() + ".txt" == saved_ollama_prompt:
                        self.ollama_list.setCurrentItem(item)
                        self.on_file_select("ollama", item)
                        break
            
            if saved_llama_prompt:
                for i in range(self.llama_list.count()):
                    item = self.llama_list.item(i)
                    if item.text() + ".txt" == saved_llama_prompt:
                        self.llama_list.setCurrentItem(item)
                        self.on_file_select("llama", item)
                        break
            
            # Load prepend settings
            ollama_prepend = settings.get("ollama_prepend_system_to_message", False)
            llama_prepend = settings.get("llama_prepend_system_to_message", False)
            self.ollama_prepend_checkbox.setChecked(ollama_prepend)
            self.llama_prepend_checkbox.setChecked(llama_prepend)
            
            self.status_label.setText(f"Loaded {len(prompt_files)} prompts")
        
        except Exception as e:
            self.status_label.setText(f"Error loading prompts: {e}")
            print(f"[DEBUG] Error loading prompts: {e}")
    
    def on_file_select(self, server, item):
        """Handle file selection from listbox"""
        if not item:
            return
        
        file_path = item.data(Qt.UserRole)
        text_widget = self.ollama_text if server == "ollama" else self.llama_text
        
        # Check for unsaved changes
        if self.current_files[server]["modified"] and self.current_files[server]["path"]:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"Save changes to {server} prompt?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Yes:
                self.save_prompt(server)
            elif reply == QMessageBox.Cancel:
                return
        
        # Load the file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            text_widget.setPlainText(content)
            self.current_files[server]["path"] = file_path
            self.current_files[server]["modified"] = False
            self.status_label.setText(f"Editing {server}: {item.text()}")
        
        except Exception as e:
            self.status_label.setText(f"Error loading: {e}")
            print(f"[DEBUG] Error loading prompt: {e}")
    
    def on_text_modify(self, server):
        """Mark file as modified when text changes"""
        if self.current_files[server]["path"]:
            self.current_files[server]["modified"] = True
    
    def create_new_prompt(self, server):
        """Create a new system prompt file"""
        name, ok = QInputDialog.getText(
            self,
            "New System Prompt",
            f"Enter filename for {server}:"
        )
        
        if ok and name:
            file_path = self.prompts_dir / f"{name}.txt"
            
            if file_path.exists():
                QMessageBox.warning(self, "Warning", "File already exists")
                return
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("")
                
                self.load_prompts()
                self.status_label.setText(f"Created: {name}")
            
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create file: {e}")
    
    def save_prompt(self, server):
        """Save the current prompt file"""
        if not self.current_files[server]["path"]:
            QMessageBox.warning(self, "Warning", "Please select a file first")
            return
        
        try:
            text_widget = self.ollama_text if server == "ollama" else self.llama_text
            content = text_widget.toPlainText()
            
            with open(self.current_files[server]["path"], "w", encoding="utf-8") as f:
                f.write(content)
            
            self.current_files[server]["modified"] = False
            filename = os.path.basename(self.current_files[server]["path"])
            self.status_label.setText(f"Saved: {filename}")
        
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not save: {e}")
    
    def delete_prompt(self, server):
        """Delete the selected prompt file"""
        list_widget = self.ollama_list if server == "ollama" else self.llama_list
        current = list_widget.currentItem()
        
        if not current:
            QMessageBox.warning(self, "Warning", "Please select a file to delete")
            return
        
        file_path = current.data(Qt.UserRole)
        prompt_name = current.text()  # Save the name before deleting
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete '{prompt_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                self.current_files[server]["path"] = None
                self.current_files[server]["modified"] = False
                text_widget = self.ollama_text if server == "ollama" else self.llama_text
                text_widget.clear()
                self.load_prompts()
                self.status_label.setText(f"Deleted: {prompt_name}")
            
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete: {e}")
    
    def activate_prompt(self, server):
        """Activate the selected prompt as the system prompt"""
        list_widget = self.ollama_list if server == "ollama" else self.llama_list
        current = list_widget.currentItem()
        
        if not current:
            self.status_label.setText("Please select a prompt to activate")
            return
        
        file_path = current.data(Qt.UserRole)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Update app's system prompt
            if server == "ollama":
                self.app.system_prompt = content.strip()
                setting_key = "system_prompt_ollama"
                selected_key = "selected_system_prompt_ollama"
            else:
                self.app.system_prompt_llama = content.strip()
                setting_key = "system_prompt_llama"
                selected_key = "selected_system_prompt_llama"
            
            # Save to settings
            settings = load_settings()
            settings[setting_key] = content.strip()
            settings[selected_key] = f"{current.text()}.txt"
            saver = get_settings_saver()
            saver.sync_from_ui_dict(settings)
            saver.save()
            
            self.status_label.setText(f"Activated {server}: {current.text()}")
        
        except Exception as e:
            self.status_label.setText(f"Error activating: {e}")
    
    def add_nomic_tracking(self, server):
        """Add nomic memory tracking context to system prompt with custom context"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout
        
        text_widget = self.ollama_text if server == "ollama" else self.llama_text
        current_text = text_widget.toPlainText()
        
        # Check if [nomic] already exists
        if "[nomic]" in current_text:
            QMessageBox.information(
                self, 
                "Info", 
                "[nomic] already present in this prompt"
            )
            return
        
        # Create dialog for custom context
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Custom Context for Nomic")
        dialog.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout()
        
        # Label and instructions
        label = QLabel(
            "Enter custom context that will be available to Nomic memory.\n"
            "Examples:\n"
            "  • my name is John\n"
            "  • you love to tell jokes\n"
            "  • my hobby is coding\n\n"
            "Leave empty to use just [nomic] placeholder:"
        )
        layout.addWidget(label)
        
        # Text edit for custom context
        context_edit = QTextEdit()
        context_edit.setPlaceholderText("Enter custom context here (optional)...")
        context_edit.setFont(QFont("Courier", 9))
        layout.addWidget(context_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add to Prompt")
        add_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(add_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # Show dialog and get result
        if dialog.exec_() == QDialog.Accepted:
            custom_context = context_edit.toPlainText().strip()
            
            # Build the nomic insertion
            if custom_context:
                nomic_insertion = f"\n\nCustom Context (for Nomic memory):\n{custom_context}\n\n[nomic]"
            else:
                nomic_insertion = "\n\nCustom Context (for Nomic memory):\n[nomic]"
            
            # Add at end of prompt
            new_text = current_text + nomic_insertion
            text_widget.setPlainText(new_text)
            
            # Show confirmation
            QMessageBox.information(
                self, 
                "Success", 
                "Custom context and nomic tracking added to prompt"
            )
    
    def save_prepend_setting(self, server):
        """Save the prepend system prompt to user message setting"""
        try:
            checkbox = self.ollama_prepend_checkbox if server == "ollama" else self.llama_prepend_checkbox
            is_checked = checkbox.isChecked()
            
            # Save to settings
            settings = load_settings()
            if server == "ollama":
                settings["ollama_prepend_system_to_message"] = is_checked
                self.app.ollama_prepend_system_to_message = is_checked
            else:
                settings["llama_prepend_system_to_message"] = is_checked
                self.app.llama_prepend_system_to_message = is_checked
            
            saver = get_settings_saver()
            saver.sync_from_ui_dict(settings)
            saver.save()
            
            status_text = "enabled" if is_checked else "disabled"
            self.status_label.setText(f"Prepend for {server} {status_text}")
        
        except Exception as e:
            self.status_label.setText(f"Error saving setting: {e}")
            print(f"[DEBUG] Error saving prepend setting: {e}")
