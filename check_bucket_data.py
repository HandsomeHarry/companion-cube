#!/usr/bin/env python3
"""Check what data is actually in the buckets"""

import requests
import json
from datetime import datetime

base_url = "http://localhost:5600/api/0"

# Get all buckets with their info
response = requests.get(f"{base_url}/buckets")
if response.status_code == 200:
    buckets = response.json()
    
    print("Bucket Information:")
    print("=" * 80)
    
    for bucket_id, bucket_info in buckets.items():
        print(f"\nBucket: {bucket_id}")
        print(f"  Type: {bucket_info.get('type', 'unknown')}")
        print(f"  Created: {bucket_info.get('created', 'unknown')}")
        print(f"  Last updated: {bucket_info.get('last_updated', 'unknown')}")
        print(f"  Hostname: {bucket_info.get('hostname', 'unknown')}")
        
        # Get event count
        events_url = f"{base_url}/buckets/{bucket_id}/events/count"
        count_response = requests.get(events_url)
        if count_response.status_code == 200:
            count = count_response.json()
            print(f"  Total events: {count}")
        
        # Get a sample of recent events
        events_url = f"{base_url}/buckets/{bucket_id}/events?limit=1"
        events_response = requests.get(events_url)
        if events_response.status_code == 200:
            events = events_response.json()
            if events:
                event = events[0]
                print(f"  Latest event timestamp: {event.get('timestamp', 'unknown')}")
                print(f"  Latest event data: {json.dumps(event.get('data', {}), indent=4)[:200]}")
            else:
                print("  No events in bucket")