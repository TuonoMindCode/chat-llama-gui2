#!/usr/bin/env python3
"""Find ComfyUI node class_type names"""

import requests
import json

url = "http://127.0.0.1:8188"

try:
    print("Trying different API endpoints...\n")
    
    # Try endpoint 1: /api/nodes
    print("1. Trying /api/nodes ...")
    response = requests.get(f"{url}/api/nodes", timeout=5)
    print(f"   Status: {response.status_code}")
    
    # Try endpoint 2: /nodes
    print("2. Trying /nodes ...")
    response = requests.get(f"{url}/nodes", timeout=5)
    print(f"   Status: {response.status_code}")
    
    # Try endpoint 3: /api/config
    print("3. Trying /api/config ...")
    response = requests.get(f"{url}/api/config", timeout=5)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        config = response.json()
        if config:
            print("   Config received:")
            print(json.dumps(config, indent=2)[:500])
    
    # Try endpoint 4: /system_stats
    print("4. Trying /system_stats ...")
    response = requests.get(f"{url}/system_stats", timeout=5)
    print(f"   Status: {response.status_code}")
    
    print("\n" + "="*80)
    print("ALTERNATIVE: Export workflow manually from ComfyUI")
    print("="*80)
    print("""
1. In ComfyUI web UI, build your GGUF workflow with:
   - UnetLoaderGGUF node
   - CLIP loader node
   - VAE loader node
   - Connected to KSampler and VAEDecode

2. Right-click on canvas → "Save (API format)"
   or Ctrl+Shift+S

3. Open the saved JSON file and look for the "class_type" values:
   - Find the node that loads your GGUF - what is its "class_type"?
   - Find the CLIP loader - what is its "class_type"?
   - Find the VAE loader - what is its "class_type"?

4. Share those class_type values with me
""")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Make sure ComfyUI is running at {url}")
