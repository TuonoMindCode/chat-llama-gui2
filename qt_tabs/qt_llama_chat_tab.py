"""
Llama Chat Tab for PyQt5
"""
# pylint: disable=no-name-in-module

from .qt_chat_tab_base import QtChatTabBase


class QtLlamaChatTab(QtChatTabBase):
    """Llama Server chat tab implementation"""
    
    def __init__(self, app):
        super().__init__(app, "llama-server", app.llama_client)

