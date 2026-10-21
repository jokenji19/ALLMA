"""Exercise actual startup callbacks without creating a native Kivy window."""
import ast
from pathlib import Path
from threading import Event, Thread, get_ident
from types import SimpleNamespace, MethodType
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]


def methods(core_factory):
    path=ROOT/'allma_model/ui/chat_view.py'
    tree=ast.parse(path.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ChatView')
    nodes=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('_load_core','_accept_core','cancel_startup')]
    queued=[]
    namespace={'ALLMACore':core_factory,'Clock':SimpleNamespace(schedule_once=lambda fn:queued.append(fn)), 'Thread':Thread}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return namespace,queued


def test_model_initialization_does_not_block_ui_and_handoff_is_scheduled():
    entered,release=Event(),Event()
    ids=[]
    core=Mock(_llm_ready=True)
    def factory(**kwargs):
        ids.append(get_ident());entered.set();assert release.wait(2)
        return core
    ns,queued=methods(factory)
    view=SimpleNamespace(_startup_cancelled=Event(),_accept_core=Mock(_llm_ready=True),intro=Mock())
    worker=Thread(target=ns['_load_core'],args=(view,'db','models',True))
    try:
        worker.start();assert entered.wait(2)
        assert worker.is_alive() and ids[0]!=get_ident()
        view._accept_core.assert_not_called()
        release.set();worker.join(2)
        assert len(queued)==2
        view._accept_core.assert_not_called()
        queued[0](0)
        view.intro.set_progress.assert_called_once_with(60)
        queued[1](0)
        view._accept_core.assert_called_once_with(core,None)
    finally:
        release.set();worker.join(2)


def test_model_failure_is_reported_on_ui_callback_not_as_ready():
    def fail(**kwargs):raise RuntimeError('model unavailable')
    ns,queued=methods(fail)
    view=SimpleNamespace(_startup_cancelled=Event(),_accept_core=Mock(_llm_ready=True))
    ns['_load_core'](view,'db','models',True)
    view._accept_core.assert_not_called();queued[0](0)
    view._accept_core.assert_called_once_with(None,'model unavailable')


def test_stop_during_loading_closes_core_without_opening_chat():
    core=Mock(_llm_ready=True);ns,queued=methods(Mock(return_value=core))
    stop=Event();stop.set()
    view=SimpleNamespace(_startup_cancelled=stop,_accept_core=Mock(_llm_ready=True))
    ns['_load_core'](view,'db','models',True)
    core.close.assert_called_once();assert queued==[]
    view._accept_core.assert_not_called()


def test_cancel_between_worker_and_ui_handoff_discards_result():
    core=Mock(_llm_ready=True);closed=Event();core.close.side_effect=closed.set
    ns,queued=methods(Mock(return_value=core))
    stop=Event();view=SimpleNamespace(_startup_cancelled=stop,intro=Mock())
    view._accept_core=MethodType(ns['_accept_core'],view)
    ns['_load_core'](view,'db','models',True)
    stop.set()
    for callback in queued:callback(0)
    assert closed.wait(2)
    view.intro.set_stage.assert_not_called()
    assert not hasattr(view,'core')


def test_startup_error_stops_indicator_and_preserves_error_detail():
    ns,_=methods(Mock())
    view=SimpleNamespace(_startup_cancelled=Event(),intro=Mock())
    ns['_accept_core'](view,None,'file missing')
    view.intro.set_stage.assert_called_once_with('Avvio non riuscito','file missing',1,busy=False)


def test_setup_ready_handoff_has_no_artificial_wait():
    path=ROOT/'allma_model/ui/setup_view.py'
    tree=ast.parse(path.read_text())
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='finish_setup')
    clock=Mock();namespace={'Clock':clock}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    view=SimpleNamespace(intro=Mock(),_notify_complete=Mock())
    namespace['finish_setup'](view)
    assert clock.schedule_once.call_args.args[1]==0
    view.intro.set_stage.assert_called_once_with('Modello verificato','Ora preparo il modello e la memoria.',1,busy=False)


def test_boot_screen_stops_animation_without_initialized_timer():
    path=ROOT/'main.py';tree=ast.parse(path.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SetupScreen')
    node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='stop_animation')
    namespace={};exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),namespace)
    namespace['stop_animation'](SimpleNamespace())
    event=Mock();screen=SimpleNamespace(_pulse_event=event)
    namespace['stop_animation'](screen)
    event.cancel.assert_called_once();assert screen._pulse_event is None


def test_native_model_load_failure_never_reports_ready_and_closes_core():
    core=Mock(_llm_ready=False)
    ns,queued=methods(Mock(return_value=core))
    view=SimpleNamespace(_startup_cancelled=Event(),_accept_core=Mock())
    ns['_load_core'](view,'db','models',True)
    core._ensure_mobile_llm.assert_called_once()
    core.close.assert_called_once()
    queued[-1](0)
    assert view._accept_core.call_args.args[0] is None
    assert 'caricare il modello' in view._accept_core.call_args.args[1]
