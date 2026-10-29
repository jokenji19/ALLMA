"""Keep mutable Android state outside python-for-android's replaceable app tree."""
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

STATE_FILES = (
    'allma.db', 'allma_memory.json', 'conversation_history.db', 'allma_settings.json', 'allma_modules.db', 'answer_recall.json', 'answer_recall.db',
    'model_binding.json', 'notifications.json',
    'incremental_cache/knowledge_states.json', 'incremental_cache/knowledge_states.db',
    'data/allma_vectors.db', 'data/dream_journal.json',
    'data/dream_journal.json.pending.json', 'data/dream_journal.json.processed.json', 'message_delivery.json',
    'data/dream_journal.json.reviews.db',
    'cognitive_state.json', 'allma_diary.json',
)


def prepare_runtime_storage(private_dir, legacy_dir=None):
    from .state_restore import apply_pending_restore,RECEIPT
    apply_pending_restore(private_dir)
    destination = Path(private_dir).resolve() / 'allma_state'
    destination.mkdir(parents=True, exist_ok=True)
    if legacy_dir is not None and not (Path(private_dir).resolve()/RECEIPT).exists():
        legacy = Path(legacy_dir).resolve()
        migrations = [(relative, relative) for relative in STATE_FILES]
        migrations.append(('Model/data/allma.db', 'legacy_coalescence.db'))
        for source_relative, target_relative in migrations:
            source, target = legacy / source_relative, destination / target_relative
            if not source.is_file() or target.exists() or source == target:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=target.name + '.', dir=target.parent)
            os.close(fd)
            try:
                if source.suffix == '.db':
                    # backup includes committed WAL records; never copy an open DB blindly.
                    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as reader:
                        with sqlite3.connect(temporary) as writer:
                            reader.backup(writer)
                else:
                    shutil.copyfile(source, temporary)
                with open(temporary, 'rb') as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    return str(destination)
