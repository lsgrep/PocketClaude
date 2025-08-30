#!/usr/bin/env python3
"""Web dashboard for monitoring Claude Code Subagent progress."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import json
from pathlib import Path
from datetime import datetime
import asyncio
from aiohttp import web
import aiohttp_cors


class AgentMonitor:
    """Web dashboard for monitoring agent progress."""
    
    def __init__(self, port: int = 8080, log_dir: str = "./logs"):
        self.port = port
        self.log_dir = Path(log_dir)
        self.current_session = None
        self.sessions = []
        
    async def start(self):
        """Start the web server."""
        app = web.Application()
        
        # Configure CORS
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*"
            )
        })
        
        # Routes
        app.router.add_get('/', self.handle_index)
        app.router.add_get('/api/sessions', self.handle_sessions)
        app.router.add_get('/api/session/{session_id}', self.handle_session)
        app.router.add_get('/api/current', self.handle_current)
        app.router.add_post('/api/webhook', self.handle_webhook)
        
        # Apply CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        print(f"""
🌐 Claude Code Subagent Monitor Started!
========================================
Dashboard: http://localhost:{self.port}
API Endpoint: http://localhost:{self.port}/api/
Webhook URL: http://localhost:{self.port}/api/webhook

Set this in your environment:
export AGENT_WEBHOOK_URL="http://localhost:{self.port}/api/webhook"
""")
        
        # Keep running
        await asyncio.Event().wait()
    
    async def handle_index(self, request):
        """Serve the dashboard HTML."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Claude Code Subagent Monitor</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
            opacity: 0.9;
            margin-bottom: 30px;
        }
        .dashboard {
            display: grid;
            grid-template-columns: 1fr 2fr;
            gap: 20px;
            margin-top: 20px;
        }
        .panel {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .sessions-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .session-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .session-item:hover {
            background: rgba(255, 255, 255, 0.2);
            transform: translateX(5px);
        }
        .session-item.active {
            background: rgba(255, 255, 255, 0.3);
            border-left: 4px solid #00ff88;
        }
        .events-timeline {
            max-height: 600px;
            overflow-y: auto;
        }
        .event {
            margin: 10px 0;
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            border-left: 3px solid #00ff88;
        }
        .event-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .event-type {
            font-weight: bold;
            color: #00ff88;
        }
        .event-time {
            opacity: 0.7;
            font-size: 0.9em;
        }
        .event-data {
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 5px;
            font-size: 0.9em;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: #00ff88;
        }
        .stat-label {
            opacity: 0.8;
            margin-top: 5px;
        }
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-left: 10px;
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .progress-bar {
            height: 30px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff88, #00ccff);
            transition: width 0.5s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Claude Code Subagent Monitor <span class="live-indicator"></span></h1>
        <p class="subtitle">Real-time monitoring of agent activities</p>
        
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-sessions">0</div>
                <div class="stat-label">Total Sessions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="files-created">0</div>
                <div class="stat-label">Files Created</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="current-status">Idle</div>
                <div class="stat-label">Current Status</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" id="progress" style="width: 0%">0%</div>
        </div>
        
        <div class="dashboard">
            <div class="panel">
                <h2>📋 Sessions</h2>
                <div class="sessions-list" id="sessions-list">
                    <p style="opacity: 0.5;">No sessions yet...</p>
                </div>
            </div>
            
            <div class="panel">
                <h2>📊 Timeline</h2>
                <div class="events-timeline" id="events-timeline">
                    <p style="opacity: 0.5;">Select a session to view events...</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let currentSession = null;
        let autoRefresh = true;
        
        async function loadSessions() {
            try {
                const response = await fetch('/api/sessions');
                const sessions = await response.json();
                
                const listEl = document.getElementById('sessions-list');
                if (sessions.length === 0) {
                    listEl.innerHTML = '<p style="opacity: 0.5;">No sessions yet...</p>';
                    return;
                }
                
                listEl.innerHTML = sessions.map(s => `
                    <div class="session-item ${s.session_id === currentSession ? 'active' : ''}" 
                         onclick="loadSession('${s.session_id}')">
                        <div><strong>${s.session_id}</strong></div>
                        <div style="font-size: 0.9em; opacity: 0.8;">${s.task || 'Unknown task'}</div>
                        <div style="font-size: 0.8em; opacity: 0.6;">${s.start_time}</div>
                    </div>
                `).join('');
                
                document.getElementById('total-sessions').textContent = sessions.length;
            } catch (error) {
                console.error('Failed to load sessions:', error);
            }
        }
        
        async function loadSession(sessionId) {
            currentSession = sessionId;
            
            try {
                const response = await fetch(`/api/session/${sessionId}`);
                const data = await response.json();
                
                const timelineEl = document.getElementById('events-timeline');
                if (!data.events || data.events.length === 0) {
                    timelineEl.innerHTML = '<p style="opacity: 0.5;">No events in this session...</p>';
                    return;
                }
                
                timelineEl.innerHTML = data.events.map(e => `
                    <div class="event">
                        <div class="event-header">
                            <span class="event-type">${e.type}</span>
                            <span class="event-time">${new Date(e.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <div class="event-data">${JSON.stringify(e.data, null, 2)}</div>
                    </div>
                `).join('');
                
                // Update stats
                const filesCreated = data.events.filter(e => e.type === 'file_created').length;
                document.getElementById('files-created').textContent = filesCreated;
                
                // Update progress
                const totalSteps = data.events.filter(e => e.type === 'step_started').length;
                const completedSteps = data.events.filter(e => e.type === 'step_completed').length;
                if (totalSteps > 0) {
                    const progress = (completedSteps / totalSteps) * 100;
                    document.getElementById('progress').style.width = progress + '%';
                    document.getElementById('progress').textContent = Math.round(progress) + '%';
                }
                
                // Reload sessions to update active state
                await loadSessions();
            } catch (error) {
                console.error('Failed to load session:', error);
            }
        }
        
        async function checkCurrent() {
            try {
                const response = await fetch('/api/current');
                const data = await response.json();
                
                if (data.session_id) {
                    document.getElementById('current-status').textContent = 'Active';
                    document.getElementById('current-status').style.color = '#00ff88';
                    
                    if (data.session_id !== currentSession && autoRefresh) {
                        await loadSession(data.session_id);
                    }
                } else {
                    document.getElementById('current-status').textContent = 'Idle';
                    document.getElementById('current-status').style.color = '#fff';
                }
            } catch (error) {
                console.error('Failed to check current session:', error);
            }
        }
        
        // Initial load
        loadSessions();
        checkCurrent();
        
        // Auto-refresh
        setInterval(() => {
            if (autoRefresh) {
                checkCurrent();
                if (currentSession) {
                    loadSession(currentSession);
                }
            }
        }, 2000);
    </script>
</body>
</html>
"""
        return web.Response(text=html, content_type='text/html')
    
    async def handle_sessions(self, request):
        """Return list of all sessions."""
        sessions = []
        
        if self.log_dir.exists():
            for log_file in self.log_dir.glob("agent_log_*.json"):
                try:
                    with open(log_file, 'r') as f:
                        data = json.load(f)
                        sessions.append({
                            "session_id": data["session_id"],
                            "start_time": data.get("start_time", "Unknown"),
                            "task": data.get("events", [{}])[0].get("data", {}).get("task", "Unknown")
                        })
                except:
                    pass
        
        return web.json_response(sorted(sessions, key=lambda x: x["start_time"], reverse=True))
    
    async def handle_session(self, request):
        """Return details of a specific session."""
        session_id = request.match_info['session_id']
        log_file = self.log_dir / f"agent_log_{session_id}.json"
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                data = json.load(f)
            return web.json_response(data)
        
        return web.json_response({"error": "Session not found"}, status=404)
    
    async def handle_current(self, request):
        """Return current active session."""
        if self.current_session:
            return web.json_response({"session_id": self.current_session})
        return web.json_response({"session_id": None})
    
    async def handle_webhook(self, request):
        """Handle webhook from agent."""
        try:
            data = await request.json()
            self.current_session = data.get("session_id")
            
            # You could also broadcast to WebSocket clients here
            print(f"📡 Webhook received: {data.get('event', {}).get('type', 'unknown')}")
            
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)


if __name__ == "__main__":
    monitor = AgentMonitor()
    asyncio.run(monitor.start())