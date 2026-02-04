"""
Chat template formatter for different LLM chat formats
Supports: ChatML, Alpaca, and plain text formats
"""

from typing import List, Dict


class ChatTemplateFormatter:
    """Format messages according to different chat template standards"""
    
    def __init__(self, template: str = "chatml"):
        """
        Initialize formatter with template type
        
        Args:
            template: "chatml", "alpaca", or "plain"
        """
        self.template = template.lower()
    
    def format_messages(self, messages: List[Dict], system_prompt: str = "") -> str:
        """
        Format messages according to the template
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: System prompt to prepend (if not in messages)
            
        Returns:
            Formatted prompt string
        """
        if self.template == "chatml":
            return self._format_chatml(messages, system_prompt)
        elif self.template == "alpaca":
            return self._format_alpaca(messages, system_prompt)
        else:
            return self._format_plain(messages, system_prompt)
    
    def _format_chatml(self, messages: List[Dict], system_prompt: str = "") -> str:
        """
        Format using ChatML template
        Used by: Dolphin, Hermes, and other models using chat templates
        
        Format:
        <|im_start|>system
        {system}<|im_end|>
        <|im_start|>user
        {user message}<|im_end|>
        <|im_start|>assistant
        """
        parts = []
        
        # Add system message first
        has_system = False
        for msg in messages:
            if msg.get("role", "").lower() == "system":
                parts.append(f"<|im_start|>system\n{msg.get('content', '')}<|im_end|>")
                has_system = True
                break
        
        # If no system message in array but provided as parameter, add it
        if not has_system and system_prompt:
            parts.append(f"<|im_start|>system\n{system_prompt}<|im_end|>")
        
        # Add conversation messages
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            # Skip system messages (already added)
            if role == "system":
                continue
            
            # Map roles to ChatML format
            if role in ["user", "assistant"]:
                parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        
        # Close with assistant prompt
        parts.append("<|im_start|>assistant")
        
        return "\n".join(parts)
    
    def _format_alpaca(self, messages: List[Dict], system_prompt: str = "") -> str:
        """
        Format using Alpaca template
        Used by: Alpaca, and other instruction-tuned models
        
        Format:
        system: {system}
        
        {user message}
        """
        parts = []
        
        # Add system message
        system = system_prompt
        for msg in messages:
            if msg.get("role", "").lower() == "system":
                system = msg.get("content", "")
                break
        
        if system:
            parts.append(f"system: {system}\n")
        
        # Add user messages
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "system":
                continue
            elif role == "user":
                parts.append(f"{content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        
        return "\n".join(parts)
    
    def _format_plain(self, messages: List[Dict], system_prompt: str = "") -> str:
        """
        Format using plain text template
        Simple format without special tokens
        
        Format:
        SYSTEM: {system}
        USER: {message}
        ASSISTANT: {response}
        """
        parts = []
        
        # Add system message
        has_system = False
        for msg in messages:
            if msg.get("role", "").lower() == "system":
                parts.append(f"SYSTEM: {msg.get('content', '')}")
                has_system = True
                break
        
        if not has_system and system_prompt:
            parts.append(f"SYSTEM: {system_prompt}")
        
        # Add conversation
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "system":
                continue
            elif role == "user":
                parts.append(f"USER: {content}")
            elif role == "assistant":
                parts.append(f"ASSISTANT: {content}")
        
        return "\n".join(parts)


# Default formatters
CHATML_FORMATTER = ChatTemplateFormatter("chatml")
ALPACA_FORMATTER = ChatTemplateFormatter("alpaca")
PLAIN_FORMATTER = ChatTemplateFormatter("plain")


def format_with_template(messages: List[Dict], template: str = "chatml", system_prompt: str = "") -> str:
    """
    Convenience function to format messages with specified template
    
    Args:
        messages: List of message dicts
        template: Template type ("chatml", "alpaca", "plain")
        system_prompt: System prompt (if not in messages)
        
    Returns:
        Formatted prompt string
    """
    formatter = ChatTemplateFormatter(template)
    return formatter.format_messages(messages, system_prompt)
