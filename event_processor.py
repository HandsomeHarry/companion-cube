from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import logging
import re
from collections import defaultdict, Counter
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class EventProcessor:
    def __init__(self):
        self.distraction_apps = {
            'social': ['facebook', 'twitter', 'instagram', 'tiktok', 'snapchat', 'discord', 'slack'],
            'video': ['youtube', 'netflix', 'twitch', 'hulu', 'prime video'],
            'news': ['reddit', 'news', 'cnn', 'bbc', 'hackernews'],
            'games': ['steam', 'game', 'minecraft', 'fortnite', 'league of legends']
        }
        
        self.distraction_domains = {
            'social': ['facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com', 'discord.com'],
            'video': ['youtube.com', 'netflix.com', 'twitch.tv', 'hulu.com'],
            'news': ['reddit.com', 'news.ycombinator.com', 'cnn.com', 'bbc.com'],
            'games': ['store.steampowered.com', 'twitch.tv/directory/gaming']
        }
        
        self.productivity_apps = {
            'coding': ['code', 'visual studio', 'vim', 'emacs', 'sublime', 'atom', 'pycharm', 'intellij', 'terminal'],
            'writing': ['word', 'docs', 'notion', 'obsidian', 'notepad', 'typora', 'scrivener'],
            'design': ['photoshop', 'illustrator', 'figma', 'sketch', 'canva'],
            'research': ['chrome', 'firefox', 'safari', 'edge', 'brave']
        }
        
        self.focus_threshold_minutes = 15
        self.rapid_switching_threshold = 5
        self.rapid_switching_window = 10
    
    def filter_and_summarize_data(self, multi_timeframe_data: Dict[str, Dict[str, List[dict]]]) -> Dict[str, Dict]:
        """Filter clutter and create clean summaries for each timeframe"""
        summaries = {}
        
        for timeframe, data in multi_timeframe_data.items():
            summary = {
                'timeframe': timeframe,
                'is_afk': self._is_currently_afk(data['afk']),
                'active_time_minutes': 0,
                'app_summary': {},
                'web_summary': {},
                'focus_sessions': [],
                'distractions': [],
                'app_switches': 0,
                'behavior_pattern': '',
                'key_activities': []
            }
            
            # Process window events
            if data['window']:
                window_summary = self._summarize_window_events(data['window'])
                summary.update(window_summary)
            
            # Process web events
            if data['web']:
                web_summary = self._summarize_web_events(data['web'])
                summary['web_summary'] = web_summary
                
                # Merge web distractions
                summary['distractions'].extend(web_summary.get('distractions', []))
            
            # Determine behavior pattern
            summary['behavior_pattern'] = self._determine_behavior_pattern(summary)
            
            summaries[timeframe] = summary
        
        return summaries
    
    def _is_currently_afk(self, afk_events: List[dict]) -> bool:
        """Check if user is AFK based on events"""
        if not afk_events:
            return False
        
        latest_event = max(afk_events, key=lambda x: x['timestamp'])
        return latest_event.get('data', {}).get('status') == 'afk'
    
    def _summarize_window_events(self, events: List[dict]) -> Dict:
        """Summarize window events, filtering out noise"""
        if not events:
            return {}
        
        app_durations = defaultdict(float)
        app_titles = defaultdict(list)
        focus_sessions = []
        app_switches = 0
        
        # Sort events by timestamp
        events.sort(key=lambda x: x['timestamp'])
        
        # Group consecutive events by app
        current_app = None
        session_start = None
        session_duration = 0
        
        for i, event in enumerate(events):
            app = event.get('data', {}).get('app', '').lower()
            title = event.get('data', {}).get('title', '')
            duration = event.get('duration', 0) / 60  # Convert to minutes
            
            # Skip very short events (less than 3 seconds)
            if duration < 0.05:
                continue
            
            # Track app usage
            if app:
                app_durations[app] += duration
                if title and title not in app_titles[app]:
                    app_titles[app].append(title)
            
            # Track app switches and sessions
            if app != current_app:
                # Save previous session if it was a focus session
                if current_app and session_duration >= self.focus_threshold_minutes:
                    focus_sessions.append({
                        'app': current_app,
                        'duration_minutes': session_duration,
                        'start_time': session_start,
                        'category': self._categorize_app(current_app)
                    })
                
                if current_app is not None:
                    app_switches += 1
                
                current_app = app
                session_start = event.get('timestamp')
                session_duration = duration
            else:
                session_duration += duration
        
        # Check final session
        if current_app and session_duration >= self.focus_threshold_minutes:
            focus_sessions.append({
                'app': current_app,
                'duration_minutes': session_duration,
                'start_time': session_start,
                'category': self._categorize_app(current_app)
            })
        
        # Calculate total active time
        total_active_time = sum(app_durations.values())
        
        # Get top apps
        top_apps = sorted(app_durations.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Identify distractions
        distractions = []
        for app, duration in app_durations.items():
            if self._is_distraction_app(app) and duration > 2:  # More than 2 minutes
                distractions.append({
                    'type': 'app',
                    'name': app,
                    'duration_minutes': duration,
                    'category': self._categorize_app(app)
                })
        
        # Identify key activities from titles
        key_activities = self._extract_key_activities(app_titles)
        
        return {
            'active_time_minutes': total_active_time,
            'app_summary': dict(top_apps),
            'app_titles': dict(app_titles),
            'focus_sessions': focus_sessions,
            'distractions': distractions,
            'app_switches': app_switches,
            'key_activities': key_activities
        }
    
    def _summarize_web_events(self, events: List[dict]) -> Dict:
        """Summarize web browsing events"""
        if not events:
            return {}
        
        domain_durations = defaultdict(float)
        domain_titles = defaultdict(list)
        distractions = []
        
        for event in events:
            url = event.get('data', {}).get('url', '')
            title = event.get('data', {}).get('title', '')
            duration = event.get('duration', 0) / 60  # Convert to minutes
            
            if url:
                domain = self._extract_domain(url)
                domain_durations[domain] += duration
                
                if title and title not in domain_titles[domain]:
                    domain_titles[domain].append(title)
                
                # Check if it's a distraction
                if self._is_distraction_domain(domain) and duration > 1:
                    distractions.append({
                        'type': 'web',
                        'name': domain,
                        'duration_minutes': duration,
                        'category': self._categorize_domain(domain)
                    })
        
        # Get top domains
        top_domains = sorted(domain_durations.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'domain_summary': dict(top_domains),
            'domain_titles': dict(domain_titles),
            'distractions': distractions,
            'total_web_time': sum(domain_durations.values())
        }
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return 'unknown'
    
    def _is_distraction_domain(self, domain: str) -> bool:
        """Check if a domain is distracting"""
        domain_lower = domain.lower()
        for domains in self.distraction_domains.values():
            if any(dist_domain in domain_lower for dist_domain in domains):
                return True
        return False
    
    def _categorize_domain(self, domain: str) -> str:
        """Categorize a domain"""
        domain_lower = domain.lower()
        for category, domains in self.distraction_domains.items():
            if any(dist_domain in domain_lower for dist_domain in domains):
                return f"distraction_{category}"
        return "neutral"
    
    def _extract_key_activities(self, app_titles: Dict[str, List[str]]) -> List[str]:
        """Extract key activities from window titles"""
        activities = []
        
        for app, titles in app_titles.items():
            for title in titles[:3]:  # Look at top 3 titles per app
                activity = self._infer_task_from_title(title, app)
                if activity and activity not in activities:
                    activities.append(activity)
        
        return activities[:5]  # Return top 5 activities
    
    def _determine_behavior_pattern(self, summary: Dict) -> str:
        """Determine the behavior pattern from summary data"""
        if summary.get('is_afk', False):
            return "away"
        
        active_time = summary.get('active_time_minutes', 0)
        app_switches = summary.get('app_switches', 0)
        focus_sessions = len(summary.get('focus_sessions', []))
        distractions = len(summary.get('distractions', []))
        
        # Calculate metrics
        if active_time > 0:
            switch_rate = app_switches / active_time
            distraction_ratio = sum(d['duration_minutes'] for d in summary.get('distractions', [])) / active_time
        else:
            switch_rate = 0
            distraction_ratio = 0
        
        # Determine pattern
        if focus_sessions > 0 and switch_rate < 0.2:
            return "focused_work"
        elif distraction_ratio > 0.5:
            return "heavily_distracted"
        elif switch_rate > 0.5:
            return "context_switching"
        elif active_time < 5:
            return "light_activity"
        else:
            return "normal_work"
    
    def create_behavior_comparison(self, summaries: Dict[str, Dict]) -> Dict:
        """Create a comparison of behavior across timeframes"""
        comparison = {
            'trend': '',
            'focus_trend': '',
            'distraction_trend': '',
            'current_state': '',
            'recommendations': []
        }
        
        # Get data for different timeframes
        five_min = summaries.get('5_minutes', {})
        ten_min = summaries.get('10_minutes', {})
        thirty_min = summaries.get('30_minutes', {})
        one_hour = summaries.get('1_hour', {})
        
        # Analyze focus trend
        recent_focus = len(five_min.get('focus_sessions', []))
        older_focus = len(thirty_min.get('focus_sessions', [])) - recent_focus
        
        if recent_focus > 0 and older_focus == 0:
            comparison['focus_trend'] = 'entering_focus'
        elif recent_focus == 0 and older_focus > 0:
            comparison['focus_trend'] = 'losing_focus'
        elif recent_focus > 0:
            comparison['focus_trend'] = 'maintaining_focus'
        else:
            comparison['focus_trend'] = 'no_focus'
        
        # Analyze distraction trend
        recent_distractions = five_min.get('distractions', [])
        ten_min_distractions = ten_min.get('distractions', [])
        
        if len(recent_distractions) > len(ten_min_distractions) * 0.5:
            comparison['distraction_trend'] = 'increasing'
        elif len(recent_distractions) < len(ten_min_distractions) * 0.2:
            comparison['distraction_trend'] = 'decreasing'
        else:
            comparison['distraction_trend'] = 'stable'
        
        # Determine current state based on patterns
        recent_pattern = five_min.get('behavior_pattern', '')
        if recent_pattern == 'focused_work':
            comparison['current_state'] = 'flow'
        elif recent_pattern == 'heavily_distracted':
            comparison['current_state'] = 'needs_nudge'
        elif recent_pattern == 'context_switching':
            comparison['current_state'] = 'needs_nudge'
        elif recent_pattern == 'away':
            comparison['current_state'] = 'afk'
        else:
            comparison['current_state'] = 'working'
        
        return comparison
    
    def generate_llm_context(self, summaries: Dict[str, Dict], comparison: Dict) -> str:
        """Generate a concise context string for the LLM"""
        # Get the most recent summary
        five_min = summaries.get('5_minutes', {})
        thirty_min = summaries.get('30_minutes', {})
        
        context_parts = []
        
        # Current activity
        if five_min.get('is_afk'):
            context_parts.append("User is currently away from keyboard.")
        else:
            top_app = list(five_min.get('app_summary', {}).items())
            if top_app:
                app_name, duration = top_app[0]
                context_parts.append(f"Currently using {app_name} for {duration:.1f} minutes.")
        
        # Behavior pattern
        pattern = five_min.get('behavior_pattern', '')
        if pattern:
            context_parts.append(f"Behavior pattern: {pattern.replace('_', ' ')}.")
        
        # Focus information
        focus_trend = comparison.get('focus_trend', '')
        if focus_trend == 'entering_focus':
            context_parts.append("Just entering a focus session.")
        elif focus_trend == 'maintaining_focus':
            context_parts.append("Maintaining good focus.")
        elif focus_trend == 'losing_focus':
            context_parts.append("Focus appears to be waning.")
        
        # Distraction information
        distraction_trend = comparison.get('distraction_trend', '')
        if distraction_trend == 'increasing':
            distractions = five_min.get('distractions', [])
            if distractions:
                dist_names = [d['name'] for d in distractions[:2]]
                context_parts.append(f"Recent distractions: {', '.join(dist_names)}.")
        
        # Key activities
        activities = five_min.get('key_activities', [])
        if activities:
            context_parts.append(f"Working on: {activities[0]}.")
        
        # App switching
        if five_min.get('app_switches', 0) > 3:
            context_parts.append(f"High context switching ({five_min['app_switches']} switches).")
        
        return " ".join(context_parts)
    
    def _categorize_app(self, app: str) -> str:
        """Categorize an application as productive, distraction, or neutral"""
        app_lower = app.lower()
        
        for category, apps in self.productivity_apps.items():
            if any(prod_app in app_lower for prod_app in apps):
                return f"productive_{category}"
        
        for category, apps in self.distraction_apps.items():
            if any(dist_app in app_lower for dist_app in apps):
                return f"distraction_{category}"
        
        return "neutral"
    
    def _is_distraction_app(self, app: str) -> bool:
        """Check if an application is considered distracting"""
        app_lower = app.lower()
        all_distractions = []
        for apps in self.distraction_apps.values():
            all_distractions.extend(apps)
        
        return any(dist_app in app_lower for dist_app in all_distractions)
    
    def _infer_task_from_title(self, title: str, app: str) -> str:
        """Infer what task the user is working on from window title"""
        if not title:
            return ""
        
        # Clean up title
        title_lower = title.lower()
        
        # Common patterns
        if 'github' in title_lower or 'git' in title_lower:
            return "Code development"
        elif any(term in title_lower for term in ['email', 'inbox', 'gmail', 'outlook']):
            return "Email management"
        elif any(term in title_lower for term in ['meeting', 'zoom', 'teams', 'slack call']):
            return "Video meeting"
        elif any(term in title_lower for term in ['doc', 'document', 'writing', 'report']):
            return "Document editing"
        elif any(term in title_lower for term in ['stackoverflow', 'documentation', 'tutorial']):
            return "Research/learning"
        elif 'slack' in title_lower or 'discord' in title_lower:
            return "Team communication"
        elif any(term in title_lower for term in ['.py', '.js', '.java', '.cpp', '.cs']):
            return "Programming"
        else:
            return ""
    
    def get_daily_summary(self, today_summary: Dict) -> Dict:
        """Generate daily summary statistics"""
        return {
            'total_active_minutes': today_summary.get('active_time_minutes', 0),
            'focus_sessions': len(today_summary.get('focus_sessions', [])),
            'total_distractions': len(today_summary.get('distractions', [])),
            'distraction_time': sum(d['duration_minutes'] for d in today_summary.get('distractions', [])),
            'top_apps': list(today_summary.get('app_summary', {}).keys())[:5],
            'longest_focus': max([s['duration_minutes'] for s in today_summary.get('focus_sessions', [])], default=0),
            'app_switches': today_summary.get('app_switches', 0),
            'key_activities': today_summary.get('key_activities', [])
        }
    
    def generate_adhd_prompt(self, state: str, context: str, timeframe_context: Dict = None) -> str:
        """Generate ADHD-appropriate prompt based on state and context"""
        if state == "flow":
            return f"""You are an ADHD coach. The user is in a flow state. {context}
Respond with brief encouragement (max 20 words). Acknowledge their focus and remind them they're doing great. 
No suggestions or interruptions - just positive reinforcement."""
        
        elif state == "needs_nudge":
            return f"""You are a gentle ADHD companion. {context}
The user might be stuck or distracted. Provide:
1) Acknowledge what you see without judgment
2) One specific, tiny next action they could take
3) Encouragement that any progress is good progress
Keep it under 40 words, warm and supportive."""
        
        elif state == "working":
            return f"""The user is working steadily. {context}
Provide a brief acknowledgment of their progress. If they've been on the same task >45 min, gently suggest a stretch.
Keep it to one supportive sentence, max 20 words."""
        
        elif state == "afk":
            return f"""The user just returned to their computer. Welcome them back warmly and ask what they'd like to focus on next.
Keep it brief and encouraging, max 20 words."""
        
        else:
            return f"""You are a supportive ADHD companion. {context}
Provide brief, encouraging feedback about their current activity. Max 20 words."""