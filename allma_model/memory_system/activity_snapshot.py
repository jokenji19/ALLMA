"""Bounded, disposable initiative view of a validated history generation."""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import timedelta
import re

from allma_model.utils.persistence import StateRecoveryRequired

MAX_USERS=8
REQUEST=re.compile(r'PROACTIVE:[0-9a-f]{32}')


def _fingerprint(store):
    """Detect SQLite writes outside the generation protocol too, including WAL."""
    from pathlib import Path
    values=[]
    for path in (store.path,Path(str(store.path)+'-wal')):
        try:
            stat=path.stat()
            values.append((stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns))
        except FileNotFoundError:
            if path==store.path:raise
            values.append(None)
    return tuple(values)


@dataclass(frozen=True)
class ActivitySnapshot:
    last_user: object
    latest_proactive: object
    pending: object
    built_at: object
    valid_until: object


def activity_snapshot(memory,user,now,policy,cooldown):
    """One scan per changed source, no repeated scan on an unchanged idle tick.

    Only canonical, clean history may reuse this view. The generation is checked
    on disk even on a hit. Unsaved edits, reloads, expiry and clock rollback force
    a new scan. Legacy/adaptor readers use the same one-pass logic without reuse.
    """
    with memory.lock:
        store=getattr(memory,'_history_store',None)
        changes=getattr(memory,'_changes',None)
        canonical=store is not None and changes is not None
        key=None
        if canonical:
            if memory._load_error is not None or store.read_error is not None:
                raise StateRecoveryRequired('History must be recovered before initiative')
            store.check_current_generation()
            clean=not (any(changes.dirty.values()) or any(changes.deleted.values())
                       or changes.sections or changes.touched)
            if clean:key=(id(memory.messages),id(changes),store.generation,policy,cooldown,_fingerprint(store))
        cache=getattr(memory,'_activity_snapshots',None)
        if not isinstance(cache,OrderedDict):
            cache=OrderedDict();memory._activity_snapshots=cache
        cached=cache.get(user)
        if key is not None and cached is not None and cached[0]==key:
            view=cached[1]
            if now>=view.built_at and (view.valid_until is None or now<view.valid_until):
                cache.move_to_end(user);return view
        cache.pop(user,None)
        last=latest=pending=None
        for row in memory.messages:
            if (row.user_id or row.metadata.get('user_id'))!=user:continue
            if row.role=='user' and (last is None or row.timestamp>last.timestamp):last=row
            meta=row.metadata
            if meta.get('source')!='proactive':continue
            if latest is None or row.timestamp>latest:latest=row.timestamp
            if (row.role=='assistant' and row.user_id==user and meta.get('is_valid') is True
                    and meta.get('revoked') is not True and meta.get('status') not in ('revoked','superseded')
                    and meta.get('identity_policy')==policy
                    and isinstance(meta.get('request_id'),str) and REQUEST.fullmatch(meta['request_id'])
                    and meta.get('proactive_delivery')=={'version':1,'state':'pending'}
                    and (now-row.timestamp).total_seconds()<cooldown):
                pending=row  # Preserve archive order, including equal timestamps.
        view=ActivitySnapshot(last,latest,pending,now,
            pending.timestamp+timedelta(seconds=cooldown) if pending is not None else None)
        if key is not None:
            store.check_current_generation()
            if _fingerprint(store)!=key[-1]:
                raise StateRecoveryRequired('History changed while preparing initiative; restart the read')
            cache[user]=(key,view)
            while len(cache)>MAX_USERS:cache.popitem(last=False)
        return view
