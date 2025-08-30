# 📡 Sharing Claude Code Subagent Progress

The Claude Code Subagent now includes multiple ways to share and monitor what's being done during execution.

## 🎯 Sharing Methods

### 1. 📄 Automatic Log Files
Every session automatically creates:
- **JSON Log**: `logs/agent_log_YYYYMMDD_HHMMSS.json` - Complete event history
- **Markdown Report**: `logs/agent_report_YYYYMMDD_HHMMSS.md` - Human-readable summary

```bash
# After running the agent, find logs in:
ls -la ./logs/
```

### 2. 🌐 Web Dashboard
Monitor agent progress in real-time through a web interface:

```bash
# Start the monitoring dashboard
python monitor.py

# Open in browser:
# http://localhost:8080
```

Features:
- Live session tracking
- Event timeline visualization
- Progress indicators
- Statistics dashboard
- Session history

### 3. 🔗 Webhook Integration
Send real-time updates to external services:

```bash
# Set webhook URL before running agent
export AGENT_WEBHOOK_URL="http://your-server.com/webhook"

# Or use with local monitor
export AGENT_WEBHOOK_URL="http://localhost:8080/api/webhook"

# Run agent
python main.py "Your task" -p ./project
```

Webhook payload format:
```json
{
  "session_id": "20240101_120000",
  "event": {
    "timestamp": "2024-01-01T12:00:00",
    "type": "file_created",
    "data": {
      "path": "/project/file.py"
    }
  }
}
```

### 4. 📊 Progress Files
Real-time progress written to file:

```python
# In your code, use ProgressReporter
from utils.logger import ProgressReporter

reporter = ProgressReporter(channel="file")
reporter.report("Starting implementation", progress=25)
```

### 5. 🔄 Integration with External Tools

#### Slack Integration
```bash
# Set up Slack webhook
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Modify webhook handler in logger.py to post to Slack
```

#### Discord Integration
```python
# Add Discord webhook support
async def send_to_discord(event):
    webhook_url = os.getenv("DISCORD_WEBHOOK")
    payload = {
        "content": f"**{event['type']}**: {json.dumps(event['data'])}"
    }
    # Send to Discord
```

## 📈 What Gets Tracked

### Event Types
- `session_started` - Agent begins work
- `plan_created` - Implementation plan generated
- `decision_made` - Action decisions
- `step_started` - Beginning implementation step
- `file_created` - New file created
- `step_completed` - Step finished
- `error` - Errors encountered
- `session_completed` - Agent finished

### Data Captured
- Timestamps for all events
- Task descriptions
- File paths created/modified
- Decision reasoning
- Error messages
- Cost tracking
- Progress percentages

## 🚀 Quick Start

### Basic Monitoring
```bash
# Terminal 1: Start monitor
python monitor.py

# Terminal 2: Run agent with logging
python main.py "Build a REST API" -p ./my-project
```

### Share Results
```bash
# After completion, share the markdown report
cat logs/agent_report_*.md

# Or share the entire log directory
tar -czf agent_logs.tar.gz logs/
```

### Programmatic Access
```python
from utils.logger import AgentLogger

# Read existing log
with open("logs/agent_log_20240101_120000.json", "r") as f:
    log_data = json.load(f)

# Process events
for event in log_data["events"]:
    print(f"{event['type']}: {event['data']}")
```

## 🔧 Configuration

### Environment Variables
```bash
# Enable webhook logging
export AGENT_WEBHOOK_URL="http://localhost:8080/api/webhook"

# Custom log directory
export AGENT_LOG_DIR="/path/to/logs"

# Disable logging
export AGENT_LOGGING_ENABLED="false"
```

### Custom Logger
```python
from utils.logger import AgentLogger

# Initialize with custom settings
logger = AgentLogger(
    log_dir="./custom_logs",
    enable_file=True,
    enable_webhook=True
)

# Log custom events
logger.log_event("custom_event", {
    "key": "value",
    "progress": 50
})
```

## 📱 Mobile Monitoring

The web dashboard is mobile-responsive. Access from your phone:
1. Start monitor with `python monitor.py`
2. Find your computer's IP: `ifconfig | grep inet`
3. Open on mobile: `http://YOUR_IP:8080`

## 🔐 Security Notes

- Webhook URLs should use HTTPS in production
- Add authentication to the monitoring dashboard for public deployment
- Sanitize sensitive data before logging
- Use environment variables for API keys and URLs

## 📋 Example Output

### Markdown Report Sample
```markdown
# Claude Code Subagent Session Report

**Session ID:** 20240101_120000
**Start Time:** 2024-01-01T12:00:00
**Task:** Build a REST API for todo list

## Timeline of Events

### 📋 12:00:15 - Plan Created
  1. Design API endpoints
  2. Implement data models
  3. Create CRUD operations
  
### 🔨 12:00:30 - Started: Design API endpoints
  - Type: implement
  
### 📄 12:01:45 - File Created
  - Path: `/project/api.py`

## Summary
- **Total Events:** 15
- **Files Created:** 3
- **Errors:** 0
```

## 🤝 Sharing with Team

1. **Real-time Collaboration**
   - Share monitor URL with team
   - Everyone sees same progress

2. **Post-Execution Sharing**
   - Send markdown reports via email/Slack
   - Commit logs to git repository
   - Upload to shared drive

3. **Integration with CI/CD**
   - Webhook to trigger deployments
   - Log to centralized logging system
   - Track metrics in monitoring tools

---

**Note**: The sharing features are designed to provide transparency and collaboration in the development process while the Claude Code Subagent works autonomously.