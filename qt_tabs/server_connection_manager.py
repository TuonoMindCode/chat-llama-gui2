"""
Server Connection Manager - Handles server connectivity, model management, and template selection
"""

import threading
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
from settings_manager import load_settings, get_setting, set_setting
from settings_saver import get_settings_saver
from chat_template_manager import template_manager
from debug_config import DebugConfig


class ConnectionSignals(QObject):
    """Qt signals for thread-safe connection updates"""
    connection_succeeded = pyqtSignal()
    connection_failed = pyqtSignal(str)
    models_loaded = pyqtSignal(list)  # Emits list of model names
    models_load_failed = pyqtSignal(str)  # Emits error message


class ServerConnectionManager:
    """Manages server connection, model loading, and template selection"""
    
    @staticmethod
    def _is_chat_model(model_name):
        """Check if model is a chat model (exclude embedding and other non-chat models)"""
        embedding_keywords = ['embed', 'embedding', 'rerank', 'bge-', 'all-minilm', 'nomic-embed']
        model_lower = model_name.lower()
        return not any(keyword in model_lower for keyword in embedding_keywords)
    
    def __init__(self, chat_tab):
        """
        Initialize server connection manager
        
        Args:
            chat_tab: Parent chat tab instance
        """
        self.chat_tab = chat_tab
        self.client = chat_tab.client
        self.server_type = chat_tab.server_type
        self.connect_button = chat_tab.connect_button
        self.status_label = chat_tab.status_label
        self.model_combo = chat_tab.model_combo
        self.message_display = chat_tab.message_display
        self.app = chat_tab.app
        self.settings = load_settings()
        
        # Template combo is now in the settings tab
        self.template_combo = None
        try:
            # Try to find the settings tab in the app's main tab widget
            if hasattr(self.app, 'tabs') and hasattr(self.app.tabs, 'widget'):
                for i in range(self.app.tabs.count()):
                    widget = self.app.tabs.widget(i)
                    if hasattr(widget, 'template_combo'):
                        self.template_combo = widget.template_combo
                        if DebugConfig.chat_template_formatting:
                            print(f"[DEBUG-TEMPLATE] Found template_combo in settings tab")
                        break
        except Exception as e:
            if DebugConfig.chat_template_formatting:
                print(f"[DEBUG-TEMPLATE] Error finding template combo: {e}")
        
        # Track the current model selection during this session (for reconnects)
        self._current_model_selection = None
        
        # Create PER-INSTANCE signal object (prevents broadcast to other managers)
        self.signals = ConnectionSignals()
        
        # Connect signals for thread-safe UI updates
        self.signals.connection_succeeded.connect(self._on_connection_succeeded)
        self.signals.connection_failed.connect(self._on_connection_failed)
        self.signals.models_loaded.connect(self._on_models_loaded)
        self.signals.models_load_failed.connect(self._on_models_load_failed)
    
    def connect_to_server(self):
        """Test connection to server"""
        self.connect_button.setText("Connecting...")
        self.connect_button.setEnabled(False)
        
        thread = threading.Thread(target=self._test_connection)
        thread.daemon = True
        thread.start()
    
    def _test_connection(self):
        """Test connection in background thread - uses signals to update UI safely"""
        try:
            print(f"[DEBUG-CONNECTION] Starting connection test in background thread...")
            if self.client.test_connection():
                print(f"[DEBUG-CONNECTION] Connection test succeeded, emitting signal")
                self.signals.connection_succeeded.emit()
            else:
                print(f"[DEBUG-CONNECTION] Connection test failed")
                self.signals.connection_failed.emit("Connection failed")
        except Exception as e:
            print(f"[DEBUG-CONNECTION] Connection test exception: {e}")
            import traceback
            traceback.print_exc()
            self.signals.connection_failed.emit(str(e))
        finally:
            # Re-enable button in main thread via signal
            self.connect_button.setText("Connect")
            self.connect_button.setEnabled(True)
    
    def _on_connection_succeeded(self):
        """Handle successful connection (called from main thread via signal)"""
        print(f"[DEBUG-CONNECTION] {self.server_type.upper()} Connection succeeded signal received, updating UI")
        self.update_connection_status(connected=True)
        # Store current selection before refresh (only for Ollama, not Llama-Server)
        if self.model_combo is not None:
            self._current_model_selection = self.model_combo.currentText()
        self.refresh_models()
        self.refresh_templates()
    
    def _on_connection_failed(self, error_msg):
        """Handle failed connection (called from main thread via signal)"""
        print(f"[DEBUG-CONNECTION] {self.server_type.upper()} Connection failed signal received: {error_msg}")
        self.update_connection_status(connected=False, error=error_msg)
    
    def _is_current_tab(self):
        """Check if this tab is the currently active tab in the tab widget"""
        try:
            parent = self.chat_tab.parent()
            if parent and hasattr(parent, 'currentWidget'):
                return parent.currentWidget() is self.chat_tab
        except:
            pass
        return False
    
    def update_connection_status(self, connected=False, error=None):
        """Update connection status display"""
        self.chat_tab.is_connected = connected
        
        if connected:
            self.status_label.setText("🟢 Connected")
            self.status_label.setStyleSheet("color: #00aa00; font-weight: bold;")
            
            # Update global status panel with this server's connection
            if self.server_type == "ollama":
                server_display = "Ollama Connected"
            else:  # llama-server
                server_display = "Llama-Server Connected"
            
            if hasattr(self.app, 'status_panel'):
                self.app.status_panel.set_connection_status(True, server_display, server_type=self.server_type)
            
            # Show initial prompt so user knows to type
            if hasattr(self.chat_tab, 'response_manager'):
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.chat_tab.response_manager.display_message("", is_user=True, timestamp=timestamp)
            
            # Scroll to bottom
            self.message_display.verticalScrollBar().setValue(
                self.message_display.verticalScrollBar().maximum()
            )
        else:
            self.status_label.setText(f"🔴 Disconnected{': ' + error if error else ''}")
            self.status_label.setStyleSheet("color: #cc0000; font-weight: bold;")
            
            # Update status panel - show offline for this server
            if hasattr(self.app, 'status_panel'):
                if self.server_type == "ollama":
                    server_display = "Ollama Offline"
                else:
                    server_display = "Llama-Server Offline"
                self.app.status_panel.set_connection_status(False, server_display, server_type=self.server_type)
        
        # Update input border based on connection state
        if hasattr(self.chat_tab, 'update_input_border_state'):
            self.chat_tab.update_input_border_state()
    
    def refresh_models(self):
        """Refresh list of available models"""
        thread = threading.Thread(target=self._load_models)
        thread.daemon = True
        thread.start()
    
    def _load_models(self):
        """Load models from server in background thread - uses signals to update UI safely"""
        try:
            print(f"[DEBUG-MODELS] Loading models from server...")
            models = self.client.get_available_models()
            if models:
                print(f"[DEBUG-MODELS] Loaded {len(models)} models, emitting signal")
                self.signals.models_loaded.emit(models)
            else:
                self.signals.models_load_failed.emit("No models available")
        except Exception as e:
            print(f"[DEBUG-MODELS] Error loading models: {e}")
            self.signals.models_load_failed.emit(str(e))
    
    def _on_models_loaded(self, models):
        """Handle models loaded - called from main thread via signal"""
        print(f"[DEBUG-MODELS] Models loaded signal received, updating UI with {len(models)} models")
        if DebugConfig.chat_enabled:
            print(f"[DEBUG-MODELS] Full model list from server: {models}")
        try:
            # Skip if no model combo (Llama-Server doesn't have one)
            if self.model_combo is None:
                print(f"[DEBUG-MODELS] Skipping model loading - Llama-Server doesn't support model selection")
                return
            
            # Remember the currently selected model
            current_selection = self.model_combo.currentText()
            if current_selection.startswith("("):  # Skip placeholder text
                current_selection = None
            
            # Block signals while populating combo to prevent triggering on_model_selected for each item
            self.model_combo.blockSignals(True)
            try:
                self.model_combo.clear()
                # Filter out embedding and non-chat models
                chat_models = [m for m in models if self._is_chat_model(m)]
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG-MODELS] After filtering: {len(chat_models)} chat models: {chat_models}")
                for model in chat_models:
                    self.model_combo.addItem(model)
                
                # SIMPLE LOGIC: Just restore if the model is actually in the list
                from settings_manager import load_settings
                current_settings = load_settings()
                tab_prefix = ""
                if "ollama" in self.server_type.lower():
                    tab_prefix = "ollama_"
                elif "llama" in self.server_type.lower():
                    tab_prefix = "llama-server_"
                
                saved_model = current_settings.get(f"{tab_prefix}server_model", None)
                
                # Only restore if the saved model is ACTUALLY in the current list
                if saved_model and saved_model in chat_models:
                    index = self.model_combo.findText(saved_model)
                    if index >= 0:
                        self.model_combo.setCurrentIndex(index)
                        self._current_model_selection = saved_model
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG-MODELS] ✓ Restored saved model (found in list): {saved_model}")
                elif chat_models:
                    # Default to first model
                    self.model_combo.setCurrentIndex(0)
                    self._current_model_selection = chat_models[0]
                    if saved_model:
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG-MODELS] ⚠️ Saved model '{saved_model}' NOT in current list, using first: {chat_models[0]}")
                    else:
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG-MODELS] No saved model, using first: {chat_models[0]}")
            finally:
                # Re-enable signals after restoration
                self.model_combo.blockSignals(False)
            
            # Update status panel with server type (only if this tab is active)
            if self._is_current_tab():
                if self.server_type == "ollama":
                    server_display = "Ollama Connected"
                else:  # llama-server
                    server_display = "Llama-Server Connected"
                if hasattr(self.app, 'status_panel'):
                    self.app.status_panel.set_connection_status(True, server_display, server_type=self.server_type)
        except Exception as e:
            print(f"[DEBUG-MODELS] Error in _on_models_loaded: {e}")
    
    def _on_models_load_failed(self, error_msg):
        """Handle models load failure - called from main thread via signal"""
        print(f"[DEBUG-MODELS] Models load failed: {error_msg}")
    
    def refresh_templates(self):
        """Refresh list of available chat templates"""
        if not self.template_combo:
            # Template combo was removed from UI, skip
            return
        
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        
        # Add all available templates
        for template_name in template_manager.get_available_templates():
            self.template_combo.addItem(template_name)
        
        # Restore saved selection or default to "auto"
        saved_template = get_setting("chat_template_selection", "auto")
        index = self.template_combo.findText(saved_template)
        if index >= 0:
            self.template_combo.setCurrentIndex(index)
            if DebugConfig.chat_template_formatting:
                print(f"[DEBUG-TEMPLATE] Restored template: {saved_template}")
        else:
            # Default to "auto"
            self.template_combo.setCurrentIndex(0)
            if DebugConfig.chat_template_formatting:
                print(f"[DEBUG-TEMPLATE] No saved template, defaulting to: auto")
        
        self.template_combo.blockSignals(False)
    
    def on_model_selected(self, model_name):
        """Handle model selection change"""
        # Don't save placeholder text
        if model_name.startswith("("):
            return
        
        # Track current model selection in session (for reconnects)
        self._current_model_selection = model_name
        
        # Update status panel with server type (only if this tab is active)
        if self._is_current_tab():
            if self.server_type == "ollama":
                server_display = "Ollama Connected"
            else:  # llama-server
                server_display = "Llama-Server Connected"
            if hasattr(self.app, 'status_panel'):
                self.app.status_panel.set_connection_status(True, server_display, server_type=self.server_type)
        
        # Determine the tab prefix for settings
        tab_prefix = ""
        if "ollama" in self.server_type.lower():
            tab_prefix = "ollama_"
        elif "llama" in self.server_type.lower():
            tab_prefix = "llama-server_"
        
        # Track model selection in settings - save immediately
        from settings_manager import set_setting
        set_setting(f"{tab_prefix}server_model", model_name)
        if DebugConfig.chat_enabled:
            print(f"[DEBUG] Model saved immediately: {model_name}")
    
    def on_template_selected(self, template_name):
        """Handle template selection change"""
        if not self.template_combo:
            # Template combo was removed from UI, skip
            return
        
        print(f"[DEBUG] on_template_selected() called with: {template_name}")
        if template_name and not template_name.startswith("("):
            print(f"[DEBUG] Saving template: {template_name}")
            set_setting("chat_template_selection", template_name)
            if DebugConfig.chat_template_formatting:
                print(f"[DEBUG-TEMPLATE] Selected and saved template: {template_name}")
        else:
            print(f"[DEBUG] Skipping template save - placeholder or empty")
