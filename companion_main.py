import json
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import signal
import sys
import argparse

from activitywatch_client import ActivityWatchClient
from event_processor import EventProcessor

# Custom logging formatter with short timestamp
class ShortTimestampFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        from datetime import datetime
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime('%m-%d %H:%M:%S.%f')[:-5]  # Remove last 5 digits of microseconds

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Apply custom formatter to all handlers
for handler in logging.getLogger().handlers:
    handler.setFormatter(ShortTimestampFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger = logging.getLogger(__name__)

class CompanionCube:
    def __init__(self, check_interval: int = 60, mode: str = "coach", verbose: bool = False):
        self.check_interval = check_interval
        self.mode = mode
        self.verbose = verbose
        self.aw_client = ActivityWatchClient()
        self.event_processor = EventProcessor()
        
        # Ollama settings
        self.ollama_url = "http://localhost:11434"
        self.model = "mistral"  # Default model
        
        # File paths for new organized data storage
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.log_file = self.data_dir / "log.json"  # 5-minute activity summaries
        self.daily_summary_file = self.data_dir / "daily_summary.json"  # Daily summaries with 30-min periods
        
        # State tracking
        self.last_intervention = datetime.now(timezone.utc)
        self.last_activity_log = datetime.now(timezone.utc)  # For 5-minute logs
        self.last_thirty_minute_summary = datetime.now(timezone.utc)  # For 30-minute summaries
        self.last_minute_summary = datetime.now(timezone.utc)  # For verbose mode
        self.last_daily_summary_date = datetime.now().date()  # Track daily summaries at 4am
        
        self.intervention_cooldown = {
            "flow": 45,  # Don't interrupt flow for 45 minutes
            "working": 15,  # Check in every 15 minutes when working
            "needs_nudge": 5,  # Can nudge every 5 minutes if needed
            "afk": 0  # No cooldown for AFK
        }
        
        # Daily tracking
        self.daily_stats = {
            'focus_sessions': 0,
            'distractions': 0,
            'interventions': 0
        }
        
        # Set up graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully - no summary generation"""
        print("\n\n💫 Companion Cube shutting down...")
        print("Great work today! See you next time! 🌟")
        sys.exit(0)
    
    def test_connections(self) -> Dict[str, any]:
        """Test connections to ActivityWatch and Ollama"""
        results = {
            'activitywatch': {},
            'ollama': {}
        }
        
        # Test ActivityWatch
        print("\n🔍 Testing ActivityWatch connection...")
        aw_test = self.aw_client.test_connection()
        results['activitywatch'] = aw_test
        
        if aw_test['connected']:
            print("✅ ActivityWatch is connected!")
            print(f"   Found buckets:")
            for bucket_type, found in aw_test['buckets'].items():
                status = "✓" if found else "✗"
                print(f"   {status} {bucket_type}")
            if aw_test.get('web_buckets'):
                print(f"   Web buckets: {', '.join(aw_test['web_buckets'])}")
        else:
            print("❌ ActivityWatch is not running!")
            for error in aw_test.get('errors', []):
                print(f"   - {error}")
        
        # Test Ollama
        print("\n🔍 Testing Ollama connection...")
        ollama_test = self.test_ollama_connection()
        results['ollama'] = ollama_test
        
        if ollama_test['connected']:
            print("✅ Ollama is connected!")
            print(f"   Available models: {', '.join(ollama_test['models'])}")
            print(f"   Selected model: {self.model}")
        else:
            print("❌ Ollama is not running!")
            print("   Run 'ollama serve' to start Ollama")
        
        return results
    
    def test_ollama_connection(self) -> Dict[str, any]:
        """Test Ollama connection and get available models"""
        result = {
            'connected': False,
            'models': [],
            'error': None
        }
        
        try:
            # Test connection
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                result['connected'] = True
                data = response.json()
                result['models'] = [model['name'] for model in data.get('models', [])]
                
                # Check if our selected model is available
                if self.model not in result['models'] and result['models']:
                    # Use first available model
                    self.model = result['models'][0]
                    logger.info(f"Selected model '{self.model}' not found, using '{self.model}'")
            else:
                result['error'] = f"Ollama returned status {response.status_code}"
        except requests.exceptions.ConnectionError:
            result['error'] = "Cannot connect to Ollama"
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def run(self):
        """Main loop for the Companion Cube"""
        logger.info(f"Companion Cube starting in {self.mode} mode")
        
        # Test connections
        connections = self.test_connections()
        
        if not connections['activitywatch']['connected']:
            print("\n❌ Cannot start without ActivityWatch! Please start ActivityWatch and try again.")
            return
        
        if not connections['ollama']['connected']:
            print("\n⚠️  Ollama not found. Will use fallback responses for a limited experience.")
            print("   For best results, install and run Ollama: https://ollama.ai")
        
        print(f"\n🧊 Companion Cube activated!")
        print(f"Mode: {self.mode.capitalize()}")
        print(f"Check interval: {self.check_interval} seconds")
        print("\nI'm here to support you, not judge you. Let's make today great! 💪")
        print("\nPress Ctrl+C to stop\n")
        
        # Schedule end of day summary
        self.last_summary_date = datetime.now().date()
        
        while True:
            try:
                now = datetime.now()
                
                # Check for daily summary at 4am (not midnight)
                if (now.hour == 4 and now.minute < 5 and 
                    now.date() > self.last_daily_summary_date):
                    self.generate_daily_summary()
                    self.last_daily_summary_date = now.date()
                
                # Check for 30-minute summaries at :00 and :30
                if now.minute in [0, 30] and now.minute != getattr(self, '_last_30min_check', -1):
                    self.generate_thirty_minute_summary()
                    self._last_30min_check = now.minute
                
                # Check for minute summaries in verbose mode only
                if self.verbose:
                    self.check_minute_summary()
                
                # Main activity check and 5-minute logging
                self.check_activity()
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.check_interval)
    
    def analyze_user_state_with_llm(self, multi_timeframe_data: Dict) -> Dict:
        """Use LLM to analyze raw activity data and determine user state"""
        try:
            # Prepare raw data for LLM analysis
            raw_data = self.event_processor.prepare_raw_data_for_llm(multi_timeframe_data)
            
            # Create comprehensive prompt for state analysis
            analysis_prompt = self._create_state_analysis_prompt(raw_data)
            
            if self.verbose:
                print(f"\n🧠 LLM STATE ANALYSIS")
                print(f"Raw data summary: {len(raw_data.get('activity_timeline', []))} timeline events")
                print(f"Context switches: {len(raw_data.get('context_switches', []))}")
                print("Sending comprehensive data to LLM for analysis...")
                print(f"\n{'='*60}")
                print(f"🧠 LLM STATE ANALYSIS PROMPT")
                print(f"{'='*60}")
                print(analysis_prompt[:2000] + "..." if len(analysis_prompt) > 2000 else analysis_prompt)
                print(f"{'='*60}")
            
            # Get LLM analysis
            system_prompt = """You are an expert ADHD productivity analyst. Analyze the provided raw activity data and determine the user's current productivity state. Be precise and data-driven in your analysis. Return your analysis in the exact JSON format requested."""
            
            request_data = {
                "model": self.model,
                "prompt": analysis_prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more consistent analysis
                    "num_predict": 400,
                    "num_ctx": 8192,  # Use full 8K context window for Mistral 7B
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "").strip()
                
                if self.verbose:
                    print(f"🤖 LLM Analysis Response:")
                    print(llm_response)
                
                # Parse structured response
                parsed_analysis = self._parse_llm_state_analysis(llm_response)
                
                if parsed_analysis:
                    return parsed_analysis
                else:
                    if self.verbose:
                        print("⚠️ Failed to parse LLM response, using fallback analysis")
                    return self._fallback_state_analysis(raw_data)
            else:
                if self.verbose:
                    print(f"⚠️ LLM request failed (status {response.status_code}), using fallback")
                return self._fallback_state_analysis(raw_data)
                
        except Exception as e:
            logger.debug(f"Error in LLM state analysis: {e}")
            if self.verbose:
                print(f"⚠️ LLM analysis error: {e}")
            return self._fallback_state_analysis(raw_data)
    
    def _create_state_analysis_prompt(self, raw_data: Dict) -> str:
        """Create a comprehensive prompt for LLM state analysis"""
        
        # Extract key statistics
        recent_timeframe = raw_data.get('timeframes', {}).get('5_minutes', {})
        medium_timeframe = raw_data.get('timeframes', {}).get('30_minutes', {})
        
        recent_stats = recent_timeframe.get('statistics', {})
        medium_stats = medium_timeframe.get('statistics', {})
        
        timeline = raw_data.get('activity_timeline', [])
        context_switches = raw_data.get('context_switches', [])
        
        # Check AFK status first
        recent_afk_events = recent_timeframe.get('afk_events', [])
        is_currently_afk = False
        if recent_afk_events:
            latest_afk = max(recent_afk_events, key=lambda x: x['timestamp'])
            is_currently_afk = latest_afk.get('data', {}).get('status') == 'afk'

        # Get current window and web context
        current_app = None
        current_website = None
        current_web_title = None
        
        if timeline:
            # Find most recent app
            for event in reversed(timeline):
                if event['type'] == 'app' and event['name']:
                    current_app = event['name']
                    break
            
            # Find most recent web activity 
            for event in reversed(timeline):
                if event['type'] == 'web' and event['name']:
                    current_website = event['name']
                    current_web_title = event.get('title', '')
                    break

        prompt = f"""Analyze this user's raw activity data and determine their current productivity state for ADHD support.

📊 RAW ACTIVITY DATA ANALYSIS

🚦 AFK STATUS CHECK:
- Currently AFK: {is_currently_afk}
{"- User is away from keyboard - state should be 'afk'" if is_currently_afk else "- User is active at computer"}

🪟 CURRENT WINDOW CONTEXT:
- Current application: {current_app or 'Unknown'}
{"- Browser detected - checking web activity below" if current_app and any(browser in current_app.lower() for browser in ['chrome', 'firefox', 'brave', 'edge', 'safari']) else ""}

🌐 WEB ACTIVITY CONTEXT:
- Current website: {current_website or 'N/A (user not in browser)'}
- Page title: {current_web_title[:100] + '...' if current_web_title and len(current_web_title) > 100 else current_web_title or 'N/A'}
- ⚠️ IMPORTANT: Web data is ONLY relevant if current app is a browser!

⏱️ TIMEFRAME STATISTICS:
Recent 5 minutes:
- Active time: {recent_stats.get('total_active_minutes', 0)} minutes
- Context switches: {recent_stats.get('context_switches', 0)}
- Unique apps: {len(recent_stats.get('unique_apps', []))}
- Unique domains: {len(recent_stats.get('unique_domains', []))}
- Apps used: {', '.join(recent_stats.get('unique_apps', [])[:5])}

Last 30 minutes:
- Active time: {medium_stats.get('total_active_minutes', 0)} minutes  
- Context switches: {medium_stats.get('context_switches', 0)}
- Unique apps: {len(medium_stats.get('unique_apps', []))}
- Unique domains: {len(medium_stats.get('unique_domains', []))}

📊 CROSS-TIMEFRAME PATTERNS:
{self._format_patterns_for_prompt(raw_data.get('patterns', {}))}

📅 COMPREHENSIVE ACTIVITY TIMELINE:"""

        # Add timeline details - PRIORITIZED for LLM context efficiency
        if timeline:
            prompt += f"\nPrioritized activity sequence ({len(timeline)} events - recent 5min data first, then historical context):"
            current_events = [e for e in timeline if e.get('priority') == 'current']
            context_events = [e for e in timeline if e.get('priority') == 'context']
            
            prompt += f"\n\n🔥 CURRENT ACTIVITY (last 5 minutes - max 30 events):"
            for i, event in enumerate(current_events):
                duration = event.get('duration_minutes', 0)
                timeframe = event.get('timeframe_source', 'unknown')
                
                if event['type'] == 'app':
                    prompt += f"\n  {i+1}. [{duration:.1f}min] APP: {event['name']}"
                    if event.get('title'):
                        prompt += f" - {event['title'][:60]}"
                else:  # web
                    prompt += f"\n  {i+1}. [{duration:.1f}min] WEB: {event['name']}"
                    if event.get('title'):
                        prompt += f" - {event['title'][:60]}"
            
            if context_events:
                prompt += f"\n\n📊 HISTORICAL CONTEXT (significant activities from longer timeframes):"
                for i, event in enumerate(context_events[:20]):  # Limit context display
                    duration = event.get('duration_minutes', 0)
                    timeframe = event.get('timeframe_source', 'unknown')
                    
                    if event['type'] == 'app':
                        prompt += f"\n  {i+1}. [{duration:.1f}min] [{timeframe}] {event['name']}"
                    else:  # web
                        prompt += f"\n  {i+1}. [{duration:.1f}min] [{timeframe}] Web: {event['name']}"
        
        # Add context switches - SHOW ALL SWITCHES
        if context_switches:
            prompt += f"\n\n🔄 CONTEXT SWITCHES ({len(context_switches)} total):"
            for i, switch in enumerate(context_switches):  # ALL switches
                prompt += f"\n  {i+1}. {switch['from_app']} → {switch['to_app']}"
        
        prompt += f"""

🎯 ANALYSIS TASK:
Based on this raw data, determine the user's current state for ADHD productivity support.

Consider these ADHD-relevant factors:
1. **Focus Duration**: Long sessions (>15min) in one app suggest flow state
2. **Context Switching**: Rapid switches may indicate distractibility or task exploration  
3. **Activity Patterns**: Are they deep in work, browsing, or switching between tasks?
4. **Productivity Indicators**: Tools like IDEs, documents, vs entertainment/social media
5. **Time Investment**: Duration spent on different types of activities

🚦 CRITICAL 3-BUCKET ANALYSIS HIERARCHY:

1️⃣ **AFK BUCKET**: 
   → If currently AFK = true → state = "afk" (ignore everything else)

2️⃣ **WINDOW BUCKET** (check current app):
   → If current app is NOT a browser:
     - Code editor (vscode, vim, etc.) → "flow" or "working" 
     - Communication (weixin.exe, slack) → "working"
     - Entertainment/games → "needs_nudge"
     - STOP HERE - ignore web data completely

3️⃣ **WEB BUCKET** (ONLY if current app IS a browser):
   → Educational YouTube, documentation → "working"/"flow"
   → GitHub, work sites → "working"/"flow" 
   → Social media, entertainment → "needs_nudge"
   → Multiple tabs/rapid switching → "needs_nudge"

⚠️ CRITICAL: If user is NOT currently in a browser app, web events are historical context only - do NOT use them for current state analysis!

EXAMPLE CORRECT ANALYSIS:

🟢 FLOW STATE: 
- Current app: "code" (VSCode) → Focus on app only, ignore web history → "flow"
- Current app: "brave.exe" + Site: "docs.python.org" → Educational browsing → "flow"

🟡 WORKING: 
- Current app: "weixin.exe" → Communication app → "working" (ignore web data)
- Current app: "brave.exe" + Site: "youtube.com" + Title: "Python Tutorial" → "working"

🟠 NEEDS_NUDGE: 
- Current app: "brave.exe" + Site: "youtube.com" + Title: "Cat Videos" → "needs_nudge"
- Current app: "game.exe" → Entertainment app → "needs_nudge" (ignore web data)

🔴 AFK: Currently AFK = true → "afk" (ignore everything else)

❌ WRONG ANALYSIS EXAMPLES:
- Current app: "vscode" + User previously visited YouTube → DON'T use web data for state!
- Current app: "terminal" + Web history shows GitHub → DON'T assume browsing GitHub now!

REQUIRED OUTPUT FORMAT (JSON):
{{
  "current_state": "[flow|working|needs_nudge|afk]",
  "focus_trend": "[maintaining_focus|entering_focus|losing_focus|variable|none]", 
  "distraction_trend": "[low|moderate|increasing|decreasing|high]",
  "confidence": "[high|medium|low]",
  "primary_activity": "[brief description]",
  "reasoning": "[2-3 sentence explanation of the analysis]"
}}

Analyze the data and respond with ONLY the JSON object above."""
        
        return prompt
    
    def _format_patterns_for_prompt(self, patterns: Dict) -> str:
        """Format cross-timeframe patterns for LLM prompt"""
        if not patterns:
            return "No pattern data available"
        
        formatted = []
        formatted.append(f"- Productivity trend: {patterns.get('productivity_trend', 'unknown')}")
        formatted.append(f"- Web browsing behavior: {patterns.get('web_browsing_behavior', 'unknown')}")
        
        # Add dominant apps by timeframe
        dom_apps = patterns.get('dominant_apps_by_timeframe', {})
        if dom_apps:
            formatted.append("- Dominant apps by timeframe:")
            for timeframe, apps in dom_apps.items():
                if apps:
                    formatted.append(f"  • {timeframe}: {', '.join(apps[:3])}")
        
        return '\n'.join(formatted)
    
    def _parse_llm_state_analysis(self, llm_response: str) -> Optional[Dict]:
        """Parse the structured LLM response for state analysis"""
        try:
            import json
            
            # Try to extract JSON from the response
            # Look for JSON-like content between curly braces
            start_idx = llm_response.find('{')
            end_idx = llm_response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                parsed = json.loads(json_str)
                
                # Validate required fields
                required_fields = ['current_state', 'focus_trend', 'distraction_trend']
                if all(field in parsed for field in required_fields):
                    # Validate state values
                    valid_states = ['flow', 'working', 'needs_nudge', 'afk']
                    valid_focus_trends = ['maintaining_focus', 'entering_focus', 'losing_focus', 'variable', 'none']
                    valid_distraction_trends = ['low', 'moderate', 'increasing', 'decreasing', 'high']
                    
                    if (parsed['current_state'] in valid_states and
                        parsed['focus_trend'] in valid_focus_trends and
                        parsed['distraction_trend'] in valid_distraction_trends):
                        return parsed
                    
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.debug(f"Error parsing LLM state analysis: {e}")
        
        return None
    
    def _fallback_state_analysis(self, raw_data: Dict) -> Dict:
        """Provide fallback state analysis when LLM is unavailable"""
        recent_stats = raw_data.get('timeframes', {}).get('5_minutes', {}).get('statistics', {})
        timeline = raw_data.get('activity_timeline', [])
        context_switches = raw_data.get('context_switches', [])
        
        # Simple rule-based fallback
        active_time = recent_stats.get('total_active_minutes', 0)
        switch_count = recent_stats.get('context_switches', 0)
        
        if active_time < 0.5:
            current_state = 'afk'
            focus_trend = 'none'
            distraction_trend = 'none'
        elif switch_count >= 5:
            current_state = 'needs_nudge'
            focus_trend = 'losing_focus'
            distraction_trend = 'increasing'
        elif active_time >= 3 and switch_count <= 2:
            current_state = 'flow'
            focus_trend = 'maintaining_focus'
            distraction_trend = 'low'
        else:
            current_state = 'working'
            focus_trend = 'variable'
            distraction_trend = 'moderate'
        
        return {
            'current_state': current_state,
            'focus_trend': focus_trend,
            'distraction_trend': distraction_trend,
            'confidence': 'low',
            'primary_activity': 'Unknown (LLM unavailable)',
            'reasoning': 'Fallback analysis based on simple activity metrics.'
        }

    def check_activity(self):
        """Check current activity and respond if appropriate"""
        try:
            if self.verbose:
                print(f"\n📊 ACTIVITY CHECK - {datetime.now().strftime('%m-%d %H:%M:%S')}")
                print("-" * 50)
            
            # Get multi-timeframe data
            multi_timeframe_data = self.aw_client.get_multi_timeframe_data()
            
            if self.verbose:
                print("📈 Multi-timeframe data collected:")
                for timeframe, data in multi_timeframe_data.items():
                    total_events = sum(len(events) for events in data.values())
                    print(f"  {timeframe}: {total_events} total events")
            
            # Use LLM to analyze raw data and determine user state
            llm_analysis = self.analyze_user_state_with_llm(multi_timeframe_data)
            
            # Extract state information from LLM analysis
            user_state = llm_analysis['current_state']
            focus_trend = llm_analysis['focus_trend']
            distraction_trend = llm_analysis['distraction_trend']
            
            logger.info(f"LLM-determined user state: {user_state} (confidence: {llm_analysis.get('confidence', 'unknown')})")
            
            if self.verbose:
                print(f"\n🎯 LLM ANALYSIS RESULTS:")
                print(f"  Current State: {user_state}")
                print(f"  Focus Trend: {focus_trend}")
                print(f"  Distraction Trend: {distraction_trend}")
                print(f"  Confidence: {llm_analysis.get('confidence', 'unknown')}")
                print(f"  Primary Activity: {llm_analysis.get('primary_activity', 'Unknown')}")
                print(f"  Reasoning: {llm_analysis.get('reasoning', 'No reasoning provided')}")
            
            # Still maintain legacy summaries for compatibility with other features
            summaries = self.event_processor.filter_and_summarize_data(multi_timeframe_data)
            
            # Create a context string for the intervention prompt
            context = f"Primary activity: {llm_analysis.get('primary_activity', 'Unknown')}. {llm_analysis.get('reasoning', '')}"
            
            # Log 5-minute activity summary (every 5 minutes regardless of intervention)
            self.log_activity_summary(llm_analysis, multi_timeframe_data)
            
            # Update daily stats
            five_min_summary = summaries.get('5_minutes', {})
            if len(five_min_summary.get('focus_sessions', [])) > 0:
                self.daily_stats['focus_sessions'] += 1
            if len(five_min_summary.get('distractions', [])) > 0:
                self.daily_stats['distractions'] += 1
            
            # Check if we should intervene
            should_intervene = self.should_intervene(user_state)
            
            if self.verbose:
                time_since_last = (datetime.now(timezone.utc) - self.last_intervention).total_seconds() / 60
                cooldown = self.intervention_cooldown.get(user_state, 15)
                print(f"\n⏰ Intervention Decision:")
                print(f"  Should intervene: {should_intervene}")
                print(f"  Time since last: {time_since_last:.1f} min")
                print(f"  Cooldown for {user_state}: {cooldown} min")
                print(f"  Mode: {self.mode}")
            
            if not should_intervene:
                if self.verbose:
                    print("  ❌ Skipping intervention")
                logger.debug(f"Skipping intervention for {user_state} state")
                return
            
            if self.verbose:
                print("  ✅ Proceeding with intervention")
            
            # Get appropriate prompt
            prompt = self.event_processor.generate_adhd_prompt(user_state, context)
            
            # Get response from LLM
            response = self.get_llm_response(prompt, user_state)
            
            # Display response to user
            self._display_response(response, user_state)
            
            # Intervention recorded (5-minute logging handles activity tracking)
            
            # Update intervention tracking
            self.last_intervention = datetime.now(timezone.utc)
            self.daily_stats['interventions'] += 1
            
        except Exception as e:
            logger.error(f"Error checking activity: {e}", exc_info=True)

    def log_activity_summary(self, llm_analysis: Dict, multi_timeframe_data: Dict):
        """Log 5-minute activity summary to log.json"""
        try:
            # Only log every 5 minutes to avoid spam
            now = datetime.now(timezone.utc)
            time_since_last_log = (now - self.last_activity_log).total_seconds() / 60
            
            if time_since_last_log >= 5.0:  # 5 minutes
                # Extract key activity data
                recent_data = multi_timeframe_data.get('5_minutes', {})
                window_events = recent_data.get('window', [])
                web_events = recent_data.get('web', [])
                
                # Get current activity summary
                current_app = None
                current_website = None
                if window_events:
                    current_app = window_events[-1].get('data', {}).get('app', 'Unknown')
                if web_events:
                    current_website = web_events[-1].get('data', {}).get('url', 'Unknown')
                
                log_entry = {
                    "timestamp": now.isoformat(),
                    "current_state": llm_analysis.get('current_state', 'unknown'),
                    "focus_trend": llm_analysis.get('focus_trend', 'unknown'),
                    "distraction_trend": llm_analysis.get('distraction_trend', 'unknown'),
                    "primary_activity": llm_analysis.get('primary_activity', 'Unknown'),
                    "reasoning": llm_analysis.get('reasoning', ''),
                    "confidence": llm_analysis.get('confidence', 'unknown'),
                    "current_app": current_app,
                    "current_website": current_website,
                    "activity_stats": {
                        "window_events": len(window_events),
                        "web_events": len(web_events),
                        "total_active_minutes": recent_data.get('statistics', {}).get('total_active_minutes', 0),
                        "context_switches": recent_data.get('statistics', {}).get('context_switches', 0)
                    }
                }
                
                # Load existing log
                log_entries = []
                if self.log_file.exists():
                    try:
                        with open(self.log_file, 'r') as f:
                            log_entries = json.load(f)
                    except:
                        log_entries = []
                
                # Add new entry
                log_entries.append(log_entry)
                
                # Keep last 7 days of 5-minute logs (7 * 24 * 12 = 2016 entries)
                if len(log_entries) > 2016:
                    log_entries = log_entries[-2016:]
                
                # Save log
                with open(self.log_file, 'w') as f:
                    json.dump(log_entries, f, indent=2)
                
                self.last_activity_log = now
                
                if self.verbose:
                    print(f"📝 Activity logged: {llm_analysis.get('current_state')} - {llm_analysis.get('primary_activity', 'Unknown')}")
                    
        except Exception as e:
            logger.error(f"Error logging activity summary: {e}")

    def generate_thirty_minute_summary(self):
        """Generate 30-minute summary with brief activities and context switches"""
        try:
            now = datetime.now()
            # Check if we have any activity in the last 30 minutes
            multi_timeframe_data = self.aw_client.get_multi_timeframe_data()
            thirty_min_data = multi_timeframe_data.get('30_minutes', {})
            
            if not thirty_min_data or not thirty_min_data.get('window_events'):
                # No activity to summarize
                return
                
            # Create LLM prompt for 30-minute summary
            window_events = thirty_min_data.get('window_events', [])
            web_events = thirty_min_data.get('web_events', [])
            stats = thirty_min_data.get('statistics', {})
            
            # Create brief activity list
            app_durations = {}
            for event in window_events:
                app = event.get('app', 'Unknown')
                duration = event.get('duration_minutes', 0)
                app_durations[app] = app_durations.get(app, 0) + duration
            
            top_apps = sorted(app_durations.items(), key=lambda x: x[1], reverse=True)[:5]
            
            web_domains = {}
            for event in web_events:
                domain = event.get('domain', 'Unknown')
                duration = event.get('duration_minutes', 0)
                web_domains[domain] = web_domains.get(domain, 0) + duration
            
            top_websites = sorted(web_domains.items(), key=lambda x: x[1], reverse=True)[:3]
            
            prompt = f"""Create a brief 30-minute activity summary for this ADHD user.

📊 30-MINUTE PERIOD: {now.strftime('%H:%M')} to {(now - timedelta(minutes=30)).strftime('%H:%M')}

🖥️ TOP APPLICATIONS:
{chr(10).join([f"• {app}: {duration:.1f} min" for app, duration in top_apps])}

🌐 TOP WEBSITES:
{chr(10).join([f"• {domain}: {duration:.1f} min" for domain, duration in top_websites])}

📈 STATISTICS:
• Total active time: {stats.get('total_active_minutes', 0):.1f} minutes
• Context switches: {stats.get('context_switches', 0)}
• Unique apps used: {len(stats.get('unique_apps', []))}

Create a practical 2-3 sentence summary focusing on:
- Main tasks/activities accomplished
- Overall productivity pattern
- Brief mention of context switching if high

Keep it factual and practical, under 100 words."""

            system_prompt = "You are a productivity analyst creating brief 30-minute summaries. Be practical and factual."
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "num_predict": 100,
                    "num_ctx": 8192,
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=20
            )
            
            summary_text = "30-minute period with activity detected"
            if response.status_code == 200:
                result = response.json()
                summary_text = result.get("response", "").strip()
            
            # Store for daily summary use
            thirty_min_summary = {
                "timestamp": now.isoformat(),
                "period": f"{(now - timedelta(minutes=30)).strftime('%H:%M')}-{now.strftime('%H:%M')}",
                "summary": summary_text,
                "stats": {
                    "active_minutes": stats.get('total_active_minutes', 0),
                    "context_switches": stats.get('context_switches', 0),
                    "top_apps": [app for app, _ in top_apps[:3]],
                    "top_websites": [domain for domain, _ in top_websites[:2]]
                }
            }
            
            # Add to daily summary data (stored in memory for now, will be written to daily summary)
            if not hasattr(self, '_thirty_min_summaries'):
                self._thirty_min_summaries = []
            self._thirty_min_summaries.append(thirty_min_summary)
            
            if self.verbose:
                print(f"\n⏰ 30-MIN SUMMARY ({thirty_min_summary['period']}): {summary_text}")
                
        except Exception as e:
            logger.error(f"Error generating 30-minute summary: {e}")

    def generate_daily_summary(self):
        """Generate practical daily summary at 4am with 30-minute periods"""
        try:
            print("\n" + "=" * 60)
            print("🌅 Daily Summary (4am)")
            print("=" * 60)
            
            # Get all 30-minute summaries from today
            today_summaries = getattr(self, '_thirty_min_summaries', [])
            
            if not today_summaries:
                print("No activity summaries available for today.")
                return
            
            # Create comprehensive daily summary prompt
            prompt = f"""Create a practical daily summary for this ADHD user.

📅 DATE: {datetime.now().strftime('%A, %B %d, %Y')}

📊 30-MINUTE PERIOD SUMMARIES:
{chr(10).join([f"• {summary['period']}: {summary['summary']}" for summary in today_summaries])}

📈 DAILY STATISTICS:
• Total 30-minute periods: {len(today_summaries)}
• Total interventions: {self.daily_stats.get('interventions', 0)}

Create a practical daily summary that includes:
1. **Main Tasks Accomplished**: What did they actually get done today?
2. **Activity Patterns**: General productivity patterns and work style
3. **Key Achievements**: Specific accomplishments worth noting
4. **Brief Overview**: Overall assessment of the day

Use a practical, matter-of-fact tone. Focus on concrete achievements and observable patterns.
Keep it under 200 words and use clear sections."""

            system_prompt = "You are a productivity analyst creating daily work summaries. Be practical, factual, and focus on accomplishments."
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.6,
                    "num_predict": 250,
                    "num_ctx": 8192,
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=30
            )
            
            daily_summary_text = "Daily activity summary generated"
            if response.status_code == 200:
                result = response.json()
                daily_summary_text = result.get("response", "").strip()
            
            print(daily_summary_text)
            
            # Save daily summary
            daily_summary = {
                "date": datetime.now().date().isoformat(),
                "summary": daily_summary_text,
                "thirty_minute_periods": today_summaries,
                "daily_stats": self.daily_stats.copy(),
                "generated_at": datetime.now().isoformat()
            }
            
            # Load existing daily summaries
            daily_summaries = []
            if self.daily_summary_file.exists():
                try:
                    with open(self.daily_summary_file, 'r') as f:
                        daily_summaries = json.load(f)
                except:
                    daily_summaries = []
            
            # Add new summary
            daily_summaries.append(daily_summary)
            
            # Keep last 30 days
            if len(daily_summaries) > 30:
                daily_summaries = daily_summaries[-30:]
            
            # Save daily summaries
            with open(self.daily_summary_file, 'w') as f:
                json.dump(daily_summaries, f, indent=2)
            
            # Reset for new day
            self._thirty_min_summaries = []
            self.daily_stats = {'focus_sessions': 0, 'distractions': 0, 'interventions': 0}
            
            print("=" * 60 + "\n")
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            print("Had trouble generating daily summary, but your productivity continues! 📈")
    
    def should_intervene(self, user_state: str) -> bool:
        """Determine if we should intervene based on state and mode"""
        if self.mode == "ghost":
            return False
        
        # Check cooldown
        time_since_last = (datetime.now(timezone.utc) - self.last_intervention).total_seconds() / 60
        cooldown = self.intervention_cooldown.get(user_state, 15)
        
        if time_since_last < cooldown:
            return False
        
        # Mode-specific logic
        if self.mode == "coach":
            return user_state in ["needs_nudge", "working", "afk"]
        elif self.mode == "study_buddy":
            return True  # Always check in
        elif self.mode == "weekend":
            return user_state == "needs_nudge"  # Only nudge on weekends
        
        return False
    
    def get_llm_response(self, prompt: str, user_state: str) -> str:
        """Get response from Ollama LLM"""
        try:
            system_prompt = "You are a supportive ADHD companion. Be encouraging, never judgmental. Keep responses very concise."
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 50  # Limit response length
                }
            }
            
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"🤖 LLM REQUEST (State: {user_state})")
                print(f"{'='*60}")
                print(f"Model: {self.model}")
                print(f"System: {system_prompt}")
                print(f"Prompt:\n{prompt}")
                print(f"{'='*60}")
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "").strip()
                
                if self.verbose:
                    print(f"✅ LLM RESPONSE: {llm_response}")
                    print(f"{'='*60}\n")
                
                return llm_response
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
                return self._get_fallback_response(user_state)
                
        except requests.exceptions.ConnectionError:
            logger.debug("Ollama not available, using fallback")
            return self._get_fallback_response(user_state)
        except Exception as e:
            logger.error(f"Error getting LLM response: {e}")
            return self._get_fallback_response(user_state)
    
    def _get_fallback_response(self, user_state: str) -> str:
        """Get fallback response when LLM is unavailable"""
        fallbacks = {
            "flow": "🚀 You're in the zone! Keep going!",
            "working": "✨ Nice steady progress!",
            "needs_nudge": "💚 Hey friend, feeling stuck? Pick one small thing to do next.",
            "afk": "👋 Welcome back! What shall we tackle?"
        }
        return fallbacks.get(user_state, "Keep going, you're doing great!")
    
    def _display_response(self, response: str, user_state: str):
        """Display response to user with appropriate formatting"""
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M")
        
        # Add emoji based on state
        emoji = {
            "flow": "🚀",
            "working": "💪",
            "needs_nudge": "💚",
            "afk": "👋"
        }.get(user_state, "🧊")
        
        print(f"\n[{timestamp}] {emoji} Companion: {response}")
    
    def save_interaction(self, state: str, response: str, summaries: Dict):
        """Save interaction data for learning"""
        interaction = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": state,
            "response": response,
            "mode": self.mode,
            "activity_summary": {
                "current_behavior": summaries.get('5_minutes', {}).get('behavior_pattern', ''),
                "active_minutes": summaries.get('5_minutes', {}).get('active_time_minutes', 0),
                "app_switches": summaries.get('5_minutes', {}).get('app_switches', 0),
                "focus_sessions": len(summaries.get('5_minutes', {}).get('focus_sessions', [])),
                "distractions": len(summaries.get('5_minutes', {}).get('distractions', []))
            }
        }
        
        # Load existing interactions
        interactions = []
        if self.interactions_file.exists():
            try:
                with open(self.interactions_file, 'r') as f:
                    interactions = json.load(f)
            except:
                interactions = []
        
        # Add new interaction
        interactions.append(interaction)
        
        # Keep only last 1000 interactions
        if len(interactions) > 1000:
            interactions = interactions[-1000:]
        
        # Save back
        with open(self.interactions_file, 'w') as f:
            json.dump(interactions, f, indent=2)
    
    def generate_end_of_day_summary(self):
        """Generate and display end of day summary using LLM"""
        print("\n" + "=" * 60)
        print("🌟 Daily Summary 🌟")
        print("=" * 60)
        
        try:
            # Get comprehensive data for LLM analysis
            print("📊 Analyzing today's patterns...")
            
            # Get activity data efficiently
            summary_data = self._collect_summary_data()
            
            # Generate LLM-powered summary
            llm_summary = self._generate_llm_daily_summary(summary_data)
            
            if llm_summary:
                print(llm_summary)
            else:
                # Fallback to basic summary if LLM fails
                self._show_basic_summary(summary_data)
            
            # Save the summary data
            try:
                summary_to_save = {
                    "date": datetime.now().date().isoformat(),
                    "llm_summary": llm_summary if llm_summary else "LLM unavailable",
                    "session_data": summary_data,
                    "companion_active": True
                }
                
                summaries = []
                if self.daily_summaries_file.exists():
                    try:
                        with open(self.daily_summaries_file, 'r') as f:
                            summaries = json.load(f)
                    except:
                        summaries = []
                
                summaries.append(summary_to_save)
                if len(summaries) > 30:
                    summaries = summaries[-30:]
                
                with open(self.daily_summaries_file, 'w') as f:
                    json.dump(summaries, f, indent=2)
                    
            except Exception as e:
                logger.error(f"Error saving daily summary: {e}")
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            print("Had trouble generating today's summary, but I'm sure you did great! 💪")
            
            # Show at least something positive
            print("\n💝 Remember:")
            print("   • You used Companion Cube today - that shows you care about productivity!")
            print("   • Every bit of progress counts, and you showed up today!")
            print("   • Tomorrow is a fresh start with new opportunities!")
        
        print("=" * 60 + "\n")
    
    def _collect_summary_data(self) -> Dict:
        """Collect comprehensive data for daily summary"""
        summary_data = {
            'session_stats': {
                'interventions': self.daily_stats.get('interventions', 0),
                'focus_sessions_detected': self.daily_stats.get('focus_sessions', 0),
                'distractions_detected': self.daily_stats.get('distractions', 0),
                'mode': self.mode,
                'check_interval': self.check_interval
            },
            'interactions': [],
            'activity_sample': {},
            'time_info': {
                'date': datetime.now().strftime('%A, %B %d, %Y'),
                'session_duration': 'Unknown'
            }
        }
        
        # Get recent interactions from file
        try:
            if self.interactions_file.exists():
                with open(self.interactions_file, 'r') as f:
                    all_interactions = json.load(f)
                    
                # Get today's interactions
                today = datetime.now().date().isoformat()
                today_interactions = [
                    i for i in all_interactions 
                    if i.get('timestamp', '').startswith(today)
                ]
                
                summary_data['interactions'] = today_interactions[-10:]  # Last 10 interactions
        except Exception as e:
            logger.error(f"Error loading interactions: {e}")
        
        # Get a sample of recent activity (limited to avoid hanging)
        try:
            # Just get last 30 minutes of activity for context
            window_events = self.aw_client.get_window_events(hours_back=0.5)
            web_events = self.aw_client.get_web_events(hours_back=0.5)
            
            if window_events:
                # Extract top apps from recent activity
                app_counts = {}
                for event in window_events[-20:]:  # Last 20 events only
                    app = event.get('data', {}).get('app', 'Unknown')
                    app_counts[app] = app_counts.get(app, 0) + 1
                
                summary_data['activity_sample'] = {
                    'recent_apps': list(app_counts.keys())[:5],
                    'total_recent_events': len(window_events),
                    'has_recent_activity': len(window_events) > 0
                }
            
            if web_events:
                # Extract recent websites
                domains = []
                for event in web_events[-10:]:  # Last 10 web events
                    url = event.get('data', {}).get('url', '')
                    if url:
                        domain = self.event_processor._extract_domain(url)
                        if domain not in domains:
                            domains.append(domain)
                
                summary_data['activity_sample']['recent_websites'] = domains[:3]
                
        except Exception as e:
            logger.error(f"Error getting activity sample: {e}")
            summary_data['activity_sample'] = {'error': 'Could not retrieve recent activity'}
        
        return summary_data
    
    def _generate_llm_daily_summary(self, summary_data: Dict) -> Optional[str]:
        """Generate daily summary using LLM"""
        try:
            # Create comprehensive prompt for daily summary
            prompt = self._create_daily_summary_prompt(summary_data)
            
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"🧠 DAILY SUMMARY LLM REQUEST")
                print(f"{'='*60}")
                print(f"Model: {self.model}")
                print(f"Data: {json.dumps(summary_data, indent=2)}")
                print(f"{'='*60}")
            
            # Get LLM response with longer limit for daily summary
            system_prompt = """You are a supportive ADHD productivity coach creating an end-of-day summary. 
Be encouraging, celebrate small wins, acknowledge challenges without judgment, and provide gentle insights. 
Keep the tone warm, personal, and supportive. Focus on progress and patterns, not perfection."""
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 300,  # Longer response for daily summary
                    "num_ctx": 8192,     # Use full 8K context window
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=30  # Longer timeout for daily summary
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "").strip()
                
                if self.verbose:
                    print(f"✅ LLM DAILY SUMMARY: {llm_response}")
                    print(f"{'='*60}\n")
                
                return llm_response
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating LLM daily summary: {e}")
            return None
    
    def _create_daily_summary_prompt(self, summary_data: Dict) -> str:
        """Create comprehensive prompt for daily summary"""
        session_stats = summary_data.get('session_stats', {})
        interactions = summary_data.get('interactions', [])
        activity_sample = summary_data.get('activity_sample', {})
        time_info = summary_data.get('time_info', {})
        
        prompt = f"""Please analyze this user's ADHD productivity session and create a warm, encouraging daily summary.

📅 DATE: {time_info.get('date', 'Today')}
⏰ SESSION TIME: {time_info.get('start_time', 'Unknown')} to {time_info.get('current_time', datetime.now().strftime('%H:%M'))}

🤖 COMPANION SESSION DATA:
- Mode: {session_stats.get('mode', 'coach')}
- Total interventions/check-ins: {session_stats.get('interventions', 0)}
- Focus sessions detected: {session_stats.get('focus_sessions_detected', 0)}
- Distractions noticed: {session_stats.get('distractions_detected', 0)}
- Check interval: {session_stats.get('check_interval', 60)} seconds
- Session duration: {session_stats.get('session_duration_hours', 'Unknown')} hours

💬 INTERACTIONS TODAY: {len(interactions)} total
"""

        # Add interaction details if available
        if interactions:
            prompt += "\nRecent companion interactions:\n"
            for interaction in interactions[-5:]:  # Last 5 interactions
                state = interaction.get('state', 'unknown')
                response = interaction.get('response', 'N/A')[:100]  # Truncate long responses
                prompt += f"- {state}: {response}\n"
        
        # Add activity context if available
        if activity_sample.get('recent_apps'):
            prompt += f"\n📱 RECENT APPS USED: {', '.join(activity_sample['recent_apps'])}"
        
        if activity_sample.get('recent_websites'):
            prompt += f"\n🌐 RECENT WEBSITES: {', '.join(activity_sample['recent_websites'])}"
        
        if activity_sample.get('has_recent_activity'):
            prompt += f"\n📊 Recent activity events: {activity_sample.get('total_recent_events', 0)}"
        
        prompt += f"""

🎯 SUMMARY REQUEST:
Create a personalized, ADHD-friendly daily summary that:

1. **Celebrates Progress**: Acknowledge what they DID accomplish, however small
2. **Recognizes Patterns**: Note any interesting productivity patterns or behaviors
3. **Shows Understanding**: Demonstrate understanding of ADHD challenges and strengths
4. **Offers Encouragement**: Be genuinely supportive and warm
5. **Suggests Insights**: Gentle observations about their work style today

IMPORTANT GUIDELINES:
- Never shame or criticize
- Celebrate effort over perfection
- Acknowledge that some days are different than others
- Be specific about what you observed
- Keep it under 250 words
- Use encouraging emojis appropriately
- End with tomorrow-focused positivity

Remember: This person chose to use a productivity tool today - that itself shows self-care and intention!"""

        return prompt
    
    def _show_basic_summary(self, summary_data: Dict):
        """Show basic summary if LLM is unavailable"""
        session_stats = summary_data.get('session_stats', {})
        interactions = summary_data.get('interactions', [])
        
        print("🤖 Session Summary:")
        print(f"• Companion interactions: {session_stats.get('interventions', 0)}")
        print(f"• Focus sessions detected: {session_stats.get('focus_sessions_detected', 0)}")
        print(f"• Mode used: {session_stats.get('mode', 'coach')}")
        
        if interactions:
            print(f"• Total interactions today: {len(interactions)}")
        
        print("\n💝 Remember:")
        print("• You used a productivity tool today - that shows self-awareness!")
        print("• Every moment of intention matters, regardless of the outcome")
        print("• Tomorrow is a fresh start with new possibilities")
        
        if session_stats.get('focus_sessions_detected', 0) > 0:
            print("• You had some focus time today - celebrate that! 🎉")
    
    def generate_weekly_insights(self):
        """Generate weekly pattern insights using LLM"""
        print("\n" + "=" * 60)
        print("📊 Weekly Pattern Insights 📊")
        print("=" * 60)
        
        try:
            # Collect weekly data
            print("📈 Analyzing your weekly patterns...")
            weekly_data = self._collect_weekly_data()
            
            # Generate LLM insights
            insights = self._generate_llm_weekly_insights(weekly_data)
            
            if insights:
                print(insights)
            else:
                print("🤖 LLM unavailable for detailed insights.")
                self._show_basic_weekly_summary(weekly_data)
                
        except Exception as e:
            logger.error(f"Error generating weekly insights: {e}")
            print("Had trouble analyzing weekly patterns, but every week teaches us something! 📚")
        
        print("=" * 60 + "\n")
    
    def _collect_weekly_data(self) -> Dict:
        """Collect weekly data for pattern analysis"""
        weekly_data = {
            'daily_summaries': [],
            'total_interactions': 0,
            'total_focus_sessions': 0,
            'common_patterns': [],
            'week_info': {
                'start_date': (datetime.now() - timedelta(days=7)).strftime('%B %d'),
                'end_date': datetime.now().strftime('%B %d, %Y')
            }
        }
        
        # Load recent daily summaries
        try:
            if self.daily_summaries_file.exists():
                with open(self.daily_summaries_file, 'r') as f:
                    all_summaries = json.load(f)
                
                # Get last 7 days
                recent_summaries = all_summaries[-7:] if len(all_summaries) >= 7 else all_summaries
                weekly_data['daily_summaries'] = recent_summaries
                
                # Calculate totals
                for summary in recent_summaries:
                    session_data = summary.get('session_data', {}).get('session_stats', {})
                    weekly_data['total_interactions'] += session_data.get('interventions', 0)
                    weekly_data['total_focus_sessions'] += session_data.get('focus_sessions_detected', 0)
                
        except Exception as e:
            logger.error(f"Error loading weekly data: {e}")
        
        return weekly_data
    
    def _generate_llm_weekly_insights(self, weekly_data: Dict) -> Optional[str]:
        """Generate weekly insights using LLM"""
        try:
            prompt = self._create_weekly_insights_prompt(weekly_data)
            
            if self.verbose:
                print(f"\n{'='*60}")
                print(f"🧠 WEEKLY INSIGHTS LLM REQUEST")
                print(f"{'='*60}")
                print(f"Model: {self.model}")
                print(f"Weekly Data: {json.dumps(weekly_data, indent=2)[:500]}...")
                print(f"{'='*60}")
            
            system_prompt = """You are an ADHD productivity coach analyzing weekly patterns. 
Identify trends, celebrate consistency, acknowledge challenges, and provide gentle insights about productivity patterns. 
Be encouraging and focus on growth and self-understanding rather than judgment."""
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 400  # Even longer for weekly insights
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=45  # Longer timeout for complex analysis
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get("response", "").strip()
                
                if self.verbose:
                    print(f"✅ LLM WEEKLY INSIGHTS: {llm_response}")
                    print(f"{'='*60}\n")
                
                return llm_response
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating LLM weekly insights: {e}")
            return None
    
    def _create_weekly_insights_prompt(self, weekly_data: Dict) -> str:
        """Create prompt for weekly pattern analysis"""
        week_info = weekly_data.get('week_info', {})
        summaries = weekly_data.get('daily_summaries', [])
        
        prompt = f"""Analyze this user's ADHD productivity patterns over the past week and provide insightful observations.

📅 WEEK PERIOD: {week_info.get('start_date', 'Last week')} - {week_info.get('end_date', 'Today')}

📊 WEEKLY OVERVIEW:
- Days with companion usage: {len(summaries)}
- Total companion interactions: {weekly_data.get('total_interactions', 0)}
- Total focus sessions detected: {weekly_data.get('total_focus_sessions', 0)}

📋 DAILY BREAKDOWN:
"""

        # Add daily summary info
        for i, summary in enumerate(summaries, 1):
            date = summary.get('date', f'Day {i}')
            session_data = summary.get('session_data', {}).get('session_stats', {})
            
            prompt += f"Day {i} ({date}):\n"
            prompt += f"  - Mode: {session_data.get('mode', 'unknown')}\n"
            prompt += f"  - Interventions: {session_data.get('interventions', 0)}\n"
            prompt += f"  - Focus sessions: {session_data.get('focus_sessions_detected', 0)}\n"
            prompt += f"  - Check interval: {session_data.get('check_interval', 60)}s\n"
        
        prompt += f"""

🎯 ANALYSIS REQUEST:
As an ADHD coach, analyze these patterns and provide insights about:

1. **Consistency Patterns**: What does their usage pattern tell us about their routine?
2. **Productivity Rhythms**: Any trends in focus sessions or engagement levels?
3. **Growth Observations**: Signs of developing better productivity habits?
4. **ADHD-Specific Insights**: How their usage patterns reflect common ADHD traits?
5. **Gentle Recommendations**: Suggestions for optimizing their companion experience?

IMPORTANT GUIDELINES:
- Celebrate any consistency, even if imperfect
- Acknowledge that ADHD productivity isn't linear
- Focus on patterns and insights, not judgments
- Offer specific, actionable suggestions
- Keep it encouraging and hopeful
- Use supportive language throughout
- Keep response under 350 words
- Use emojis to make it engaging

Remember: Using a productivity tool consistently shows self-awareness and commitment to growth!"""

        return prompt
    
    def _show_basic_weekly_summary(self, weekly_data: Dict):
        """Show basic weekly summary if LLM unavailable"""
        summaries = weekly_data.get('daily_summaries', [])
        
        print("📊 Basic Weekly Summary:")
        print(f"• Days active: {len(summaries)}")
        print(f"• Total interactions: {weekly_data.get('total_interactions', 0)}")
        print(f"• Total focus sessions: {weekly_data.get('total_focus_sessions', 0)}")
        
        if len(summaries) >= 3:
            print("• You've been consistently using your productivity companion!")
        elif len(summaries) >= 1:
            print("• You've started building a productivity habit!")
        
        print("\n💝 Weekly Wins:")
        print("• You're tracking your productivity patterns")
        print("• Every day of usage builds better self-awareness")
        print("• Consistency matters more than perfection")
    
    def _save_daily_summary(self, daily_stats: Dict):
        """Save daily summary to file"""
        summary = {
            "date": datetime.now().date().isoformat(),
            "stats": daily_stats,
            "interventions": self.daily_stats['interventions']
        }
        
        # Load existing summaries
        summaries = []
        if self.daily_summaries_file.exists():
            try:
                with open(self.daily_summaries_file, 'r') as f:
                    summaries = json.load(f)
            except:
                summaries = []
        
        # Add new summary
        summaries.append(summary)
        
        # Keep last 30 days
        if len(summaries) > 30:
            summaries = summaries[-30:]
        
        # Save back
        with open(self.daily_summaries_file, 'w') as f:
            json.dump(summaries, f, indent=2)

    def check_hourly_summary(self):
        """Generate and save hourly activity summaries"""
        now = datetime.now(timezone.utc)
        time_since_last_hourly = (now - self.last_hourly_summary).total_seconds() / 3600
        
        if time_since_last_hourly >= 1.0:  # 1 hour
            try:
                # Get activity data for the last hour
                multi_timeframe_data = self.aw_client.get_multi_timeframe_data()
                hourly_data = multi_timeframe_data.get('1_hour', {})
                
                if hourly_data:
                    # Process the data
                    summaries = self.event_processor.filter_and_summarize_data({'1_hour': hourly_data})
                    hour_summary = summaries.get('1_hour', {})
                    
                    # Generate LLM summary
                    llm_summary = self._generate_llm_hourly_summary(hour_summary)
                    
                    # Save to hourly summaries file
                    self._save_hourly_summary(hour_summary, llm_summary)
                    
                    if self.verbose:
                        print(f"\n⏰ HOURLY SUMMARY GENERATED - {now.strftime('%H:%M')}")
                        if llm_summary:
                            print(f"📝 {llm_summary}")
                
                self.last_hourly_summary = now
                
            except Exception as e:
                logger.error(f"Error generating hourly summary: {e}")

    def check_minute_summary(self):
        """Generate minute-by-minute summaries in verbose mode"""
        now = datetime.now(timezone.utc)
        time_since_last_minute = (now - self.last_minute_summary).total_seconds()
        
        if time_since_last_minute >= 60:  # 1 minute
            try:
                # Get recent activity (last 5 minutes)
                multi_timeframe_data = self.aw_client.get_multi_timeframe_data()
                recent_data = multi_timeframe_data.get('5_minutes', {})
                
                if recent_data:
                    # Quick summary without full processing
                    window_events = recent_data.get('window', [])
                    web_events = recent_data.get('web', [])
                    
                    if window_events:
                        latest_app = window_events[-1].get('data', {}).get('app', 'Unknown')
                        latest_title = window_events[-1].get('data', {}).get('title', '')[:50]
                        
                        summary = f"🕐 Currently: {latest_app}"
                        if latest_title:
                            summary += f" - {latest_title}"
                        
                        if web_events:
                            latest_url = web_events[-1].get('data', {}).get('url', '')
                            if latest_url:
                                domain = self.event_processor._extract_domain(latest_url)
                                summary += f" @ {domain}"
                        
                        print(f"\n{summary}")
                
                self.last_minute_summary = now
                
            except Exception as e:
                logger.debug(f"Error in minute summary: {e}")

    def _generate_llm_hourly_summary(self, hour_data: Dict) -> Optional[str]:
        """Generate LLM-powered hourly summary"""
        try:
            prompt = f"""Please create a brief, encouraging hourly summary for this ADHD user.

📊 HOUR DATA:
- App switches: {hour_data.get('app_switches', 0)}
- Focus sessions: {len(hour_data.get('focus_sessions', []))}
- Distractions detected: {len(hour_data.get('distractions', []))}
- Primary apps: {', '.join(hour_data.get('top_apps', [])[:3])}
- Behavior pattern: {hour_data.get('behavior_pattern', 'unknown')}

Create a 1-2 sentence positive summary that:
- Acknowledges what they accomplished this hour
- Notes interesting patterns (if any)
- Stays encouraging and supportive
- Uses appropriate emojis
- Keeps it under 100 words

Focus on progress, not perfection!"""

            system_prompt = "You are a supportive ADHD productivity coach providing brief hourly check-ins. Be warm, encouraging, and focus on small wins."
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 100,
                    "num_ctx": 8192,  # Use full 8K context window
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            
        except Exception as e:
            logger.debug(f"Error generating hourly LLM summary: {e}")
        
        return None

    def _save_hourly_summary(self, hour_data: Dict, llm_summary: Optional[str]):
        """Save hourly summary to file"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "hour": datetime.now().strftime('%H:00'),
            "date": datetime.now().date().isoformat(),
            "data": hour_data,
            "llm_summary": llm_summary if llm_summary else "LLM unavailable",
            "stats": {
                "app_switches": hour_data.get('app_switches', 0),
                "focus_sessions": len(hour_data.get('focus_sessions', [])),
                "distractions": len(hour_data.get('distractions', [])),
                "top_apps": hour_data.get('top_apps', [])[:3]
            }
        }
        
        # Load existing summaries
        summaries = []
        if self.hourly_summaries_file.exists():
            try:
                with open(self.hourly_summaries_file, 'r') as f:
                    summaries = json.load(f)
            except:
                summaries = []
        
        # Add new summary
        summaries.append(summary)
        
        # Keep last 7 days (168 hours)
        if len(summaries) > 168:
            summaries = summaries[-168:]
        
        # Save back
        with open(self.hourly_summaries_file, 'w') as f:
            json.dump(summaries, f, indent=2)

    def generate_productivity_insights(self):
        """Generate LLM-powered productivity pattern insights"""
        try:
            print("\n" + "=" * 60)
            print("🧠 Productivity Pattern Analysis")
            print("=" * 60)
            
            # Collect data from multiple sources
            insights_data = self._collect_insights_data()
            
            # Generate LLM insights
            llm_insights = self._generate_llm_productivity_insights(insights_data)
            
            if llm_insights:
                print(llm_insights)
            else:
                print("🤖 LLM unavailable for detailed insights.")
                self._show_basic_productivity_insights(insights_data)
                
        except Exception as e:
            logger.error(f"Error generating productivity insights: {e}")
            print("Had trouble analyzing patterns, but every session is valuable data! 📚")
        
        print("=" * 60 + "\n")

    def _collect_insights_data(self) -> Dict:
        """Collect comprehensive data for productivity insights"""
        insights_data = {
            'hourly_patterns': [],
            'daily_trends': [],
            'focus_patterns': {},
            'distraction_patterns': {},
            'intervention_effectiveness': {}
        }
        
        try:
            # Load hourly summaries for pattern analysis
            if self.hourly_summaries_file.exists():
                with open(self.hourly_summaries_file, 'r') as f:
                    hourly_data = json.load(f)
                
                # Analyze hourly patterns
                insights_data['hourly_patterns'] = self._analyze_hourly_patterns(hourly_data)
                
            # Load daily summaries for trend analysis
            if self.daily_summaries_file.exists():
                with open(self.daily_summaries_file, 'r') as f:
                    daily_data = json.load(f)
                
                insights_data['daily_trends'] = self._analyze_daily_trends(daily_data)
                
            # Load interactions for effectiveness analysis
            if self.interactions_file.exists():
                with open(self.interactions_file, 'r') as f:
                    interactions = json.load(f)
                
                insights_data['intervention_effectiveness'] = self._analyze_intervention_effectiveness(interactions)
                
        except Exception as e:
            logger.error(f"Error collecting insights data: {e}")
        
        return insights_data

    def _analyze_hourly_patterns(self, hourly_data: List[Dict]) -> Dict:
        """Analyze patterns in hourly data"""
        patterns = {
            'most_productive_hours': [],
            'common_focus_times': [],
            'distraction_prone_hours': []
        }
        
        try:
            # Group by hour of day
            hour_stats = {}
            for entry in hourly_data[-168:]:  # Last week
                hour = entry.get('hour', '00:00')
                stats = entry.get('stats', {})
                
                if hour not in hour_stats:
                    hour_stats[hour] = {'focus': 0, 'distractions': 0, 'count': 0}
                
                hour_stats[hour]['focus'] += stats.get('focus_sessions', 0)
                hour_stats[hour]['distractions'] += stats.get('distractions', 0)
                hour_stats[hour]['count'] += 1
            
            # Find patterns
            if hour_stats:
                # Most productive hours (highest focus ratio)
                productive_hours = sorted(
                    hour_stats.items(), 
                    key=lambda x: x[1]['focus'] / max(x[1]['count'], 1) if x[1]['count'] > 0 else 0, 
                    reverse=True
                )[:3]
                patterns['most_productive_hours'] = [hour for hour, stats in productive_hours if stats['focus'] > 0]
                
                # Distraction-prone hours
                distraction_hours = sorted(
                    hour_stats.items(),
                    key=lambda x: x[1]['distractions'] / max(x[1]['count'], 1) if x[1]['count'] > 0 else 0,
                    reverse=True
                )[:2]
                patterns['distraction_prone_hours'] = [hour for hour, stats in distraction_hours if stats['distractions'] > 0]
                
        except Exception as e:
            logger.error(f"Error analyzing hourly patterns: {e}")
        
        return patterns

    def _analyze_daily_trends(self, daily_data: List[Dict]) -> Dict:
        """Analyze trends in daily data"""
        trends = {
            'consistency_score': 0,
            'improvement_areas': [],
            'recent_changes': []
        }
        
        try:
            if len(daily_data) >= 3:
                recent_days = daily_data[-7:]  # Last week
                
                # Calculate consistency (regular usage)
                active_days = sum(1 for day in recent_days if day.get('stats', {}).get('interventions', 0) > 0)
                trends['consistency_score'] = (active_days / len(recent_days)) * 100
                
                # Identify improvement areas
                avg_focus = sum(day.get('stats', {}).get('focus_sessions_detected', 0) for day in recent_days) / len(recent_days)
                avg_distractions = sum(day.get('stats', {}).get('distractions_detected', 0) for day in recent_days) / len(recent_days)
                
                if avg_distractions > avg_focus:
                    trends['improvement_areas'].append('Focus vs distraction balance')
                if trends['consistency_score'] < 70:
                    trends['improvement_areas'].append('Regular tool usage consistency')
                    
        except Exception as e:
            logger.error(f"Error analyzing daily trends: {e}")
        
        return trends

    def _analyze_intervention_effectiveness(self, interactions: List[Dict]) -> Dict:
        """Analyze how effective interventions are"""
        effectiveness = {
            'total_interventions': len(interactions),
            'state_breakdown': {},
            'response_patterns': []
        }
        
        try:
            # Count interventions by state
            state_counts = {}
            for interaction in interactions[-50:]:  # Last 50 interactions
                state = interaction.get('state', 'unknown')
                state_counts[state] = state_counts.get(state, 0) + 1
            
            effectiveness['state_breakdown'] = state_counts
            
        except Exception as e:
            logger.error(f"Error analyzing intervention effectiveness: {e}")
        
        return effectiveness

    def _generate_llm_productivity_insights(self, insights_data: Dict) -> Optional[str]:
        """Generate comprehensive productivity insights using LLM"""
        try:
            prompt = f"""Please analyze this ADHD user's productivity patterns and provide personalized insights.

📊 PRODUCTIVITY PATTERN DATA:

⏰ HOURLY PATTERNS:
- Most productive hours: {', '.join(insights_data.get('hourly_patterns', {}).get('most_productive_hours', ['None identified']))}
- Distraction-prone times: {', '.join(insights_data.get('hourly_patterns', {}).get('distraction_prone_hours', ['None identified']))}

📈 DAILY TRENDS:
- Consistency score: {insights_data.get('daily_trends', {}).get('consistency_score', 0):.1f}%
- Improvement areas: {', '.join(insights_data.get('daily_trends', {}).get('improvement_areas', ['Great job overall!']))}

🎯 INTERVENTION DATA:
- Total interactions: {insights_data.get('intervention_effectiveness', {}).get('total_interventions', 0)}
- State breakdown: {dict(list(insights_data.get('intervention_effectiveness', {}).get('state_breakdown', {}).items())[:3])}

Please provide:
1. **Pattern Recognition**: What interesting patterns do you notice?
2. **ADHD-Specific Insights**: How do these patterns relate to ADHD traits?
3. **Personalized Suggestions**: 2-3 specific, actionable recommendations
4. **Encouragement**: Celebrate what's working well
5. **Future Focus**: Gentle suggestions for optimization

GUIDELINES:
- Be supportive and understanding of ADHD challenges
- Focus on patterns, not judgments
- Offer specific, actionable suggestions
- Celebrate small wins and progress
- Keep tone warm and encouraging
- Use emojis appropriately
- Limit to 400 words

Remember: Every person with ADHD has unique patterns - help them understand theirs!"""

            system_prompt = "You are a specialized ADHD productivity coach analyzing behavioral patterns. Provide insights that are understanding, encouraging, and actionable for someone with ADHD."
            
            request_data = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 400,
                    "num_ctx": 8192,  # Use full 8K context window
                    "top_k": 40,
                    "top_p": 0.9
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=request_data,
                timeout=45
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            
        except Exception as e:
            logger.debug(f"Error generating productivity insights: {e}")
        
        return None

    def _show_basic_productivity_insights(self, insights_data: Dict):
        """Show basic insights if LLM unavailable"""
        hourly = insights_data.get('hourly_patterns', {})
        daily = insights_data.get('daily_trends', {})
        
        print("📊 Basic Pattern Analysis:")
        
        if hourly.get('most_productive_hours'):
            print(f"• Your most productive hours: {', '.join(hourly['most_productive_hours'])}")
        
        if daily.get('consistency_score', 0) > 0:
            print(f"• Consistency score: {daily['consistency_score']:.1f}%")
        
        if daily.get('improvement_areas'):
            print(f"• Growth opportunities: {', '.join(daily['improvement_areas'])}")
        
        print("\n💡 Remember:")
        print("• Every pattern tells a story about your unique brain")
        print("• Small consistent changes lead to big improvements")
        print("• You're building valuable self-awareness!")


def main():
    parser = argparse.ArgumentParser(description="Companion Cube - ADHD Productivity Assistant")
    parser.add_argument("--mode", choices=["ghost", "coach", "study_buddy", "weekend"], 
                       default="coach", help="Companion mode")
    parser.add_argument("--interval", type=int, default=60, 
                       help="Check interval in seconds")
    parser.add_argument("--model", type=str, default="mistral",
                       help="Ollama model to use")
    parser.add_argument("--test", action="store_true", 
                       help="Run a single check for testing")
    parser.add_argument("--test-connections", action="store_true",
                       help="Test connections and exit")
    parser.add_argument("--daily-summary", action="store_true",
                       help="Generate daily summary and exit")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose mode with detailed LLM prompts and processing info")
    parser.add_argument("--weekly-insights", action="store_true",
                       help="Generate weekly pattern insights using LLM")
    parser.add_argument("--productivity-insights", action="store_true",
                       help="Generate comprehensive productivity pattern analysis using LLM")
    
    args = parser.parse_args()
    
    cube = CompanionCube(check_interval=args.interval, mode=args.mode, verbose=args.verbose)
    cube.model = args.model
    
    print("\n🧊 Companion Cube - ADHD Productivity Assistant 🧊")
    print("=" * 60)
    
    if args.test_connections:
        cube.test_connections()
        return
    
    if args.daily_summary:
        cube.generate_end_of_day_summary()
        return
    
    if args.weekly_insights:
        cube.generate_weekly_insights()
        return
    
    if args.productivity_insights:
        cube.generate_productivity_insights()
        return
    
    if args.test:
        print("Running single test check...")
        cube.test_connections()
        print("\nPerforming activity check...")
        cube.check_activity()
        return
    
    print("I'm here to support you, not judge you.")
    print("Let's work together to make today great!")
    print("=" * 60)
    
    try:
        cube.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()