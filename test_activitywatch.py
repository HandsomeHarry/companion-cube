#!/usr/bin/env python3
"""Test script to debug ActivityWatch API issues"""

import requests
import json
from datetime import datetime, timezone, timedelta
import socket

def test_activitywatch():
    """Test various ActivityWatch API endpoints to identify issues"""
    base_url = "http://localhost:5600/api/0"
    hostname = socket.gethostname()
    
    print("Testing ActivityWatch API...")
    print(f"Hostname: {hostname}")
    print(f"Base URL: {base_url}")
    print("-" * 60)
    
    # Test 1: Check if API is accessible
    print("\n1. Testing API accessibility...")
    try:
        response = requests.get(f"{base_url}/info")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   Info: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: List buckets
    print("\n2. Listing buckets...")
    try:
        response = requests.get(f"{base_url}/buckets")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            buckets = response.json()
            for bucket_id in buckets:
                print(f"   - {bucket_id}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Test different time formats
    print("\n3. Testing time formats for window bucket...")
    window_bucket = f"aw-watcher-window_{hostname}"
    
    # Try different time formats
    now = datetime.now(timezone.utc)
    
    test_cases = [
        ("ISO with timezone", now.isoformat()),
        ("ISO without microseconds", now.replace(microsecond=0).isoformat()),
        ("ISO with Z suffix", now.replace(microsecond=0).isoformat().replace('+00:00', 'Z')),
        ("ISO local time", datetime.now().replace(microsecond=0).isoformat()),
    ]
    
    for desc, end_time in test_cases:
        print(f"\n   Testing: {desc}")
        print(f"   End time: {end_time}")
        
        # Calculate start time (5 minutes ago)
        if isinstance(end_time, str):
            if end_time.endswith('Z'):
                start_dt = now - timedelta(minutes=5)
                start_time = start_dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
            elif '+' in end_time or 'T' in end_time:
                start_dt = now - timedelta(minutes=5)
                start_time = start_dt.replace(microsecond=0).isoformat()
            else:
                start_dt = datetime.now() - timedelta(minutes=5)
                start_time = start_dt.replace(microsecond=0).isoformat()
        
        print(f"   Start time: {start_time}")
        
        url = f"{base_url}/buckets/{window_bucket}/events?start={start_time}&end={end_time}"
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Error response: {response.text[:200]}")
            else:
                events = response.json()
                print(f"   Success! Got {len(events)} events")
                break
        except Exception as e:
            print(f"   Exception: {e}")
    
    # Test 4: Get bucket info
    print(f"\n4. Getting bucket info for {window_bucket}...")
    try:
        response = requests.get(f"{base_url}/buckets/{window_bucket}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            info = response.json()
            print(f"   Bucket type: {info.get('type', 'unknown')}")
            print(f"   Created: {info.get('created', 'unknown')}")
            print(f"   Last updated: {info.get('last_updated', 'unknown')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Try with very recent time range
    print("\n5. Testing with very recent time range (last 1 minute)...")
    end_time = (now - timedelta(seconds=5)).replace(microsecond=0)
    start_time = end_time - timedelta(minutes=1)
    
    print(f"   Start: {start_time.isoformat()}")
    print(f"   End: {end_time.isoformat()}")
    
    url = f"{base_url}/buckets/{window_bucket}/events"
    params = {
        'start': start_time.isoformat(),
        'end': end_time.isoformat(),
        'limit': 10
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            events = response.json()
            print(f"   Success! Got {len(events)} events")
            if events:
                print(f"   First event: {events[0].get('timestamp', 'no timestamp')}")
                print(f"   Last event: {events[-1].get('timestamp', 'no timestamp')}")
        else:
            print(f"   Error: {response.text[:300]}")
    except Exception as e:
        print(f"   Exception: {e}")

if __name__ == "__main__":
    test_activitywatch()