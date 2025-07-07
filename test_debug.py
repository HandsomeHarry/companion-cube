#!/usr/bin/env python3
"""Debug script to test ActivityWatch with detailed logging"""

import logging
import sys

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import after setting up logging
from activitywatch_client import ActivityWatchClient
from event_processor import EventProcessor

def test_debug():
    print("Testing ActivityWatch client with debug logging...\n")
    
    client = ActivityWatchClient()
    
    # Test getting multi-timeframe data (this is what companion_main.py does)
    print("Getting multi-timeframe data...")
    try:
        data = client.get_multi_timeframe_data()
        
        for timeframe, events_dict in data.items():
            print(f"\n{timeframe}:")
            for event_type, events in events_dict.items():
                print(f"  {event_type}: {len(events)} events")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_debug()