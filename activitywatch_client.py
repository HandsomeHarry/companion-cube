import requests
import json
import socket
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ActivityWatchClient:
    def __init__(self, host: str = "localhost", port: int = 5600):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api/0"
        self.hostname = socket.gethostname()
        
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[dict] = None) -> Optional[dict]:
        """Make HTTP request to ActivityWatch API with error handling"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.request(method, url, json=data, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            logger.warning("ActivityWatch not running or unreachable")
            return None
        except requests.exceptions.Timeout:
            logger.warning("ActivityWatch API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"ActivityWatch API error: {e}")
            return None
    
    def test_connection(self) -> Dict[str, bool]:
        """Test connection to ActivityWatch and check available buckets"""
        results = {
            'connected': False,
            'buckets': {},
            'errors': []
        }
        
        buckets = self.get_buckets()
        if buckets is None:
            results['errors'].append("Cannot connect to ActivityWatch API")
            return results
        
        results['connected'] = True
        
        # Check for expected buckets
        expected_buckets = {
            'window': f"aw-watcher-window_{self.hostname}",
            'afk': f"aw-watcher-afk_{self.hostname}",
        }
        
        # Check for web watchers
        web_buckets = []
        for bucket_name in buckets:
            if 'web' in bucket_name and self.hostname in bucket_name:
                web_buckets.append(bucket_name)
        
        for bucket_type, bucket_name in expected_buckets.items():
            results['buckets'][bucket_type] = bucket_name in buckets
            if not results['buckets'][bucket_type]:
                results['errors'].append(f"Missing {bucket_type} bucket: {bucket_name}")
        
        results['buckets']['web'] = len(web_buckets) > 0
        results['web_buckets'] = web_buckets
        
        return results
    
    def get_buckets(self) -> Dict[str, dict]:
        """Get all available buckets from ActivityWatch"""
        buckets = self._make_request("buckets")
        return buckets or {}
    
    def get_events(self, bucket_id: str, start_time: datetime, end_time: datetime) -> List[dict]:
        """Get events from a specific bucket within time range"""
        start_iso = start_time.isoformat()
        end_iso = end_time.isoformat()
        
        endpoint = f"buckets/{bucket_id}/events"
        params = f"?start={start_iso}&end={end_iso}"
        
        events = self._make_request(endpoint + params)
        return events or []
    
    def query(self, query_str: str, timeperiods: List[tuple] = None) -> dict:
        """Execute a query against ActivityWatch data"""
        if timeperiods is None:
            now = datetime.now(timezone.utc)
            timeperiods = [(now.replace(hour=0, minute=0, second=0), now)]
        
        query_data = {
            "query": [query_str],
            "timeperiods": [
                [period[0].isoformat(), period[1].isoformat()] 
                for period in timeperiods
            ]
        }
        
        result = self._make_request("query", method="POST", data=query_data)
        return result or {}
    
    def get_window_events(self, hours_back: float = 1.0) -> List[dict]:
        """Get window events from the last N hours"""
        now = datetime.now(timezone.utc)
        start_time = now.replace(microsecond=0) - timedelta(hours=hours_back)
        
        window_bucket = f"aw-watcher-window_{self.hostname}"
        buckets = self.get_buckets()
        
        if window_bucket not in buckets:
            logger.warning(f"Window bucket '{window_bucket}' not found")
            return []
        
        events = self.get_events(window_bucket, start_time, now)
        
        # Sort events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def get_web_events(self, hours_back: float = 1.0) -> List[dict]:
        """Get web browsing events from the last N hours"""
        now = datetime.now(timezone.utc)
        start_time = now.replace(microsecond=0) - timedelta(hours=hours_back)
        
        # Try different possible web bucket names
        possible_buckets = [
            f"aw-watcher-web-chrome_{self.hostname}",
            f"aw-watcher-web-firefox_{self.hostname}",
            f"aw-watcher-web-edge_{self.hostname}",
            f"aw-watcher-web_{self.hostname}"
        ]
        
        buckets = self.get_buckets()
        web_events = []
        
        for bucket_name in possible_buckets:
            if bucket_name in buckets:
                events = self.get_events(bucket_name, start_time, now)
                web_events.extend(events)
        
        # Sort events by timestamp
        web_events.sort(key=lambda x: x['timestamp'])
        
        return web_events
    
    def get_afk_events(self, hours_back: float = 1.0) -> List[dict]:
        """Get AFK events from the last N hours"""
        now = datetime.now(timezone.utc)
        start_time = now.replace(microsecond=0) - timedelta(hours=hours_back)
        
        afk_bucket = f"aw-watcher-afk_{self.hostname}"
        buckets = self.get_buckets()
        
        if afk_bucket not in buckets:
            logger.warning(f"AFK bucket '{afk_bucket}' not found")
            return []
        
        events = self.get_events(afk_bucket, start_time, now)
        events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def get_all_events(self, hours_back: float = 1.0) -> Dict[str, List[dict]]:
        """Get all events from AFK, window, and web buckets"""
        return {
            'window': self.get_window_events(hours_back),
            'web': self.get_web_events(hours_back),
            'afk': self.get_afk_events(hours_back)
        }
    
    def get_multi_timeframe_data(self) -> Dict[str, Dict[str, List[dict]]]:
        """Get data for multiple timeframes: 5min, 10min, 30min, 1hr, today"""
        timeframes = {
            '5_minutes': 5/60,
            '10_minutes': 10/60,
            '30_minutes': 0.5,
            '1_hour': 1.0,
            'today': 24.0  # Will be adjusted to start of day
        }
        
        data = {}
        for timeframe, hours in timeframes.items():
            if timeframe == 'today':
                # Get from start of day
                now = datetime.now(timezone.utc)
                hours_since_midnight = now.hour + now.minute/60
                data[timeframe] = self.get_all_events(hours_since_midnight)
            else:
                data[timeframe] = self.get_all_events(hours)
        
        return data
    
    def get_afk_status(self) -> bool:
        """Check if user is currently AFK (Away From Keyboard)"""
        afk_bucket = f"aw-watcher-afk_{self.hostname}"
        buckets = self.get_buckets()
        
        if afk_bucket not in buckets:
            logger.warning(f"AFK bucket '{afk_bucket}' not found")
            return False
        
        # Get last 5 minutes of AFK data
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=5)
        
        events = self.get_events(afk_bucket, start_time, now)
        
        if not events:
            return False
        
        # Get the most recent event
        latest_event = max(events, key=lambda x: x['timestamp'])
        
        # Check if the latest event indicates AFK
        return latest_event.get('data', {}).get('status') == 'afk'
    
    def get_app_usage_summary(self, hours_back: float = 1.0) -> Dict[str, float]:
        """Get summary of application usage in the last N hours"""
        events = self.get_window_events(hours_back)
        
        app_usage = {}
        for event in events:
            app = event.get('data', {}).get('app', 'Unknown')
            duration = event.get('duration', 0)
            
            if app in app_usage:
                app_usage[app] += duration
            else:
                app_usage[app] = duration
        
        # Convert from seconds to minutes
        return {app: duration / 60 for app, duration in app_usage.items()}
    
    def is_available(self) -> bool:
        """Check if ActivityWatch is running and accessible"""
        buckets = self.get_buckets()
        return buckets is not None