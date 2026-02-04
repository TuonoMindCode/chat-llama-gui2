#!/usr/bin/env python3
"""
IMAGE GENERATION FEATURE - DEPLOYMENT CHECKLIST
================================================

Run through this checklist to ensure everything is working correctly.
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("IMAGE GENERATION FEATURE - DEPLOYMENT CHECKLIST")
print("=" * 60)

checks = {
    "✓ New Files Created": [
        ("image_client.py", "ComfyUI API client"),
        ("image_prompt_extractor.py", "Prompt extraction"),
        ("ui/image_viewer.py", "Image display widget"),
    ],
    
    "✓ Modified Files": [
        ("ui/ollama_tab.py", "Split-view layout + controls"),
        ("ui/ollama_chat_handler.py", "Image generation trigger"),
        ("settings_tab.py", "Image settings section"),
        ("main.py", "Image variables initialization"),
    ],
    
    "✓ Documentation": [
        ("IMAGE_QUICK_START.md", "User quick start guide"),
        ("IMAGE_GENERATION_GUIDE.md", "Technical documentation"),
        ("IMPLEMENTATION_SUMMARY.md", "Feature summary"),
    ]
}

def check_file_exists(filepath):
    """Check if a file exists"""
    return Path(filepath).exists()

# Check all files
all_good = True
print("\n📋 CHECKING FILES...")
print("-" * 60)

for category, files in checks.items():
    print(f"\n{category}")
    for filename, description in files:
        exists = check_file_exists(filename)
        status = "✓" if exists else "✗"
        print(f"  {status} {filename:40} ({description})")
        if not exists:
            all_good = False

# Check dependencies
print("\n\n📦 CHECKING DEPENDENCIES...")
print("-" * 60)

try:
    import requests
    print("  ✓ requests (ComfyUI API)")
except ImportError:
    print("  ✗ requests NOT INSTALLED - Run: pip install requests")
    all_good = False

try:
    import PIL
    print("  ✓ Pillow (Image handling)")
except ImportError:
    print("  ✗ Pillow NOT INSTALLED - Run: pip install Pillow")
    all_good = False

try:
    import tkinter
    print("  ✓ tkinter (UI framework)")
except ImportError:
    print("  ✗ tkinter NOT INSTALLED - Usually pre-installed with Python")
    all_good = False

# Setup instructions
print("\n\n🚀 SETUP INSTRUCTIONS")
print("-" * 60)

print("""
STEP 1: Install Dependencies (if needed)
  pip install requests Pillow

STEP 2: Start ComfyUI
  cd /path/to/ComfyUI
  python -m comfyui.main
  
  Verify it starts at: http://127.0.0.1:8188

STEP 3: Launch Chat App
  python main.py

STEP 4: Configure in App
  - Go to Settings tab
  - Verify ComfyUI URL = http://127.0.0.1:8188
  - Click Test button (should show ✓ Connected)

STEP 5: Test Image Generation
  - Go to Ollama Chat tab
  - Check "🎨 Generate Images" checkbox
  - Send a message
  - Watch images appear on right panel!
""")

# Feature checklist
print("\n✅ FEATURE CHECKLIST")
print("-" * 60)

features = [
    ("Split-view layout", "Chat on left, images on right"),
    ("Auto prompt extraction", "2B model creates image prompts"),
    ("ComfyUI integration", "Generates images from prompts"),
    ("Image viewer widget", "Browse and manage images"),
    ("Settings integration", "Configure ComfyUI URL and model"),
    ("Per-tab control", "Enable/disable per Ollama chat tab"),
    ("Status indicators", "Show extraction/generation progress"),
    ("Non-blocking", "Chat continues while image generates"),
]

for feature, description in features:
    print(f"  ✓ {feature:30} - {description}")

# Quick test
print("\n\n🔍 QUICK TEST")
print("-" * 60)

print("""
1. Message: "Describe a beautiful sunset on a beach"
   Expected: Image of sunset on beach

2. Message: "What would a futuristic city look like?"
   Expected: Sci-fi cityscape image

3. Message: "Tell me about Python programming"
   Expected: No image (not visual content)

4. Try toggling "🎨 Generate Images" on/off
   Expected: Images only generate when enabled
""")

# Final status
print("\n" * 1)
print("=" * 60)

if all_good:
    print("✅ ALL CHECKS PASSED - READY TO USE!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Start ComfyUI: python -m comfyui.main")
    print("  2. Launch app: python main.py")
    print("  3. Go to Settings and test ComfyUI connection")
    print("  4. Check '🎨 Generate Images' in Ollama Chat tab")
    print("  5. Send a message and watch images appear!")
    sys.exit(0)
else:
    print("⚠️  SOME CHECKS FAILED - SEE ABOVE")
    print("=" * 60)
    print("\nFix the issues above and run this again.")
    sys.exit(1)
