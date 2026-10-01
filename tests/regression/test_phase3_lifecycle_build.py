"""Headless checks for bootstrap callbacks, build invalidation and persisted progress."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]


def extract_class(path, name, namespace):
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
    module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


def test_bootstrap_forwards_lifecycle():
    cls = extract_class(ROOT / 'main.py', 'AllmaApp', {'App': object})
    app = cls()
    assert app.on_pause() is True
    internal = Mock()
    internal.on_pause.return_value = True
    app.internal_app = internal
    assert app.on_pause() is True
    app.on_resume()
    app.on_stop()
    internal.on_pause.assert_called_once()
    internal.on_resume.assert_called_once()
    internal.on_stop.assert_called_once()


def test_pause_cancels_generation_saves_and_restores_dream_setting():
    cls = extract_class(ROOT / 'allma_model/ui/app_entry.py', 'AllmaInternalApp', {'MDApp': object})
    app = cls()
    core = Mock(dream_enabled=True)
    app.chat_screen = SimpleNamespace(core=core, chat_session=Mock())
    assert app.on_pause() is True
    app.chat_screen.chat_session.cancel.assert_called_once()
    core.set_dream_mode.assert_called_with(False, persist=False)
    core.conversational_memory.save_memory.assert_called_once()
    core.incremental_learner.save_state.assert_called_once()
    core.dream_enabled = False
    app.on_pause()  # A repeated pause must not overwrite the enabled preference.
    app.on_resume()
    core.set_dream_mode.assert_called_with(True, persist=False)


def test_progress_survives_restart(tmp_path):
    from allma_model.learning_system.incremental_learning import IncrementalLearner
    path = str(tmp_path / 'learning.json')
    learner = IncrementalLearner(path)
    learner.learn_from_interaction({'input': 'mare', 'response': 'blu', 'topic': 'mare', 'feedback': 'neutral'}, 'u')
    expected = learner.get_learning_progress('u')
    assert expected['topics'] == ['mare']
    assert sum(expected['confidence_levels'].values()) == 1
    assert IncrementalLearner(path).get_learning_progress('u') == expected


def test_build_hash_includes_service_manifest_and_native_libs(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('build_helper', ROOT / 'tools/build_android_safe.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    monkeypatch.setattr(helper, 'ROOT', tmp_path)
    previous = helper.compute_hash()
    for name in ['service.py', 'AndroidManifest.xml', 'libs_custom/lib.so']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('changed')
        current = helper.compute_hash()
        assert current != previous
        previous = current


def test_feedback_survives_restart(tmp_path):
    from allma_model.learning_system.incremental_learning import IncrementalLearner, FeedbackType
    path = str(tmp_path / 'learning.json')
    learner = IncrementalLearner(path)
    learner.learn_from_interaction({'input': 'mare', 'response': 'blu', 'topic': 'mare', 'feedback': 'neutral'}, 'u')
    learner.integrate_feedback('mare', FeedbackType.NEGATIVE, 'Servono esempi e chiarezza')
    restored = IncrementalLearner(path)
    assert restored.knowledge_states['mare'].feedback_history == learner.knowledge_states['mare'].feedback_history
    assert restored.knowledge_states['mare'].improvement_areas == {'esempi', 'chiarezza'}


def test_native_loader_uses_packaged_library_only(tmp_path):
    import os
    tree = ast.parse((ROOT / 'main.py').read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'configure_native_library')
    fake_os = SimpleNamespace(environ={'ANDROID_PRIVATE': str(tmp_path)}, path=os.path)
    namespace = {'os': fake_os, 'sys': SimpleNamespace(path=[str(tmp_path)]), 'logging': Mock()}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), 'loader', 'exec'), namespace)
    configure = namespace['configure_native_library']
    assert configure() is None
    library = tmp_path / 'llama_cpp/libllama.so'
    library.parent.mkdir()
    library.write_bytes(b'test binary')
    assert configure() == str(library)
    assert fake_os.environ['LLAMA_CPP_LIB'] == str(library)


def test_bootstrap_keeps_outer_app_when_internal_constructor_changes_running_app():
    outer = SimpleNamespace(root=object())
    original_root = outer.root
    registry = SimpleNamespace(current=outer)
    app_api = SimpleNamespace(get_running_app=lambda: registry.current)
    window = Mock()
    cls = extract_class(ROOT / 'main.py', 'SetupScreen', {'Screen': object, 'App': app_api, 'Window': window})
    setup = object.__new__(cls)
    setup.show_error = Mock()

    class Internal:
        def __init__(self):
            registry.current = self
            self.on_start = Mock()
        def build(self):
            return object()

    setup.switch_to_internal_app(Internal)
    setup.show_error.assert_not_called()
    assert outer.root is outer.internal_app.root
    window.remove_widget.assert_called_once_with(original_root)
    window.add_widget.assert_called_once_with(outer.root)
    outer.internal_app.on_start.assert_called_once()


def test_build_records_hash_after_packing(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('build_helper_order', ROOT / 'tools/build_android_safe.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    monkeypatch.setattr(helper, 'ROOT', tmp_path)
    monkeypatch.setattr(helper.sys, 'argv', ['build_android_safe.py'])
    main = tmp_path / 'main.py'
    main.write_text('old payload')
    previous_hash = helper.compute_hash()
    calls = []
    def run(command):
        calls.append(command)
        if command == ['buildozer', 'android', 'debug']:
            (tmp_path / 'bin').mkdir()
            (tmp_path / 'bin/app.apk').write_bytes(b'test artifact')
        if command[-1] == 'pack_brain.py':
            main.write_text('new payload')
    monkeypatch.setattr(helper, 'run_command', run)
    helper.main()
    state = helper.load_state(tmp_path / '.buildozer/allma_build_state.json')
    assert state['hash'] == helper.compute_hash()
    assert state['hash'] != previous_hash
    assert calls[0][-1] == 'pack_brain.py'
    assert calls[-2] == ['buildozer', 'android', 'debug']
    assert calls[-1][1] == 'tools/verify_android_apk.py'


def test_app_build_leaves_checksum_verification_to_setup_worker():
    manager = Mock()
    setup_screen = Mock()
    downloader = Mock(side_effect=AssertionError('Model verification on UI thread'))
    namespace = {'MDApp': object, 'Window': SimpleNamespace(), 'ScreenManager': Mock(return_value=manager),
                 'FadeTransition': Mock(), 'SetupView': Mock(return_value=setup_screen), 'ModelDownloader': downloader}
    cls = extract_class(ROOT / 'allma_model/ui/app_entry.py', 'AllmaInternalApp', namespace)
    app = cls()
    app.theme_cls = SimpleNamespace()
    app.load_and_switch_chat = Mock()
    assert app.build() is manager
    assert manager.current == 'setup'
    setup_screen.set_callback.assert_called_once_with(app.on_setup_complete)
    downloader.assert_not_called()
    app.load_and_switch_chat.assert_not_called()
