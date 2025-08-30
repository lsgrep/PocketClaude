"""Logging and sharing utilities for Claude Code Subagent."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import aiohttp


class AgentLogger:
    """Logger that saves agent actions to file and can share via various methods."""
    
    def __init__(self, log_dir: str = "./logs", enable_file: bool = True, enable_webhook: bool = False):
        """
        Initialize the logger.
        
        Args:
            log_dir: Directory to save log files
            enable_file: Whether to save logs to file
            enable_webhook: Whether to send logs to webhook
        """
        self.log_dir = Path(log_dir)
        self.enable_file = enable_file
        self.enable_webhook = enable_webhook
        self.webhook_url = os.getenv("AGENT_WEBHOOK_URL", "")
        
        # Create session ID for this run
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = None
        
        if self.enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.log_file = self.log_dir / f"agent_log_{self.session_id}.json"
            self.markdown_file = self.log_dir / f"agent_report_{self.session_id}.md"
            
            # Initialize log file
            self._init_log_file()
    
    def _init_log_file(self):
        """Initialize the JSON log file."""
        initial_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "events": []
        }
        with open(self.log_file, 'w') as f:
            json.dump(initial_data, f, indent=2)
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """
        Log an event.
        
        Args:
            event_type: Type of event (e.g., "plan_created", "step_started", "file_created")
            data: Event data
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        
        # Save to file
        if self.enable_file and self.log_file:
            self._append_to_log(event)
        
        # Send to webhook (async)
        if self.enable_webhook and self.webhook_url:
            asyncio.create_task(self._send_to_webhook(event))
        
        return event
    
    def _append_to_log(self, event: Dict[str, Any]):
        """Append event to log file."""
        try:
            with open(self.log_file, 'r') as f:
                log_data = json.load(f)
            
            log_data["events"].append(event)
            log_data["last_updated"] = datetime.now().isoformat()
            
            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            print(f"Error saving to log: {e}")
    
    async def _send_to_webhook(self, event: Dict[str, Any]):
        """Send event to webhook."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "session_id": self.session_id,
                    "event": event
                }
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        print(f"Webhook failed: {response.status}")
        except Exception as e:
            print(f"Webhook error: {e}")
    
    def generate_markdown_report(self) -> str:
        """Generate a markdown report of the session."""
        if not self.log_file or not self.log_file.exists():
            return "No log data available"
        
        with open(self.log_file, 'r') as f:
            log_data = json.load(f)
        
        report = f"""# Claude Code Subagent Session Report

**Session ID:** {log_data['session_id']}  
**Start Time:** {log_data['start_time']}  
**Last Updated:** {log_data.get('last_updated', 'N/A')}

## Timeline of Events

"""
        
        # Group events by type
        events_by_type = {}
        for event in log_data["events"]:
            event_type = event["type"]
            if event_type not in events_by_type:
                events_by_type[event_type] = []
            events_by_type[event_type].append(event)
        
        # Add events to report
        for event in log_data["events"]:
            timestamp = event["timestamp"].split("T")[1].split(".")[0]  # Get time only
            event_type = event["type"]
            data = event["data"]
            
            if event_type == "plan_created":
                report += f"\n### 📋 {timestamp} - Plan Created\n"
                if "steps" in data:
                    for i, step in enumerate(data["steps"], 1):
                        report += f"  {i}. {step.get('name', 'Step')}\n"
            
            elif event_type == "decision_made":
                report += f"\n### 🤔 {timestamp} - Decision: {data.get('action', 'unknown').upper()}\n"
                report += f"  - Reasoning: {data.get('reasoning', 'N/A')}\n"
            
            elif event_type == "step_started":
                report += f"\n### 🔨 {timestamp} - Started: {data.get('name', 'Step')}\n"
                report += f"  - Type: {data.get('type', 'N/A')}\n"
            
            elif event_type == "file_created":
                report += f"\n### 📄 {timestamp} - File Created\n"
                report += f"  - Path: `{data.get('path', 'unknown')}`\n"
            
            elif event_type == "error":
                report += f"\n### ❌ {timestamp} - Error\n"
                report += f"  - {data.get('message', 'Unknown error')}\n"
        
        # Add summary
        report += "\n## Summary\n\n"
        file_events = events_by_type.get("file_created", [])
        error_events = events_by_type.get("error", [])
        
        report += f"- **Total Events:** {len(log_data['events'])}\n"
        report += f"- **Files Created:** {len(file_events)}\n"
        report += f"- **Errors:** {len(error_events)}\n"
        
        # Save markdown report
        if self.markdown_file:
            with open(self.markdown_file, 'w') as f:
                f.write(report)
        
        return report
    
    def get_shareable_link(self) -> str:
        """Generate a shareable summary."""
        report_path = self.markdown_file if self.markdown_file else "No report available"
        log_path = self.log_file if self.log_file else "No log available"
        
        return f"""
📊 Agent Session Complete!

Session ID: {self.session_id}
Log File: {log_path}
Report: {report_path}

To share this session:
1. Send the markdown report: {report_path}
2. View raw logs: {log_path}
3. Set AGENT_WEBHOOK_URL environment variable for real-time updates
"""


class ProgressReporter:
    """Real-time progress reporter for sharing agent status."""
    
    def __init__(self, channel: str = "console"):
        """
        Initialize progress reporter.
        
        Args:
            channel: Where to report ("console", "file", "webhook", "slack")
        """
        self.channel = channel
        self.progress_file = Path("./progress.txt")
        
    def report(self, message: str, progress: Optional[float] = None):
        """
        Report progress.
        
        Args:
            message: Status message
            progress: Progress percentage (0-100)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if progress is not None:
            status = f"[{timestamp}] [{progress:.0f}%] {message}"
        else:
            status = f"[{timestamp}] {message}"
        
        if self.channel == "console":
            print(f"📡 {status}")
        
        elif self.channel == "file":
            with open(self.progress_file, 'a') as f:
                f.write(f"{status}\n")
        
        return status


class LiveShareServer:
    """Simple HTTP server to share agent progress via web interface."""
    
    def __init__(self, port: int = 8080):
        """Initialize live share server."""
        self.port = port
        self.events = []
        
    async def start(self):
        """Start the web server."""
        from aiohttp import web
        
        async def handle_events(request):
            """Return current events as JSON."""
            return web.json_response(self.events)
        
        async def handle_index(request):
            """Return simple HTML interface."""
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>Claude Code Subagent - Live Progress</title>
    <style>
        body { font-family: monospace; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
        h1 { color: #569cd6; }
        .event { margin: 10px 0; padding: 10px; background: #2d2d2d; border-radius: 5px; }
        .timestamp { color: #608b4e; }
        .type { color: #dcdcaa; font-weight: bold; }
        .data { color: #ce9178; }
    </style>
</head>
<body>
    <h1>🤖 Claude Code Subagent - Live Progress</h1>
    <div id="events"></div>
    <script>
        async function updateEvents() {
            const response = await fetch('/events');
            const events = await response.json();
            const container = document.getElementById('events');
            container.innerHTML = events.map(e => `
                <div class="event">
                    <span class="timestamp">${e.timestamp}</span>
                    <span class="type">${e.type}</span>
                    <pre class="data">${JSON.stringify(e.data, null, 2)}</pre>
                </div>
            `).join('');
        }
        setInterval(updateEvents, 1000);
        updateEvents();
    </script>
</body>
</html>
"""
            return web.Response(text=html, content_type='text/html')
        
        app = web.Application()
        app.router.add_get('/', handle_index)
        app.router.add_get('/events', handle_events)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        print(f"🌐 Live progress available at: http://localhost:{self.port}")
        
    def add_event(self, event: Dict[str, Any]):
        """Add an event to the live feed."""
        self.events.append(event)
        # Keep only last 100 events
        if len(self.events) > 100:
            self.events.pop(0)


# Test the logger
if __name__ == "__main__":
    logger = AgentLogger()
    
    # Log some test events
    logger.log_event("session_started", {"task": "Test task"})
    logger.log_event("plan_created", {
        "steps": [
            {"name": "Step 1", "type": "implement"},
            {"name": "Step 2", "type": "test"}
        ]
    })
    logger.log_event("file_created", {"path": "/test/file.py"})
    
    # Generate report
    report = logger.generate_markdown_report()
    print(report)
    print(logger.get_shareable_link())