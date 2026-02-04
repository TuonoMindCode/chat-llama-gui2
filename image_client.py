"""
ComfyUI Client for image generation
Handles API communication with ComfyUI server
"""

import requests
import json
import time
from pathlib import Path
import uuid
from debug_config import DebugConfig


class ComfyUIClient:
    """Client for communicating with ComfyUI API"""
    
    def __init__(self, url="http://127.0.0.1:8188", output_folder=None):
        """
        Initialize ComfyUI client
        
        Args:
            url: ComfyUI server URL
            output_folder: Optional folder to save images to (instead of default generated_images)
        """
        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/api"
        
        if output_folder:
            self.image_folder = Path(output_folder)
        else:
            self.image_folder = Path("generated_images")
        self.image_folder.mkdir(exist_ok=True)
    
    def test_connection(self):
        """Test connection to ComfyUI server"""
        try:
            response = requests.get(f"{self.url}/api", timeout=5)
            success = response.status_code == 200
            if DebugConfig.connection_enabled:
                print(f"[DEBUG] ComfyUI connection test: {'✓ Connected' if success else '✗ Failed'}")
            return success
        except Exception as e:
            if DebugConfig.connection_enabled:
                print(f"[DEBUG] ComfyUI connection error: {e}")
            return False
    
    def get_system_info(self):
        """Get system info from ComfyUI"""
        try:
            response = requests.get(f"{self.api_url}/system", timeout=10)
            if response.status_code == 200:
                if response.text:  # Check if response has content
                    result = response.json()
                    if DebugConfig.connection_enabled:
                        print(f"[DEBUG] ComfyUI system info retrieved successfully")
                    return result
                else:
                    if DebugConfig.connection_enabled:
                        print(f"[DEBUG] ComfyUI returned empty response for /system")
                    return None
            return None
        except Exception as e:
            if DebugConfig.connection_enabled:
                print(f"[DEBUG] Error getting ComfyUI system info: {e}")
            return None
    
    def get_node_types(self):
        """Get available node types and their input options from ComfyUI"""
        try:
            response = requests.get(f"{self.api_url}/node_types", timeout=10)
            if response.status_code == 200 and response.text:
                try:
                    return response.json()
                except ValueError as json_err:
                    if DebugConfig.connection_enabled:
                        print(f"[DEBUG] Failed to parse node_types JSON: {json_err}")
                    return None
            return None
        except Exception as e:
            if DebugConfig.connection_enabled:
                print(f"[DEBUG] Error getting node types: {e}")
            return None
    
    def get_available_models(self):
        """
        Get available checkpoint models from ComfyUI
        
        Returns:
            list: List of available model names
        """
        try:
            node_types = self.get_node_types()
            if not node_types:
                return []
            
            # Get CheckpointLoaderSimple node info
            if "CheckpointLoaderSimple" in node_types:
                node_info = node_types["CheckpointLoaderSimple"]
                if "input" in node_info and "required" in node_info["input"]:
                    if "ckpt_name" in node_info["input"]["required"]:
                        ckpt_info = node_info["input"]["required"]["ckpt_name"]
                        # ckpt_info is typically [["model1", "model2", ...], {"tooltip": "..."}]
                        if isinstance(ckpt_info, list) and len(ckpt_info) > 0:
                            if isinstance(ckpt_info[0], list):
                                return ckpt_info[0]
            
            return []
        except Exception as e:
            if DebugConfig.connection_enabled:
                print(f"[DEBUG] Error getting available models: {e}")
            return []
    
    def queue_prompt(self, prompt_dict):
        """
        Queue a prompt for generation
        
        Args:
            prompt_dict: ComfyUI workflow as dict
            
        Returns:
            dict: Response with prompt_id
        """
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                f"{self.api_url}/prompt",
                json={"prompt": prompt_dict},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                if response.text:  # Check if response has content
                    try:
                        result = response.json()
                        if DebugConfig.comfyui_queue_operations:
                            print(f"[DEBUG] Queued prompt: {result}")
                        return result
                    except ValueError as json_err:
                        if DebugConfig.comfyui_queue_operations:
                            print(f"[DEBUG] Failed to parse JSON response: {json_err}")
                            if DebugConfig.chat_enabled:
                                print(f"[DEBUG] Response text: {response.text[:200]}")
                        return None
                else:
                    if DebugConfig.comfyui_queue_operations:
                        print(f"[DEBUG] Queue prompt: empty response body")
                    return None
            else:
                if DebugConfig.comfyui_queue_operations:
                    print(f"[DEBUG] Queue prompt error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            if DebugConfig.comfyui_queue_operations:
                print(f"[DEBUG] Error queuing prompt: {e}")
            return None
    
    def get_prompt_status(self, prompt_id):
        """
        Get status of queued prompt
        
        Args:
            prompt_id: ID of the prompt
            
        Returns:
            dict: Prompt status info
        """
        try:
            response = requests.get(
                f"{self.api_url}/prompt/{prompt_id}",
                timeout=10
            )
            if response.status_code == 200 and response.text:
                try:
                    return response.json()
                except ValueError as json_err:
                    if DebugConfig.comfyui_generation_settings:
                        print(f"[DEBUG] Failed to parse prompt status JSON: {json_err}")
                    return None
            return None
        except Exception as e:
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Error getting prompt status: {e}")
            return None
    
    def wait_for_completion(self, prompt_id, max_wait=300, poll_interval=2, timeout=None):
        """
        Wait for image generation to complete
        
        Args:
            prompt_id: ID of the prompt
            max_wait: Maximum seconds to wait (deprecated, use timeout instead)
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait (overrides max_wait if provided)
            
        Returns:
            str: Generated image filename or None if timeout
        """
        # Use timeout parameter if provided, otherwise fall back to max_wait
        if timeout is not None:
            max_wait = timeout
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f"{self.api_url}/history/{prompt_id}",
                    timeout=10
                )
                
                if response.status_code == 200 and response.text:
                    try:
                        history = response.json()
                    except ValueError as json_err:
                        if DebugConfig.comfyui_generation_settings:
                            print(f"[DEBUG] Failed to parse history JSON: {json_err}")
                        time.sleep(poll_interval)
                        continue
                    
                    if prompt_id in history:
                        result = history[prompt_id]
                        
                        # Check if generation completed
                        if "outputs" in result:
                            outputs = result["outputs"]
                            
                            # Look for image outputs
                            for node_id, node_output in outputs.items():
                                if "images" in node_output:
                                    images = node_output["images"]
                                    if images:
                                        image_filename = images[0]["filename"]
                                        if DebugConfig.comfyui_generation_settings:
                                            print(f"[DEBUG] Generation completed: {image_filename}")
                                        return image_filename
                
                # Not ready yet, wait and retry
                time.sleep(poll_interval)
                
            except Exception as e:
                if DebugConfig.comfyui_generation_settings:
                    print(f"[DEBUG] Error checking completion: {e}")
                time.sleep(poll_interval)
        
        if DebugConfig.comfyui_generation_settings:
            print(f"[DEBUG] Generation timeout for prompt {prompt_id}")
        return None
    
    def get_image(self, filename, subfolder=""):
        """
        Get image from ComfyUI server
        
        Args:
            filename: Image filename
            subfolder: Image subfolder (if any)
            
        Returns:
            bytes: Image data or None
        """
        try:
            params = {"filename": filename}
            if subfolder:
                params["subfolder"] = subfolder
            
            response = requests.get(
                f"{self.url}/view",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                # Save to local folder
                image_path = self.image_folder / filename
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                return str(image_path)
            else:
                if DebugConfig.connection_enabled:
                    print(f"[DEBUG] Error getting image: {response.status_code}")
                return None
                
        except Exception as e:
            if DebugConfig.connection_enabled:
                print(f"[DEBUG] Error retrieving image: {e}")
            return None
    
    def generate_from_text(self, text_prompt, workflow_template=None, resolution="768x768", steps=20, cfg_scale=7.5, sampler="euler", scheduler="normal", checkpoint_model="sdxl_turbo.safetensors", timestamp=None, loader_type="standard", vae_model=None, text_encoder_model=None, text_encoder_model_2=None, clip_type="stable_diffusion", clip_loader="CLIPLoader", weight_dtype="default", lora_enabled=False, lora_name=None, lora_strength=1.0, timeout=300):
        """
        Generate image from text prompt using a workflow
        
        Args:
            text_prompt: Text description of image
            workflow_template: ComfyUI workflow template dict
            resolution: Image resolution (e.g., "768x768")
            steps: Number of inference steps
            cfg_scale: CFG scale (guidance scale)
            sampler: Sampler name (e.g., "euler", "euler_ancestral")
            scheduler: Scheduler name (e.g., "normal", "karras", "exponential", "simple")
            checkpoint_model: Model checkpoint name (e.g., "sdxl_turbo.safetensors")
            timestamp: Optional HH:MM:SS timestamp to use in filename
            loader_type: "standard", "gguf", "unet", or "diffuse"
            vae_model: Optional VAE model name
            text_encoder_model: Optional text encoder model name
            clip_type: CLIP type (e.g., "stable_diffusion", "flux2")
            clip_loader: CLIP loader type ("CLIPLoader", "DualCLIPLoader", "DualCLIPLoaderGGUF")
            weight_dtype: UNet weight dtype (e.g., "default", "fp8_e4m3fn")
            lora_enabled: Whether to use LoRA
            lora_name: Name of LoRA file to use
            lora_strength: LoRA strength (0.0-2.0)
            timeout: Generation timeout in seconds (default 300 = 5 minutes)
            
        Returns:
            str or tuple: Path to generated image, or (path, timestamp) tuple if timestamp provided
        """
        try:
            # Build prompt dict with text_prompt
            if workflow_template is None:
                # Simple workflow with just KSampler
                prompt_dict = self._build_simple_workflow(text_prompt, resolution, steps, cfg_scale, sampler, scheduler, checkpoint_model, loader_type, vae_model, text_encoder_model, text_encoder_model_2, clip_type, clip_loader, weight_dtype, lora_enabled, lora_name, lora_strength)
            else:
                prompt_dict = workflow_template.copy()
                # Inject text prompt and settings where needed
                # This is customizable based on workflow
            
            # Queue the prompt
            result = self.queue_prompt(prompt_dict)
            if not result or "prompt_id" not in result:
                return None
            
            prompt_id = result["prompt_id"]
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] Waiting for image generation with prompt_id: {prompt_id}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Settings: {resolution}, {steps} steps, CFG {cfg_scale}, sampler: {sampler}, model: {checkpoint_model}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Timeout: {timeout} seconds")
            
            # Wait for completion
            filename = self.wait_for_completion(prompt_id, timeout=timeout)
            if filename:
                # Download and save image
                image_path = self.get_image(filename)
                if image_path and timestamp:
                    return image_path, timestamp
                return image_path
            
            return None
            
        except Exception as e:
            if DebugConfig.chat_enabled:
                print(f"[DEBUG] Error in generate_from_text: {e}")
            return None
    
    def _build_simple_workflow(self, text_prompt, resolution="768x768", steps=20, cfg_scale=7.5, sampler="euler", scheduler="normal", checkpoint_model="sdxl_turbo.safetensors", loader_type="standard", vae_model=None, text_encoder_model=None, text_encoder_model_2=None, clip_type="stable_diffusion", clip_loader="CLIPLoader", weight_dtype="default", lora_enabled=False, lora_name=None, lora_strength=1.0):
        """
        Build a simple ComfyUI workflow dict from text prompt
        Customizable with resolution, steps, CFG, sampler, and scheduler
        Supports standard checkpoints, GGUF models, UNet models, and Diffusion models
        Optionally adds LoRA loader
        
        Args:
            text_prompt: Text description
            resolution: Image resolution (e.g., "768x768", "512x1024")
            steps: Number of inference steps
            cfg_scale: CFG scale (guidance)
            sampler: Sampler name (e.g., "euler", "euler_ancestral")
            scheduler: Scheduler name (e.g., "normal", "karras", "exponential", "simple")
            checkpoint_model: Model checkpoint name (.safetensors or .gguf)
            loader_type: "standard", "gguf", "unet", or "diffuse"
            vae_model: Optional VAE model name
            text_encoder_model: Optional text encoder model name
            clip_type: CLIP type (e.g., "stable_diffusion", "flux2")
            clip_loader: CLIP loader type ("CLIPLoader", "DualCLIPLoader", "DualCLIPLoaderGGUF")
            weight_dtype: UNet weight dtype (e.g., "default", "fp8_e4m3fn")
            lora_enabled: Whether to use LoRA
            lora_name: Name of LoRA file
            lora_strength: LoRA strength (0.0-2.0)
            
        Returns:
            dict: ComfyUI workflow
        """
        # Parse resolution
        try:
            width, height = map(int, resolution.split('x'))
        except:
            width, height = 768, 768
        
        # Parse seed (random or use current timestamp)
        import time
        from datetime import datetime
        seed = int(time.time()) % 2147483647
        
        # Create timestamp-based filename prefix (same format as audio: YYYYMMDD_HHMMSS)
        timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use provided VAE and text encoder or defaults
        if vae_model is None:
            vae_model = "ae_lm2.safetensors"
        if text_encoder_model is None:
            text_encoder_model = "qwen_3_4b.safetensors"
        
        # For GGUF workflows, CLIPLoader only accepts safetensors - strip GGUF if needed
        if loader_type == "gguf" and text_encoder_model and text_encoder_model.endswith(".gguf"):
            # Replace GGUF CLIP with safetensors equivalent (CLIPLoader doesn't support GGUF)
            if "t5" in text_encoder_model.lower():
                text_encoder_model = "t5xxl_fp8_e4m3fn.safetensors"
            else:
                text_encoder_model = "qwen_3_4b.safetensors"
            if DebugConfig.comfyui_generation_settings:
                print(f"[DEBUG] GGUF workflow detected - converted text encoder to safetensors: {text_encoder_model}")
        
        # Print loader type being used
        if DebugConfig.comfyui_enabled:
            print(f"[DEBUG] Using loader type: {loader_type} for model: {checkpoint_model}")
        
        if loader_type == "unet":
            # Build workflow for UNet model loader (e.g., flux models)
            if DebugConfig.comfyui_workflow:
                print(f"[DEBUG] Building UNet workflow for: {checkpoint_model}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] UNet CLIP Loader: {clip_loader}, Text Encoder: {text_encoder_model}, Type: {clip_type}")
            
            workflow = {
                "1": {
                    "inputs": {
                        "unet_name": checkpoint_model,
                        "weight_dtype": weight_dtype  # Use user-selected weight_dtype (default, fp8_e4m3fn, etc.)
                    },
                    "class_type": "UNETLoader",
                    "_meta": {"title": "Load UNet"}
                }
            }
            
            # Add CLIP loader - handle both single and dual CLIP loaders
            if clip_loader in ["DualCLIPLoader", "DualCLIPLoaderGGUF"]:
                if DebugConfig.comfyui_workflow:
                    print(f"[DEBUG] UNet: Using DUAL CLIP loader with clip_name1 and clip_name2")
                # Use text_encoder_model_2 if provided, otherwise use text_encoder_model for both
                clip_name2 = text_encoder_model_2 if text_encoder_model_2 else text_encoder_model
                # Handle (auto) by skipping it - let ComfyUI use defaults
                if text_encoder_model == "(auto)":
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name 1 is (auto), sending empty string for auto-selection")
                    text_encoder_model = ""
                if clip_name2 == "(auto)" or clip_name2 == "(same as CLIP Name 1)":
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name 2 is (auto) or (same), sending empty string for auto-selection")
                    clip_name2 = ""
                workflow["2"] = {
                    "inputs": {
                        "clip_name1": text_encoder_model,
                        "clip_name2": clip_name2,
                        "type": clip_type
                    },
                    "class_type": clip_loader,
                    "_meta": {"title": "Load Dual CLIP"}
                }
            else:
                if DebugConfig.comfyui_workflow:
                    print(f"[DEBUG] UNet: Using SINGLE CLIP loader with clip_name")
                # Handle None/(auto) - if no model specified, don't create CLIP loader node
                # This will let ComfyUI use defaults or fail gracefully
                if text_encoder_model and text_encoder_model not in ["(auto)", ""]:
                    workflow["2"] = {
                        "inputs": {
                            "clip_name": text_encoder_model,
                            "type": clip_type
                        },
                        "class_type": clip_loader,
                        "_meta": {"title": "Load CLIP"}
                    }
                else:
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name is None or (auto), will use ComfyUI defaults")
                    # Skip creating CLIP loader - let ComfyUI handle it
                    workflow["2"] = {
                        "inputs": {
                            "clip_name": "t5xxl_fp16.safetensors",  # Use a default
                            "type": clip_type
                        },
                        "class_type": clip_loader,
                        "_meta": {"title": "Load CLIP"}
                    }
            
            # Continue with rest of workflow
            workflow.update({
                "3": {
                    "inputs": {
                        "text": text_prompt,
                        "clip": ["2", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Positive)"}
                },
                "4": {
                    "inputs": {
                        "text": "low quality, blurry, deformed",
                        "clip": ["2", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Negative)"}
                },
                "5": {
                    "inputs": {
                        "vae_name": vae_model
                    },
                    "class_type": "VAELoader",
                    "_meta": {"title": "Load VAE"}
                },
                "6": {
                    "inputs": {
                        "width": width,
                        "height": height,
                        "length": 1,
                        "batch_size": 1
                    },
                    "class_type": "EmptyLatentImage",
                    "_meta": {"title": "Empty Latent Image"}
                }
            })
            
            # Add LoRA loader if enabled
            if lora_enabled and lora_name:
                workflow["7"] = {
                    "inputs": {
                        "lora_name": lora_name,
                        "strength_model": float(lora_strength),
                        "model": ["1", 0]
                    },
                    "class_type": "LoraLoaderModelOnly",
                    "_meta": {"title": "Load LoRA"}
                }
                
                # KSampler uses LoRA-modified model (node 7)
                model_node = ["7", 0]
                ksampler_node = "8"
                vae_decode_node = "9"
                save_node = "10"
                
                if DebugConfig.comfyui_generation_settings:
                    print(f"[DEBUG] LoRA enabled: {lora_name} (strength: {lora_strength})")
            else:
                # KSampler uses unmodified model (node 1)
                model_node = ["1", 0]
                ksampler_node = "7"
                vae_decode_node = "8"
                save_node = "9"
            
            # KSampler
            workflow[ksampler_node] = {
                "inputs": {
                    "seed": seed,
                    "steps": int(steps),
                    "cfg": float(cfg_scale),
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "denoise": 1,
                    "model": model_node,
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["6", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            }
            
            # VAE Decode
            workflow[vae_decode_node] = {
                "inputs": {
                    "samples": [ksampler_node, 0],
                    "vae": ["5", 0]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            }
            
            # Save Image
            workflow[save_node] = {
                "inputs": {
                    "filename_prefix": timestamp_prefix,
                    "images": [vae_decode_node, 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        elif loader_type == "diffuse":
            # Build workflow for Diffusion model loader
            if DebugConfig.comfyui_workflow:
                print(f"[DEBUG] Building Diffusion workflow for: {checkpoint_model}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] Diffuse CLIP Loader: {clip_loader}, Text Encoder: {text_encoder_model}, Type: {clip_type}")
            
            # Diffusion models typically use DiffusersLoader or similar
            workflow = {
                "1": {
                    "inputs": {
                        "model_name": checkpoint_model
                    },
                    "class_type": "DiffusersLoader",
                    "_meta": {"title": "Load Diffusion Model"}
                }
            }
            
            # Add CLIP loader - handle both single and dual CLIP loaders
            if clip_loader in ["DualCLIPLoader", "DualCLIPLoaderGGUF"]:
                if DebugConfig.comfyui_workflow:
                    print(f"[DEBUG] Diffuse: Using DUAL CLIP loader with clip_name1 and clip_name2")
                # Use text_encoder_model_2 if provided, otherwise use text_encoder_model for both
                clip_name2 = text_encoder_model_2 if text_encoder_model_2 else text_encoder_model
                # Handle (auto) by skipping it - let ComfyUI use defaults
                if text_encoder_model == "(auto)":
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name 1 is (auto), sending empty string for auto-selection")
                    text_encoder_model = ""
                if clip_name2 == "(auto)" or clip_name2 == "(same as CLIP Name 1)":
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name 2 is (auto) or (same), sending empty string for auto-selection")
                    clip_name2 = ""
                workflow["2"] = {
                    "inputs": {
                        "clip_name1": text_encoder_model,
                        "clip_name2": clip_name2,
                        "type": clip_type
                    },
                    "class_type": clip_loader,
                    "_meta": {"title": "Load Dual CLIP"}
                }
            else:
                if DebugConfig.comfyui_workflow:
                    print(f"[DEBUG] Diffuse: Using SINGLE CLIP loader with clip_name")
                # Handle None/(auto) - if no model specified, use a safe default
                if not text_encoder_model or text_encoder_model in ["(auto)", ""]:
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name is None or (auto), using default")
                    text_encoder_model = "t5xxl_fp16.safetensors"  # Use a sensible default
                workflow["2"] = {
                    "inputs": {
                        "clip_name": text_encoder_model,
                        "type": clip_type
                    },
                    "class_type": clip_loader,
                    "_meta": {"title": "Load CLIP"}
                }
            
            # Add remaining nodes for Diffuse workflow
            workflow.update({
                "3": {
                    "inputs": {
                        "text": text_prompt,
                        "clip": ["2", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Positive)"}
                },
                "4": {
                    "inputs": {
                        "text": "low quality, blurry, deformed",
                        "clip": ["2", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Negative)"}
                },
                "5": {
                    "inputs": {
                        "vae_name": vae_model
                    },
                    "class_type": "VAELoader",
                    "_meta": {"title": "Load VAE"}
                },
                "6": {
                    "inputs": {
                        "width": width,
                        "height": height,
                        "length": 1,
                        "batch_size": 1
                    },
                    "class_type": "EmptyLatentImage",
                    "_meta": {"title": "Empty Latent Image"}
                }
            })
            
            # Add LoRA loader if enabled
            if lora_enabled and lora_name:
                workflow["7"] = {
                    "inputs": {
                        "lora_name": lora_name,
                        "strength_model": float(lora_strength),
                        "model": ["1", 0]
                    },
                    "class_type": "LoraLoaderModelOnly",
                    "_meta": {"title": "Load LoRA"}
                }
                
                # KSampler uses LoRA-modified model (node 7)
                model_node = ["7", 0]
                ksampler_node = "8"
                vae_decode_node = "9"
                save_node = "10"
                
                if DebugConfig.comfyui_generation_settings:
                    print(f"[DEBUG] LoRA enabled: {lora_name} (strength: {lora_strength})")
            else:
                # KSampler uses unmodified model (node 1)
                model_node = ["1", 0]
                ksampler_node = "7"
                vae_decode_node = "8"
                save_node = "9"
            
            # KSampler
            workflow[ksampler_node] = {
                "inputs": {
                    "seed": seed,
                    "steps": int(steps),
                    "cfg": float(cfg_scale),
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "denoise": 1,
                    "model": model_node,
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["6", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            }
            
            # VAE Decode
            workflow[vae_decode_node] = {
                "inputs": {
                    "samples": [ksampler_node, 0],
                    "vae": ["5", 0]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            }
            
            # Save Image
            workflow[save_node] = {
                "inputs": {
                    "filename_prefix": timestamp_prefix,
                    "images": [vae_decode_node, 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        elif loader_type == "gguf":
            # Build workflow for GGUF model with separate UNET, CLIP, and VAE loaders
            if DebugConfig.comfyui_workflow:
                print(f"[DEBUG] Building GGUF workflow for: {checkpoint_model}")
                if DebugConfig.chat_enabled:
                    print(f"[DEBUG] GGUF CLIP Loader: {clip_loader}, Text Encoder: {text_encoder_model}, Type: {clip_type}")
            
            workflow = {
                "1": {
                    "inputs": {
                        "unet_name": checkpoint_model
                    },
                    "class_type": "UnetLoaderGGUF",
                    "_meta": {"title": "Load GGUF UNet"}
                }
            }
            
            # Add CLIP loader - handle both single and dual CLIP loaders
            if clip_loader in ["DualCLIPLoader", "DualCLIPLoaderGGUF"]:
                if DebugConfig.comfyui_workflow:
                    print(f"[DEBUG] GGUF: Using DUAL CLIP loader with clip_name1 and clip_name2")
                # Use text_encoder_model_2 if provided, otherwise use text_encoder_model for both
                clip_name2 = text_encoder_model_2 if text_encoder_model_2 else text_encoder_model
                # Handle (auto) by skipping it - let ComfyUI use defaults
                if text_encoder_model == "(auto)":
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name 1 is (auto), sending empty string for auto-selection")
                    text_encoder_model = ""
                if clip_name2 == "(auto)" or clip_name2 == "(same as CLIP Name 1)":
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name 2 is (auto) or (same), sending empty string for auto-selection")
                    clip_name2 = ""
                workflow["2"] = {
                    "inputs": {
                        "clip_name1": text_encoder_model,
                        "clip_name2": clip_name2,
                        "type": clip_type
                    },
                    "class_type": clip_loader,
                    "_meta": {"title": "Load Dual CLIP"}
                }
            else:
                if DebugConfig.comfyui_workflow:
                    print(f"[DEBUG] GGUF: Using SINGLE CLIP loader with clip_name")
                # Handle None/(auto) - if no model specified, use a safe default
                if not text_encoder_model or text_encoder_model in ["(auto)", ""]:
                    if DebugConfig.comfyui_workflow:
                        print(f"[DEBUG] CLIP Name is None or (auto), using default")
                    text_encoder_model = "t5xxl_fp16.safetensors"  # Use a sensible default
                workflow["2"] = {
                    "inputs": {
                        "clip_name": text_encoder_model,
                        "type": clip_type
                    },
                    "class_type": clip_loader,
                    "_meta": {"title": "Load CLIP"}
                }
            
            # Add remaining nodes for GGUF workflow
            workflow.update({
                "3": {
                    "inputs": {
                        "text": text_prompt,
                        "clip": ["2", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Positive)"}
                },
                "4": {
                    "inputs": {
                        "text": "low quality, blurry, deformed",
                        "clip": ["2", 0]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Negative)"}
                },
                "5": {
                    "inputs": {
                        "vae_name": vae_model
                    },
                    "class_type": "VAELoader",
                    "_meta": {"title": "Load VAE"}
                },
                "6": {
                    "inputs": {
                        "width": width,
                        "height": height,
                        "length": 1,
                        "batch_size": 1
                    },
                    "class_type": "EmptyLatentImage",
                    "_meta": {"title": "Empty Latent Image"}
                }
            })
            
            # Add LoRA loader if enabled
            if lora_enabled and lora_name:
                workflow["7"] = {
                    "inputs": {
                        "lora_name": lora_name,
                        "strength_model": float(lora_strength),
                        "model": ["1", 0]
                    },
                    "class_type": "LoraLoaderModelOnly",
                    "_meta": {"title": "Load LoRA"}
                }
                
                # KSampler uses LoRA-modified model (node 7)
                model_node = ["7", 0]
                ksampler_node = "8"
                vae_decode_node = "9"
                save_node = "10"
                
                if DebugConfig.comfyui_generation_settings:
                    print(f"[DEBUG] LoRA enabled: {lora_name} (strength: {lora_strength})")
            else:
                # KSampler uses unmodified model (node 1)
                model_node = ["1", 0]
                ksampler_node = "7"
                vae_decode_node = "8"
                save_node = "9"
            
            # KSampler
            workflow[ksampler_node] = {
                "inputs": {
                    "seed": seed,
                    "steps": int(steps),
                    "cfg": float(cfg_scale),
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "denoise": 1,
                    "model": model_node,
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["6", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            }
            
            # VAE Decode
            workflow[vae_decode_node] = {
                "inputs": {
                    "samples": [ksampler_node, 0],
                    "vae": ["5", 0]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            }
            
            # Save Image
            workflow[save_node] = {
                "inputs": {
                    "filename_prefix": timestamp_prefix,
                    "images": [vae_decode_node, 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        else:
            # Build standard workflow for safetensors checkpoint (loader_type == "standard")
            if DebugConfig.comfyui_workflow:
                print(f"[DEBUG] Building standard workflow for: {checkpoint_model}")
            
            # Standard checkpoints embed CLIP, so we use CheckpointLoaderSimple
            workflow = {
                "1": {
                    "inputs": {
                        "ckpt_name": checkpoint_model
                    },
                    "class_type": "CheckpointLoaderSimple",
                    "_meta": {"title": "Load Checkpoint"}
                },
                "2": {
                    "inputs": {
                        "text": text_prompt,
                        "clip": ["1", 1]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Positive)"}
                },
                "3": {
                    "inputs": {
                        "text": "low quality, blurry, deformed",
                        "clip": ["1", 1]
                    },
                    "class_type": "CLIPTextEncode",
                    "_meta": {"title": "CLIP Text Encode (Negative)"}
                },
                "4": {
                    "inputs": {
                        "width": width,
                        "height": height,
                        "length": 1,
                        "batch_size": 1
                    },
                    "class_type": "EmptyLatentImage",
                    "_meta": {"title": "Empty Latent Image"}
                }
            }
            
            # Add LoRA loader if enabled
            if lora_enabled and lora_name:
                workflow["5"] = {
                    "inputs": {
                        "lora_name": lora_name,
                        "strength_model": float(lora_strength),
                        "model": ["1", 0]
                    },
                    "class_type": "LoraLoaderModelOnly",
                    "_meta": {"title": "Load LoRA"}
                }
                
                # KSampler uses LoRA-modified model (node 5)
                model_node = ["5", 0]
                ksampler_node = "6"
                vae_node = "7"
                save_node = "8"
                
                if DebugConfig.comfyui_generation_settings:
                    print(f"[DEBUG] LoRA enabled: {lora_name} (strength: {lora_strength})")
                
                # Add VAE decoder after LoRA (need to extract VAE separately)
                workflow["7"] = {
                    "inputs": {
                        "samples": [ksampler_node, 0],
                        "vae": ["1", 2]
                    },
                    "class_type": "VAEDecode",
                    "_meta": {"title": "VAE Decode"}
                }
            else:
                # KSampler uses unmodified model (node 1)
                model_node = ["1", 0]
                ksampler_node = "5"
                vae_node = "6"
                save_node = "7"
                
                # Standard VAE decoder
                workflow["6"] = {
                    "inputs": {
                        "samples": [ksampler_node, 0],
                        "vae": ["1", 2]
                    },
                    "class_type": "VAEDecode",
                    "_meta": {"title": "VAE Decode"}
                }
            
            # KSampler
            workflow[ksampler_node] = {
                "inputs": {
                    "seed": seed,
                    "steps": int(steps),
                    "cfg": float(cfg_scale),
                    "sampler_name": sampler,
                    "scheduler": scheduler,
                    "denoise": 1,
                    "model": model_node,
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            }
            
            # Save Image
            workflow[save_node] = {
                "inputs": {
                    "filename_prefix": timestamp_prefix,
                    "images": [vae_node, 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "Save Image"}
            }
        
        if DebugConfig.comfyui_generation_settings:
            print(f"[DEBUG] Built workflow: {width}x{height}, {steps} steps, CFG {cfg_scale}, sampler: {sampler}, scheduler: {scheduler}, model: {checkpoint_model}")
        return workflow
    
    def load_workflow_from_file(self, filepath):
        """Load workflow from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] Error loading workflow: {e}")
            return None
    
    def save_workflow_to_file(self, workflow, filepath):
        """Save workflow to JSON file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow, f, indent=2)
            return True
        except Exception as e:
            if DebugConfig.comfyui_enabled:
                print(f"[DEBUG] Error saving workflow: {e}")
            return False
