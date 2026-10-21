import json
from threading import Event
from pathlib import Path

from memory_recovery_battery import run_battery
from reliability_android import AndroidMemoryRecoveryRun


def test_production_memory_recovery_challenges_pass_and_preserve_cwd(tmp_path):
    before=Path.cwd()
    summary=run_battery(tmp_path/'reports')
    assert summary['complete'] and summary['passed']==summary['planned']==16, summary['failures']
    assert Path.cwd()==before
    assert len(json.loads((tmp_path/'reports/plan.json').read_text())['cases'])==16


def test_cancellation_does_not_claim_a_complete_memory_score(tmp_path):
    event=Event()
    def cancel(current,total,name):
        event.set()
    summary=run_battery(tmp_path/'reports',cancel_event=event,progress_callback=cancel)
    assert summary['total']==1 and summary['percent'] is None and not summary['complete']


def test_android_memory_runner_is_separate_from_fixed_sixty_case_battery():
    run=AndroidMemoryRecoveryRun()
    assert run.battery_module=='memory_recovery_battery'
    assert run.folder_prefix=='memory_recovery'
