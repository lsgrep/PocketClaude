"""Code analysis utilities for understanding project structure."""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import ast
import re


def analyze_project(project_path: str) -> Dict[str, Any]:
    """
    Analyze a project directory to understand its structure.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Dictionary containing project analysis
    """
    path = Path(project_path)
    if not path.exists():
        return {"error": f"Path {project_path} does not exist"}
    
    analysis = {
        "path": str(path.absolute()),
        "structure": {},
        "file_types": {},
        "dependencies": {},
        "entry_points": [],
        "total_files": 0,
        "total_lines": 0
    }
    
    # Analyze directory structure
    for root, dirs, files in os.walk(path):
        # Skip hidden and common ignore directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
        
        rel_root = Path(root).relative_to(path)
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = Path(root) / file
            rel_path = file_path.relative_to(path)
            ext = file_path.suffix
            
            # Count file types
            analysis["file_types"][ext] = analysis["file_types"].get(ext, 0) + 1
            analysis["total_files"] += 1
            
            # Count lines
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = len(f.readlines())
                    analysis["total_lines"] += lines
            except:
                pass
            
            # Check for entry points
            if file in ['main.py', 'app.py', 'index.js', 'main.js', 'index.ts', 'main.ts']:
                analysis["entry_points"].append(str(rel_path))
            
            # Check for dependency files
            if file in ['requirements.txt', 'package.json', 'Cargo.toml', 'go.mod', 'pom.xml']:
                analysis["dependencies"][file] = str(rel_path)
    
    # Build directory tree structure
    analysis["structure"] = build_tree_structure(path)
    
    return analysis


def build_tree_structure(path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
    """
    Build a tree structure of the directory.
    
    Args:
        path: Path to analyze
        max_depth: Maximum depth to traverse
        current_depth: Current traversal depth
        
    Returns:
        Dictionary representing the tree structure
    """
    if current_depth >= max_depth:
        return {"...": "max_depth_reached"}
    
    tree = {}
    
    try:
        for item in sorted(path.iterdir()):
            if item.name.startswith('.'):
                continue
                
            if item.is_dir():
                if item.name not in ['node_modules', '__pycache__', 'venv', 'env', '.git']:
                    tree[item.name + "/"] = build_tree_structure(item, max_depth, current_depth + 1)
            else:
                tree[item.name] = "file"
    except PermissionError:
        tree["<permission_denied>"] = None
    
    return tree


def analyze_python_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a Python file for its structure.
    
    Args:
        file_path: Path to the Python file
        
    Returns:
        Dictionary containing file analysis
    """
    analysis = {
        "classes": [],
        "functions": [],
        "imports": [],
        "docstring": None
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Get module docstring
        if ast.get_docstring(tree):
            analysis["docstring"] = ast.get_docstring(tree)
        
        for node in ast.walk(tree):
            # Find classes
            if isinstance(node, ast.ClassDef):
                analysis["classes"].append({
                    "name": node.name,
                    "methods": [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                    "docstring": ast.get_docstring(node)
                })
            
            # Find top-level functions
            elif isinstance(node, ast.FunctionDef):
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    analysis["functions"].append({
                        "name": node.name,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node)
                    })
            
            # Find imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    analysis["imports"].append(f"{module}.{alias.name}")
    
    except Exception as e:
        analysis["error"] = str(e)
    
    return analysis


def find_similar_files(project_path: str, reference_file: str) -> List[str]:
    """
    Find files similar to a reference file in structure or naming.
    
    Args:
        project_path: Path to the project
        reference_file: Name or path of reference file
        
    Returns:
        List of similar file paths
    """
    path = Path(project_path)
    ref_path = Path(reference_file)
    ref_name = ref_path.stem
    ref_ext = ref_path.suffix
    
    similar_files = []
    
    for file_path in path.rglob(f"*{ref_ext}"):
        if file_path.is_file():
            # Check for similar naming patterns
            if (ref_name.lower() in file_path.stem.lower() or
                file_path.stem.lower() in ref_name.lower()):
                similar_files.append(str(file_path.relative_to(path)))
    
    return similar_files


def extract_todo_comments(project_path: str) -> List[Dict[str, str]]:
    """
    Extract TODO/FIXME comments from code files.
    
    Args:
        project_path: Path to the project
        
    Returns:
        List of TODO items with file location
    """
    path = Path(project_path)
    todo_pattern = re.compile(r'#\s*(TODO|FIXME|HACK|NOTE|XXX):\s*(.+)', re.IGNORECASE)
    todos = []
    
    for file_path in path.rglob('*'):
        if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        match = todo_pattern.search(line)
                        if match:
                            todos.append({
                                "file": str(file_path.relative_to(path)),
                                "line": line_num,
                                "type": match.group(1).upper(),
                                "message": match.group(2).strip()
                            })
            except:
                pass
    
    return todos


# Test the analyzer
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        project_path = "."
    
    print(f"Analyzing project: {project_path}\n")
    analysis = analyze_project(project_path)
    
    print("Project Structure:")
    print(json.dumps(analysis["structure"], indent=2))
    
    print(f"\nTotal files: {analysis['total_files']}")
    print(f"Total lines: {analysis['total_lines']}")
    print(f"File types: {analysis['file_types']}")
    print(f"Entry points: {analysis['entry_points']}")
    print(f"Dependencies: {analysis['dependencies']}")