"""Static inventory: reachability is evidence, not proof that a module is unused."""
import ast
import hashlib
import json
from pathlib import Path


def audit(root):
    package = root / 'allma_model'
    files = {'.'.join(p.relative_to(root).with_suffix('').parts).removesuffix('.__init__'): p
             for p in package.rglob('*.py') if 'tests' not in p.parts and '__pycache__' not in p.parts
             and not p.name.startswith(('test_', 'demo_', 'beta_test_'))
             and p.name not in {'run_tests.py', 'complete_test.py', 'interactive_allma.py', 'performance_test.py', 'performance_profiler.py'}}
    graph = {name: set() for name in files}
    errors, missing, bodies = [], [], {}
    for name, path in files.items():
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeError) as error:
            errors.append({'file': str(path), 'error': str(error)})
            continue
        base = name.split('.') if path.name == '__init__.py' else name.split('.')[:-1]
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                if node.level:
                    module = '.'.join(base[:len(base) - node.level + 1] + ([module] if module else []))
                targets = [module] + [module + '.' + alias.name for alias in node.names]
                if module.startswith('allma_model') and module not in files:
                    # A namespace folder is a valid import base even without __init__.py.
                    folder = root.joinpath(*module.split('.'))
                    if not folder.is_dir():
                        missing.append({'file': str(path), 'line': node.lineno, 'module': module})
            for target in targets:
                if target in files:
                    graph[name].add(target)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno - node.lineno > 12:
                body = node.body[:]
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                    body = body[1:]
                digest = hashlib.sha256(ast.dump(ast.Module(body=body, type_ignores=[]), include_attributes=False).encode()).hexdigest()
                bodies.setdefault(digest, []).append({'file': str(path), 'line': node.lineno, 'function': node.name})
    roots = {'allma_model.core.allma_core', 'allma_model.ui.app_entry', 'allma_model.ui.webview_bridge'}
    seen, todo = set(), list(roots)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo.extend(graph.get(name, set()) - seen)
    return {'scope': 'Python files eligible for the embedded app payload, excluding tests and demos. Static imports only; dynamic imports, standalone tools and alternate entry points may be absent from reachability.',
            'module_count': len(files), 'reachable_from_main_roots': len(seen & files.keys()),
            'syntax_errors': errors, 'missing_local_import_bases': missing,
            'missing_imports_on_main_paths': [item for item in missing if '.'.join(
                Path(item['file']).relative_to(root).with_suffix('').parts) in seen],
            'outside_main_static_graph': sorted(set(files) - seen),
            'identical_long_function_bodies': [group for group in bodies.values() if len(group) > 1],
            'imports': {key: sorted(value) for key, value in graph.items()}}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = audit(Path(__file__).resolve().parents[1])
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k in ('module_count', 'reachable_from_main_roots', 'syntax_errors', 'missing_local_import_bases')}, ensure_ascii=False, indent=2))
