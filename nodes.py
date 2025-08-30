"""Node definitions for Claude Code Subagent."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pathlib import Path
import json
import yaml
from pocketflow import Node, AsyncNode, BatchNode
from utils.claude_interface import call_claude_code, call_claude_with_tools, parse_yaml_response
from utils.code_analyzer import analyze_project, analyze_python_file, extract_todo_comments
from utils.task_decomposer import decompose_task, prioritize_steps, validate_plan
from claude_code_sdk import ClaudeCodeOptions


class UnderstandRequirements(AsyncNode):
    """Parse and understand the user's coding task."""
    
    async def prep_async(self, shared):
        return shared.get("task", "")
    
    async def exec_async(self, task):
        if not task:
            return {"error": "No task provided"}
        
        prompt = f"""DO NOT explore files or use tools. Simply analyze this text and return YAML.

Task to analyze: {task}

Return ONLY the following YAML structure with no other text:
```yaml
requirements:
  main_goal: "Primary objective"
  features:
    - "Feature 1"
    - "Feature 2"
  constraints:
    - "Any limitations or requirements"
  suggested_tech:
    - "Technology or framework suggestions"
  deliverables:
    - "Expected outputs"
```"""
        
        options = ClaudeCodeOptions(
            system_prompt="You are an expert software architect analyzing requirements.",
            max_turns=1
        )
        
        return await parse_yaml_response(prompt, options)
    
    async def post_async(self, shared, prep_res, exec_res):
        if isinstance(exec_res, dict) and "requirements" in exec_res:
            shared["requirements"] = exec_res["requirements"]
            shared["state"] = "requirements_understood"
            main_goal = exec_res['requirements'].get('main_goal', 'Task parsed')
            print(f"✓ Requirements understood: {main_goal}")
        elif isinstance(exec_res, dict) and "error" in exec_res:
            # Use a fallback for requirements
            shared["requirements"] = {
                "main_goal": prep_res,  # Use the original task as main goal
                "features": [],
                "constraints": [],
                "suggested_tech": [],
                "deliverables": []
            }
            shared["state"] = "requirements_understood"
            print(f"✓ Using simplified requirements for: {prep_res}")
        else:
            shared["errors"] = shared.get("errors", []) + ["Failed to understand requirements"]
            print(f"✗ Failed to parse requirements: {type(exec_res)}")
        
        return "default"


class AnalyzeContext(Node):
    """Analyze existing codebase and project structure."""
    
    def prep(self, shared):
        return shared.get("context", {}).get("project_path", ".")
    
    def exec(self, project_path):
        analysis = analyze_project(project_path)
        
        # Extract TODOs if present
        todos = extract_todo_comments(project_path)
        if todos:
            analysis["todos"] = todos
        
        return analysis
    
    def post(self, shared, prep_res, exec_res):
        shared["context"].update(exec_res)
        shared["state"] = "context_analyzed"
        
        if "error" not in exec_res:
            print(f"✓ Analyzed project: {exec_res.get('total_files', 0)} files, {exec_res.get('total_lines', 0)} lines")
            if exec_res.get("entry_points"):
                print(f"  Entry points: {', '.join(exec_res['entry_points'])}")
        else:
            print(f"✓ Project analysis: {exec_res.get('error', 'Unknown error')}")
        
        return "default"


class DecideAction(AsyncNode):
    """Determine next action based on current state."""
    
    async def prep_async(self, shared):
        return {
            "state": shared.get("state", "initial"),
            "task": shared.get("task", ""),
            "requirements": shared.get("requirements", {}),
            "plan": shared.get("plan", {}),
            "implementation": shared.get("implementation", {}),
            "history": shared.get("history", []),
            "errors": shared.get("errors", [])
        }
    
    async def exec_async(self, context):
        # Build decision prompt
        prompt = f"""DO NOT explore files or use tools. Just decide on the next action.

Current State: {context['state']}
Task: {context['task']}
Completed Steps: {len(context['history'])}
Errors: {len(context.get('errors', []))}

Available Actions:
- plan: Create or update implementation plan
- implement: Write or modify code
- test: Test the implementation
- refactor: Improve existing code
- complete: Task is finished

Consider:
1. Has a plan been created? {bool(context['plan'])}
2. Has implementation started? {bool(context['implementation'])}
3. Are there errors to fix? {bool(context['errors'])}

Return ONLY this YAML structure:
```yaml
action: <action_name>
reasoning: "Why this action"
confidence: <0.0-1.0>
```"""
        
        options = ClaudeCodeOptions(
            system_prompt="You are an intelligent agent deciding on the next best action.",
            max_turns=1
        )
        
        result = await parse_yaml_response(prompt, options)
        return result
    
    async def post_async(self, shared, prep_res, exec_res):
        # Increment iteration counter
        shared["current_iteration"] = shared.get("current_iteration", 0) + 1
        
        print(f"\n🤔 DECISION POINT (Iteration {shared['current_iteration']}):")
        print("="*60)
        print(f"Current State: {prep_res.get('state', 'unknown')}")
        print(f"Has Plan: {bool(prep_res.get('plan'))}")
        print(f"Has Implementation: {bool(prep_res.get('implementation'))}")
        print(f"Errors Present: {bool(prep_res.get('errors'))}")
        print(f"History Length: {len(prep_res.get('history', []))}")
        
        # Check if we've hit the iteration limit
        max_iterations = shared.get("max_iterations", 10)
        if shared["current_iteration"] >= max_iterations:
            print(f"⚠️ Reached maximum iterations ({max_iterations}), completing...")
            return "complete"
        
        # Handle parsing errors with fallback logic
        if not isinstance(exec_res, dict):
            # Determine fallback action based on state
            state = prep_res.get("state", "initial")
            plan_count = len([h for h in prep_res.get("history", []) if h.get("action") == "plan"])
            
            if plan_count >= 3:
                # If we've tried planning 3 times, move to implementation
                exec_res = {"action": "implement", "reasoning": "Moving to implementation after multiple planning attempts"}
            elif state == "initial" or not prep_res.get("plan"):
                exec_res = {"action": "plan", "reasoning": "Starting with planning phase"}
            elif not prep_res.get("implementation"):
                exec_res = {"action": "implement", "reasoning": "Moving to implementation"}
            else:
                exec_res = {"action": "test", "reasoning": "Testing implementation"}
        
        action = exec_res.get("action", "plan")
        reasoning = exec_res.get("reasoning", "Continuing development")
        
        # Prevent getting stuck in planning
        if action == "plan":
            plan_count = len([h for h in shared.get("history", []) if h.get("action") == "plan"])
            if plan_count >= 3:
                action = "implement"
                reasoning = "Moving to implementation after multiple planning attempts"
        
        # Add to history
        shared["history"] = shared.get("history", []) + [{
            "action": action,
            "reasoning": reasoning,
            "state": shared.get("state", "unknown")
        }]
        
        print(f"\n📍 DECISION MADE:")
        print(f"   Action: {action.upper()}")
        print(f"   Reasoning: {reasoning}")
        print(f"   Confidence: {exec_res.get('confidence', 'N/A')}")
        print("="*60 + "\n")
        
        return action


class CreatePlan(AsyncNode):
    """Generate implementation plan."""
    
    async def prep_async(self, shared):
        return {
            "task": shared.get("task", ""),
            "requirements": shared.get("requirements", {}),
            "context": shared.get("context", {})
        }
    
    async def exec_async(self, inputs):
        task = inputs["task"]
        context = inputs["context"]
        
        steps = await decompose_task(task, context)
        
        # Ensure steps is always a list
        if not isinstance(steps, list):
            steps = []
        
        validation = validate_plan(steps)
        
        return {
            "steps": steps,
            "validation": validation
        }
    
    async def post_async(self, shared, prep_res, exec_res):
        plan = {
            "steps": exec_res["steps"],
            "current_step": 0,
            "validation": exec_res["validation"]
        }
        
        shared["plan"] = plan
        shared["state"] = "planned"
        
        print(f"\n✓ Created plan with {len(plan['steps'])} steps")
        print("\n📋 DETAILED PLAN:")
        print("="*60)
        for i, step in enumerate(plan['steps'], 1):
            print(f"\n{i}. {step.get('name', 'Step')}")
            print(f"   Description: {step.get('description', 'N/A')}")
            print(f"   Type: {step.get('type', 'N/A')}")
            print(f"   Tools needed: {', '.join(step.get('tools_needed', []))}")
            if step.get('dependencies'):
                print(f"   Dependencies: {step.get('dependencies')}")
        print("="*60 + "\n")
        
        if not exec_res["validation"]["is_valid"]:
            print(f"  ⚠ Plan validation issues: {exec_res['validation']['issues']}")
        
        return "default"


class ImplementCode(AsyncNode):
    """Generate or modify code files."""
    
    async def prep_async(self, shared):
        plan = shared.get("plan", {})
        current_step = plan.get("current_step", 0)
        steps = plan.get("steps", [])
        
        if current_step < len(steps):
            step = steps[current_step]
        else:
            step = None
        
        return {
            "step": step,
            "current_step_num": current_step + 1,
            "total_steps": len(steps),
            "project_path": shared.get("context", {}).get("project_path", "."),
            "requirements": shared.get("requirements", {}),
            "previous_files": shared.get("implementation", {}).get("files_created", [])
        }
    
    async def exec_async(self, inputs):
        if not inputs["step"]:
            return {"error": "No step to implement"}
        
        step = inputs["step"]
        project_path = Path(inputs["project_path"])
        
        # Show what we're about to implement
        print(f"\n🔨 IMPLEMENTING STEP {inputs.get('current_step_num', 'N/A')}/{inputs.get('total_steps', '?')}:")
        print("="*60)
        print(f"   Name: {step.get('name', 'Unknown')}")
        print(f"   Description: {step.get('description', 'N/A')}")
        print(f"   Type: {step.get('type', 'N/A')}")
        print(f"   Tools: {', '.join(step.get('tools_needed', ['Read', 'Write']))}")
        print(f"   Timeout: 5 minutes")
        print("="*60)
        print("   Starting implementation...\n")
        
        prompt = f"""Implement the following step in the coding task:

Step: {step['name']}
Description: {step['description']}
Type: {step['type']}

Project Path: {project_path}
Previous files created: {inputs['previous_files']}

Requirements context:
{json.dumps(inputs['requirements'], indent=2)}

Please implement this step by creating or modifying the necessary files.
Use the appropriate tools (Read, Write, Bash) to complete the implementation.
Ensure the code is well-structured, follows best practices, and includes appropriate comments."""
        
        # Determine which tools are needed
        tools_needed = step.get("tools_needed", ["Read", "Write"])
        if "Bash" not in tools_needed and step['type'] == 'test':
            tools_needed.append("Bash")
        
        try:
            # Add timeout for tool operations
            import asyncio
            result = await asyncio.wait_for(
                call_claude_with_tools(
                    prompt,
                    allowed_tools=tools_needed,
                    working_dir=project_path,
                    permission_mode='bypassPermissions'
                ),
                timeout=300.0  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            print("⚠️ Implementation step timed out after 5 minutes")
            result = {"error": "Timeout during implementation", "text": "Operation timed out"}
        
        return result
    
    async def post_async(self, shared, prep_res, exec_res):
        if "error" in exec_res:
            shared["errors"] = shared.get("errors", []) + [exec_res["error"]]
            return "error"
        
        # Track implementation changes
        impl = shared.get("implementation", {
            "files_created": [],
            "files_modified": [],
            "tool_uses": []
        })
        
        # Parse tool uses to track file changes
        for tool_use in exec_res.get("tool_uses", []):
            impl["tool_uses"].append(tool_use)
            
            if tool_use["name"] == "Write":
                file_path = tool_use["input"].get("file_path", "")
                if file_path and file_path not in impl["files_created"]:
                    impl["files_created"].append(file_path)
        
        shared["implementation"] = impl
        
        # Update plan progress
        plan = shared.get("plan", {})
        plan["current_step"] = plan.get("current_step", 0) + 1
        shared["plan"] = plan
        
        shared["state"] = "implementing"
        
        print(f"\n✅ STEP COMPLETED: {plan['current_step']}/{len(plan.get('steps', []))}")
        if impl["files_created"]:
            print(f"   Files created so far: {len(impl['files_created'])}")
            for file in impl["files_created"][-3:]:  # Show last 3 files
                print(f"     - {file}")
        if exec_res.get("cost", 0) > 0:
            print(f"   Cost: ${exec_res['cost']:.4f}")
        print()
        
        return "default"


class TestImplementation(AsyncNode):
    """Test the generated code."""
    
    async def prep_async(self, shared):
        return {
            "project_path": shared.get("context", {}).get("project_path", "."),
            "files_created": shared.get("implementation", {}).get("files_created", []),
            "entry_points": shared.get("context", {}).get("entry_points", [])
        }
    
    async def exec_async(self, inputs):
        project_path = Path(inputs["project_path"])
        
        # Build test prompt
        test_commands = []
        
        # Check for Python files
        python_files = [f for f in inputs["files_created"] if f.endswith('.py')]
        if python_files:
            test_commands.append("python -m pytest -v")
            test_commands.append(f"python {python_files[0]} --help")
        
        # Check for JavaScript/TypeScript
        js_files = [f for f in inputs["files_created"] if f.endswith(('.js', '.ts'))]
        if js_files:
            test_commands.append("npm test")
            test_commands.append(f"node {js_files[0]}")
        
        prompt = f"""Test the implementation to ensure it works correctly.

Files created: {inputs['files_created']}
Project path: {project_path}

Suggested test commands:
{chr(10).join(f'- {cmd}' for cmd in test_commands)}

Please:
1. Check if the files are syntactically correct
2. Run any available tests
3. Try to execute the main entry points
4. Report any errors or issues found

Use the Bash tool to run commands and Read tool to check files as needed."""
        
        try:
            import asyncio
            result = await asyncio.wait_for(
                call_claude_with_tools(
                    prompt,
                    allowed_tools=["Read", "Bash"],
                    working_dir=project_path,
                    permission_mode='default'
                ),
                timeout=180.0  # 3 minute timeout for tests
            )
        except asyncio.TimeoutError:
            print("⚠️ Test step timed out after 3 minutes")
            result = {"error": "Timeout during testing", "text": "Test operation timed out"}
        
        return result
    
    async def post_async(self, shared, prep_res, exec_res):
        test_results = {
            "success": True,
            "errors": [],
            "output": exec_res.get("text", "")
        }
        
        # Check for error indicators in the output
        error_indicators = ["error", "failed", "exception", "traceback", "syntaxerror"]
        output_lower = test_results["output"].lower()
        
        for indicator in error_indicators:
            if indicator in output_lower:
                test_results["success"] = False
                break
        
        shared["test_results"] = test_results
        shared["state"] = "tested"
        
        if test_results["success"]:
            print("✓ Tests passed successfully")
        else:
            print("✗ Tests failed - may need refactoring")
            shared["errors"] = shared.get("errors", []) + ["Test failures detected"]
        
        return "default"


class RefactorCode(AsyncNode):
    """Improve code based on test results or requirements."""
    
    async def prep_async(self, shared):
        return {
            "project_path": shared.get("context", {}).get("project_path", "."),
            "test_results": shared.get("test_results", {}),
            "errors": shared.get("errors", []),
            "files_created": shared.get("implementation", {}).get("files_created", [])
        }
    
    async def exec_async(self, inputs):
        project_path = Path(inputs["project_path"])
        
        issues = []
        if not inputs["test_results"].get("success", True):
            issues.append("Test failures detected")
        issues.extend(inputs.get("errors", []))
        
        prompt = f"""Refactor and improve the code implementation.

Files to refactor: {inputs['files_created']}
Issues found: {issues}
Test output: {inputs['test_results'].get('output', 'No test output')}

Please:
1. Fix any errors or issues identified
2. Improve code quality and structure
3. Add better error handling
4. Ensure code follows best practices
5. Add or improve documentation/comments

Use Read to examine files, Write to modify them, and Bash to test changes."""
        
        try:
            import asyncio
            result = await asyncio.wait_for(
                call_claude_with_tools(
                    prompt,
                    allowed_tools=["Read", "Write", "Bash"],
                    working_dir=project_path,
                    permission_mode='bypassPermissions'
                ),
                timeout=240.0  # 4 minute timeout
            )
        except asyncio.TimeoutError:
            print("⚠️ Refactor step timed out after 4 minutes")
            result = {"error": "Timeout during refactoring", "text": "Refactor operation timed out"}
        
        return result
    
    async def post_async(self, shared, prep_res, exec_res):
        # Clear errors after refactoring
        shared["errors"] = []
        shared["state"] = "refactored"
        
        print("✓ Code refactored and improved")
        
        return "default"


class FinalizeProject(Node):
    """Complete the task and generate summary."""
    
    def prep(self, shared):
        return {
            "task": shared.get("task", ""),
            "implementation": shared.get("implementation", {}),
            "test_results": shared.get("test_results", {}),
            "history": shared.get("history", [])
        }
    
    def exec(self, inputs):
        summary = {
            "task": inputs["task"],
            "files_created": inputs["implementation"].get("files_created", []),
            "files_modified": inputs["implementation"].get("files_modified", []),
            "tests_passed": inputs["test_results"].get("success", False),
            "total_actions": len(inputs["history"]),
            "status": "completed"
        }
        
        return summary
    
    def post(self, shared, prep_res, exec_res):
        shared["summary"] = exec_res
        shared["state"] = "completed"
        
        print("\n" + "="*50)
        print("✓ Task Completed Successfully!")
        print("="*50)
        print(f"Task: {exec_res['task']}")
        print(f"Files created: {len(exec_res['files_created'])}")
        for file in exec_res['files_created']:
            print(f"  - {file}")
        print(f"Tests: {'✓ Passed' if exec_res['tests_passed'] else '✗ Failed'}")
        print(f"Total actions taken: {exec_res['total_actions']}")
        
        return None  # End the flow