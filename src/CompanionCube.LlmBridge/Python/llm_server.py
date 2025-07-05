#!/usr/bin/env python3
"""
LLM Server for Companion Cube
Provides a REST API for the C# service to query the local LLM
"""

import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, Any
from flask import Flask, request, jsonify
from llama_cpp import Llama

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
llm = None

# ADHD-focused system prompt
SYSTEM_PROMPT = """You are Companion Cube, an ADHD productivity assistant. Your core principles:
1. Celebrate what users did, not what they should do
2. No judgment, shame, or pressure
3. All suggestions are optional
4. Understand ADHD patterns: hyperfocus, task switching, time blindness
5. Be encouraging and supportive
6. Keep responses concise and actionable
"""

def load_model(model_path: str):
    """Load the LLM model"""
    global llm
    try:
        logger.info(f"Loading model from {model_path}")
        llm = Llama(
            model_path=model_path,
            n_ctx=2048,  # Context window
            n_threads=4,  # CPU threads
            use_mlock=True  # Keep model in RAM
        )
        logger.info("Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        sys.exit(1)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': llm is not None
    })

@app.route('/generate', methods=['POST'])
def generate():
    """Generate text from prompt"""
    if llm is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        prompt = data.get('prompt', '')
        max_tokens = data.get('max_tokens', 150)
        temperature = data.get('temperature', 0.7)
        
        # Add system prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n\nAssistant:"
        
        start_time = time.time()
        
        # Generate response
        response = llm(
            full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["User:", "\n\n"],
            echo=False
        )
        
        response_time = time.time() - start_time
        
        # Extract text from response
        generated_text = response['choices'][0]['text'].strip()
        
        return jsonify({
            'text': generated_text,
            'tokens_used': response['usage']['total_tokens'],
            'response_time': response_time,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/analyze_behavior', methods=['POST'])
def analyze_behavior():
    """Specialized endpoint for ADHD behavior analysis"""
    if llm is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        activities = data.get('activities', [])
        analysis_type = data.get('type', 'general')
        
        # Build specialized prompt based on analysis type
        if analysis_type == 'focus_pattern':
            prompt = build_focus_pattern_prompt(activities)
        elif analysis_type == 'distraction_triggers':
            prompt = build_distraction_trigger_prompt(activities)
        elif analysis_type == 'optimal_schedule':
            prompt = build_optimal_schedule_prompt(activities)
        else:
            prompt = build_general_analysis_prompt(activities)
        
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        
        response = llm(
            full_prompt,
            max_tokens=300,
            temperature=0.5,
            echo=False
        )
        
        insights = response['choices'][0]['text'].strip()
        
        return jsonify({
            'insights': insights,
            'analysis_type': analysis_type,
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

def build_focus_pattern_prompt(activities: list) -> str:
    """Build prompt for analyzing focus patterns"""
    return f"""Analyze these activities for ADHD focus patterns:
    
Activities: {len(activities)} total
Most common apps: {get_top_apps(activities, 3)}

Identify:
1. When hyperfocus occurs (time of day, specific tasks)
2. Average focus duration before task switching
3. Which activities lead to sustained focus

Provide 3 specific, actionable insights:"""

def build_distraction_trigger_prompt(activities: list) -> str:
    """Build prompt for identifying distraction triggers"""
    return f"""Analyze these activities for ADHD distraction patterns:
    
Task switches in last hour: {count_task_switches(activities)}
Entertainment app usage: {get_entertainment_percentage(activities)}%

Identify:
1. Common distraction triggers
2. Times when focus breaks down
3. Patterns before getting stuck

Provide 3 supportive suggestions (no judgment):"""

def build_optimal_schedule_prompt(activities: list) -> str:
    """Build prompt for suggesting optimal schedule"""
    return f"""Based on these ADHD user activity patterns:
    
Peak productivity hours: {get_peak_hours(activities)}
Average session length: {get_avg_session_length(activities)} minutes

Suggest:
1. Best times for deep work
2. When to schedule breaks
3. Optimal task batching approach

Keep suggestions flexible and ADHD-friendly:"""

def build_general_analysis_prompt(activities: list) -> str:
    """Build general analysis prompt"""
    return f"""Analyze these activities for an ADHD user:
    
Total activities: {len(activities)}
Time span: {get_time_span(activities)} hours

Provide supportive insights about:
1. What went well today
2. Natural work patterns observed
3. One gentle suggestion for tomorrow

Remember: celebrate accomplishments, no pressure:"""

# Helper functions for analysis
def get_top_apps(activities: list, n: int) -> str:
    """Get top N most used applications"""
    app_counts = {}
    for activity in activities:
        app = activity.get('application_name', 'Unknown')
        app_counts[app] = app_counts.get(app, 0) + 1
    
    top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:n]
    return ', '.join([f"{app[0]} ({app[1]})" for app in top_apps])

def count_task_switches(activities: list) -> int:
    """Count number of task switches"""
    if len(activities) < 2:
        return 0
    
    switches = 0
    last_app = activities[0].get('application_name')
    
    for activity in activities[1:]:
        current_app = activity.get('application_name')
        if current_app != last_app:
            switches += 1
        last_app = current_app
    
    return switches

def get_entertainment_percentage(activities: list) -> int:
    """Calculate percentage of time on entertainment apps"""
    entertainment_apps = ['chrome', 'firefox', 'edge', 'youtube', 'netflix', 'spotify', 'discord']
    total_time = sum(a.get('duration_seconds', 0) for a in activities)
    entertainment_time = sum(
        a.get('duration_seconds', 0) 
        for a in activities 
        if any(app in a.get('application_name', '').lower() for app in entertainment_apps)
    )
    
    return int((entertainment_time / total_time * 100) if total_time > 0 else 0)

def get_peak_hours(activities: list) -> str:
    """Identify peak productivity hours"""
    # Simplified - in real implementation would analyze timestamps
    return "10am-12pm, 2pm-4pm"

def get_avg_session_length(activities: list) -> int:
    """Calculate average session length"""
    if not activities:
        return 0
    
    durations = [a.get('duration_seconds', 0) for a in activities]
    return int(sum(durations) / len(durations) / 60)  # Convert to minutes

def get_time_span(activities: list) -> float:
    """Get time span of activities in hours"""
    if not activities:
        return 0
    
    # In real implementation would calculate from timestamps
    return 8.5

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Companion Cube LLM Server')
    parser.add_argument('--model', required=True, help='Path to GGUF model file')
    parser.add_argument('--port', type=int, default=5678, help='Port to run server on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    
    args = parser.parse_args()
    
    # Load the model
    load_model(args.model)
    
    # Start the server
    logger.info(f"Starting server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)