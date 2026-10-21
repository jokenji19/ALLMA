"""Prepare a complete replacement; apply only before the managed core opens.

The old directory is preserved intact. A durable marker makes both rename
boundaries resumable after process death. Never overwrite a live database.
"""
import json
import os
from pathlib import Path
import re
import shutil
import uuid

from .persistence import atomic_write_json,sync_directory
from .state_backup import BackupError,verify_archive,file_digest

PENDING='.allma-restore.json'
RECEIPT='.allma-last-restore.json'


def stage_restore(root,archive,*,primary='allma.db'):
    root=Path(root).resolve()
    if root.name!='allma_state' or primary!='allma.db':
        raise BackupError('Il ripristino richiede la cartella dati gestita di ALLMA')
    marker=root.parent/PENDING
    if marker.exists():raise BackupError('Un ripristino è già preparato; riavvia ALLMA prima di continuare')
    identifier=uuid.uuid4().hex
    candidate=root.parent/('allma_state.restore.'+identifier)
    prior=root.parent/('allma_state.before-restore.'+identifier)
    candidate.mkdir(mode=0o700)
    try:
        manifest=verify_archive(archive,candidate,primary=primary)
        for directory in sorted((p for p in candidate.rglob('*') if p.is_dir()),reverse=True):
            sync_directory(directory)
        sync_directory(candidate)
        atomic_write_json(marker,{'version':1,'candidate':candidate.name,'previous':prior.name,
                                 'primary':primary,'files':manifest['files']})
        return {'prepared':True,'files':len(manifest['files']),'restart_required':True}
    except Exception:
        if not marker.exists():shutil.rmtree(candidate)
        raise


def _verify_candidate(root,files):
    from .state_backup import ALLOWED
    if not isinstance(files,dict) or not files or not set(files)<=set(ALLOWED):
        raise BackupError('Elenco del ripristino non valido')
    for name,entry in files.items():
        path=root/name
        if (not isinstance(entry,dict) or path.is_symlink() or not path.is_file()
                or not path.resolve().is_relative_to(root) or path.stat().st_size!=entry.get('size')
                or file_digest(path)!=entry.get('sha256')):
            raise BackupError('La copia preparata è cambiata; lo stato precedente è conservato')


def apply_pending_restore(private_dir):
    """Called before constructing any core/database handle in allma_state."""
    base=Path(private_dir).resolve();marker=base/PENDING
    if not marker.exists():return None
    if marker.is_symlink() or marker.stat().st_size>64*1024:
        raise BackupError('Marcatore di ripristino non valido')
    data=json.loads(marker.read_text())
    if (not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1
            or data.get('primary')!='allma.db'):
        raise BackupError('Versione del ripristino non supportata')
    candidate_name=data.get('candidate','');prior_name=data.get('previous','')
    match=re.fullmatch(r'allma_state\.restore\.([a-f0-9]{32})',candidate_name) if isinstance(candidate_name,str) else None
    if not match or prior_name!='allma_state.before-restore.'+match[1]:
        raise BackupError('Percorso del ripristino non valido')
    current=base/'allma_state';candidate=base/candidate_name;prior=base/prior_name
    if any(path.is_symlink() for path in (current,candidate,prior)):
        raise BackupError('Collegamento non ammesso nel ripristino')
    if candidate.exists():
        _verify_candidate(candidate,data['files'])
        if current.exists():
            if prior.exists():raise BackupError('Stato del ripristino ambiguo; nessuna copia viene rimossa')
            os.replace(current,prior)
            sync_directory(base)
        os.replace(candidate,current)
        sync_directory(base)
    elif not current.exists():
        raise BackupError('Copia preparata non disponibile; lo stato precedente è conservato')
    _verify_candidate(current,data['files'])
    receipt={'version':1,'previous':prior.name if prior.exists() else None,'restored_files':len(data['files'])}
    atomic_write_json(base/RECEIPT,receipt)
    marker.unlink();sync_directory(base)
    return receipt
