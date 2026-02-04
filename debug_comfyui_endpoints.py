#!/usr/bin/env python3
"""Debug script to find available ComfyUI endpoints"""

import requests

url = "http://127.0.0.1:8188"

print("[TEST] Checking ComfyUI endpoints...")
print(f"URL: {url}\n")

endpoints = [
    "/api",
    "/api/",
    "/api/node_types",
    "/api/system_stats",
    "/object_info",
    "/api/object_info",
    "/system_stats",
    "/status",
    "/api/status",
]

for endpoint in endpoints:
    try:
        full_url = url + endpoint
        response = requests.get(full_url, timeout=5)
        status = response.status_code
        print(f"[{status:3d}] {endpoint:30} - {full_url}")
        if status == 200:
            try:
                data = response.json()
                print(f"      Response type: {type(data).__name__}")
                if isinstance(data, dict):
                    keys = list(data.keys())[:5]
                    print(f"      Keys (first 5): {keys}")
            except:
                print(f"      (not JSON)")
    except Exception as e:
        print(f"[ERR] {endpoint:30} - {str(e)[:50]}")

print("\n" + "="*60)
print("Try checking one of the successful endpoints in browser:")
print(f"  http://127.0.0.1:8188/object_info")
print(f"  http://127.0.0.1:8188/api/system_stats")
print("="*60)
