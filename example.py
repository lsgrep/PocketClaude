#!/usr/bin/env python3
"""Simple example of using Claude Code Subagent."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import anyio
from flow import create_simple_coding_flow


async def main():
    """Run a simple coding task."""
    
    # Initialize shared store with a simple task
    shared = {
        "task": "Create a simple HTML page with a greeting",
        "context": {
            "project_path": "./test-output",
            "existing_files": [],
            "dependencies": {},
            "constraints": []
        },
        "state": "initial",
        "history": [],
        "errors": []
    }
    
    # Create output directory if it doesn't exist
    os.makedirs("./test-output", exist_ok=True)
    
    print("🤖 Running Claude Code Subagent Example")
    print("="*50)
    print(f"Task: {shared['task']}")
    print(f"Output: {shared['context']['project_path']}")
    print("="*50 + "\n")
    
    # Create and run the simple flow
    flow = create_simple_coding_flow()
    
    try:
        await flow.run_async(shared)
        
        print("\n" + "="*50)
        print("✅ Task completed successfully!")
        
        if shared.get("summary"):
            summary = shared["summary"]
            print(f"Files created: {summary.get('files_created', [])}")
            
            # Show the created files
            if summary.get('files_created'):
                print("\n📄 Created files content:")
                for file_path in summary['files_created']:
                    full_path = os.path.join("./test-output", file_path)
                    if os.path.exists(full_path):
                        print(f"\n--- {file_path} ---")
                        with open(full_path, 'r') as f:
                            print(f.read())
                        print("---\n")
                        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    anyio.run(main)