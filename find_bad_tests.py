import ast
import os
import glob

def check_test_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    bad_tests = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            has_assert = False
            has_with_raises = False
            for child in ast.walk(node):
                if isinstance(child, ast.Assert):
                    has_assert = True
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if child.func.attr.startswith('assert'):
                        has_assert = True
                if isinstance(child, ast.With):
                    for item in child.items:
                        if isinstance(item.context_expr, ast.Call) and isinstance(item.context_expr.func, ast.Attribute):
                            if item.context_expr.func.attr == 'assertRaises':
                                has_assert = True
                                break
            if not has_assert:
                bad_tests.append((filepath, node.name, node.lineno))
                
    return bad_tests

all_bad = []
for filepath in glob.glob('tests/**/*.py', recursive=True):
    all_bad.extend(check_test_file(filepath))

if not all_bad:
    print("No tests without assertions found.")
else:
    for filepath, name, line in all_bad:
        print(f"{filepath}:{line} - {name} has NO assertions!")
