"""A Kivy Clock callback is not Android's WebView UI thread."""
import ast
from pathlib import Path
from types import SimpleNamespace, ModuleType
import sys


def test_benchmark_close_dispatches_webview_work_to_android_thread(monkeypatch):
    source = Path(__file__).resolve().parents[2]/'allma_model/ui/webview_bridge.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WebViewBridge')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'execute_js')
    env = {}
    evaluator = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_evaluate_js')
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method, evaluator], type_ignores=[])), str(source), 'exec'), env)
    ui_queue, calls = [], []
    runnable = ModuleType('android.runnable')
    runnable.run_on_ui_thread = lambda fn: lambda: ui_queue.append(fn)
    monkeypatch.setitem(sys.modules, 'android.runnable', runnable)
    bridge = SimpleNamespace(webview=SimpleNamespace(evaluateJavascript=lambda code, callback: calls.append(code)))
    bridge._closed = False
    bridge._evaluate_js = lambda code, callback: env['_evaluate_js'](bridge, code, callback)
    bridge.execute_js = lambda code: env['execute_js'](bridge, code)
    receiver = SimpleNamespace(bridge=bridge)
    closes = [n for n in ast.walk(tree) if isinstance(n, ast.Lambda)
              and 'benchmarkUI.close' in ast.unparse(n.body)]
    assert len(closes) == 2  # Completion and error paths.
    for callback in closes:
        cb = eval(compile(ast.Expression(callback), str(source), 'eval'), {'self': receiver})
        cb(0)  # Simulate the callback running on SDL/Kivy, outside Android UI.
    assert calls == []
    assert len(ui_queue) == 2
    for job in ui_queue:
        job()
    assert len(calls) == 2 and all('benchmarkUI.close' in code for code in calls)

    # A scheduled callback must not touch a destroyed WebView.
    bridge.execute_js('window.benchmarkUI.close()')
    bridge._closed = True
    ui_queue[-1]()
    assert len(calls) == 2
