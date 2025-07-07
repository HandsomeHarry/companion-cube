#!/usr/bin/env python3
"""Test the fixed ActivityWatch client"""

import logging

# Set up debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from activitywatch_client import ActivityWatchClient

print("Testing fixed ActivityWatch client...\n")

client = ActivityWatchClient()

# Test connection
print("Testing connection...")
result = client.test_connection()
print(f"Connected: {result['connected']}")

# Get some window events
print("\nGetting window events...")
events = client.get_window_events(hours_back=0.5)  # Last 30 minutes
print(f"Got {len(events)} window events")

if events:
    print("\nFirst few events:")
    for event in events[:3]:
        print(f"  - {event.get('timestamp')}: {event.get('data', {}).get('app')} - {event.get('data', {}).get('title', '')[:50]}")

# Get multi-timeframe data
print("\nGetting multi-timeframe data...")
data = client.get_multi_timeframe_data()

for timeframe, events_dict in data.items():
    total_events = sum(len(events) for events in events_dict.values())
    print(f"{timeframe}: {total_events} total events")