from pathlib import Path
from threading import Event, RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from reliability_android import AndroidReliabilityRun


def source(tmp_path):
    return SimpleNamespace(db_path=str(tmp_path/'source.db'), _lock=RLock(),
        _user_active=Event(), _shutdown_event=Event(), _benchmark_active=False,
        dream_manager=SimpleNamespace(is_dreaming=False))


def test_failure_releases_activity_and_benchmark_flags(tmp_path, monkeypatch):
    parent=source(tmp_path)
    run=AndroidReliabilityRun()
    run.setup_brain(parent)
    monkeypatch.setattr('reliability_battery.run_battery', Mock(side_effect=RuntimeError('injected failure')))
    with pytest.raises(RuntimeError):
        run.run_tests()
    assert not parent._benchmark_active and not parent._user_active.is_set()


def test_partial_run_has_no_complete_percentage(tmp_path, monkeypatch):
    parent=source(tmp_path)
    run=AndroidReliabilityRun()
    run.setup_brain(parent)
    summary=dict(complete=False,passed=3,total=4,percent=None,groups={},failures=[])
    monkeypatch.setattr('reliability_battery.run_battery', Mock(return_value=summary))
    run.run_tests()
    assert run.manifest['cancelled']
    assert 'nessuna percentuale completa' in Path(run.report_path).read_text()
    assert not parent._user_active.is_set()


def test_busy_source_is_not_taken_over(tmp_path):
    parent=source(tmp_path)
    parent._user_active.set()
    with pytest.raises(RuntimeError):
        AndroidReliabilityRun().setup_brain(parent)
    assert parent._user_active.is_set()
