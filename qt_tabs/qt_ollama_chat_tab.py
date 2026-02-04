"""
Ollama Chat Tab for PyQt5
"""
# pylint: disable=no-name-in-module

from .qt_chat_tab_base import QtChatTabBase


class QtOllamaChatTab(QtChatTabBase):
    """Ollama chat tab implementation"""
    
    def __init__(self, app):
        super().__init__(app, "ollama", app.ollama_client)

