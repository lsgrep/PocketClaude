# Claude Code Subagent 🤖

An intelligent coding agent that leverages Claude Code SDK with PocketFlow's graph-based abstractions to automate software development tasks. Following the **Agentic Coding** methodology - humans design, agents code!

## Overview

Claude Code Subagent is a sophisticated autonomous coding assistant that can:
- 📝 Understand high-level requirements
- 🗺️ Create implementation plans
- 💻 Generate and modify code
- 🧪 Test implementations
- 🔧 Refactor and improve code
- 📊 Provide progress feedback

## Features

- **Autonomous Decision Making**: The agent decides what actions to take based on context
- **Iterative Development**: Supports multiple implementation-test-refactor cycles
- **Error Recovery**: Automatically handles and recovers from errors
- **Tool Integration**: Uses Claude Code's tools (Read, Write, Bash) for file operations
- **Flexible Workflows**: Multiple flow patterns for different complexity levels
- **Project Analysis**: Understands existing codebases before making changes

## Prerequisites

- Python 3.10+
- Node.js (for Claude Code CLI)
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- PocketFlow: `pip install pocketflow`
- Claude Code SDK: `pip install claude-code-sdk`

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd cookbook/pocketflow-claude-subagent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Claude Code (if not already done):
```bash
npm install -g @anthropic-ai/claude-code
```

## Usage

### Command Line Interface

```bash
# Simple task
python main.py "Create a hello world script"

# Specify project path and complexity
python main.py "Build a REST API for todo list" -p ./my-project -c complex

# Interactive mode
python main.py -i

# View example tasks
python main.py --examples
```

### Python API

```python
import anyio
from flow import create_coding_agent_flow

async def main():
    # Initialize shared store
    shared = {
        "task": "Create a calculator CLI app",
        "context": {
            "project_path": "./calculator-app"
        }
    }
    
    # Create and run flow
    flow = create_coding_agent_flow()
    await flow.run_async(shared)
    
    # Check results
    print(shared["summary"])

anyio.run(main)
```

## Architecture

### Flow Design

The agent uses a graph-based architecture with decision branching:

```
Requirements → Analysis → Decision → [Plan/Implement/Test/Refactor] → Decision → ... → Complete
                              ↑                                           ↓
                              └───────────────────────────────────────────┘
```

### Core Components

#### Nodes
- **UnderstandRequirements**: Parses user task into structured requirements
- **AnalyzeContext**: Scans existing project structure
- **DecideAction**: Determines next best action based on state
- **CreatePlan**: Generates step-by-step implementation plan
- **ImplementCode**: Writes or modifies code files
- **TestImplementation**: Runs tests and validates code
- **RefactorCode**: Improves code quality and fixes issues
- **FinalizeProject**: Completes task and generates summary

#### Utilities
- **claude_interface.py**: Claude Code SDK wrapper functions
- **code_analyzer.py**: Project structure and code analysis
- **task_decomposer.py**: Breaks complex tasks into steps

#### Flows
- **Simple Flow**: Linear progression for straightforward tasks
- **Iterative Flow**: Multiple cycles for complex development
- **Advanced Flow**: Full agent with all capabilities

## Shared Store Schema

```python
shared = {
    "task": str,                    # User's task description
    "requirements": {               # Parsed requirements
        "main_goal": str,
        "features": list,
        "constraints": list
    },
    "context": {                    # Project context
        "project_path": str,
        "existing_files": list,
        "dependencies": dict
    },
    "plan": {                       # Implementation plan
        "steps": list,
        "current_step": int
    },
    "implementation": {             # Code changes
        "files_created": list,
        "files_modified": list,
        "tool_uses": list
    },
    "test_results": dict,          # Test outcomes
    "history": list,               # Action history
    "state": str                   # Current state
}
```

## Example Tasks

### Simple (< 30 min)
```bash
python main.py "Create a Python script that generates random passwords" -c simple
```

### Medium (30-60 min)
```bash
python main.py "Build a CLI todo app with add, remove, list commands" -c medium
```

### Complex (> 1 hour)
```bash
python main.py "Create a REST API with authentication and database" -c complex
```

## Best Practices

1. **Start Simple**: Begin with simple tasks to understand the agent's capabilities
2. **Clear Requirements**: Provide specific, detailed task descriptions
3. **Project Structure**: Ensure clean project directory for better context analysis
4. **Iterative Approach**: Let the agent cycle through implement-test-refactor
5. **Monitor Progress**: Watch the agent's decisions and reasoning

## Configuration

### Retry Settings
Nodes have configurable retry logic:
```python
node = ImplementCode(max_retries=5, wait=2)  # 5 retries with 2s wait
```

### Tool Permissions
Control file operation permissions:
```python
options = ClaudeCodeOptions(
    permission_mode='ask'  # 'ask', 'acceptEdits', 'denyEdits'
)
```

## Troubleshooting

### Common Issues

1. **Claude Code not found**
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

2. **Import errors**
   ```bash
   pip install pocketflow claude-code-sdk pyyaml
   ```

3. **Permission errors**
   - Ensure write permissions in project directory
   - Use appropriate `permission_mode` setting

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Nodes
1. Create node class inheriting from `Node` or `AsyncNode`
2. Implement `prep`, `exec`, `post` methods
3. Add to flow orchestration in `flow.py`

### Custom Flows
```python
from pocketflow import AsyncFlow
from nodes import YourCustomNode

# Create custom flow
custom_node = YourCustomNode()
flow = AsyncFlow(start=custom_node)
```

## Limitations

- Requires active Claude Code subscription
- Limited by Claude's context window for large projects
- Best suited for well-defined, scoped tasks
- May require human intervention for complex architectural decisions

## Contributing

Contributions are welcome! Please:
1. Follow the existing code structure
2. Add tests for new features
3. Update documentation
4. Use type hints where appropriate

## License

MIT

## Acknowledgments

- Built on [PocketFlow](https://github.com/The-Pocket/PocketFlow) - 100-line LLM framework
- Powered by [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code/sdk)
- Follows Agentic Coding methodology

---

**Remember**: This agent is a tool to augment your coding, not replace human creativity and decision-making. Always review generated code before deployment!