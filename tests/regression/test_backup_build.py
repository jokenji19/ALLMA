from types import SimpleNamespace
from pathlib import Path
import importlib.util


def test_manifest_fragments_have_no_literal_shell_quotes():
    path=Path(__file__).resolve().parents[2]/'libs/android_build_hook.py'
    spec=importlib.util.spec_from_file_location('allma_build_hook',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    values=['--name=ALLMA','--extra-manifest-application-arguments="android:fullBackupContent=\\"@xml/allma_backup_rules\\""',
            '--extra-manifest-xml="<queries />"','--permission=INTERNET']
    module.before_apk_build(SimpleNamespace(args=SimpleNamespace(unknown_args=values)))
    assert values==['--name=ALLMA','--extra-manifest-application-arguments=android:fullBackupContent="@xml/allma_backup_rules"',
                    '--extra-manifest-xml=<queries />','--permission=INTERNET']
    module.before_apk_build(SimpleNamespace(args=SimpleNamespace(unknown_args=values)))
    assert values[1].endswith('="@xml/allma_backup_rules"')


def test_packaging_excludes_local_personal_state_and_desktop_caches():
    import configparser
    from allma_model.utils.runtime_storage import STATE_FILES
    root=Path(__file__).resolve().parents[2]
    config=configparser.ConfigParser();config.read(root/'buildozer.spec')
    patterns=set(config['app']['source.exclude_patterns'].split(','))
    assert set(STATE_FILES)<=patterns
    directories={n.strip() for n in config['app']['source.exclude_dirs'].split(',')}
    assert {'Library','htmlcov','_quarantine','models','benchmarks/reports'}<=directories
    assert 'allma_model.zip' in patterns
