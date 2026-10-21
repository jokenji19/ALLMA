"""A fresh checkout must reach Buildozer's preparation before any clean command."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def build_env(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('cold_build_helper', ROOT/'tools/build_android_safe.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    monkeypatch.setattr(helper, 'ROOT', tmp_path)
    monkeypatch.setattr(helper.sys, 'argv', ['build_android_safe.py'])
    calls = []
    def run(command):
        calls.append(command)
        if command == ['buildozer', 'android', 'debug']:
            (tmp_path/'bin').mkdir(exist_ok=True)
            (tmp_path/'bin/app.apk').write_bytes(b'synthetic APK')
    monkeypatch.setattr(helper, 'run_command', run)
    return helper, calls


@pytest.mark.parametrize('build_dir,source', [
    ('.buildozer', ''), ('.buildozer_local', ''), ('custom-cache', 'native-source'),
])
def test_fresh_build_skips_clean_and_still_verifies_apk(build_env, tmp_path, build_dir, source):
    helper, calls = build_env
    (tmp_path/'buildozer.spec').write_text(f'[app]\np4a.source_dir = {source}\n[buildozer]\nbuild_dir = {build_dir}\n')
    assert not helper.android_toolchain_ready()
    helper.main()
    assert ['buildozer', 'android', 'clean'] not in calls
    assert ['buildozer', 'android', 'debug'] in calls
    assert calls[-1][1] == 'tools/verify_android_apk.py'
    assert helper.load_state(tmp_path/'.buildozer/allma_build_state.json')['hash'] == helper.compute_hash()


@pytest.mark.parametrize('source', ['', 'custom-p4a'])
def test_changed_initialized_build_keeps_cleaning(build_env, tmp_path, source):
    helper, calls = build_env
    (tmp_path/'buildozer.spec').write_text(f'[app]\np4a.source_dir = {source}\n[buildozer]\nbuild_dir = .buildozer_local\n')
    checkout = tmp_path/(source or '.buildozer_local/android/platform/python-for-android')
    checkout.mkdir(parents=True)
    helper.save_state(tmp_path/'.buildozer/allma_build_state.json', {'hash': 'old'})
    helper.main()
    assert calls.index(['buildozer', 'android', 'clean']) < calls.index(['buildozer', 'android', 'debug'])


def test_unchanged_initialized_build_reuses_verified_state(build_env, tmp_path):
    helper, calls = build_env
    (tmp_path/'.buildozer/android/platform/python-for-android').mkdir(parents=True)
    helper.save_state(tmp_path/'.buildozer/allma_build_state.json', {'hash': helper.compute_hash()})
    helper.main()
    assert ['buildozer', 'android', 'clean'] not in calls
    assert calls[-1][1] == 'tools/verify_android_apk.py'
