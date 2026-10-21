"""Durable replacement of JSON state without removing the last good copy."""
import json
import os
import tempfile
import hashlib
import shutil
import logging
from pathlib import Path


class StateRecoveryRequired(RuntimeError):
    """An unreadable archive must be repaired/reloaded before normal writes."""


def sync_directory(path):
    """Persist a replacement's directory entry when the filesystem supports it.

    A failure after os.replace must not make callers roll RAM back while disk
    already contains the new state. Report reduced durability separately.
    """
    try:
        descriptor = os.open(str(path), os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        return True
    except OSError:
        logging.warning('Directory sync unavailable; replacement retained')
        return False


def preserve_invalid_file(path):
    """Keep original bytes, including when an older recovery copy already exists."""
    path = Path(path)
    if not path.exists():
        return None
    backup = path.with_name(path.name + '.invalid.bak')
    if backup.exists():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        backup = path.with_name(path.name + '.invalid.' + digest + '.bak')
    if not backup.exists():
        # Android may reject copying security extended attributes. Preserve
        # original bytes using a private descriptor, without chmod/xattr calls.
        try:
            descriptor=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        except FileExistsError:
            return backup
        try:
            with os.fdopen(descriptor,'wb') as writer,path.open('rb') as reader:
                shutil.copyfileobj(reader,writer,256*1024)
                writer.flush();os.fsync(writer.fileno())
            sync_directory(path.parent)
        except BaseException:
            backup.unlink(missing_ok=True)
            raise
    return backup


def atomic_write_json(path, data, default=None):
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=os.path.basename(path) + '.', suffix='.tmp',
                                     dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, default=default, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        sync_directory(os.path.dirname(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
