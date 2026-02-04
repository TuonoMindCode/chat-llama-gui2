"""
Text utility functions for cleaning and processing text
"""

import re


def clean_text_for_tts(text):
    """
    Clean text by removing markdown formatting for TTS readability.
    
    Removes:
    - Bold markers: **text**, __text__
    - Italic markers: *text*, _text_
    - Strikethrough: ~~text~~
    - Inline code: `text`
    - Links: [text](url) -> text
    - Images: ![alt](url) -> [alt text]
    - Headers: # heading -> heading
    - Blockquotes: > text -> text
    - Lists: - item, * item, + item -> item
    - HTML tags: <tag>text</tag> -> text
    - Extra whitespace
    
    Args:
        text: Text string to clean
        
    Returns:
        Cleaned text string
    """
    if not text or not isinstance(text, str):
        return text
    
    # Remove bold markers: **text** or __text__ -> text
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # Remove empty bold markers: ** -> (nothing)
    text = re.sub(r'\*\*', '', text)
    text = re.sub(r'__', '', text)
    
    # Remove italic markers: *text* or _text_ -> text (non-greedy, but avoid matching ** or __)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', text)
    # Remove any remaining single asterisks and underscores that are formatting marks
    text = re.sub(r'(?<!\w)\*(?!\*)', '', text)
    text = re.sub(r'(?<!\w)_(?!_)', '', text)
    
    # Remove strikethrough: ~~text~~ -> text
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    text = re.sub(r'~~', '', text)
    
    # Remove inline code: `text` -> text
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'`', '', text)
    
    # Remove image markdown but keep alt text: ![alt](url) -> alt
    text = re.sub(r'!\[(.+?)\]\(.+?\)', r'\1', text)
    
    # Remove links but keep the text: [text](url) -> text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    
    # Remove HTML tags: <tag>text</tag> -> text
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove header markers from line start: # heading -> heading
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove blockquote markers from line start: > text -> text
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove list markers from line start: - item, * item, + item -> item
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    
    # Remove any remaining special characters that shouldn't be spoken
    # Keep: letters, numbers, spaces, common punctuation (. , ! ? : ; ' " - ())
    text = re.sub(r'[^\w\s.,!?:;\'"\-()—–…]', '', text)
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text
