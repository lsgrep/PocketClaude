"""Main entry point for Claude Code Subagent."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import anyio
import argparse
from pathlib import Path
from flow import create_coding_agent_flow, create_flow_for_task


async def run_coding_agent(task: str, project_path: str = ".", complexity: str = "medium"):
    """
    Run the coding agent with a given task.
    
    Args:
        task: The coding task to accomplish
        project_path: Path to the project directory
        complexity: Task complexity ("simple", "medium", "complex")
    """
    print("="*60)
    print("🤖 Claude Code Subagent - Agentic Coding Assistant")
    print("="*60)
    print(f"Task: {task}")
    print(f"Project Path: {project_path}")
    print(f"Complexity: {complexity}")
    print("="*60 + "\n")
    
    # Create project directory if it doesn't exist
    os.makedirs(project_path, exist_ok=True)
    
    # Initialize shared store
    shared = {
        "task": task,
        "context": {
            "project_path": project_path,
            "existing_files": [],
            "dependencies": {},
            "constraints": []
        },
        "state": "initial",
        "history": [],
        "errors": []
    }
    
    # Create appropriate flow based on complexity
    flow = create_flow_for_task(complexity)
    
    try:
        # Run the flow
        await flow.run_async(shared)
        
        # Display results
        if shared.get("summary"):
            print("\n" + "="*60)
            print("✨ Task Completed Successfully!")
            print("="*60)
            summary = shared["summary"]
            
            if summary.get("files_created"):
                print("\n📁 Files Created:")
                for file in summary["files_created"]:
                    print(f"  • {file}")
            
            if summary.get("files_modified"):
                print("\n✏️ Files Modified:")
                for file in summary["files_modified"]:
                    print(f"  • {file}")
            
            print(f"\n📊 Total Actions: {summary.get('total_actions', 0)}")
            print(f"✅ Tests: {'Passed' if summary.get('tests_passed') else 'Failed or Not Run'}")
        else:
            print("\n⚠️ Task completed but no summary generated")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nDebug Information:")
        print(f"Final State: {shared.get('state', 'unknown')}")
        print(f"Errors: {shared.get('errors', [])}")
        raise


async def interactive_mode():
    """Run the agent in interactive mode."""
    print("="*60)
    print("🤖 Claude Code Subagent - Interactive Mode")
    print("="*60)
    print("Enter your coding task (or 'quit' to exit)")
    print("="*60 + "\n")
    
    while True:
        task = input("Task> ").strip()
        
        if task.lower() in ['quit', 'exit', 'q']:
            print("Goodbye! 👋")
            break
        
        if not task:
            print("Please enter a task or 'quit' to exit")
            continue
        
        # Ask for project path
        project_path = input("Project path (default: current directory): ").strip() or "."
        
        # Ask for complexity
        complexity = input("Complexity [simple/medium/complex] (default: medium): ").strip() or "medium"
        
        if complexity not in ["simple", "medium", "complex"]:
            complexity = "medium"
        
        try:
            await run_coding_agent(task, project_path, complexity)
        except Exception as e:
            print(f"\n❌ Task failed: {e}")
        
        print("\n" + "="*60 + "\n")


async def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Claude Code Subagent - Automated coding assistant using PocketFlow and Claude Code SDK"
    )
    
    parser.add_argument(
        "task",
        nargs="?",
        help="The coding task to accomplish"
    )
    
    parser.add_argument(
        "-p", "--path",
        default=".",
        help="Project path (default: current directory)"
    )
    
    parser.add_argument(
        "-c", "--complexity",
        choices=["simple", "medium", "complex"],
        default="medium",
        help="Task complexity level (default: medium)"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode"
    )
    
    args = parser.parse_args()
    
    if args.interactive or not args.task:
        await interactive_mode()
    else:
        await run_coding_agent(args.task, args.path, args.complexity)


# Example tasks for demonstration
EXAMPLE_TASKS = {
    "simple": "Create a Python script that prints 'Hello, World!'",
    
    "medium": "Create a todo list CLI application in Python with add, remove, and list commands",
    
    "complex": "Build a REST API for a note-taking app with CRUD operations, using FastAPI and SQLite"
}


def print_examples():
    """Print example tasks."""
    print("\n📚 Example Tasks:")
    print("="*60)
    for complexity, task in EXAMPLE_TASKS.items():
        print(f"\n{complexity.upper()}:")
        print(f"  {task}")
    print("="*60)


if __name__ == "__main__":
    # Check if running with --examples flag
    if len(sys.argv) > 1 and sys.argv[1] == "--examples":
        print_examples()
    else:
        anyio.run(main)