from pathlib import Path
import json
from preservation_battery import run_battery,CASES


def test_fixed_preservation_challenges_pass(tmp_path):
    assert len(CASES)==28
    previous=Path.cwd()
    summary=run_battery(tmp_path/'reports')
    assert Path.cwd()==previous
    assert summary['complete'] and summary['passed']==28,summary['failures']
    plan=json.loads((tmp_path/'reports/plan.json').read_text())
    assert plan['version']=='preservation-v2' and len(plan['cases'])==28


def test_backup_frontend_controls_password_and_restore_state():
    import subprocess
    root=Path(__file__).resolve().parents[2]
    subprocess.run(['node','tests/regression/backup_actions_checks.cjs'],cwd=root,check=True,capture_output=True,text=True)


def test_android_backup_rules_include_only_authoritative_state():
    import xml.etree.ElementTree as ET
    from allma_model.utils.state_backup import ALLOWED
    root=Path(__file__).resolve().parents[2]
    old=ET.parse(root/'assets/android/xml/allma_backup_rules.xml').getroot()
    assert {e.attrib['path'] for e in old}=={'allma_state/'+n for n in ALLOWED}
    assert all(e.attrib['requireFlags']=='clientSideEncryption' for e in old)
    rules=ET.parse(root/'assets/android/xml/allma_extraction_rules.xml').getroot()
    assert rules.find('cloud-backup').attrib['disableIfNoEncryptionCapabilities']=='true'
    for group in rules:
        assert {e.attrib['path'] for e in group}=={'allma_state/'+n for n in ALLOWED}
