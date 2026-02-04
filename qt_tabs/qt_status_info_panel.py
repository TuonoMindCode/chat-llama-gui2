"""
Status Info Panel - Shows real-time status of various components
Displays at bottom corner of the app
"""
# pylint: disable=no-name-in-module

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from debug_config import DebugConfig


class QtStatusInfoPanel(QFrame):
    """Status info panel showing various app status indicators"""
    
    # Signals for status updates
    status_changed = pyqtSignal(str)  # Emits status text
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Status tracking
        self.status_info = {
            'connection': '🔴 Offline',
            'llm_status': '⏸️ Idle',
            'whisper_status': '🎤 Off',
            'comfyui_status': '🖼️ Idle',
            'last_tokens': '',
            'custom_info': ''
        }
        
        # Per-server connection status tracking - initialize both servers as offline
        self._server_status = {
            "ollama": "🔴 ollama: offline",
            "llama-server": "🔴 llama-server: offline"
        }
        
        # Update timer for info refresh (will be started after widgets are created)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_display)
        
        self.create_widgets()
        self.apply_styles()
        
        # Start timer after widgets are fully initialized
        self.update_timer.start(500)  # Update every 500ms
    
    def create_widgets(self):
        """Create status panel UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(15)
        
        # Connection status
        self.connection_label = QLabel("🔴 Offline")
        self.connection_label.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(self.connection_label)
        
        # Separator
        sep1 = QLabel("│")
        sep1.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(sep1)
        
        # LLM Status
        self.llm_status_label = QLabel("⏸️ Idle")
        self.llm_status_label.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(self.llm_status_label)
        
        # Separator
        sep2 = QLabel("│")
        sep2.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(sep2)
        
        # Whisper Status
        self.whisper_status_label = QLabel("🎤 Off")
        self.whisper_status_label.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(self.whisper_status_label)
        
        # Separator
        sep3 = QLabel("│")
        sep3.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(sep3)
        
        # ComfyUI Status
        self.comfyui_status_label = QLabel("🖼️ Idle")
        self.comfyui_status_label.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(self.comfyui_status_label)
        
        # Separator
        sep4 = QLabel("│")
        sep4.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(sep4)
        
        # Tokens info
        self.tokens_label = QLabel("")
        self.tokens_label.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(self.tokens_label)
        
        # Separator
        sep5 = QLabel("│")
        sep5.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(sep5)
        
        # Custom info
        self.custom_info_label = QLabel("")
        self.custom_info_label.setFont(QFont("Courier", 10, QFont.Bold))
        layout.addWidget(self.custom_info_label)
        
        # Add stretch to push everything to the left
        layout.addStretch()
        
        self.setLayout(layout)
    
    def apply_styles(self):
        """Apply styles to the status panel"""
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-top: 1px solid #cccccc;
                border-left: 1px solid #cccccc;
                min-height: 32px;
            }
            
            QLabel {
                color: #333333;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                font-weight: bold;
            }
        """)
    
    def set_connection_status(self, connected, model_name="", server_type=None):
        """Update connection status for a specific server
        
        Args:
            connected: bool - Whether connected
            model_name: str - Current server/model name (unused, kept for compatibility)
            server_type: str - "ollama" or "llama-server" to update specific server
        """
        if server_type:
            # Ensure both servers are initialized
            if not hasattr(self, '_server_status'):
                self._server_status = {}
            if "ollama" not in self._server_status:
                self._server_status["ollama"] = "🔴 ollama: offline"
            if "llama-server" not in self._server_status:
                self._server_status["llama-server"] = "🔴 llama-server: offline"
            
            # Update ONLY the requested server
            if connected:
                self._server_status[server_type] = f"🟢 {server_type}: connected"
            else:
                self._server_status[server_type] = f"🔴 {server_type}: offline"
            
            if DebugConfig.connection_status:
                print(f"[DEBUG-STATUS] Updated {server_type}: {'connected' if connected else 'offline'}")
                print(f"[DEBUG-STATUS] Full status dict: {self._server_status}")
            
            # Build combined status showing both servers
            statuses = []
            if "ollama" in self._server_status:
                statuses.append(self._server_status["ollama"])
            if "llama-server" in self._server_status:
                statuses.append(self._server_status["llama-server"])
            
            if statuses:
                self.status_info['connection'] = " | ".join(statuses)
                if DebugConfig.connection_status:
                    print(f"[DEBUG-STATUS] Combined display: {self.status_info['connection']}")
            else:
                self.status_info['connection'] = "🔴 Offline"
        else:
            # Legacy single-server mode
            if connected:
                if model_name:
                    self.status_info['connection'] = f"🟢 {model_name}"
                else:
                    self.status_info['connection'] = "🟢 Connected"
            else:
                self.status_info['connection'] = "🔴 Offline"
        
        self.refresh_display()
    
    def set_llm_status(self, status):
        """Update LLM status
        
        Args:
            status: One of 'idle', 'thinking', 'generating'
        """
        status_map = {
            'idle': '⏸️ Idle',
            'thinking': '🤔 Thinking...',
            'generating': '✍️ Generating...',
            'streaming': '📝 Streaming...'
        }
        self.status_info['llm_status'] = status_map.get(status, status)
        self.refresh_display()
    
    def set_whisper_status(self, active):
        """Update Whisper/Mic status"""
        self.status_info['whisper_status'] = "🎤 Recording" if active else "🎤 Off"
        self.refresh_display()
    
    def set_comfyui_status(self, status):
        """Update ComfyUI status
        
        Args:
            status: One of 'idle', 'generating', 'error'
        """
        status_map = {
            'idle': '🖼️ Idle',
            'generating': '🎨 Generating...',
            'error': '❌ Error',
            'queued': '⏳ Queued...'
        }
        self.status_info['comfyui_status'] = status_map.get(status, status)
        self.refresh_display()
    
    def set_token_count(self, prompt_tokens=None, generated_tokens=None, server_type=None):
        """Update token count display
        
        Args:
            prompt_tokens: Number of tokens in prompt
            generated_tokens: Number of tokens generated in response
            server_type: "ollama" or "llama-server" for prefix label
        """
        if prompt_tokens is not None and generated_tokens is not None:
            total = prompt_tokens + generated_tokens
            # Add server-specific prefix
            if server_type == "ollama":
                prefix = "Ollama: "
            elif server_type == "llama-server":
                prefix = "Llama: "
            else:
                prefix = ""
            self.status_info['last_tokens'] = f"📊 {prefix}{prompt_tokens}+{generated_tokens}={total} tokens"
        else:
            self.status_info['last_tokens'] = ''
        self.refresh_display()
    
    def set_custom_info(self, text):
        """Set custom info text
        
        Args:
            text: Custom status text to display
        """
        self.status_info['custom_info'] = text
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh all status labels"""
        self.connection_label.setText(self.status_info['connection'])
        self.llm_status_label.setText(self.status_info['llm_status'])
        self.whisper_status_label.setText(self.status_info['whisper_status'])
        self.comfyui_status_label.setText(self.status_info['comfyui_status'])
        
        # Only show tokens if available
        if self.status_info['last_tokens']:
            self.tokens_label.setText(self.status_info['last_tokens'])
            self.tokens_label.show()
        else:
            self.tokens_label.hide()
        
        # Only show custom info if available
        if self.status_info['custom_info']:
            self.custom_info_label.setText(self.status_info['custom_info'])
            self.custom_info_label.show()
        else:
            self.custom_info_label.hide()
