import ast
import os
import glob

def is_tautology(node):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        attr = node.func.attr
        if attr == 'assertTrue' and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value is True:
            return True
        if attr == 'assertFalse' and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and node.args[0].value is False:
            return True
        if attr == 'assertEqual' and len(node.args) == 2:
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant) and node.args[0].value == node.args[1].value:
                return True
        if attr == 'assert_called': 
            return True
    return False

def check_test_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    bad_tests = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            has_assert = False
            only_tautologies = True
            
            for child in ast.walk(node):
                if isinstance(child, ast.Assert):
                    has_assert = True
                    only_tautologies = False
                
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    attr = child.func.attr
                    if attr.startswith('assert'):
                        has_assert = True
                        if not is_tautology(child):
                            only_tautologies = False
                            
                if isinstance(child, ast.With):
                    for item in child.items:
                        if isinstance(item.context_expr, ast.Call) and isinstance(item.context_expr.func, ast.Attribute):
                            if item.context_expr.func.attr == 'assertRaises':
                                has_assert = True
                                only_tautologies = False
                                break
            
            if not has_assert or (has_assert and only_tautologies):
                bad_tests.append((filepath, node.name, node.lineno))
                
    return bad_tests

all_bad = []
for filepath in glob.glob('tests/**/*.py', recursive=True):
    all_bad.extend(check_test_file(filepath))

for filepath, name, line in all_bad:
    print(f"{filepath}:{line} - {name} is garbage!")
if not all_bad:
    print("NO GARBAGE TESTS FOUND!")
