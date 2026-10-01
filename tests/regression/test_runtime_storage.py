import sqlite3
from allma_model.utils.runtime_storage import prepare_runtime_storage
from allma_model.core.dream_system.dream_manager import DreamManager


def test_migration_preserves_wal_and_survives_code_replacement(tmp_path):
    import shutil
    legacy = tmp_path / 'app'
    legacy.mkdir()
    db = sqlite3.connect(legacy / 'allma.db')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE test(value TEXT)')
    db.execute("INSERT INTO test VALUES ('remember')")
    db.commit()
    (legacy / 'allma_memory.json').write_text('{"messages": []}')
    state = prepare_runtime_storage(tmp_path, legacy)
    from pathlib import Path
    state = Path(state)
    with sqlite3.connect(state / 'allma.db') as restored:
        assert restored.execute('SELECT value FROM test').fetchone() == ('remember',)
    db.close()
    shutil.rmtree(legacy)
    assert (state / 'allma_memory.json').exists()
    assert state.parent == tmp_path


def test_existing_state_is_never_overwritten(tmp_path):
    from pathlib import Path
    legacy = tmp_path / 'app'
    legacy.mkdir()
    source = legacy / 'allma_memory.json'
    source.write_text('old')
    state = Path(prepare_runtime_storage(tmp_path, legacy))
    (state / 'allma_memory.json').write_text('new')
    prepare_runtime_storage(tmp_path, legacy)
    assert (state / 'allma_memory.json').read_text() == 'new'
    assert source.read_text() == 'old'


def test_dream_journal_uses_explicit_persistent_path(tmp_path, monkeypatch):
    path = tmp_path / 'state/dreams.json'
    manager = DreamManager(None, None, journal_path=str(path))
    manager.dream_history = [{'text': 'remember'}]
    manager._save_dream_journal()
    other = tmp_path / 'new_code_directory'
    other.mkdir()
    monkeypatch.chdir(other)
    restored = DreamManager(None, None, journal_path=str(path))
    assert restored.dream_history == manager.dream_history
