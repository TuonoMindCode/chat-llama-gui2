"""
Trivia Tracker - Manages daily trivia facts shown in LLM responses
Tracks which trivia has been shown today to avoid repetition
"""

from datetime import datetime
from settings_manager import load_settings, save_settings


class TriviaTracker:
    """Track daily trivia to avoid repetition within a day"""
    
    @staticmethod
    def get_today_key():
        """Get today's trivia tracking key (YYYY_MM_DD format)"""
        today = datetime.now().strftime("%Y_%m_%d")
        return f"trivia_shown_{today}"
    
    @staticmethod
    def get_shown_trivia_list():
        """Get list of trivia already shown today"""
        try:
            settings = load_settings()
            today_key = TriviaTracker.get_today_key()
            trivia_list = settings.get(today_key, [])
            return trivia_list if isinstance(trivia_list, list) else []
        except Exception as e:
            print(f"[TRIVIA] Error loading trivia list: {e}")
            return []
    
    @staticmethod
    def add_trivia(trivia_text):
        """Add trivia to today's list (avoid duplicates)"""
        try:
            if not trivia_text or not trivia_text.strip():
                return
            
            settings = load_settings()
            today_key = TriviaTracker.get_today_key()
            
            trivia_list = settings.get(today_key, [])
            if not isinstance(trivia_list, list):
                trivia_list = []
            
            # Clean trivia text and check for duplicates
            clean_trivia = trivia_text.strip()
            if clean_trivia not in trivia_list:
                trivia_list.append(clean_trivia)
                settings[today_key] = trivia_list
                save_settings(settings)
                print(f"[TRIVIA] Added trivia (total today: {len(trivia_list)})")
        except Exception as e:
            print(f"[TRIVIA] Error adding trivia: {e}")
    
    @staticmethod
    def build_trivia_instruction():
        """Build instruction for LLM to add trivia"""
        shown_trivia = TriviaTracker.get_shown_trivia_list()
        
        # Base instruction - very explicit
        instruction = "\n\n**IMPORTANT - TRIVIA REQUIREMENT**: At the end of your response, add EXACTLY ONE sentence of interesting, non-political trivia that happened on this date in history. Make it fun and educational, avoiding politics. "
        
        if shown_trivia:
            # Make it VERY clear what NOT to repeat
            instruction += f"**DO NOT repeat these facts** (already shared today): "
            instruction += " | ".join([f"[{i+1}] {fact[:80]}" for i, fact in enumerate(shown_trivia[:5])])  # Show first 80 chars of each, max 5
            instruction += " | **Share a NEW and DIFFERENT fact instead.**"
        else:
            instruction += "This is the first trivia of the day, so pick something interesting!"
        
        return instruction
    
    @staticmethod
    def cleanup_old_trivia():
        """Remove old trivia entries from settings (keep only today's trivia)"""
        try:
            settings = load_settings()
            today_key = TriviaTracker.get_today_key()
            
            # Find all trivia keys (format: trivia_shown_YYYY_MM_DD)
            keys_to_remove = []
            for key in settings.keys():
                if key.startswith("trivia_shown_") and key != today_key:
                    keys_to_remove.append(key)
            
            # Remove old entries
            if keys_to_remove:
                for key in keys_to_remove:
                    del settings[key]
                save_settings(settings)
                print(f"[TRIVIA] Cleaned up {len(keys_to_remove)} old trivia entries: {keys_to_remove}")
                return len(keys_to_remove)
            
            return 0
        except Exception as e:
            print(f"[TRIVIA] Error cleaning up old trivia: {e}")
            return 0
    
    @staticmethod
    def extract_trivia_from_response(response_text):
        """
        Extract trivia from response - looks for 'fun fact' or 'did you know' patterns
        Captures and cleans the full trivia statement
        """
        try:
            if not response_text or not response_text.strip():
                return None
            
            text = response_text.strip()
            
            # Look for "fun fact:" or "did you know" pattern (case-insensitive)
            fun_fact_idx = text.lower().find("fun fact")
            did_you_know_idx = text.lower().find("did you know")
            
            # Find which pattern appears last (most recent in response)
            start_idx = -1
            if fun_fact_idx >= 0 and did_you_know_idx >= 0:
                start_idx = max(fun_fact_idx, did_you_know_idx)
            elif fun_fact_idx >= 0:
                start_idx = fun_fact_idx
            elif did_you_know_idx >= 0:
                start_idx = did_you_know_idx
            
            if start_idx < 0:
                return None
            
            # Extract from the keyword to the end
            trivia = text[start_idx:].strip()
            
            # Clean up - remove excessive punctuation
            trivia = trivia.rstrip('.,!?;')
            
            # Remove markdown formatting if present
            trivia = trivia.replace('**', '')
            trivia = trivia.replace('__', '')
            
            if len(trivia) > 30:  # Must be substantive (longer than short phrase)
                return trivia
            
            return None
        except Exception as e:
            print(f"[TRIVIA] Error extracting trivia: {e}")
            return None

    @staticmethod
    def remove_trivia_from_response(response_text):
        """
        Aggressively remove trivia sentences - finds and removes sentences with date/trivia patterns
        Returns response with trivia removed
        """
        try:
            if not response_text or not response_text.strip():
                return response_text
            
            import re
            text = response_text.strip()
            sentences = text.split('.')
            
            filtered_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                lower = sentence.lower()
                
                # Skip sentences that contain trivia markers
                trivia_markers = [
                    "fun fact",
                    "did you know",
                    "interesting fact",
                    "in history",
                    "on this date",
                    "this day in",
                    "historical",
                    "trivia"
                ]
                
                # Check if any trivia marker present
                has_trivia = any(marker in lower for marker in trivia_markers)
                
                # Also check for year/date patterns (e.g., "1492", "2024", "January 1")
                if not has_trivia:
                    # Pattern: numbers that look like years or date references
                    has_date = bool(re.search(r'\b(1\d{3}|2\d{3})\b', sentence))  # Years like 1492, 2024
                    # Also check for month/day combinations
                    if not has_date:
                        has_date = bool(re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+', lower))
                    
                    if has_date and len(sentence) < 200:  # Short sentences with dates are likely trivia
                        has_trivia = True
                
                if not has_trivia:
                    filtered_sentences.append(sentence)
            
            # Rejoin sentences
            result = '. '.join(filtered_sentences).strip()
            
            # Clean up spacing and extra periods
            result = re.sub(r'\s+', ' ', result)  # Collapse multiple spaces
            result = result.rstrip(' .')
            
            if result != text:
                print(f"[TRIVIA] Removed trivia from response")
            
            return result
        except Exception as e:
            print(f"[TRIVIA] Error removing trivia: {e}")
            return response_text
