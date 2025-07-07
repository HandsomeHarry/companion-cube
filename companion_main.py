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
        self.model = "cas/mistral-7b-instruct-v0.3"  # Default model
        
        # File paths for data storage
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.interactions_file = self.data_dir / "interactions.json"
        self.good_days_file = self.data_dir / "good_days.json"
        self.daily_summaries_file = self.data_dir / "daily_summaries.json"
        
        # State tracking
        self.last_intervention = datetime.now(timezone.utc)
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
        """Handle Ctrl+C gracefully"""
        print("\n\n💫 Companion Cube shutting down...")
        self.generate_end_of_day_summary()
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
                # Check if it's a new day
                current_date = datetime.now().date()
                if current_date > self.last_summary_date:
                    self.generate_end_of_day_summary()
                    self.last_summary_date = current_date
                    self.daily_stats = {'focus_sessions': 0, 'distractions': 0, 'interventions': 0}
                
                self.check_activity()
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(self.check_interval)
    
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
            
            # Filter and summarize data
            summaries = self.event_processor.filter_and_summarize_data(multi_timeframe_data)
            
            # Create behavior comparison
            comparison = self.event_processor.create_behavior_comparison(summaries)
            
            if self.verbose:
                five_min = summaries.get('5_minutes', {})
                print(f"\n🧠 Analysis Results:")
                print(f"  Current behavior: {five_min.get('behavior_pattern', 'unknown')}")
                print(f"  App switches: {five_min.get('app_switches', 0)}")
                print(f"  Focus sessions: {len(five_min.get('focus_sessions', []))}")
                print(f"  Distractions: {len(five_min.get('distractions', []))}")
                print(f"  Focus trend: {comparison.get('focus_trend', 'unknown')}")
                print(f"  Distraction trend: {comparison.get('distraction_trend', 'unknown')}")
            
            # Generate context for LLM
            context = self.event_processor.generate_llm_context(summaries, comparison)
            
            # Get current state
            user_state = comparison['current_state']
            logger.info(f"Detected user state: {user_state}")
            
            if self.verbose:
                print(f"🎯 User State: {user_state}")
                print(f"📝 Context: {context}")
            
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
            
            # Save interaction
            self.save_interaction(user_state, response, summaries)
            
            # Update intervention tracking
            self.last_intervention = datetime.now(timezone.utc)
            self.daily_stats['interventions'] += 1
            
        except Exception as e:
            logger.error(f"Error checking activity: {e}", exc_info=True)
    
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
        """Generate and display end of day summary"""
        print("\n" + "=" * 60)
        print("🌟 Daily Summary 🌟")
        print("=" * 60)
        
        try:
            # Get today's data
            today_data = self.aw_client.get_multi_timeframe_data()['today']
            today_summary = self.event_processor.filter_and_summarize_data({'today': today_data})['today']
            
            # Get daily statistics
            daily_stats = self.event_processor.get_daily_summary(today_summary)
            
            # Create summary message
            summary_parts = []
            
            # Active time
            active_hours = daily_stats['total_active_minutes'] / 60
            summary_parts.append(f"🕐 Active time: {active_hours:.1f} hours")
            
            # Focus sessions
            focus_count = daily_stats['focus_sessions']
            longest_focus = daily_stats['longest_focus']
            if focus_count > 0:
                summary_parts.append(f"🎯 Focus sessions: {focus_count} (longest: {longest_focus:.0f} min)")
            
            # Key activities
            if daily_stats['key_activities']:
                activities = ", ".join(daily_stats['key_activities'][:3])
                summary_parts.append(f"💼 Main activities: {activities}")
            
            # Distractions
            distraction_time = daily_stats['distraction_time']
            if distraction_time > 0:
                summary_parts.append(f"🌐 Distraction time: {distraction_time:.0f} min")
            
            # Context switches
            switches = daily_stats['app_switches']
            summary_parts.append(f"🔄 Context switches: {switches}")
            
            # Top apps
            if daily_stats['top_apps']:
                apps = ", ".join(daily_stats['top_apps'][:3])
                summary_parts.append(f"📱 Top apps: {apps}")
            
            # Display summary
            for part in summary_parts:
                print(part)
            
            # Generate encouragement
            print("\n💝 Remember:")
            
            if focus_count > 0:
                print(f"   • You had {focus_count} deep focus sessions today - that's amazing!")
            
            if active_hours > 4:
                print(f"   • You were active for {active_hours:.1f} hours - great stamina!")
            
            if daily_stats['key_activities']:
                print(f"   • You worked on important tasks like {daily_stats['key_activities'][0]}")
            
            print("   • Every bit of progress counts, and you showed up today!")
            
            # Ask about saving as good day
            if focus_count >= 2 or active_hours >= 4:
                print("\n✨ This looks like it was a productive day!")
                print("   Would you like to save this pattern as a 'good day' template?")
                print("   (Feature coming soon!)")
            
            # Save summary to file
            self._save_daily_summary(daily_stats)
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            print("Had trouble generating today's summary, but I'm sure you did great! 💪")
        
        print("=" * 60 + "\n")
    
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


def main():
    parser = argparse.ArgumentParser(description="Companion Cube - ADHD Productivity Assistant")
    parser.add_argument("--mode", choices=["ghost", "coach", "study_buddy", "weekend"], 
                       default="coach", help="Companion mode")
    parser.add_argument("--interval", type=int, default=60, 
                       help="Check interval in seconds")
    parser.add_argument("--model", type=str, default="cas/mistral-7b-instruct-v0.3",
                       help="Ollama model to use")
    parser.add_argument("--test", action="store_true", 
                       help="Run a single check for testing")
    parser.add_argument("--test-connections", action="store_true",
                       help="Test connections and exit")
    parser.add_argument("--daily-summary", action="store_true",
                       help="Generate daily summary and exit")
    parser.add_argument("--verbose", action="store_true",
                       help="Enable verbose mode with detailed LLM prompts and processing info")
    
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