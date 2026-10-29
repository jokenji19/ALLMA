import pytest
from allma_model.memory_system.storage_diagnostics import CASES,run_battery

@pytest.mark.parametrize('challenge',CASES,ids=[row[1] for row in CASES])
def test_incremental_storage_challenge(tmp_path,challenge):
    challenge[3](tmp_path)


def test_complete_storage_diagnostic_uses_isolated_case_directories(tmp_path):
    """Exercise the shared runner too, as Android does; cases alone miss collisions."""
    summary=run_battery(tmp_path/'report',scope='Desktop; synthetic archives')
    assert summary['complete']
    assert summary['total']==len(CASES)==38
    assert summary['passed']==38
    assert summary['failures']==[]
