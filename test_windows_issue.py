#!/usr/bin/env python3
"""Test to identify Windows-specific ActivityWatch issues"""

import requests
import json
from datetime import datetime, timezone, timedelta
import socket

def test_direct_api():
    """Test direct API calls to identify the issue"""
    base_url = "http://localhost:5600/api/0"
    
    print("Direct API Test")
    print("=" * 60)
    
    # Get buckets
    buckets_response = requests.get(f"{base_url}/buckets")
    print(f"Get buckets status: {buckets_response.status_code}")
    
    if buckets_response.status_code == 200:
        buckets = buckets_response.json()
        
        # Find first window bucket
        window_bucket = None
        for bucket in buckets:
            if 'window' in bucket:
                window_bucket = bucket
                break
        
        if window_bucket:
            print(f"\nTesting bucket: {window_bucket}")
            
            # Test different time ranges
            now = datetime.now(timezone.utc).replace(microsecond=0)
            
            test_cases = [
                ("1 minute ago", now - timedelta(minutes=1), now),
                ("5 minutes ago", now - timedelta(minutes=5), now - timedelta(seconds=2)),
                ("10 minutes ago", now - timedelta(minutes=10), now - timedelta(seconds=5)),
                ("30 minutes ago", now - timedelta(minutes=30), now - timedelta(seconds=10)),
            ]
            
            for desc, start, end in test_cases:
                print(f"\nTest: {desc}")
                
                # Try both time formats
                formats = [
                    ("Z suffix", start.isoformat().replace('+00:00', 'Z'), end.isoformat().replace('+00:00', 'Z')),
                    ("+00:00 suffix", start.isoformat(), end.isoformat()),
                ]
                
                for fmt_name, start_str, end_str in formats:
                    url = f"{base_url}/buckets/{window_bucket}/events"
                    params = {
                        'start': start_str,
                        'end': end_str,
                        'limit': 100
                    }
                    
                    print(f"  {fmt_name}: ", end='')
                    try:
                        response = requests.get(url, params=params, timeout=5)
                        print(f"Status {response.status_code}", end='')
                        
                        if response.status_code == 200:
                            events = response.json()
                            print(f" - {len(events)} events")
                        else:
                            print(f" - Error: {response.text[:100]}")
                            
                    except Exception as e:
                        print(f" - Exception: {e}")

if __name__ == "__main__":
    test_direct_api()