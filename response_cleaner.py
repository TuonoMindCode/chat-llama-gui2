"""
Response cleaner - removes hallucinated conversation exchanges from LLM responses
"""

import re


class ResponseCleaner:
    """Cleans LLM responses by removing unwanted patterns"""
    
    @staticmethod
    def clean_response(response_text):
        """
        Clean response by removing hallucinated conversation exchanges
        Examples of patterns to remove:
        - "USER: ..." (model quoting previous user message)
        - "OLLAMA: ..." (model quoting itself)
        - "ASSISTANT: ..." (model quoting assistant)
        - "[HH:MM:SS] You: ..." (model repeating chat format)
        - Everything after "[INST]" or "[/INST]" tokens (stop sequence failure)
        
        Returns cleaned response
        """
        if not response_text or not isinstance(response_text, str):
            return response_text
        
        # If stop sequence failed and [INST] appears, truncate there
        if "[INST]" in response_text:
            response_text = response_text.split("[INST]")[0]
        if "[/INST]" in response_text:
            response_text = response_text.split("[/INST]")[0]
        
        lines = response_text.split('\n')
        cleaned_lines = []
        skip_next_empty = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip lines that look like quoted chat messages
            if ResponseCleaner._is_quoted_message(stripped):
                skip_next_empty = True
                continue
            
            # Skip empty lines after removed messages
            if skip_next_empty and not stripped:
                skip_next_empty = False
                continue
            
            skip_next_empty = False
            cleaned_lines.append(line)
        
        # Remove leading/trailing empty lines
        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()
        
        result = '\n'.join(cleaned_lines)
        
        # If we removed a significant portion, log it
        if len(result) < len(response_text) * 0.7:  # Removed more than 30%
            removed_chars = len(response_text) - len(result)
            print(f"[RESPONSE-CLEAN] Removed {removed_chars} chars ({(removed_chars/len(response_text)*100):.1f}%) from response")
        
        return result
    
    @staticmethod
    def _is_quoted_message(line):
        """Check if line looks like a quoted chat message"""
        if not line:
            return False
        
        # Pattern: "USER: ..." or "ASSISTANT: ..." or "OLLAMA: ..."
        if re.match(r'^(USER|ASSISTANT|OLLAMA|SARA|YOU):\s', line):
            return True
        
        # Pattern: "[HH:MM:SS] You: ..." or "[YYYY-MM-DD HH:MM:SS] OLLAMA: ..."
        if re.match(r'^\[\d{2}:\d{2}:\d{2}\]\s', line):
            return True
        if re.match(r'^\[\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\]\s', line):
            return True
        
        # Pattern: "- User said: ..." or "- Assistant responded: ..."
        if re.match(r'^-\s(User|Assistant|OLLAMA|You|I said)', line, re.IGNORECASE):
            return True
        
        return False
