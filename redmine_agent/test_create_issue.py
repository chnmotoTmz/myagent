"""Test script to check if create_issue method exists in RedmineAgent."""

import importlib
import inspect
from app.core import RedmineAgent

# Force reload the module
importlib = importlib.reload(importlib)
core_module = importlib.import_module('app.core')
importlib.reload(core_module)

# Create an instance of RedmineAgent
agent = RedmineAgent("http://example.com", "dummy_key")

# Check if create_issue exists
methods = [name for name, method in inspect.getmembers(agent, predicate=inspect.ismethod)]
print("Available methods in RedmineAgent:")
for method in sorted(methods):
    print(f"  - {method}")

# Specifically check for create_issue
if hasattr(agent, 'create_issue'):
    print("\nThe create_issue method EXISTS in RedmineAgent")
else:
    print("\nThe create_issue method DOES NOT EXIST in RedmineAgent")
    
    # Let's check the source file to see if it exists there
    import inspect
    import os
    
    source_file = inspect.getsourcefile(RedmineAgent)
    print(f"\nSource file: {source_file}")
    
    # Check if the string 'create_issue' exists in the source file
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'def create_issue' in content:
            print("But 'def create_issue' does exist in the source file!")
            
            # Get line numbers for analysis
            for i, line in enumerate(content.splitlines()):
                if 'def create_issue' in line:
                    start_line = i
                    print(f"Found at line {start_line + 1}")
                    break
        else:
            print("'def create_issue' is not in the source file either!")
