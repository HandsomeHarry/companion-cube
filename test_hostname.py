#!/usr/bin/env python3
"""Test hostname detection"""

import socket
import platform
import os

print("Hostname detection test:")
print(f"socket.gethostname(): {socket.gethostname()}")
print(f"platform.node(): {platform.node()}")
print(f"os.uname().nodename: {os.uname().nodename}")
print(f"Platform: {platform.system()}")

# Test what ActivityWatch sees
import requests

response = requests.get("http://localhost:5600/api/0/info")
if response.status_code == 200:
    info = response.json()
    print(f"\nActivityWatch hostname: {info.get('hostname', 'unknown')}")
    
# List all buckets
response = requests.get("http://localhost:5600/api/0/buckets")
if response.status_code == 200:
    buckets = response.json()
    print("\nAvailable buckets:")
    for bucket in buckets:
        print(f"  - {bucket}")