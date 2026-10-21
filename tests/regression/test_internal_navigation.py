from pathlib import Path
import ast
import sys
from types import SimpleNamespace,ModuleType
from unittest.mock import Mock
import pytest
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[2]


def method(name):
    path=ROOT/'allma_model/ui/webview_bridge.py'
    tree=ast.parse(path.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WebViewBridge')
    node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
    env={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(path),'exec'),env)
    return env[name]


@pytest.mark.parametrize('sdk',[24,32,33,36])
def test_native_back_connects_gesture_and_legacy_key_to_one_router(monkeypatch,sdk):
    jnius=ModuleType('jnius');jnius.PythonJavaClass=object
    jnius.java_method=lambda signature:lambda fn:fn
    jnius.autoclass=lambda name:SimpleNamespace(SDK_INT=sdk)
    monkeypatch.setitem(sys.modules,'jnius',jnius)
    bridge=SimpleNamespace(webview=Mock(),execute_js=Mock())
    activity=Mock()
    method('_install_back_handler')(bridge,activity)
    assert bridge._back_key.onKey(None,24,SimpleNamespace(getAction=lambda:1)) is False
    assert bridge._back_key.onKey(None,4,SimpleNamespace(getAction=lambda:0)) is True
    bridge.execute_js.assert_not_called()
    bridge._back_key.onKey(None,4,SimpleNamespace(getAction=lambda:1))
    assert bridge.execute_js.call_count==1
    if sdk>=33:
        activity.getOnBackInvokedDispatcher.return_value.registerOnBackInvokedCallback.assert_called_once_with(0,bridge._back_callback)
        bridge._back_callback.onBackInvoked()
        assert bridge.execute_js.call_count==2
    else:activity.getOnBackInvokedDispatcher.assert_not_called()


class Document(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.screens=[];self.options=[];self.popups=[];self.select=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        if 'data-screen' in attrs:self.screens.append(attrs['data-screen'])
        if tag=='select':self.select=attrs.get('id')
        if tag=='option' and self.select=='benchmark-profile':self.options.append(attrs.get('value'))
        if set(attrs.get('class','').split())&{'sidebar-panel','modal-backdrop'}:self.popups.append(attrs)


def test_sidebar_destinations_are_internal_pages_and_all_benchmark_choices_remain():
    doc=Document();doc.feed((ROOT/'assets/web/index.html').read_text())
    assert len(doc.ids)==len(set(doc.ids))
    assert set(doc.screens)=={'settings','memory','dream','voice','profile','diagnostics'}
    assert not doc.popups
    assert {'model-choice','backup-auto','notification-toggle','dream-mode-toggle','benchmark-start','decider-toggle','voice-mic-btn'}<=set(doc.ids)
    assert len(doc.options)==len(set(doc.options))
    tree=ast.parse((ROOT/'allma_model/ui/webview_bridge.py').read_text())
    allowed=next(node.comparators[0] for node in ast.walk(tree) if isinstance(node,ast.Compare)
                 and isinstance(node.left,ast.Name) and node.left.id=='profile'
                 and isinstance(node.ops[0],ast.NotIn) and isinstance(node.comparators[0],ast.Tuple))
    assert set(doc.options)==set(ast.literal_eval(allowed))


def test_offline_android_bundle_loads_navigation_after_legacy_callbacks():
    source=(ROOT/'allma_model/ui/webview_bridge.py').read_text()
    assert source.index("'navigation.js'")>source.index("'script_v24.js'")
    from allma_model.ui.web_assets import inline_stylesheets
    root=ROOT/'assets/web'
    html=inline_stylesheets((root/'index.html').read_text(),root)
    assert 'internal pages, one surface' in html
    assert 'href="screens.css"' not in html
