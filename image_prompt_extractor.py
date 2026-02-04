"""
Image Prompt Extractor using a small 2B LLM model
Extracts image generation prompts from LLM responses
Supports both Ollama and Llama Server (local models only)
"""

import re
from debug_config import DebugConfig


class ImagePromptExtractor:
    """Extracts and creates image prompts from LLM responses using a 2B model"""
    
    def __init__(self, model="dolphin-2.1:2.4b", provider="ollama", provider_url="http://localhost:11434",
                 system_prompt=None, user_prompt_template=None):
        """
        Initialize the prompt extractor
        
        Args:
            model: Small 2B LLM model name (default: dolphin-2.1:2.4b)
            provider: "ollama" or "llama_server"
            provider_url: URL to the provider
            system_prompt: Custom system prompt for extraction
            user_prompt_template: Custom user prompt template (must contain {response} placeholder)
        """
        self.model = model
        self.provider = provider
        self.provider_url = provider_url
        
        # Initialize appropriate client
        if provider == "ollama":
            from ollama_client import OllamaClient
            self.client = OllamaClient(provider_url)
        elif provider == "llama_server":
            from llama_client import LlamaServerClient
            self.client = LlamaServerClient(provider_url)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Set prompts (use defaults if not provided)
        self.system_prompt = system_prompt or """You are a faithful visual description extractor for a single, unified location. When text describes multiple different locations (interior and exterior, different rooms, etc.), identify them and extract ONLY visual elements from the PRIMARY/FIRST location. Do NOT mix descriptions from different locations. Do NOT include non-visual sensory information (sounds, smells, tastes, emotions). Extract ONLY what is visually described in ONE cohesive scene. Be precise, faithful to the source location, and do NOT hallucinate. Create prompts that are 1-2 paragraphs long, describing ONLY the visual scene from ONE location as described in the source text."""
        
        self.user_prompt_template = user_prompt_template or """**CRITICAL INSTRUCTION - EXTRACT ONLY VISUAL ELEMENTS FROM ONE LOCATION**

You are creating an image generation prompt. ONLY describe what can be SEEN in ONE unified scene/location.

**GOLDEN RULES - FOLLOW EXACTLY:**
1. **SINGLE LOCATION**: If the source describes multiple different locations (outside/inside, different rooms), choose the PRIMARY/FIRST location and extract ONLY from that
2. **VISUAL ONLY**: Include ONLY what you can SEE - no smells, sounds, tastes, feelings, or emotions
3. **DO NOT INVENT**: Do not add details, locations, relationships, or context not explicitly mentioned
4. **DO NOT MIX LOCATIONS**: If text describes both exterior and interior, pick ONE - don't combine them
5. **NO HALLUCINATIONS**: If something isn't described visually in the source, do not include it

**LOCATION DETECTION:**
- Watch for transitions like "inside", "within", "entering", "beyond the doors", etc.
- Watch for clear section breaks describing different spaces
- If multiple distinct locations are described, choose the PRIMARY one (usually first/most detailed)
- Exclude descriptions that clearly belong to OTHER locations

**WHAT TO EXTRACT AND INCLUDE:**
- Objects and people that are explicitly mentioned as visible in the CHOSEN location
- Colors explicitly mentioned in that location
- Lighting and weather explicitly mentioned in that location
- Actions/movement visually described in that location
- Spatial arrangements explicitly stated in that location
- Materials and textures explicitly named
- Architectural/design details explicitly described

**WHAT TO EXCLUDE:**
- Any sensory details (smell, sound, taste, touch)
- Visual elements from OTHER locations (if multiple are described)
- Implied or inferred details not stated in source
- Emotions, moods, atmospheres not visually described
- Made-up supporting details
- Interior details if describing exterior, or vice versa

**FORMAT**: 
1-2 paragraphs describing ONLY the visual elements from ONE unified location

**EXAMPLES OF WHAT NOT TO DO:**
- Source describes "marble exterior... inside dark wood desks" → describe EITHER exterior OR interior, NOT both
- Source: "outside the building" then "inside the hall" → pick one, don't mix
- Don't include "desks" if you're describing the exterior facade

SOURCE TEXT TO EXTRACT FROM:
{response}

NOW OUTPUT THE IMAGE PROMPT - ONE LOCATION ONLY, VISUAL ELEMENTS ONLY (1-2 paragraphs, NO labels):"""
    
    def test_connection(self):
        """Test connection to provider and model availability"""
        try:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Testing {self.provider} connection to {self.provider_url}")
            response = self.client.generate(
                f"Test prompt for {self.model}",
                model=self.model,
                stream=False
            )
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Connection test successful")
            return bool(response)
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Prompt extractor connection error: {e}")
            return False
    
    def extract_prompt(self, response_text, temperature=0.3, min_response_length=100, timeout=120):
        """
        Extract image prompt from LLM response
        
        Args:
            response_text: Text from LLM response
            temperature: Temperature for extraction model (lower = more focused)
            min_response_length: Skip if response is shorter than this (chars)
            timeout: Request timeout in seconds
            
        Returns:
            str: Image prompt or None if extraction fails or response too short
        """
        try:
            # Check response length threshold
            if len(response_text) < min_response_length:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Response too short ({len(response_text)} chars < {min_response_length} threshold). Skipping image generation.")
                return None
            
            # Use more of the response for better context - increased from 4000 to 6000 chars
            # This allows for capturing much more detail from longer responses
            max_length = 6000
            if len(response_text) > max_length:
                response_text = response_text[:max_length] + "..."
            
            # Create extraction prompt using template
            user_prompt = self.user_prompt_template.format(response=response_text)
            
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Extracting image prompt using {self.provider}:{self.model}...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Response length: {len(response_text)} chars (max {max_length})")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Timeout: {timeout}s")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] System prompt: {self.system_prompt[:100]}...")
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] User prompt: {user_prompt[:150]}...")
            
            # Get image prompt from small model
            if self.provider == "ollama":
                result = self.client.generate(
                    user_prompt,
                    model=self.model,
                    stream=False,
                    temperature=temperature,
                    system=self.system_prompt,
                    timeout=timeout
                )
            else:  # llama_server
                result = self.client.generate(
                    user_prompt,
                    model=self.model,
                    stream=False,
                    temperature=temperature,
                    system=self.system_prompt,
                    timeout=timeout
                )
            
            if result:
                # Clean up the response
                image_prompt = result.strip()
                # Remove any leading/trailing quotes or special characters
                image_prompt = image_prompt.strip('"\'').strip()
                
                # Check for explicit rejection or failure responses
                if image_prompt.upper() in ["NOTHING", "NO", "N/A", "NONE", "ERROR"] or "not" in image_prompt.lower()[:20]:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] ✗ Model returned rejection/failure: '{image_prompt}'")
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] Try changing extraction model or adjust prompts in Image Settings tab")
                    return None
                
                # Remove common label prefixes that extraction models add
                labels_to_remove = [
                    "IMAGE PROMPT:",
                    "image prompt:",
                    "PROMPT:",
                    "prompt:",
                    "DESCRIPTION:",
                    "description:",
                    "IMAGE:",
                    "image:",
                    "DETAILED IMAGE PROMPT:",
                    "detailed image prompt:",
                ]
                for label in labels_to_remove:
                    if image_prompt.startswith(label):
                        image_prompt = image_prompt[len(label):].strip()
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Removed label: {label}")
                        break
                
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Raw extracted result: {result}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Cleaned prompt: {image_prompt}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Prompt length: {len(image_prompt)}")
                
                if image_prompt:
                    # Load settings for prefix/suffix and realistic keywords
                    from settings_manager import load_settings
                    settings = load_settings()
                    prefix = settings.get("extraction_prefix", "").strip()
                    suffix = settings.get("extraction_suffix", "").strip()
                    add_realistic = settings.get("add_realistic_keywords", False)
                    
                    # Build final prompt (apply keywords BEFORE length check)
                    final_prompt = image_prompt
                    if prefix:
                        final_prompt = f"{prefix} {final_prompt}"
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Applied prefix: {prefix}")
                    if suffix:
                        final_prompt = f"{final_prompt} {suffix}"
                        if DebugConfig.chat_enabled:
                            print(f"[DEBUG] Applied suffix: {suffix}")
                    if add_realistic:
                        # Check if realistic keywords already present
                        realistic_keywords = ["photorealistic", "realistic", "8k", "detailed", "high quality"]
                        has_keywords = any(keyword in final_prompt.lower() for keyword in realistic_keywords)
                        if not has_keywords:
                            final_prompt = f"photorealistic, detailed, 8k, high quality, {final_prompt}"
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] ✓ Added realistic keywords to prompt")
                        else:
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] ✓ Prompt already contains realistic keywords")
                    
                    # Always return if we got a prompt (keywords now applied)
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] ✓ Final image prompt: {final_prompt}")
                    return final_prompt
                else:
                    if DebugConfig.chat_enabled:
                        print(f"[DEBUG] ✗ Prompt empty")
            else:
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] ✗ No result from extraction model")
            
            return None
            
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error extracting prompt: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_multiple_prompts(self, response_text, max_prompts=3, temperature=0.3, min_response_length=100, timeout=120):
        """
        Extract multiple image prompts if multiple subjects are mentioned
        (Currently just returns one, but can be extended)
        
        Args:
            response_text: Text from LLM response
            max_prompts: Maximum prompts to extract (currently unused - always 1)
            temperature: Temperature for extraction model
            min_response_length: Skip if response is shorter than this
            timeout: Request timeout in seconds
            
        Returns:
            list: List of image prompts
        """
        # For now, just extract one combined prompt per your requirements
        prompt = self.extract_prompt(response_text, temperature, min_response_length, timeout)
        return [prompt] if prompt else []
    
    def build_image_prompt_from_keywords(self, keywords, style="photorealistic"):
        """
        Build image prompt from extracted keywords
        
        Args:
            keywords: List of keywords or subjects
            style: Art style (e.g., "photorealistic", "oil painting", "3d render")
            
        Returns:
            str: Formatted image prompt
        """
        if not keywords:
            return None
        
        # Combine keywords into a prompt
        if isinstance(keywords, list):
            subjects = ", ".join(keywords)
        else:
            subjects = keywords
        
        image_prompt = f"{subjects}, {style}, high quality, detailed, professional"
        return image_prompt
    
    def is_response_imageable(self, response_text):
        """
        Check if response likely contains image-worthy content
        
        Args:
            response_text: LLM response text
            
        Returns:
            bool: True if response seems suitable for image generation
        """
        # Keywords that suggest visual/image content
        visual_keywords = [
            'image', 'picture', 'photo', 'scene', 'view', 'landscape',
            'portrait', 'painting', 'draw', 'design', 'artwork', 'visual',
            'look', 'appear', 'see', 'show', 'demonstrate', 'illustrate',
            'character', 'person', 'place', 'object', 'thing', 'creature',
            'illustration', 'render', 'concept', 'idea', 'imagine', 'create'
        ]
        
        text_lower = response_text.lower()
        
        # Count visual keywords
        keyword_count = sum(1 for keyword in visual_keywords if keyword in text_lower)
        
        # Response is imageable if it has multiple visual keywords or is long enough
        return keyword_count >= 2 or len(response_text) > 100
    
    def get_available_models(self):
        """Get list of available models from provider"""
        try:
            if self.provider == "ollama":
                return self.client.get_available_models()
            else:  # llama_server
                return self.client.get_available_models()
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error getting models: {e}")
            return []
