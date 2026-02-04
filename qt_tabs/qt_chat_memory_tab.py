"""
Chat Memory Settings Tab for PyQt5
Allows configuration of conversation memory with semantic search
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSpinBox, 
    QPushButton, QGroupBox, QScrollArea, QFrame, QTextEdit, QComboBox, QFileDialog, QLineEdit, QMessageBox,
    QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from pathlib import Path
from settings_manager import load_settings, get_setting, set_setting
from settings_saver import get_settings_saver
import json


class QtChatMemoryTab(QWidget):
    """Chat Memory Settings and Management Tab"""
    
    memory_settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_content.setLayout(scroll_layout)
        
        # ============ OLLAMA MEMORY SETTINGS ============
        ollama_group = QGroupBox("Ollama Memory Settings")
        ollama_layout = QVBoxLayout()
        
        # Enable Memory
        self.ollama_memory_enabled = QCheckBox("Enable Conversation Memory")
        ollama_layout.addWidget(self.ollama_memory_enabled)
        
        # Max Context Messages
        context_layout = QHBoxLayout()
        context_layout.addWidget(QLabel("Recent Messages in Prompt:"))
        self.ollama_max_context = QSpinBox()
        self.ollama_max_context.setMinimum(5)
        self.ollama_max_context.setMaximum(100)
        self.ollama_max_context.setValue(20)
        context_layout.addWidget(self.ollama_max_context)
        context_layout.addWidget(QLabel("(limits messages sent to AI)"))
        context_layout.addStretch()
        ollama_layout.addLayout(context_layout)
        
        # Semantic Search Limit
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Semantically Similar Facts to Retrieve:"))
        self.ollama_semantic_limit = QSpinBox()
        self.ollama_semantic_limit.setMinimum(1)
        self.ollama_semantic_limit.setMaximum(20)
        self.ollama_semantic_limit.setValue(5)
        search_layout.addWidget(self.ollama_semantic_limit)
        search_layout.addStretch()
        ollama_layout.addLayout(search_layout)
        
        # Nomic Long Term Memory Section
        ollama_layout.addSpacing(10)
        nomic_label = QLabel("Nomic Long Term Memory:")
        nomic_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        ollama_layout.addWidget(nomic_label)
        
        # Nomic On/Off radio buttons
        nomic_radio_layout = QHBoxLayout()
        nomic_radio_layout.addWidget(QLabel("Enable:"))
        self.ollama_nomic_group = QButtonGroup()
        self.ollama_nomic_off = QRadioButton("Off")
        self.ollama_nomic_on = QRadioButton("On")
        self.ollama_nomic_off.setChecked(True)
        self.ollama_nomic_group.addButton(self.ollama_nomic_off, 0)
        self.ollama_nomic_group.addButton(self.ollama_nomic_on, 1)
        nomic_radio_layout.addWidget(self.ollama_nomic_off)
        nomic_radio_layout.addWidget(self.ollama_nomic_on)
        nomic_radio_layout.addStretch()
        ollama_layout.addLayout(nomic_radio_layout)
        
        # Fact File Long Term Memory - Per Chat Only
        fact_label = QLabel("Fact File Long Term Memory (Per Chat):")
        fact_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        ollama_layout.addWidget(fact_label)
        
        self.ollama_fact_file_enabled = QCheckBox("Enable - searches current chat's memory")
        self.ollama_fact_file_enabled.setChecked(True)
        ollama_layout.addWidget(self.ollama_fact_file_enabled)
        
        # Max recent messages to scan
        scan_layout = QHBoxLayout()
        scan_layout.addWidget(QLabel("Max messages to scan for facts:"))
        self.ollama_max_scan_messages = QSpinBox()
        self.ollama_max_scan_messages.setMinimum(10)
        self.ollama_max_scan_messages.setMaximum(500)
        self.ollama_max_scan_messages.setValue(50)
        scan_layout.addWidget(self.ollama_max_scan_messages)
        scan_layout.addWidget(QLabel("(when Nomic enabled, 0 = all)"))
        scan_layout.addStretch()
        ollama_layout.addLayout(scan_layout)
        
        # Ollama URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Ollama URL:"))
        self.ollama_url = QLineEdit()
        self.ollama_url.setPlaceholderText("http://localhost:11434")
        self.ollama_url.setText("http://localhost:11434")
        url_layout.addWidget(self.ollama_url)
        url_layout.addStretch()
        ollama_layout.addLayout(url_layout)
        
        ollama_group.setLayout(ollama_layout)
        scroll_layout.addWidget(ollama_group)
        
        # ============ LLAMA SERVER MEMORY SETTINGS ============
        llama_group = QGroupBox("Llama Server Memory Settings")
        llama_layout = QVBoxLayout()
        
        # Enable Memory
        self.llama_memory_enabled = QCheckBox("Enable Conversation Memory")
        llama_layout.addWidget(self.llama_memory_enabled)
        
        # Max Context Messages
        llama_context_layout = QHBoxLayout()
        llama_context_layout.addWidget(QLabel("Recent Messages in Prompt:"))
        self.llama_max_context = QSpinBox()
        self.llama_max_context.setMinimum(5)
        self.llama_max_context.setMaximum(100)
        self.llama_max_context.setValue(20)
        llama_context_layout.addWidget(self.llama_max_context)
        llama_context_layout.addWidget(QLabel("(limits messages sent to AI)"))
        llama_context_layout.addStretch()
        llama_layout.addLayout(llama_context_layout)
        
        # Semantic Search Limit
        llama_search_layout = QHBoxLayout()
        llama_search_layout.addWidget(QLabel("Semantically Similar Facts to Retrieve:"))
        self.llama_semantic_limit = QSpinBox()
        self.llama_semantic_limit.setMinimum(1)
        self.llama_semantic_limit.setMaximum(20)
        self.llama_semantic_limit.setValue(5)
        llama_search_layout.addWidget(self.llama_semantic_limit)
        llama_search_layout.addStretch()
        llama_layout.addLayout(llama_search_layout)
        
        # Nomic Long Term Memory Section
        llama_layout.addSpacing(10)
        llama_nomic_label = QLabel("Nomic Long Term Memory:")
        llama_nomic_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        llama_layout.addWidget(llama_nomic_label)
        
        # Nomic On/Off radio buttons
        llama_nomic_radio_layout = QHBoxLayout()
        llama_nomic_radio_layout.addWidget(QLabel("Enable:"))
        self.llama_nomic_group = QButtonGroup()
        self.llama_nomic_off = QRadioButton("Off")
        self.llama_nomic_on = QRadioButton("On")
        self.llama_nomic_off.setChecked(True)
        self.llama_nomic_group.addButton(self.llama_nomic_off, 0)
        self.llama_nomic_group.addButton(self.llama_nomic_on, 1)
        llama_nomic_radio_layout.addWidget(self.llama_nomic_off)
        llama_nomic_radio_layout.addWidget(self.llama_nomic_on)
        llama_nomic_radio_layout.addStretch()
        llama_layout.addLayout(llama_nomic_radio_layout)
        
        # Fact File Long Term Memory - Per Chat Only
        llama_fact_label = QLabel("Fact File Long Term Memory (Per Chat):")
        llama_fact_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        llama_layout.addWidget(llama_fact_label)
        
        self.llama_fact_file_enabled = QCheckBox("Enable - searches current chat's memory")
        self.llama_fact_file_enabled.setChecked(True)
        llama_layout.addWidget(self.llama_fact_file_enabled)
        
        # Max recent messages to scan
        llama_scan_layout = QHBoxLayout()
        llama_scan_layout.addWidget(QLabel("Max messages to scan for facts:"))
        self.llama_max_scan_messages = QSpinBox()
        self.llama_max_scan_messages.setMinimum(10)
        self.llama_max_scan_messages.setMaximum(500)
        self.llama_max_scan_messages.setValue(50)
        llama_scan_layout.addWidget(self.llama_max_scan_messages)
        llama_scan_layout.addWidget(QLabel("(when Nomic enabled, 0 = all)"))
        llama_scan_layout.addStretch()
        llama_layout.addLayout(llama_scan_layout)
        
        # Ollama URL for embeddings (required for Nomic)
        llama_ollama_url_layout = QHBoxLayout()
        llama_ollama_url_layout.addWidget(QLabel("Ollama URL (Embeddings):"))
        self.llama_ollama_url = QLineEdit()
        self.llama_ollama_url.setPlaceholderText("http://localhost:11434")
        self.llama_ollama_url.setText("http://localhost:11434")
        llama_ollama_url_layout.addWidget(self.llama_ollama_url)
        llama_ollama_url_layout.addStretch()
        llama_layout.addLayout(llama_ollama_url_layout)
        
        llama_group.setLayout(llama_layout)
        scroll_layout.addWidget(llama_group)
        
        # ============ EMBEDDING MODEL SETTINGS ============
        embedding_group = QGroupBox("Embedding Model")
        embedding_layout = QVBoxLayout()
        
        embedding_info = QLabel("⚙️ ALWAYS uses Ollama for embeddings (nomic-embed-text-v1.5)")
        embedding_info.setStyleSheet("color: #1976D2; font-weight: bold; font-size: 10pt;")
        embedding_layout.addWidget(embedding_info)
        
        embedding_note = QLabel(
            "📌 NOTE: Embeddings always use Ollama even if Llama-Server is selected for chat.\n"
            "This is required because llama-server can only run ONE model at a time.\n"
            "✓ Ollama can run multiple models in parallel (chat + embeddings)\n"
            "✓ No conflicts - Ollama and Llama-Server run on different ports\n"
            "✓ Memory/personalization features work seamlessly with either chat server"
        )
        embedding_note.setStyleSheet("color: #555; font-size: 9pt; background-color: #f5f5f5; padding: 8px; border-radius: 4px;")
        embedding_note.setWordWrap(True)
        embedding_layout.addWidget(embedding_note)
        
        # Embedding model name
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Embedding Model:"))
        self.embedding_model = QLineEdit()
        self.embedding_model.setText("nomic-embed-text")
        model_layout.addWidget(self.embedding_model)
        embedding_layout.addLayout(model_layout)
        
        embedding_group.setLayout(embedding_layout)
        scroll_layout.addWidget(embedding_group)
        
        scroll_layout.addSpacing(10)
        # Test Nomic Setup Button
        test_nomic_btn_layout = QHBoxLayout()
        self.test_nomic_btn = QPushButton("Test Nomic Setup")
        self.test_nomic_btn.clicked.connect(self.test_nomic_setup)
        test_nomic_btn_layout.addStretch()
        test_nomic_btn_layout.addWidget(self.test_nomic_btn)
        test_nomic_btn_layout.addStretch()
        scroll_layout.addLayout(test_nomic_btn_layout)
        
        scroll_layout.addSpacing(10)
        track_group = QGroupBox("What Personal Facts to Track")
        track_layout = QVBoxLayout()
        
        info = QLabel("Select which categories of personal information to track and remember:")
        info.setStyleSheet("color: #666; font-style: italic;")
        track_layout.addWidget(info)
        
        # Checkboxes for each category
        self.category_checkboxes = {}
        self.default_categories = ["name", "job", "pet", "family", "location", "age"]
        
        category_descriptions = {
            "name": "Name (my name, call me)",
            "job": "Work/Career (my job, work as, profession)",
            "pet": "Pets (my dog, my pet, my cat)",
            "family": "Family info (wife, husband, kids, siblings, parents)",
            "location": "Location (where I live, from, city, country)",
            "age": "Age (years old, born in)"
        }
        
        for category, description in category_descriptions.items():
            checkbox = QCheckBox(description)
            checkbox.setChecked(category in self.default_categories)
            self.category_checkboxes[category] = checkbox
            track_layout.addWidget(checkbox)
        
        # Custom keywords section
        track_layout.addSpacing(15)
        
        custom_label = QLabel("Custom Keywords to Track:")
        custom_label.setStyleSheet("font-weight: bold;")
        track_layout.addWidget(custom_label)
        
        custom_info = QLabel("Add custom keywords (comma-separated) or patterns to track specific topics:")
        custom_info.setStyleSheet("color: #666; font-style: italic; font-size: 10px;")
        track_layout.addWidget(custom_info)
        
        # Examples
        examples_label = QLabel("Examples:")
        examples_label.setStyleSheet("font-weight: bold; font-size: 9px; color: #555;")
        track_layout.addWidget(examples_label)
        
        examples_text = QLabel(
            "• my hobby:, interested in:, love:, passionate about:\n"
            "• my project:, working on:, building:\n"
            "• my goal:, want to:, planning to:\n"
            "• my favorite:, prefer:, like:\n"
            "• (separate multiple with commas)"
        )
        examples_text.setStyleSheet("color: #777; font-size: 9px; font-family: monospace; margin-left: 10px;")
        examples_text.setWordWrap(True)
        track_layout.addWidget(examples_text)
        
        # Custom keywords input
        self.custom_keywords = QTextEdit()
        self.custom_keywords.setPlaceholderText(
            "Examples (one per line, no colons needed):\n"
            "my hobby, interested in, love\n"
            "my project, working on\n"
            "my goal, want to, dream of"
        )
        self.custom_keywords.setMaximumHeight(80)
        self.custom_keywords.setMinimumHeight(60)
        track_layout.addWidget(self.custom_keywords)
        
        track_group.setLayout(track_layout)
        scroll_layout.addWidget(track_group)
        
        # ============ CONVERSATION MANAGEMENT ============
        manage_group = QGroupBox("Conversation Management")
        manage_layout = QVBoxLayout()
        
        # Statistics
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        manage_layout.addWidget(QLabel("Memory Statistics:"))
        manage_layout.addWidget(self.stats_text)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.clear_ollama_btn = QPushButton("Clear Ollama Memory")
        self.clear_ollama_btn.clicked.connect(self.clear_ollama_memory)
        button_layout.addWidget(self.clear_ollama_btn)
        
        self.clear_llama_btn = QPushButton("Clear Llama Memory")
        self.clear_llama_btn.clicked.connect(self.clear_llama_memory)
        button_layout.addWidget(self.clear_llama_btn)
        
        self.export_btn = QPushButton("Export Conversations")
        self.export_btn.clicked.connect(self.export_conversations)
        button_layout.addWidget(self.export_btn)
        
        manage_layout.addLayout(button_layout)
        manage_group.setLayout(manage_layout)
        scroll_layout.addWidget(manage_group)
        
        # ============ SAVE/APPLY BUTTONS ============
        scroll_layout.addStretch()
        
        button_save_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_settings_to_file)
        button_save_layout.addStretch()
        button_save_layout.addWidget(self.save_btn)
        scroll_layout.addLayout(button_save_layout)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
    def load_settings(self):
        """Load settings from file"""
        settings = load_settings()
        
        # Ollama settings
        self.ollama_memory_enabled.setChecked(
            settings.get("ollama_memory_enabled", True)
        )
        
        # Ollama Nomic On/Off
        ollama_nomic_enabled = settings.get("nomic_ollama_enabled", False)
        if ollama_nomic_enabled:
            self.ollama_nomic_on.setChecked(True)
        else:
            self.ollama_nomic_off.setChecked(True)
        
        # Ollama Fact File Mode (Per Chat)
        ollama_fact_enabled = settings.get("nomic_ollama_fact_file_enabled", True)
        self.ollama_fact_file_enabled.setChecked(ollama_fact_enabled)
        
        self.ollama_max_context.setValue(
            settings.get("ollama_max_context_messages", 20)
        )
        self.ollama_semantic_limit.setValue(
            settings.get("ollama_semantic_search_limit", 5)
        )
        self.ollama_max_scan_messages.setValue(
            settings.get("nomic_ollama_max_scan_messages", 50)
        )
        
        # Ollama URL
        self.ollama_url.setText(
            settings.get("ollama_url", "http://localhost:11434")
        )
        
        # Llama settings
        self.llama_memory_enabled.setChecked(
            settings.get("llama_memory_enabled", True)
        )
        
        # Llama Nomic On/Off
        llama_nomic_enabled = settings.get("nomic_llama_enabled", False)
        if llama_nomic_enabled:
            self.llama_nomic_on.setChecked(True)
        else:
            self.llama_nomic_off.setChecked(True)
        
        # Llama Fact File Mode (Per Chat)
        llama_fact_enabled = settings.get("nomic_llama_fact_file_enabled", True)
        self.llama_fact_file_enabled.setChecked(llama_fact_enabled)
        
        self.llama_max_context.setValue(
            settings.get("llama_max_context_messages", 20)
        )
        self.llama_semantic_limit.setValue(
            settings.get("llama_semantic_search_limit", 5)
        )
        self.llama_max_scan_messages.setValue(
            settings.get("nomic_llama_max_scan_messages", 50)
        )
        
        # Ollama URL for Llama embeddings
        self.llama_ollama_url.setText(
            settings.get("llama_ollama_url", "http://localhost:11434")
        )
        
        # Embedding model
        self.embedding_model.setText(
            settings.get("embedding_model", "nomic-embed-text")
        )
        
        # Load tracking categories from settings
        enabled_categories = settings.get("memory_track_categories", self.default_categories)
        for category, checkbox in self.category_checkboxes.items():
            checkbox.setChecked(category in enabled_categories)
        
        # Load custom keywords from settings
        custom_keywords = settings.get("memory_custom_keywords", "")
        self.custom_keywords.setPlainText(custom_keywords)
        
        self.update_statistics()
    
    def save_settings_to_file(self):
        """Save settings to file"""
        settings = load_settings()
        
        # Ollama settings
        settings["ollama_memory_enabled"] = self.ollama_memory_enabled.isChecked()
        settings["nomic_ollama_enabled"] = self.ollama_nomic_on.isChecked()
        settings["ollama_max_context_messages"] = self.ollama_max_context.value()
        settings["ollama_semantic_search_limit"] = self.ollama_semantic_limit.value()
        
        # Ollama fact file mode (Per Chat)
        settings["nomic_ollama_fact_file_enabled"] = self.ollama_fact_file_enabled.isChecked()
        
        settings["nomic_ollama_max_scan_messages"] = self.ollama_max_scan_messages.value()
        settings["ollama_url"] = self.ollama_url.text()
        
        # Llama settings
        settings["llama_memory_enabled"] = self.llama_memory_enabled.isChecked()
        settings["nomic_llama_enabled"] = self.llama_nomic_on.isChecked()
        settings["llama_max_context_messages"] = self.llama_max_context.value()
        settings["llama_semantic_search_limit"] = self.llama_semantic_limit.value()
        
        # Llama fact file mode (Per Chat)
        settings["nomic_llama_fact_file_enabled"] = self.llama_fact_file_enabled.isChecked()
        
        settings["nomic_llama_max_scan_messages"] = self.llama_max_scan_messages.value()
        settings["llama_ollama_url"] = self.llama_ollama_url.text()
        
        # Embedding model
        settings["embedding_model"] = self.embedding_model.text()
        
        # Save tracking categories (which ones are checked)
        enabled_categories = [
            cat for cat, checkbox in self.category_checkboxes.items() 
            if checkbox.isChecked()
        ]
        settings["memory_track_categories"] = enabled_categories
        
        # Save custom keywords (parse them into a list)
        custom_keywords_text = self.custom_keywords.toPlainText().strip()
        settings["memory_custom_keywords"] = custom_keywords_text
        
        saver = get_settings_saver()
        saver.sync_from_ui_dict(settings)
        saver.save()
        self.memory_settings_changed.emit(settings)
        
        # Show confirmation
        QMessageBox.information(self, "Success", "Memory settings saved successfully!")
    
    def update_statistics(self):
        """Update memory statistics"""
        stats = []
        
        # Check Ollama history
        ollama_history = Path("chat_history_ollama.json")
        if ollama_history.exists():
            try:
                with open(ollama_history, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    msg_count = len(data.get("messages", []))
                    stats.append(f"Ollama: {msg_count} messages stored")
            except Exception as e:
                stats.append(f"Ollama: Error reading history ({str(e)})")
        else:
            stats.append("Ollama: No history yet")
        
        # Check Llama history
        llama_history = Path("chat_history_llama.json")
        if llama_history.exists():
            try:
                with open(llama_history, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    msg_count = len(data.get("messages", []))
                    stats.append(f"Llama Server: {msg_count} messages stored")
            except Exception as e:
                stats.append(f"Llama Server: Error reading history ({str(e)})")
        else:
            stats.append("Llama Server: No history yet")
        
        # Always set text, even if empty (though it shouldn't be now)
        text_content = "\n".join(stats) if stats else "No statistics available"
        self.stats_text.setText(text_content)
    
    def test_nomic_setup(self):
        """Test if nomic embedding setup is working correctly for selected chat files"""
        import requests
        from memory_integration import MemoryIntegration
        from settings_manager import load_settings
        
        test_results = []
        
        # Test Ollama connection
        settings = load_settings()
        ollama_url = settings.get("ollama_url", "http://localhost:11434")
        test_results.append("=== NOMIC SETUP TEST ===\n")
        
        try:
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            test_results.append("✓ Ollama connection: OK")
            
            # Check if nomic-embed-text is installed
            models_data = response.json()
            models = models_data.get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            nomic_found = any("nomic" in name for name in model_names)
            if nomic_found:
                test_results.append("✓ Nomic embedding model: INSTALLED")
            else:
                test_results.append("✗ Nomic embedding model: NOT FOUND")
                test_results.append(f"  Available models: {', '.join(model_names[:3])}")
        
        except requests.exceptions.ConnectionError:
            test_results.append("✗ Ollama connection: FAILED (not running?)")
        except Exception as e:
            test_results.append(f"✗ Ollama error: {str(e)}")
        
        # Test memory settings
        test_results.append("\n=== MEMORY SETTINGS ===")
        test_results.append(f"Ollama Nomic Enabled: {self.ollama_nomic_on.isChecked()}")
        test_results.append(f"Ollama Fact File (Per Chat): {self.ollama_fact_file_enabled.isChecked()}")
        test_results.append(f"Llama Nomic Enabled: {self.llama_nomic_on.isChecked()}")
        test_results.append(f"Llama Fact File (Per Chat): {self.llama_fact_file_enabled.isChecked()}")
        
        # Get selected chat files from tabs
        ollama_chat_name = "default"
        llama_chat_name = "default"
        
        try:
            if hasattr(self.parent(), 'parent') and hasattr(self.parent().parent(), 'ollama_tab'):
                app = self.parent().parent()
                if hasattr(app, 'ollama_tab') and hasattr(app.ollama_tab, 'current_chat_name'):
                    ollama_chat_name = app.ollama_tab.current_chat_name
                if hasattr(app, 'llama_tab') and hasattr(app.llama_tab, 'current_chat_name'):
                    llama_chat_name = app.llama_tab.current_chat_name
        except:
            pass
        
        # Test memory integration for selected files
        test_results.append("\n=== SELECTED CHAT FILES ===")
        test_results.append(f"Ollama Chat: {ollama_chat_name}.json")
        test_results.append(f"Llama Server Chat: {llama_chat_name}.json")
        
        try:
            test_results.append("\n=== PERSONAL FACTS EXTRACTION ===")
            
            # Test Ollama chat facts
            memory_ollama = MemoryIntegration(ollama_chat_name=ollama_chat_name, llama_chat_name="default")
            ollama_facts = memory_ollama.get_ollama_personal_facts()
            
            if ollama_facts:
                preview = ollama_facts[:300] + "..." if len(ollama_facts) > 300 else ollama_facts
                test_results.append(f"✓ Ollama chat facts found ({len(ollama_facts)} chars):\n{preview}")
            else:
                test_results.append(f"ℹ Ollama chat: No personal facts found")
            
            # Test Llama chat facts
            memory_llama = MemoryIntegration(ollama_chat_name="default", llama_chat_name=llama_chat_name)
            llama_facts = memory_llama.get_llama_personal_facts()
            
            if llama_facts:
                preview = llama_facts[:300] + "..." if len(llama_facts) > 300 else llama_facts
                test_results.append(f"✓ Llama chat facts found ({len(llama_facts)} chars):\n{preview}")
            else:
                test_results.append(f"ℹ Llama chat: No personal facts found")
        
        except Exception as e:
            test_results.append(f"✗ Memory extraction error: {str(e)}")
        
        # Show results in scrollable dialog
        result_text = "\n".join(test_results)
        self._show_scrollable_dialog("Nomic Setup Test Results", result_text)
        print(result_text)
    
    def _show_scrollable_dialog(self, title, text):
        """Show a scrollable dialog for long text"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setGeometry(100, 100, 700, 500)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setText(text)
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-family: monospace; font-size: 9pt;")
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def clear_ollama_memory(self):
        """Clear Ollama conversation memory"""
        reply = QMessageBox.question(
            self, "Confirm", "Clear all Ollama conversation memory?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            ollama_history = Path("chat_history_ollama.json")
            if ollama_history.exists():
                ollama_history.unlink()
            self.update_statistics()
            QMessageBox.information(self, "Success", "Ollama memory cleared!")
    
    def clear_llama_memory(self):
        """Clear Llama conversation memory"""
        reply = QMessageBox.question(
            self, "Confirm", "Clear all Llama Server conversation memory?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            llama_history = Path("chat_history_llama.json")
            if llama_history.exists():
                llama_history.unlink()
            self.update_statistics()
            QMessageBox.information(self, "Success", "Llama memory cleared!")
    
    def export_conversations(self):
        """Export conversations to a backup file"""
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            return
        
        export_path = Path(folder)
        
        # Export Ollama
        ollama_history = Path("chat_history_ollama.json")
        if ollama_history.exists():
            import shutil
            shutil.copy(ollama_history, export_path / "chat_history_ollama_backup.json")
        
        # Export Llama
        llama_history = Path("chat_history_llama.json")
        if llama_history.exists():
            import shutil
            shutil.copy(llama_history, export_path / "chat_history_llama_backup.json")
        
        QMessageBox.information(self, "Success", "Conversations exported successfully!")

