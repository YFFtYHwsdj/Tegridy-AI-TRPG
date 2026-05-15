import ast
import os
import glob

def check_test_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    weak_tests = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            has_strong_assert = False
            for child in ast.walk(node):
                if isinstance(child, ast.Assert):
                    has_strong_assert = True
                
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    attr = child.func.attr
                    if attr in ('assert_called_once_with', 'assert_called_with', 'assert_not_called'):
                        has_strong_assert = True
                    elif attr.startswith('assert') and attr not in ('assert_called', 'assertTrue', 'assertFalse'):
                        if attr == 'assertEqual' and len(child.args) == 2:
                            if isinstance(child.args[0], ast.Constant) and isinstance(child.args[1], ast.Constant):
                                continue 
                        has_strong_assert = True
                    
                if isinstance(child, ast.With):
                    for item in child.items:
                        if isinstance(item.context_expr, ast.Call) and isinstance(item.context_expr.func, ast.Attribute):
                            if item.context_expr.func.attr == 'assertRaises':
                                has_strong_assert = True
                                break
            
            if not has_strong_assert:
                weak_tests.append((filepath, node.name, node.lineno))
                
    return weak_tests

all_weak = []
for filepath in glob.glob('tests/**/*.py', recursive=True):
    all_weak.extend(check_test_file(filepath))

if not all_weak:
    print("No weak tests found.")
else:
    for filepath, name, line in all_weak:
        print(f"{filepath}:{line} - {name} has NO strong assertions!")
