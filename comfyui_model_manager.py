"""
ComfyUI Model Manager
Handles discovery and management of ComfyUI models, checkpoints, VAE, text encoders, and loaders
Supports multiple loader types: Standard, GGUF, UNet, Diffuse
"""

from pathlib import Path
from typing import List, Dict, Optional
import json
from debug_config import DebugConfig


class ComfyUIModelManager:
    """Manages ComfyUI models, checkpoints, and loader configuration"""
    
    def __init__(self, comfyui_root: str):
        """
        Initialize model manager with ComfyUI root directory
        
        Args:
            comfyui_root: Path to ComfyUI installation root
        """
        self.comfyui_root = Path(comfyui_root)
        
        # Standard model directories
        self.checkpoints_dir = self.comfyui_root / "models" / "checkpoints"
        self.vae_dir = self.comfyui_root / "models" / "vae"
        # CLIP/Text Encoders - try both common locations
        self.text_encoders_dir = self.comfyui_root / "models" / "text_encoders"
        self.clip_dir = self.comfyui_root / "models" / "clip"
        
        # Loader-specific directories
        self.unet_dir = self.comfyui_root / "models" / "unet"
        self.diffusion_models_dir = self.comfyui_root / "models" / "diffusion_models"
        self.gguf_dir = self.comfyui_root / "models" / "gguf"
        self.lora_dir = self.comfyui_root / "models" / "loras"
        
        # Alternative search paths
        self.custom_nodes_dir = self.comfyui_root / "custom_nodes"
    
    # ==================== CHECKPOINT SCANNING ====================
    def scan_checkpoints(self) -> Dict[str, Dict]:
        """
        Scan checkpoints folder and return model info with metadata
        
        Returns:
            {filename: {path, filename, size, has_clip, has_vae, type}}
        """
        checkpoints = {}
        if not self.checkpoints_dir.exists():
            return checkpoints
        
        valid_extensions = ("*.safetensors", "*.ckpt", "*.pt")
        
        for file in self.checkpoints_dir.glob("*"):
            if not any(file.match(ext) for ext in valid_extensions):
                continue
            if not file.is_file():
                continue
            
            info = {
                "path": str(file),
                "filename": file.name,
                "size": file.stat().st_size,
                "has_clip": self._detect_has_clip_in_checkpoint(file.name),
                "has_vae": self._detect_has_vae_in_checkpoint(file.name),
                "model_type": self._detect_model_type(file.name)
            }
            checkpoints[file.name] = info
        
        return checkpoints
    
    def _detect_has_clip_in_checkpoint(self, filename: str) -> bool:
        """
        Detect if checkpoint has built-in CLIP encoder
        Uses heuristic-based filename matching
        
        Args:
            filename: Checkpoint filename
            
        Returns:
            bool: True if likely has built-in CLIP
        """
        name_lower = filename.lower()
        
        # Models known to have built-in CLIP
        has_clip_keywords = [
            "sdxl",           # SDXL models (1.0, Turbo, Lightning)
            "pony",           # Pony models (anime-focused)
            "animagine",      # Animagine models
            "dreamshaperxl",  # Dreamshaper XL
            "juggernaut",     # Juggernaut XL
            "copaxl",         # Copax XL
            "copacabana",
            "realvis",
        ]
        
        return any(keyword in name_lower for keyword in has_clip_keywords)
    
    def _detect_has_vae_in_checkpoint(self, filename: str) -> bool:
        """
        Detect if checkpoint has built-in VAE
        Uses heuristic-based filename matching
        
        Args:
            filename: Checkpoint filename
            
        Returns:
            bool: True if likely has built-in VAE
        """
        name_lower = filename.lower()
        
        # Models known to have built-in VAE
        has_vae_keywords = [
            "sdxl",           # SDXL models typically have VAE
            "pony",
            "animagine",
            "dreamshaperxl",
            "juggernaut",
            "copaxl",
        ]
        
        # Models known to NOT have VAE (need external)
        no_vae_keywords = ["sd15", "sd1.5", "sd14"]
        
        has_vae = any(keyword in name_lower for keyword in has_vae_keywords)
        no_vae = any(keyword in name_lower for keyword in no_vae_keywords)
        
        if no_vae:
            return False
        return has_vae
    
    def _detect_model_type(self, filename: str) -> str:
        """
        Detect model type from filename
        
        Args:
            filename: Checkpoint filename
            
        Returns:
            str: Model type ("sdxl", "sd15", "pony", or "unknown")
        """
        name_lower = filename.lower()
        
        if "sdxl" in name_lower or "xl" in name_lower:
            return "sdxl"
        elif "pony" in name_lower or "anime" in name_lower:
            return "pony"
        elif "sd15" in name_lower or "sd1.5" in name_lower:
            return "sd15"
        elif "sd14" in name_lower or "sd1.4" in name_lower:
            return "sd14"
        else:
            return "unknown"
    
    # ==================== VAE SCANNING ====================
    def scan_vaes(self) -> List[str]:
        """Scan VAE folder and return sorted filenames"""
        vaes = []
        if DebugConfig.model_scanning:
            print(f"[DEBUG] Scanning VAE directory: {self.vae_dir}")
        if self.vae_dir.exists():
            vaes = sorted([f.name for f in self.vae_dir.glob("*") if f.is_file()])
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(vaes)} VAE files: {vaes}")
        elif DebugConfig.model_scanning:
            print(f"[DEBUG] VAE directory does not exist: {self.vae_dir}")
        return vaes
    
    # ==================== TEXT ENCODER SCANNING ====================
    def scan_text_encoders(self) -> List[str]:
        """Scan text encoders folders and return sorted filenames
        Scans both models/clip and models/text_encoders directories
        """
        encoders = []
        # Scan clip directory first (standard ComfyUI location)
        if DebugConfig.model_scanning:
            print(f"[DEBUG] Scanning CLIP directory: {self.clip_dir}")
        if self.clip_dir.exists():
            clip_encoders = [f.name for f in self.clip_dir.glob("*") if f.is_file()]
            encoders.extend(clip_encoders)
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(clip_encoders)} CLIP/encoder files: {clip_encoders}")
        elif DebugConfig.model_scanning:
            print(f"[DEBUG] CLIP directory does not exist: {self.clip_dir}")
        
        # Also scan text_encoders directory
        if DebugConfig.model_scanning:
            print(f"[DEBUG] Scanning text_encoders directory: {self.text_encoders_dir}")
        if self.text_encoders_dir.exists():
            text_enc_files = [f.name for f in self.text_encoders_dir.glob("*") if f.is_file()]
            # Only add if not already in list (avoid duplicates)
            for f in text_enc_files:
                if f not in encoders:
                    encoders.append(f)
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(text_enc_files)} text_encoders files: {text_enc_files}")
        elif DebugConfig.model_scanning:
            print(f"[DEBUG] text_encoders directory does not exist: {self.text_encoders_dir}")
        
        # Return sorted and deduplicated list
        return sorted(list(set(encoders)))
    
    # ==================== LOADER-SPECIFIC SCANNING ====================
    def scan_unets(self) -> List[str]:
        """Scan UNet folder for standalone UNet models"""
        unets = []
        if self.unet_dir.exists():
            unets = sorted([f.name for f in self.unet_dir.glob("*") if f.is_file()])
        return unets
    
    def scan_gguf_models(self) -> List[str]:
        """
        Scan for GGUF format models
        Searches in multiple locations (gguf_dir, checkpoints, custom_nodes)
        """
        gguf_models = []
        search_dirs = [self.gguf_dir, self.checkpoints_dir, self.custom_nodes_dir]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for file in search_dir.rglob("*.gguf"):
                    if file.is_file():
                        gguf_models.append(file.name)
        
        return sorted(list(set(gguf_models)))  # Remove duplicates and sort
    
    def scan_diffusion_models(self) -> List[str]:
        """Scan diffusion_models folder for diffusion-only models"""
        models = []
        if self.diffusion_models_dir.exists():
            models = sorted([f.name for f in self.diffusion_models_dir.glob("*") if f.is_file()])
        return models
    
    # ==================== LORA SCANNING ====================
    def scan_loras(self) -> List[str]:
        """Scan LoRA folder for LoRA models"""
        loras = []
        if DebugConfig.model_scanning:
            print(f"[DEBUG] Scanning LoRA directory: {self.lora_dir}")
        if self.lora_dir.exists():
            # Support common LoRA formats: .safetensors, .gguf
            loras = sorted([f.name for f in self.lora_dir.glob("*") if f.is_file() and f.suffix in {'.safetensors', '.gguf'}])
            if DebugConfig.model_discovery:
                print(f"[DEBUG] Found {len(loras)} LoRA files: {loras}")
        elif DebugConfig.model_scanning:
            print(f"[DEBUG] LoRA directory does not exist: {self.lora_dir}")
        return loras
    
    # ==================== COMPREHENSIVE SCANNING ====================
    def get_all_models(self) -> Dict[str, any]:
        """
        Get comprehensive model configuration
        
        Returns:
            Dictionary with all available models organized by type
        """
        return {
            "checkpoints": self.scan_checkpoints(),
            "vaes": self.scan_vaes(),
            "text_encoders": self.scan_text_encoders(),
            "unets": self.scan_unets(),
            "gguf_models": self.scan_gguf_models(),
            "diffusion_models": self.scan_diffusion_models(),
            "loras": self.scan_loras(),
        }
    
    # ==================== LOADER DETECTION ====================
    def recommend_loader(self, checkpoint_filename: str) -> str:
        """
        Recommend appropriate loader based on checkpoint filename
        
        Args:
            checkpoint_filename: Name of checkpoint file
            
        Returns:
            str: Recommended loader ("standard", "gguf", "unet", "diffuse")
        """
        name_lower = checkpoint_filename.lower()
        
        if ".gguf" in name_lower:
            return "gguf"
        elif "unet" in name_lower:
            return "unet"
        elif "diffuse" in name_lower or "diffusion" in name_lower:
            return "diffuse"
        else:
            return "standard"
    
    def get_loader_config(self, loader_type: str) -> Dict:
        """
        Get configuration for specific loader type
        
        Args:
            loader_type: Loader type ("standard", "gguf", "unet", "diffuse")
            
        Returns:
            Dictionary with loader configuration and available models
        """
        loaders = {
            "standard": {
                "name": "Standard Checkpoint Loader",
                "description": "Traditional checkpoint loader (safetensors/ckpt)",
                "requires_vae": False,  # Can use built-in or external
                "requires_text_encoder": False,  # Can use built-in or external
                "models": list(self.scan_checkpoints().keys()),
            },
            "gguf": {
                "name": "GGUF Loader",
                "description": "Quantized GGUF format (faster, smaller, lower quality)",
                "requires_vae": False,
                "requires_text_encoder": False,
                "models": self.scan_gguf_models(),
            },
            "unet": {
                "name": "UNet Loader",
                "description": "Standalone UNet model (requires separate CLIP and VAE)",
                "requires_vae": True,
                "requires_text_encoder": True,
                "models": self.scan_unets(),
            },
            "diffuse": {
                "name": "Diffusion Loader",
                "description": "Diffusion-only models (requires separate VAE and encoder)",
                "requires_vae": True,
                "requires_text_encoder": True,
                "models": self.scan_diffusion_models(),
            },
        }
        
        return loaders.get(loader_type, loaders["standard"])
    
    # ==================== VALIDATION ====================
    def validate_checkpoint(self, checkpoint_filename: str) -> Dict:
        """
        Validate checkpoint and return metadata
        
        Args:
            checkpoint_filename: Name of checkpoint
            
        Returns:
            Dictionary with validation results and recommendations
        """
        checkpoints = self.scan_checkpoints()
        if checkpoint_filename not in checkpoints:
            return {"valid": False, "error": "Checkpoint not found"}
        
        info = checkpoints[checkpoint_filename]
        return {
            "valid": True,
            "filename": checkpoint_filename,
            "size": info["size"],
            "has_clip": info["has_clip"],
            "has_vae": info["has_vae"],
            "model_type": info["model_type"],
            "needs_vae": not info["has_vae"],
            "needs_text_encoder": not info["has_clip"],
            "recommended_vae": "standard" if info["model_type"] == "sdxl" else None,
        }
    
    # ==================== UTILITY ====================
    def get_checkpoint_path(self, filename: str) -> Optional[str]:
        """Get full path for a checkpoint filename"""
        checkpoints = self.scan_checkpoints()
        return checkpoints.get(filename, {}).get("path")
    
    def get_vae_path(self, filename: str) -> Optional[str]:
        """Get full path for a VAE filename"""
        if self.vae_dir.exists():
            vae_file = self.vae_dir / filename
            return str(vae_file) if vae_file.exists() else None
        return None
    
    def get_text_encoder_path(self, filename: str) -> Optional[str]:
        """Get full path for a text encoder filename (tries clip first, then text_encoders)"""
        # Try clip directory first (standard ComfyUI)
        if self.clip_dir.exists():
            encoder_file = self.clip_dir / filename
            if encoder_file.exists():
                return str(encoder_file)
        # Fall back to text_encoders directory
        if self.text_encoders_dir.exists():
            encoder_file = self.text_encoders_dir / filename
            if encoder_file.exists():
                return str(encoder_file)
        return None
    
    def format_size(self, size_bytes: int) -> str:
        """Format byte size to human readable"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
