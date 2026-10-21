"""Exercise the real pre-extraction APK resource loader without Kivy or a phone."""
import ast
import os
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ('startup_ui.py', 'assets/web/images/startup-connection.png',
             'assets/web/fonts/Inter-Regular.ttf', 'assets/web/fonts/Inter-LICENSE.txt')


def loader(tmp_path, monkeypatch, resources=RESOURCES):
    package = tmp_path/'app.apk'
    def write(version):
        with zipfile.ZipFile(package, 'w') as archive:
            for name in resources:
                archive.writestr('assets/startup/'+name, f'{version}:{name}'.encode())
    write('first')
    activity = SimpleNamespace(
        getFilesDir=lambda:SimpleNamespace(getAbsolutePath=lambda:str(tmp_path/'private')),
        getApplicationInfo=lambda:SimpleNamespace(sourceDir=str(package)))
    monkeypatch.setitem(sys.modules, 'jnius', SimpleNamespace(autoclass=lambda _:SimpleNamespace(mActivity=activity)))
    tree = ast.parse((ROOT/'main.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name=='prepare_startup_ui')
    environment = {'os':os, 'zipfile':zipfile, 'sys':SimpleNamespace(path=[]), 'platform':'android'}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'main.py', 'exec'), environment)
    return environment, write, tmp_path/'private/allma_startup_ui'


def test_resources_available_before_model_extraction_and_unchanged_files_are_reused(tmp_path, monkeypatch):
    env, _, destination = loader(tmp_path, monkeypatch)
    env['prepare_startup_ui']()
    for name in RESOURCES:
        assert (destination/name).read_bytes()==f'first:{name}'.encode()
    times = {name:(destination/name).stat().st_mtime_ns for name in RESOURCES}
    env['prepare_startup_ui']()
    assert {name:(destination/name).stat().st_mtime_ns for name in RESOURCES}==times
    assert env['sys'].path==[str(destination)]
    assert not list(destination.rglob('*.tmp'))


def test_corrupted_cache_is_replaced_from_apk(tmp_path, monkeypatch):
    env, _, destination = loader(tmp_path, monkeypatch)
    env['prepare_startup_ui']()
    (destination/'startup_ui.py').write_bytes(b'corrupted cached code')
    env['prepare_startup_ui']()
    assert (destination/'startup_ui.py').read_bytes()==b'first:startup_ui.py'


def test_updated_apk_replaces_old_illustration_and_component(tmp_path, monkeypatch):
    env, write, destination = loader(tmp_path, monkeypatch)
    env['prepare_startup_ui']()
    write('second')
    env['prepare_startup_ui']()
    assert all((destination/name).read_bytes()==f'second:{name}'.encode() for name in RESOURCES)


def test_incomplete_apk_never_exposes_partial_component_to_imports(tmp_path, monkeypatch):
    env, _, _ = loader(tmp_path, monkeypatch, resources=RESOURCES[:1])
    with pytest.raises(KeyError):
        env['prepare_startup_ui']()
    assert env['sys'].path==[]


def test_desktop_uses_the_project_resources_without_android_imports(tmp_path, monkeypatch):
    env, _, destination = loader(tmp_path, monkeypatch)
    env['platform']='linux'
    env['prepare_startup_ui']()
    assert not destination.exists() and env['sys'].path==[]
