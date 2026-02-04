"""
List all available audio devices on the system
Useful for finding the right device to use
"""

import sounddevice as sd

print("=" * 80)
print("ALL AVAILABLE AUDIO DEVICES")
print("=" * 80)

devices = sd.query_devices()
for i, device in enumerate(devices):
    print(f"\n[Device {i}]")
    print(f"  Name: {device['name']}")
    print(f"  Input Channels: {device['max_input_channels']}")
    print(f"  Output Channels: {device['max_output_channels']}")
    print(f"  Sample Rate: {device['default_samplerate']}")
    if device['max_input_channels'] > 0:
        print(f"  ✓ Can record from this device")

print("\n" + "=" * 80)
print("Default input device:", sd.default.device[0])
print("=" * 80)
