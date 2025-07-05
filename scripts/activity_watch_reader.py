#!/usr/bin/env python3
"""
ActivityWatch Data Reader
Fetches and displays activity data from ActivityWatch server
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time
import sys


class ActivityWatchReader:
    def __init__(self, base_url: str = "http://localhost:5600"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/0"
        
    def check_connection(self) -> bool:
        """Check if ActivityWatch server is running"""
        try:
            response = requests.get(f"{self.api_base}/info", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_buckets(self) -> Dict[str, Any]:
        """Get all available buckets"""
        try:
            response = requests.get(f"{self.api_base}/buckets")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching buckets: {e}")
            return {}
    
    def get_bucket_events(self, bucket_id: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events from a specific bucket"""
        try:
            params = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
            response = requests.get(f"{self.api_base}/buckets/{bucket_id}/events", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching events from bucket {bucket_id}: {e}")
            return []
    
    def query_data(self, query: str, timeperiods: List[str]) -> Dict:
        """Execute a custom query"""
        try:
            payload = {
                "query": query,
                "timeperiods": timeperiods
            }
            response = requests.post(f"{self.api_base}/query", json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error executing query: {e}")
            return {}


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def main():
    reader = ActivityWatchReader()
    
    print("ActivityWatch Data Reader")
    print("-" * 40)
    
    # Check connection
    if not reader.check_connection():
        print("❌ Cannot connect to ActivityWatch server!")
        print("Please make sure ActivityWatch is running on http://localhost:5600")
        sys.exit(1)
    
    print("✅ Connected to ActivityWatch server")
    
    # Get time range (last 24 hours)
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    print(f"📅 Showing data from: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}")
    
    # Get all buckets
    print_header("Available Buckets")
    buckets = reader.get_buckets()
    
    if not buckets:
        print("No buckets found!")
        return
    
    for bucket_id, bucket_info in buckets.items():
        bucket_type = bucket_info.get('type', 'unknown')
        hostname = bucket_info.get('hostname', 'unknown')
        created = bucket_info.get('created', 'unknown')
        event_count = bucket_info.get('event_count', 0)
        
        print(f"🪣 {bucket_id}")
        print(f"   Type: {bucket_type}")
        print(f"   Hostname: {hostname}")
        print(f"   Events: {event_count}")
        print(f"   Created: {created}")
        print()
    
    # Get recent events from each bucket
    for bucket_id in buckets.keys():
        print_header(f"Recent Events: {bucket_id}")
        
        events = reader.get_bucket_events(bucket_id, start_time, end_time)
        
        if not events:
            print(f"No events found in bucket {bucket_id}")
            continue
        
        # Sort events by timestamp (newest first)
        events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Show last 10 events
        for event in events[:10]:
            timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            duration = event.get('duration', 0)
            data = event.get('data', {})
            
            print(f"⏰ {timestamp.strftime('%H:%M:%S')} ({format_duration(duration)})")
            
            # Display relevant data based on bucket type
            if 'currentwindow' in bucket_id.lower():
                app = data.get('app', 'Unknown')
                title = data.get('title', 'No title')
                print(f"   📱 App: {app}")
                print(f"   📄 Title: {title[:80]}{'...' if len(title) > 80 else ''}")
            
            elif 'afk' in bucket_id.lower():
                status = data.get('status', 'unknown')
                print(f"   👤 Status: {status}")
            
            elif 'web' in bucket_id.lower():
                url = data.get('url', 'No URL')
                title = data.get('title', 'No title')
                print(f"   🌐 URL: {url}")
                print(f"   📄 Title: {title[:80]}{'...' if len(title) > 80 else ''}")
            
            else:
                # Generic data display
                for key, value in data.items():
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"   {key}: {value}")
            
            print()
    
    # Show application usage summary
    print_header("Application Usage Summary (Last 24h)")
    
    # Try to find window watcher bucket
    window_bucket = None
    for bucket_id in buckets.keys():
        if 'currentwindow' in bucket_id.lower():
            window_bucket = bucket_id
            break
    
    if window_bucket:
        events = reader.get_bucket_events(window_bucket, start_time, end_time)
        
        # Calculate app usage
        app_usage = {}
        for event in events:
            app = event.get('data', {}).get('app', 'Unknown')
            duration = event.get('duration', 0)
            app_usage[app] = app_usage.get(app, 0) + duration
        
        # Sort by usage time
        sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
        
        for app, total_seconds in sorted_apps[:15]:  # Top 15 apps
            print(f"📱 {app:20} {format_duration(total_seconds):>10}")
    
    else:
        print("No window watcher bucket found - cannot show app usage")
    
    print("\n" + "="*60)
    print("Data fetch complete! 🎉")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)