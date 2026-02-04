#!/usr/bin/env python
"""Diagnostic script to check Whisper and GPU setup"""

import sys

print("\n" + "="*60)
print("WHISPER & GPU DIAGNOSTIC")
print("="*60)

# Check Whisper
try:
    import whisper
    print(f"\n✓ Whisper installed")
    print(f"  Version: {whisper.__version__}")
    print(f"  Location: {whisper.__file__}")
    print(f"  Available models: {', '.join(whisper.available_models())}")
except ImportError as e:
    print(f"\n✗ Whisper not installed: {e}")
    sys.exit(1)

# Check PyTorch
try:
    import torch
    print(f"\n✓ PyTorch installed")
    print(f"  Version: {torch.__version__}")
except ImportError as e:
    print(f"\n✗ PyTorch not installed: {e}")
    sys.exit(1)

# Check CUDA
print(f"\n{'='*60}")
print("GPU/CUDA Status:")
print(f"{'='*60}")
try:
    import torch
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        print(f"✓ CUDA is AVAILABLE")
        print(f"  Device: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  cuDNN Version: {torch.backends.cudnn.version()}")
        print(f"  Device Count: {torch.cuda.device_count()}")
        
        # Get GPU memory
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  GPU Memory: {gpu_memory:.1f} GB")
    else:
        print(f"✗ CUDA is NOT available - using CPU only")
        print(f"  To enable GPU:")
        print(f"    1. Install NVIDIA GPU drivers")
        print(f"    2. Install CUDA Toolkit")
        print(f"    3. Install cuDNN")
        print(f"    4. Reinstall PyTorch with CUDA support:")
        print(f"       pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
except Exception as e:
    print(f"✗ Error checking CUDA: {e}")

# Check other dependencies
print(f"\n{'='*60}")
print("Other Dependencies:")
print(f"{'='*60}")

deps = {
    'sounddevice': 'Audio input',
    'soundfile': 'Audio file I/O',
    'numpy': 'Numerical computing',
    'tkinter': 'GUI framework',
    'requests': 'HTTP requests'
}

for module, desc in deps.items():
    try:
        __import__(module)
        print(f"✓ {module:15} - {desc}")
    except ImportError:
        print(f"✗ {module:15} - {desc} (NOT INSTALLED)")

print(f"\n{'='*60}\n")
