"""Claude Code SDK interface utilities."""

import os
from typing import Optional, AsyncIterator, List, Dict, Any
from pathlib import Path
import json
import yaml

from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)


async def call_claude_code(
    prompt: str,
    options: Optional[ClaudeCodeOptions] = None,
    extract_text: bool = True
) -> str:
    """
    Call Claude Code SDK and return the response.
    
    Args:
        prompt: The prompt to send to Claude
        options: Optional ClaudeCodeOptions for configuration
        extract_text: If True, extract only text content from response
        
    Returns:
        The response from Claude as a string
    """
    response_text = []
    tool_uses = []
    
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and extract_text:
                    response_text.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_uses.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
        elif isinstance(message, ResultMessage):
            if message.total_cost_usd > 0:
                print(f"[Claude Cost: ${message.total_cost_usd:.4f}]")
    
    if extract_text:
        return "\n".join(response_text)
    else:
        return json.dumps({"text": response_text, "tool_uses": tool_uses})


async def call_claude_with_tools(
    prompt: str,
    allowed_tools: List[str],
    working_dir: Optional[Path] = None,
    system_prompt: Optional[str] = None,
    permission_mode: str = 'default'
) -> Dict[str, Any]:
    """
    Call Claude with specific tools enabled.
    
    Args:
        prompt: The prompt to send to Claude
        allowed_tools: List of tool names to allow (e.g., ["Read", "Write", "Bash"])
        working_dir: Working directory for file operations
        system_prompt: Optional system prompt
        permission_mode: Permission mode for file operations ('default', 'acceptEdits', 'bypassPermissions', 'plan')
        
    Returns:
        Dictionary with response text and tool usage information
    """
    options = ClaudeCodeOptions(
        allowed_tools=allowed_tools,
        cwd=working_dir or os.getcwd(),
        system_prompt=system_prompt,
        permission_mode=permission_mode
    )
    
    response = {
        "text": [],
        "tool_uses": [],
        "tool_results": [],
        "cost": 0.0
    }
    
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response["text"].append(block.text)
                elif isinstance(block, ToolUseBlock):
                    response["tool_uses"].append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
                elif isinstance(block, ToolResultBlock):
                    response["tool_results"].append({
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                        "is_error": block.is_error if hasattr(block, 'is_error') else False
                    })
        elif isinstance(message, ResultMessage):
            response["cost"] = message.total_cost_usd
    
    response["text"] = "\n".join(response["text"])
    return response


async def parse_yaml_response(prompt: str, options: Optional[ClaudeCodeOptions] = None) -> Dict[str, Any]:
    """
    Call Claude and parse YAML response.
    
    Args:
        prompt: The prompt requesting YAML output
        options: Optional ClaudeCodeOptions
        
    Returns:
        Parsed YAML as dictionary
    """
    response = await call_claude_code(prompt, options, extract_text=True)
    
    # Debug: Show what we received
    if len(response) < 500:
        print(f"[DEBUG] Response: {response[:200]}...")
    
    # Extract YAML block if wrapped in code fences
    if "```yaml" in response:
        yaml_str = response.split("```yaml")[1].split("```")[0].strip()
    elif "```" in response:
        # Try to extract any code block
        yaml_str = response.split("```")[1].split("```")[0].strip()
        # Remove language identifier if present
        if yaml_str.startswith(('yaml', 'yml')):
            lines = yaml_str.split('\n')
            yaml_str = '\n'.join(lines[1:])
    else:
        yaml_str = response
    
    try:
        parsed = yaml.safe_load(yaml_str)
        # Ensure we return a dictionary
        if not isinstance(parsed, dict):
            print(f"YAML parsed to non-dict type: {type(parsed)}, value: {str(parsed)[:100]}")
            # Try to extract structured data from string
            if isinstance(parsed, str) and ':' in parsed:
                # Attempt to re-parse as YAML
                try:
                    reparsed = yaml.safe_load(parsed)
                    if isinstance(reparsed, dict):
                        return reparsed
                except:
                    pass
            return {"error": "YAML did not parse to dictionary", "raw": response, "parsed": parsed}
        return parsed
    except yaml.YAMLError as e:
        print(f"Failed to parse YAML: {e}")
        print(f"Attempted to parse: {yaml_str[:200]}...")
        return {"error": "Failed to parse YAML", "raw": response}


# Test the interface
if __name__ == "__main__":
    import anyio
    
    async def test():
        # Test basic call
        print("Testing basic Claude call...")
        response = await call_claude_code("What is 2 + 2?")
        print(f"Response: {response}\n")
        
        # Test with tools
        print("Testing Claude with tools...")
        result = await call_claude_with_tools(
            "List files in current directory",
            allowed_tools=["Bash"],
            permission_mode='acceptEdits'
        )
        print(f"Tool result: {result}\n")
    
    anyio.run(test)