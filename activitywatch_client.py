import requests
import json
import socket
import time
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
        
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[dict] = None, retries: int = 3) -> Optional[dict]:
        """Make HTTP request to ActivityWatch API with error handling and retries"""
        for attempt in range(retries):
            try:
                url = f"{self.base_url}/{endpoint}"
                
                # Log the URL for debugging
                if '?' in endpoint:
                    logger.debug(f"Request URL: {url}")
                
                response = requests.request(method, url, json=data, timeout=10)
                
                # Handle specific status codes
                if response.status_code == 500:
                    # Log more details about the error
                    logger.warning(f"ActivityWatch 500 error for URL: {url}")
                    logger.warning(f"Response text: {response.text[:200]}")
                    
                    # Internal server error - might be temporary
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 2  # Exponential backoff
                        logger.warning(f"Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"ActivityWatch API error after {retries} attempts: {response.status_code}")
                        return None
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.ConnectionError:
                if attempt == retries - 1:
                    logger.warning("ActivityWatch not running or unreachable")
                return None
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    logger.warning(f"ActivityWatch API timeout, retry {attempt + 1}/{retries}")
                    continue
                else:
                    logger.warning("ActivityWatch API request timed out")
                return None
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    logger.error(f"ActivityWatch API error: {e}")
                return None
        
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
        
        # Check for buckets by prefix
        window_found = False
        afk_found = False
        web_buckets = []
        
        for bucket_name in buckets:
            if bucket_name.startswith('aw-watcher-window_'):
                window_found = True
                logger.debug(f"Found window bucket: {bucket_name}")
            elif bucket_name.startswith('aw-watcher-afk_'):
                afk_found = True
                logger.debug(f"Found AFK bucket: {bucket_name}")
            elif 'web' in bucket_name:
                web_buckets.append(bucket_name)
                logger.debug(f"Found web bucket: {bucket_name}")
        
        results['buckets']['window'] = window_found
        results['buckets']['afk'] = afk_found
        results['buckets']['web'] = len(web_buckets) > 0
        results['web_buckets'] = web_buckets
        
        if not window_found:
            results['errors'].append("No window watcher bucket found")
        if not afk_found:
            results['errors'].append("No AFK watcher bucket found")
        
        return results
    
    def get_buckets(self) -> Dict[str, dict]:
        """Get all available buckets from ActivityWatch"""
        buckets = self._make_request("buckets")
        return buckets or {}
    
    def get_events(self, bucket_id: str, start_time: datetime, end_time: datetime) -> List[dict]:
        """Get events from a specific bucket within time range"""
        # Ensure times are timezone-aware and properly formatted
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
            
        # ActivityWatch prefers ISO format with Z suffix
        start_iso = start_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        end_iso = end_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        # Ensure end time is not in the future
        now = datetime.now(timezone.utc)
        if end_time > now:
            end_time = now
            end_iso = end_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        endpoint = f"buckets/{bucket_id}/events"
        params = f"?start={start_iso}&end={end_iso}&limit=1000"
        
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
                [period[0].isoformat().replace('+00:00', 'Z'), 
                 period[1].isoformat().replace('+00:00', 'Z')] 
                for period in timeperiods
            ]
        }
        
        result = self._make_request("query", method="POST", data=query_data)
        return result or {}
    
    def get_window_events(self, hours_back: float = 1.0) -> List[dict]:
        """Get window events from the last N hours"""
        now = datetime.now(timezone.utc).replace(microsecond=0)
        # Subtract a few seconds from end time to avoid querying the exact current moment
        end_time = now - timedelta(seconds=2)
        start_time = end_time - timedelta(hours=hours_back)
        
        buckets = self.get_buckets()
        
        # Try to find the window bucket with data - prefer buckets with recent updates
        window_buckets = []
        for bucket_name, bucket_info in buckets.items():
            if bucket_name.startswith('aw-watcher-window_'):
                # Check if bucket has recent data
                last_updated = bucket_info.get('last_updated')
                window_buckets.append((bucket_name, last_updated))
                logger.debug(f"Found window bucket: {bucket_name}, last updated: {last_updated}")
        
        if not window_buckets:
            logger.warning("No window bucket found")
            return []
        
        # Sort by last_updated (most recent first), None values go to end
        window_buckets.sort(key=lambda x: x[1] if x[1] else '', reverse=True)
        window_bucket = window_buckets[0][0]
        logger.info(f"Using window bucket: {window_bucket}")
        
        events = self.get_events(window_bucket, start_time, end_time)
        
        if events:
            # Sort events by timestamp
            events.sort(key=lambda x: x['timestamp'])
        
        return events
    
    def get_web_events(self, hours_back: float = 1.0) -> List[dict]:
        """Get web browsing events from the last N hours"""
        now = datetime.now(timezone.utc).replace(microsecond=0)
        end_time = now - timedelta(seconds=2)
        start_time = end_time - timedelta(hours=hours_back)
        
        buckets = self.get_buckets()
        web_events = []
        
        # Find all web buckets dynamically (supports any browser)
        web_buckets = []
        for bucket_name, bucket_info in buckets.items():
            if bucket_name.startswith('aw-watcher-web'):
                last_updated = bucket_info.get('last_updated')
                web_buckets.append((bucket_name, last_updated))
        
        if web_buckets:
            # Sort by last_updated (most recent first) and use the most active bucket
            web_buckets.sort(key=lambda x: x[1] if x[1] else '', reverse=True)
            selected_bucket = web_buckets[0][0]
            logger.info(f"Using web bucket: {selected_bucket}")
            
            events = self.get_events(selected_bucket, start_time, end_time)
            web_events.extend(events)
        else:
            logger.warning("No web bucket found")
        
        # Sort events by timestamp
        web_events.sort(key=lambda x: x['timestamp'])
        
        return web_events
    
    def get_afk_events(self, hours_back: float = 1.0) -> List[dict]:
        """Get AFK events from the last N hours"""
        now = datetime.now(timezone.utc).replace(microsecond=0)
        end_time = now - timedelta(seconds=2)
        start_time = end_time - timedelta(hours=hours_back)
        
        buckets = self.get_buckets()
        
        # Try to find the AFK bucket with data - prefer buckets with recent updates
        afk_buckets = []
        for bucket_name, bucket_info in buckets.items():
            if bucket_name.startswith('aw-watcher-afk_'):
                last_updated = bucket_info.get('last_updated')
                afk_buckets.append((bucket_name, last_updated))
                logger.debug(f"Found AFK bucket: {bucket_name}, last updated: {last_updated}")
        
        if not afk_buckets:
            logger.warning("No AFK bucket found")
            return []
        
        # Sort by last_updated (most recent first), None values go to end
        afk_buckets.sort(key=lambda x: x[1] if x[1] else '', reverse=True)
        afk_bucket = afk_buckets[0][0]
        logger.info(f"Using AFK bucket: {afk_bucket}")
        
        events = self.get_events(afk_bucket, start_time, end_time)
        if events:
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
        buckets = self.get_buckets()
        
        # Try to find the AFK bucket with most recent data
        afk_buckets = []
        for bucket_name, bucket_info in buckets.items():
            if bucket_name.startswith('aw-watcher-afk_'):
                last_updated = bucket_info.get('last_updated')
                afk_buckets.append((bucket_name, last_updated))
        
        if not afk_buckets:
            logger.warning("No AFK bucket found")
            return False
        
        # Sort by last_updated (most recent first)
        afk_buckets.sort(key=lambda x: x[1] if x[1] else '', reverse=True)
        afk_bucket = afk_buckets[0][0]
        
        # Get last 5 minutes of AFK data
        now = datetime.now(timezone.utc).replace(microsecond=0)
        end_time = now - timedelta(seconds=2)
        start_time = end_time - timedelta(minutes=5)
        
        events = self.get_events(afk_bucket, start_time, end_time)
        
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