"""Flow orchestration for Claude Code Subagent."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from pocketflow import AsyncFlow
from nodes import (
    UnderstandRequirements,
    AnalyzeContext,
    DecideAction,
    CreatePlan,
    ImplementCode,
    TestImplementation,
    RefactorCode,
    FinalizeProject
)
from utils.logger import AgentLogger, ProgressReporter


def create_coding_agent_flow():
    """Create and configure the coding agent flow."""
    
    # Create node instances with retry configuration
    understand = UnderstandRequirements(max_retries=2, wait=1)
    analyze = AnalyzeContext(max_retries=2)
    decide = DecideAction(max_retries=3, wait=2)
    plan = CreatePlan(max_retries=2, wait=1)
    implement = ImplementCode(max_retries=3, wait=2)
    test = TestImplementation(max_retries=2, wait=1)
    refactor = RefactorCode(max_retries=2, wait=1)
    finalize = FinalizeProject()
    
    # Define the flow connections
    # Start with understanding requirements
    understand >> analyze >> decide
    
    # Decision node branches to different actions
    decide - "plan" >> plan
    decide - "implement" >> implement
    decide - "test" >> test
    decide - "refactor" >> refactor
    decide - "complete" >> finalize
    
    # After each action, loop back to decide (except finalize)
    plan >> decide
    implement >> decide
    test >> decide
    refactor >> decide
    
    # Handle error cases
    implement - "error" >> refactor
    
    # Create the flow starting with understanding requirements
    flow = AsyncFlow(start=understand)
    
    return flow


def create_simple_coding_flow():
    """Create a simplified linear flow for straightforward tasks."""
    
    # Create nodes
    understand = UnderstandRequirements()
    analyze = AnalyzeContext()
    plan = CreatePlan()
    implement = ImplementCode()
    test = TestImplementation()
    finalize = FinalizeProject()
    
    # Simple linear flow
    understand >> analyze >> plan >> implement >> test >> finalize
    
    flow = AsyncFlow(start=understand)
    
    return flow


def create_iterative_coding_flow():
    """Create an iterative flow with multiple implementation cycles."""
    
    # Create nodes with higher retry counts for robustness
    decide = DecideAction(max_retries=5, wait=1)
    plan = CreatePlan(max_retries=3)
    implement = ImplementCode(max_retries=5, wait=2)
    test = TestImplementation(max_retries=3)
    refactor = RefactorCode(max_retries=3)
    finalize = FinalizeProject()
    
    # Start with decision making
    # This flow assumes requirements are already in shared store
    
    # Decision branches
    decide - "plan" >> plan
    decide - "implement" >> implement
    decide - "test" >> test
    decide - "refactor" >> refactor
    decide - "complete" >> finalize
    
    # All actions loop back to decide for next iteration
    plan >> decide
    implement >> decide
    test >> decide
    refactor >> decide
    
    flow = AsyncFlow(start=decide)
    
    return flow


class CodingAgentFlow(AsyncFlow):
    """Main coding agent flow with built-in state management and logging."""
    
    def __init__(self, start=None, enable_logging=True):
        """Initialize with optional logging."""
        super().__init__(start)
        self.enable_logging = enable_logging
        self.logger = None
        
    async def prep_async(self, shared):
        """Initialize the shared store with default values."""
        
        # Initialize logger
        if self.enable_logging:
            self.logger = AgentLogger()
            shared["logger"] = self.logger
            self.logger.log_event("session_started", {
                "task": shared.get("task", "Unknown task"),
                "project_path": shared.get("context", {}).get("project_path", ".")
            })
        
        # Set default values if not present
        if "state" not in shared:
            shared["state"] = "initial"
        
        if "context" not in shared:
            shared["context"] = {
                "project_path": os.getcwd(),
                "existing_files": [],
                "dependencies": {},
                "constraints": []
            }
        
        if "implementation" not in shared:
            shared["implementation"] = {
                "files_created": [],
                "files_modified": [],
                "tool_uses": [],
                "errors": []
            }
        
        if "history" not in shared:
            shared["history"] = []
        
        if "max_iterations" not in shared:
            shared["max_iterations"] = 10
        
        # Track iterations to prevent infinite loops
        shared["current_iteration"] = 0
        
        return None
    
    async def post_async(self, shared, prep_res, exec_res):
        """Finalize the flow and clean up."""
        
        # Log final state
        print("\n" + "="*50)
        print("Coding Agent Flow Complete")
        print("="*50)
        print(f"Final state: {shared.get('state', 'unknown')}")
        print(f"Total iterations: {len(shared.get('history', []))}")
        
        if shared.get("summary"):
            summary = shared["summary"]
            print(f"Files created: {len(summary.get('files_created', []))}")
            print(f"Status: {summary.get('status', 'unknown')}")
        
        # Generate and show shareable report
        if self.logger:
            self.logger.log_event("session_completed", {
                "final_state": shared.get('state', 'unknown'),
                "files_created": shared.get("summary", {}).get('files_created', []),
                "total_iterations": len(shared.get('history', []))
            })
            
            report = self.logger.generate_markdown_report()
            shareable = self.logger.get_shareable_link()
            print(shareable)
        
        return exec_res


def create_advanced_coding_flow():
    """Create the advanced coding agent flow with full capabilities."""
    
    # Create all nodes
    understand = UnderstandRequirements(max_retries=2)
    analyze = AnalyzeContext(max_retries=2)
    decide = DecideAction(max_retries=3)
    plan = CreatePlan(max_retries=2)
    implement = ImplementCode(max_retries=5, wait=2)
    test = TestImplementation(max_retries=3)
    refactor = RefactorCode(max_retries=3)
    finalize = FinalizeProject()
    
    # Build the complete flow
    understand >> analyze >> decide
    
    # Decision tree
    decide - "plan" >> plan
    decide - "implement" >> implement  
    decide - "test" >> test
    decide - "refactor" >> refactor
    decide - "complete" >> finalize
    
    # Loops back to decision
    plan >> decide
    implement >> decide
    test >> decide
    refactor >> decide
    
    # Error handling
    implement - "error" >> refactor
    
    # Create custom flow class
    flow = CodingAgentFlow(start=understand)
    
    return flow


# Helper function to create flow based on complexity
def create_flow_for_task(task_complexity: str = "medium"):
    """
    Create appropriate flow based on task complexity.
    
    Args:
        task_complexity: "simple", "medium", or "complex"
        
    Returns:
        Configured AsyncFlow instance
    """
    if task_complexity == "simple":
        return create_simple_coding_flow()
    elif task_complexity == "complex":
        return create_advanced_coding_flow()
    else:  # medium
        return create_coding_agent_flow()


if __name__ == "__main__":
    # Example: Create a flow
    flow = create_coding_agent_flow()
    print("Coding agent flow created successfully!")
    print("Use flow.run_async(shared) to execute the flow")