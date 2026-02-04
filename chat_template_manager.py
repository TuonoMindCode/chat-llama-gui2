"""
Chat Template Manager
Manages loading, saving, and applying chat templates
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from debug_config import DebugConfig


class ChatTemplateManager:
    """Manage chat templates from files"""
    
    def __init__(self, template_folder: str = "chat_template_files"):
        """Initialize template manager
        
        Args:
            template_folder: Folder containing template files
        """
        self.template_folder = Path(template_folder)
        self.template_folder.mkdir(exist_ok=True)
        
        # Built-in templates (hardcoded)
        self.builtin_templates = {
            "chatml": "<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant",
            "zephyr": "<|system|>\n{system_prompt}<|user|>\n{prompt}\n<|assistant|>",
            "alpaca": "system: {system_prompt}\n\n{prompt}\n\nA:",
            "plain": "SYSTEM: {system_prompt}\n\nUSER: {prompt}\n\nA:"
        }
    
    def get_available_templates(self) -> List[str]:
        """Get list of available templates
        
        Returns:
            List of template names: ["auto", "built-in: chatml", "custom: file1", ...]
        """
        templates = ["auto"]
        
        # Add built-in templates
        for name in self.builtin_templates.keys():
            templates.append(f"built-in: {name}")
        
        # Add custom templates from files
        if self.template_folder.exists():
            for file in sorted(self.template_folder.glob("*.txt")):
                template_name = file.stem
                # Skip if it's a built-in template
                if template_name not in self.builtin_templates:
                    templates.append(f"custom: {template_name}")
        
        return templates
    
    def format_prompt(self, template_name: str, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Format prompt using selected template
        
        Args:
            template_name: Template to use ("auto", "built-in: chatml", "custom: xyz")
            system_prompt: System/instruction prompt
            user_prompt: User message
            
        Returns:
            Formatted prompt string, or None for auto mode
        """
        if template_name == "auto":
            # Auto mode: don't format, return None to signal no formatting
            return None
        
        if template_name.startswith("built-in: "):
            # Built-in template
            template_key = template_name.replace("built-in: ", "")
            template_content = self.builtin_templates.get(template_key)
            if not template_content:
                print(f"[WARN] Built-in template not found: {template_key}, using auto")
                return None
        
        elif template_name.startswith("custom: "):
            # Custom template from file
            template_key = template_name.replace("custom: ", "")
            template_path = self.template_folder / f"{template_key}.txt"
            
            if not template_path.exists():
                print(f"[WARN] Template file not found: {template_path}, using auto")
                return None
            
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
            except Exception as e:
                print(f"[ERROR] Failed to read template {template_path}: {e}, using auto")
                return None
        
        else:
            print(f"[WARN] Unknown template format: {template_name}, using auto")
            return None
        
        # Replace placeholders
        formatted = template_content.replace("{system_prompt}", system_prompt)
        formatted = formatted.replace("{prompt}", user_prompt)
        
        if DebugConfig.chat_template_formatting:
            print(f"[DEBUG-TEMPLATE] Using template: {template_name}")
            print(f"[DEBUG-TEMPLATE] Formatted prompt (first 200 chars):\n{formatted[:200]}...\n")
        
        return formatted
    
    def save_template(self, template_name: str, content: str) -> bool:
        """Save custom template to file
        
        Args:
            template_name: Name for template (without .txt)
            content: Template content
            
        Returns:
            True if successful, False otherwise
        """
        template_path = self.template_folder / f"{template_name}.txt"
        
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[DEBUG] Saved template: {template_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save template {template_path}: {e}")
            return False
    
    def load_template(self, template_name: str) -> Optional[str]:
        """Load template content
        
        Args:
            template_name: Template to load (with or without "built-in: " or "custom: " prefix)
            
        Returns:
            Template content or None if not found
        """
        # Strip prefix if present
        if template_name.startswith("built-in: "):
            template_key = template_name.replace("built-in: ", "")
            return self.builtin_templates.get(template_key)
        
        elif template_name.startswith("custom: "):
            template_key = template_name.replace("custom: ", "")
            template_path = self.template_folder / f"{template_key}.txt"
            
            if template_path.exists():
                try:
                    with open(template_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    print(f"[ERROR] Failed to read template {template_path}: {e}")
                    return None
        
        return None
    
    def delete_template(self, template_name: str) -> bool:
        """Delete custom template file
        
        Args:
            template_name: Template to delete (with "custom: " prefix)
            
        Returns:
            True if successful, False otherwise
        """
        if not template_name.startswith("custom: "):
            print(f"[WARN] Can only delete custom templates, got: {template_name}")
            return False
        
        template_key = template_name.replace("custom: ", "")
        template_path = self.template_folder / f"{template_key}.txt"
        
        try:
            template_path.unlink()
            print(f"[DEBUG] Deleted template: {template_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to delete template {template_path}: {e}")
            return False
    
    def rename_template(self, old_name: str, new_name: str) -> bool:
        """Rename custom template file
        
        Args:
            old_name: Current template name (with "custom: " prefix)
            new_name: New template name (just the name, without prefix)
            
        Returns:
            True if successful, False otherwise
        """
        if not old_name.startswith("custom: "):
            print(f"[WARN] Can only rename custom templates, got: {old_name}")
            return False
        
        old_key = old_name.replace("custom: ", "")
        old_path = self.template_folder / f"{old_key}.txt"
        new_path = self.template_folder / f"{new_name}.txt"
        
        try:
            old_path.rename(new_path)
            print(f"[DEBUG] Renamed template: {old_path} -> {new_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to rename template {old_path}: {e}")
            return False
    
    def list_custom_templates(self) -> List[str]:
        """Get list of custom template filenames (without .txt)
        
        Returns:
            List of custom template names
        """
        custom = []
        if self.template_folder.exists():
            for file in sorted(self.template_folder.glob("*.txt")):
                template_name = file.stem
                # Skip built-in templates
                if template_name not in self.builtin_templates:
                    custom.append(template_name)
        return custom


# Global instance
template_manager = ChatTemplateManager()
