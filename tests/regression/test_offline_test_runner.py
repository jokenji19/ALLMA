"""The offline runner must not inherit models from the developer's cache."""
import json
import os
from pathlib import Path
import subprocess
import sys


def test_runner_isolates_hub_cache_and_blocks_network(tmp_path):
    runner = Path(__file__).resolve().parents[2]/'tools/run_tests.py'
    inherited_cache = tmp_path/'developer-model-cache'
    inherited_cache.mkdir()
    (inherited_cache/'developer-only-model').write_text('cached')
    probe = tmp_path/'test_environment.py'
    probe.write_text('''
import os
from pathlib import Path
import socket
import pytest

def test_environment():
    home = Path(os.environ['HF_HOME'])
    hub = Path(os.environ['HF_HUB_CACHE'])
    assert home != Path(os.environ['DEVELOPER_HF_CACHE'])
    assert hub == home/'hub'
    assert os.environ['HUGGINGFACE_HUB_CACHE'] == str(hub)
    assert 'TRANSFORMERS_CACHE' not in os.environ
    assert not (hub/'developer-only-model').exists()
    assert os.environ['HF_HUB_OFFLINE'] == os.environ['TRANSFORMERS_OFFLINE'] == '1'
    with pytest.raises(OSError, match='External DNS disabled'):
        socket.getaddrinfo('huggingface.co', 443)
''')
    output = tmp_path/'results'
    env = dict(os.environ, HF_HOME=str(inherited_cache), HF_HUB_CACHE=str(inherited_cache),
               HUGGINGFACE_HUB_CACHE=str(inherited_cache), TRANSFORMERS_CACHE=str(inherited_cache),
               DEVELOPER_HF_CACHE=str(inherited_cache), PYTEST_ADDOPTS='')
    result = subprocess.run([sys.executable, str(runner), str(probe), '--output', str(output),
                             '--timeout', '45'], env=env, capture_output=True, text=True, timeout=100)
    assert result.returncode == 0, result.stdout+'\n'+result.stderr
    report = json.loads((output/'summary.json').read_text())
    assert report['successful'] and report['complete']
    assert report['counts'] == {'passed': 1}
    assert 'isolated' in report['model_cache']
