"""Task decomposition utilities for breaking down complex coding tasks."""

from typing import List, Dict, Any, Optional
import json
from utils.claude_interface import call_claude_code, parse_yaml_response
from claude_code_sdk import ClaudeCodeOptions


async def decompose_task(
    task: str, 
    context: Optional[Dict[str, Any]] = None,
    max_steps: int = 10
) -> List[Dict[str, Any]]:
    """
    Decompose a high-level task into actionable steps.
    
    Args:
        task: The high-level task description
        context: Optional context about the project
        max_steps: Maximum number of steps to generate
        
    Returns:
        List of step dictionaries
    """
    context_str = ""
    if context:
        context_str = f"""
### Project Context:
- Project path: {context.get('project_path', 'Not specified')}
- Existing files: {len(context.get('existing_files', []))} files
- File types: {context.get('file_types', {})}
- Dependencies: {context.get('dependencies', {})}
"""
    
    prompt = f"""Break down the following coding task into clear, actionable steps.

### Task:
{task}
{context_str}

### Instructions:
- Create a step-by-step plan with no more than {max_steps} steps
- Each step should be specific and achievable
- Consider dependencies between steps
- Include testing and validation steps

Output in YAML format:
```yaml
steps:
  - id: 1
    name: "Step name"
    description: "What to do"
    type: "plan|implement|test|refactor"
    dependencies: []  # IDs of steps this depends on
    tools_needed: []  # Claude Code tools needed (Read, Write, Bash, etc.)
  - id: 2
    name: "Next step"
    description: "Details"
    type: "implement"
    dependencies: [1]
    tools_needed: ["Write"]
```"""
    
    options = ClaudeCodeOptions(
        system_prompt="You are an expert software architect who creates clear, actionable development plans.",
        max_turns=1
    )
    
    try:
        result = await parse_yaml_response(prompt, options)
        
        if isinstance(result, dict):
            if "error" in result:
                # Fallback to a simple default plan
                print(f"Failed to parse plan, using default: {result.get('error')}")
                return create_default_plan(task)
            
            # Extract steps from the result
            steps = result.get("steps", [])
            if isinstance(steps, list):
                return steps
        
        # If we get here, something unexpected happened
        print("Unexpected response format, using default plan")
        return create_default_plan(task)
    
    except Exception as e:
        print(f"Error decomposing task: {e}")
        return create_default_plan(task)


def create_default_plan(task: str) -> List[Dict[str, Any]]:
    """
    Create a default plan when decomposition fails.
    
    Args:
        task: The task description
        
    Returns:
        List of default steps
    """
    return [
        {
            "id": 1,
            "name": "Understand Requirements",
            "description": f"Analyze and understand: {task}",
            "type": "plan",
            "dependencies": [],
            "tools_needed": []
        },
        {
            "id": 2,
            "name": "Design Solution",
            "description": "Create high-level design and architecture",
            "type": "plan",
            "dependencies": [1],
            "tools_needed": []
        },
        {
            "id": 3,
            "name": "Implement Core Features",
            "description": "Write the main implementation code",
            "type": "implement",
            "dependencies": [2],
            "tools_needed": ["Write", "Read"]
        },
        {
            "id": 4,
            "name": "Test Implementation",
            "description": "Test the code and fix any issues",
            "type": "test",
            "dependencies": [3],
            "tools_needed": ["Bash", "Read"]
        },
        {
            "id": 5,
            "name": "Refine and Document",
            "description": "Improve code quality and add documentation",
            "type": "refactor",
            "dependencies": [4],
            "tools_needed": ["Write", "Read"]
        }
    ]


async def prioritize_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prioritize steps based on dependencies and importance.
    
    Args:
        steps: List of step dictionaries
        
    Returns:
        Prioritized list of steps
    """
    # Build dependency graph
    dep_graph = {}
    for step in steps:
        step_id = step["id"]
        deps = step.get("dependencies", [])
        dep_graph[step_id] = deps
    
    # Topological sort
    sorted_steps = []
    visited = set()
    
    def visit(step_id):
        if step_id in visited:
            return
        visited.add(step_id)
        
        for dep in dep_graph.get(step_id, []):
            visit(dep)
        
        step = next((s for s in steps if s["id"] == step_id), None)
        if step and step not in sorted_steps:
            sorted_steps.append(step)
    
    for step in steps:
        visit(step["id"])
    
    return sorted_steps


async def estimate_complexity(task: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Estimate the complexity of a task based on its steps.
    
    Args:
        task: The task description
        steps: List of steps
        
    Returns:
        Complexity estimation
    """
    complexity = {
        "overall": "medium",
        "estimated_time": "unknown",
        "difficulty_factors": [],
        "risk_factors": []
    }
    
    # Simple heuristics for complexity
    num_steps = len(steps)
    num_impl_steps = sum(1 for s in steps if s.get("type") == "implement")
    num_test_steps = sum(1 for s in steps if s.get("type") == "test")
    
    if num_steps <= 3:
        complexity["overall"] = "low"
        complexity["estimated_time"] = "< 30 minutes"
    elif num_steps <= 7:
        complexity["overall"] = "medium"
        complexity["estimated_time"] = "30-60 minutes"
    else:
        complexity["overall"] = "high"
        complexity["estimated_time"] = "> 1 hour"
    
    # Check for complexity indicators
    if num_impl_steps > 5:
        complexity["difficulty_factors"].append("Multiple implementation steps")
    
    if num_test_steps == 0:
        complexity["risk_factors"].append("No testing steps defined")
    
    # Check for certain keywords that indicate complexity
    complex_keywords = ["architecture", "refactor", "migrate", "optimize", "scale"]
    for keyword in complex_keywords:
        if keyword.lower() in task.lower():
            complexity["difficulty_factors"].append(f"Involves {keyword}")
    
    return complexity


def validate_plan(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a plan for completeness and consistency.
    
    Args:
        steps: List of steps to validate
        
    Returns:
        Validation results
    """
    validation = {
        "is_valid": True,
        "issues": [],
        "warnings": []
    }
    
    if not steps:
        validation["is_valid"] = False
        validation["issues"].append("No steps defined")
        return validation
    
    # Check for required fields
    for i, step in enumerate(steps):
        if "id" not in step:
            validation["issues"].append(f"Step {i} missing 'id' field")
            validation["is_valid"] = False
        
        if "name" not in step:
            validation["issues"].append(f"Step {i} missing 'name' field")
            validation["is_valid"] = False
    
    # Check for dependency consistency
    all_ids = {step.get("id") for step in steps}
    for step in steps:
        for dep in step.get("dependencies", []):
            if dep not in all_ids:
                validation["issues"].append(f"Step {step.get('id')} has invalid dependency: {dep}")
                validation["is_valid"] = False
    
    # Check for circular dependencies
    def has_cycle(graph):
        visited = set()
        rec_stack = set()
        
        def visit(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if visit(neighbor):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if visit(node):
                return True
        return False
    
    dep_graph = {step["id"]: step.get("dependencies", []) for step in steps if "id" in step}
    if has_cycle(dep_graph):
        validation["issues"].append("Circular dependency detected")
        validation["is_valid"] = False
    
    # Warnings
    if not any(step.get("type") == "test" for step in steps):
        validation["warnings"].append("No testing steps defined")
    
    if len(steps) > 15:
        validation["warnings"].append("Plan has many steps, consider breaking into sub-tasks")
    
    return validation


# Test the decomposer
if __name__ == "__main__":
    import anyio
    
    async def test():
        task = "Create a REST API for a todo list application with CRUD operations"
        
        print(f"Decomposing task: {task}\n")
        steps = await decompose_task(task)
        
        print("Generated steps:")
        for step in steps:
            print(f"  {step['id']}. {step['name']}: {step['description']}")
        
        print("\nValidating plan...")
        validation = validate_plan(steps)
        print(f"Valid: {validation['is_valid']}")
        if validation['issues']:
            print(f"Issues: {validation['issues']}")
        if validation['warnings']:
            print(f"Warnings: {validation['warnings']}")
        
        print("\nEstimating complexity...")
        complexity = await estimate_complexity(task, steps)
        print(f"Complexity: {complexity}")
    
    anyio.run(test)