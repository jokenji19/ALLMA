"""Verified snapshots of authoritative ALLMA data, never models or app code.

Private rolling copies protect against accidental corruption, not loss of the
phone. Only an independently saved encrypted export can survive that event.
"""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile
import threading
import uuid
import zipfile

from .persistence import atomic_write_json,preserve_invalid_file,sync_directory
from .runtime_storage import STATE_FILES

VERSION=1
MAX_FILE=512*1024**2
MAX_TOTAL=2*1024**3
MAX_FILES=64
BLOCK=256*1024
MAX_JSON=128*1024**2
ALLOWED=tuple(n for n in STATE_FILES if n!='data/allma_vectors.db')+('legacy_coalescence.db',)


class BackupError(RuntimeError):
    pass


def file_digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as reader:
        for data in iter(lambda:reader.read(BLOCK),b''):
            value.update(data)
    return value.hexdigest()


def _check_data(path,name):
    if name.endswith('.db'):
        with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('PRAGMA quick_check').fetchone()!=('ok',):
                raise BackupError('Un archivio SQLite richiede recupero')
    else:
        if Path(path).stat().st_size>MAX_JSON:
            raise BackupError('JSON troppo grande per la verifica sicura su questo dispositivo; serve una migrazione del formato')
        with Path(path).open(encoding='utf-8') as reader:
            data=json.load(reader,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON number')))
        if name=='data/dream_journal.json' or name.endswith(('.pending.json','.processed.json')):
            if not isinstance(data,list):
                raise BackupError('Indice onirico non valido')
            if name.endswith('.processed.json'):
                if any(not isinstance(v,str) for v in data):raise BackupError('Indice onirico non valido')
            elif any(not isinstance(v,dict) or not isinstance(v.get('text'),str) for v in data):
                raise BackupError('Voce onirica non valida')
        elif not isinstance(data,dict):
            raise BackupError('Archivio JSON non valido')
        if name=='allma_memory.json':
            from .autobiography_validation import validate_history_archive
            validate_history_archive(data)
        if name=='incremental_cache/knowledge_states.json':
            from allma_model.learning_system.incremental_learning import IncrementalLearner
            if IncrementalLearner(str(path)).load_error is not None:
                raise BackupError('Archivio di apprendimento non valido')
        if name=='answer_recall.json':
            from allma_model.learning_system.answer_recall import AnswerRecall
            if (type(data.get('version')) is not int or data['version']!=1
                    or not isinstance(data.get('records'),dict)
                    or type(data.get('delivery_checkpoint',0)) is not int
                    or not 0<=data.get('delivery_checkpoint',0)<2**53
                    or any(not AnswerRecall._valid_record(k,v) for k,v in data['records'].items())):
                raise BackupError('Archivio delle risposte apprese non valido')
        if name=='cognitive_state.json':
            if type(data.get('version')) is not int or data['version']!=1 or not isinstance(data.get('sections'),dict):
                raise BackupError('Versione dello stato cognitivo non supportata')
            if any(not isinstance(value,dict) for value in data['sections'].values()):
                raise BackupError('Sezione cognitiva non valida')


def verify_archive(archive,destination=None,*,primary='allma.db',cancel_event=None):
    """Validate every byte/path before permitting a staged restore.

    Extraction always targets a new private directory, never the live state.
    Unknown future schemas and files fail explicitly rather than being dropped.
    """
    check_cancel(cancel_event)
    permitted=set(ALLOWED)-{'allma.db'}|{primary}
    with zipfile.ZipFile(archive) as zipped:
        infos=zipped.infolist()
        names=[i.filename for i in infos]
        if len(infos)>MAX_FILES or len(names)!=len(set(names)) or 'manifest.json' not in names:
            raise BackupError('Indice del backup non valido')
        if zipped.getinfo('manifest.json').file_size>64*1024:
            raise BackupError('Indice del backup troppo grande')
        manifest=json.loads(zipped.read('manifest.json'))
        if (not isinstance(manifest,dict) or type(manifest.get('version')) is not int
                or manifest['version']!=VERSION or manifest.get('primary_database')!=primary
                or not isinstance(manifest.get('files'),dict) or not manifest['files']):
            raise BackupError('Versione del backup non supportata')
        date=manifest.get('created')
        if not isinstance(date,str) or datetime.fromisoformat(date).tzinfo is None:
            raise BackupError('Data del backup non valida')
        files=manifest['files']
        if set(names)!={'manifest.json',*('state/'+n for n in files)} or not set(files)<=permitted:
            raise BackupError('Il backup contiene file non ammessi')
        total=0
        for name,entry in files.items():
            if (not isinstance(entry,dict) or type(entry.get('size')) is not int
                    or not 0<=entry['size']<=MAX_FILE
                    or not isinstance(entry.get('sha256'),str) or re.fullmatch('[0-9a-f]{64}',entry['sha256']) is None):
                raise BackupError('Indice del file non valido')
            info=zipped.getinfo('state/'+name)
            mode=(info.external_attr>>16)&0o170000
            if info.is_dir() or mode not in (0,stat.S_IFREG) or info.file_size!=entry['size']:
                raise BackupError('Tipo o dimensione del file non valido')
            total+=info.file_size
            if total>MAX_TOTAL:
                raise BackupError('Backup troppo grande per questo dispositivo')
        with tempfile.TemporaryDirectory(prefix='allma-verify-') as temporary:
            base=Path(destination) if destination is not None else Path(temporary)
            for name,entry in files.items():
                check_cancel(cancel_event)
                target=base/name
                target.parent.mkdir(parents=True,exist_ok=True)
                digest=hashlib.sha256()
                written=0
                with zipped.open('state/'+name) as reader,target.open('xb') as writer:
                    while True:
                        check_cancel(cancel_event)
                        block=reader.read(BLOCK)
                        if not block:break
                        written+=len(block)
                        if written>entry['size']:
                            raise BackupError('Dati espansi oltre il limite dichiarato')
                        writer.write(block);digest.update(block)
                    writer.flush();os.fsync(writer.fileno())
                if written!=entry['size'] or digest.hexdigest()!=entry['sha256']:
                    raise BackupError('La verifica di integrità del backup non è riuscita')
                _check_data(target,name)
            return manifest


def check_cancel(event):
    if event is not None and event.is_set():
        raise BackupError('Copia rinviata: ALLMA è tornata attiva')


def copy_chunks(reader,writer,cancel_event=None):
    while True:
        check_cancel(cancel_event)
        block=reader.read(BLOCK)
        if not block:return
        writer.write(block)


class StateBackups:
    _guard=threading.Lock()
    _locks={}

    def __init__(self,root,*,primary='allma.db',backup_dir=None):
        self.root=Path(root).resolve()
        if Path(primary).name!=primary or not primary.endswith('.db'):
            raise ValueError('Nome della base dati non valido')
        self.primary=primary
        self.allowed=tuple(primary if n=='allma.db' else n for n in ALLOWED)
        default=self.root.parent/'allma_state_backups' if self.root.name=='allma_state' else self.root/'.allma_backups'
        self.directory=Path(backup_dir).resolve() if backup_dir else default
        self.catalog=self.directory/'index.json'
        with self._guard:
            self.lock=self._locks.setdefault(str(self.directory),threading.RLock())

    def _index(self):
        if not self.catalog.exists():
            existing=list(self.directory.glob('backup-*.zip')) if self.directory.exists() else []
            if existing:
                raise BackupError('Indice dei backup da recuperare; le copie esistenti sono conservate')
            return {'version':1,'counter':0,'enabled':True,'entries':[]}
        try:
            data=json.loads(self.catalog.read_text())
            if (not isinstance(data,dict) or type(data.get('version')) is not int or data['version']!=1 or type(data.get('counter')) is not int
                    or data['counter']<0 or type(data.get('enabled')) is not bool or not isinstance(data.get('entries'),list)):
                raise ValueError('Invalid backup catalog')
            for entry in data['entries']:
                if (not isinstance(entry,dict) or not isinstance(entry.get('id'),str)
                        or re.fullmatch(r'backup-[0-9]{16,}-[a-f0-9]{32}\.zip',entry['id']) is None
                        or type(entry.get('sequence')) is not int or not 0<entry['sequence']<=data['counter']
                        or not isinstance(entry.get('created'),str)
                        or datetime.fromisoformat(entry['created']).tzinfo is None
                        or not isinstance(entry.get('sha256'),str) or re.fullmatch('[a-f0-9]{64}',entry['sha256']) is None
                        or type(entry.get('bytes')) is not int or entry['bytes']<0):
                    raise ValueError('Invalid backup entry')
            if len({e['id'] for e in data['entries']})!=len(data['entries']):
                raise ValueError('Duplicate backup entry')
            return data
        except (OSError,ValueError) as error:
            try:preserve_invalid_file(self.catalog)
            except OSError:pass
            raise BackupError('Indice dei backup da recuperare; nessuna copia viene sovrascritta') from error

    def _prepare(self):
        self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)

    def configure(self,enabled):
        if type(enabled) is not bool:raise ValueError('Preferenza di backup non valida')
        with self.lock:
            index=self._index();index['enabled']=enabled
            self._prepare();atomic_write_json(self.catalog,index)
        return self.status()

    def status(self):
        with self.lock:
            try:
                index=self._index()
                entries=sorted(index['entries'],key=lambda e:e['sequence'])
                latest=entries[-1] if entries else None
                exists=bool(latest and (self.directory/latest['id']).is_file())
                return {'available':True,'enabled':index['enabled'],'count':len(entries),
                        'latest':{'id':latest['id'],'created':latest['created'],'bytes':latest.get('bytes',0)} if exists else None,
                        'external_copy_needed':True,'managed_restore':self.root.name=='allma_state'}
            except BackupError as error:
                return {'available':False,'enabled':False,'count':0,'latest':None,'error':str(error),
                        'external_copy_needed':True,'managed_restore':self.root.name=='allma_state'}

    def _signature(self):
        result={}
        for name in self.allowed:
            path=self.root/name
            if not path.is_file():continue
            if any(parent.is_symlink() for parent in (path,*path.parents) if parent!=self.root.parent):
                raise BackupError('Un file di stato usa un collegamento non ammesso')
            if not path.resolve().is_relative_to(self.root):raise BackupError('Percorso di stato non valido')
            info=path.stat()
            result[name]=(info.st_size,info.st_mtime_ns)
            wal=Path(str(path)+'-wal')
            if name.endswith('.db') and wal.exists():
                info=wal.stat();result[name+'-wal']=(info.st_size,info.st_mtime_ns)
        return result

    def due(self,now=None):
        from datetime import timedelta
        with self.lock:
            index=self._index()
            if not index['enabled']:return False
            if not index['entries']:return bool(self._signature())
            latest=max(index['entries'],key=lambda e:e['sequence'])
            saved_signature=latest.get('source_signature')
            if saved_signature is not None and saved_signature=={k:list(v) for k,v in self._signature().items()}:
                return False  # No new durable data: avoid copying unchanged history.
            # A clock rollback never suspends protection indefinitely.
            current=now or datetime.now(timezone.utc)
            saved=datetime.fromisoformat(latest['created'])
            delta=current-saved
            return delta.total_seconds()<0 or delta>=timedelta(minutes=30)

    def create(self,cancel_event=None):
        with self.lock:
            check_cancel(cancel_event)
            index=self._index();self._prepare()
            signature=self._signature()
            files=[name for name in self.allowed if name in signature]
            if not files:raise BackupError('Non ci sono ancora dati persistenti da copiare')
            size=sum(value[0] for value in signature.values())
            if size>MAX_TOTAL or shutil.disk_usage(self.directory).free<size*2+16*1024**2:
                raise BackupError('Spazio insufficiente per una nuova copia sicura; le copie precedenti restano disponibili')
            identifier=f"backup-{index['counter']+1:016d}-{uuid.uuid4().hex}.zip"
            final=self.directory/identifier
            manifest={'version':VERSION,'primary_database':self.primary,'created':datetime.now(timezone.utc).isoformat(),
                      'files':{},'excluded':['model_weights','code','derived_vector_cache','benchmark_reports']}
            try:
                with tempfile.TemporaryDirectory(prefix='.snapshot-',dir=self.directory) as temporary:
                    staging=Path(temporary)
                    for name in files:
                        check_cancel(cancel_event)
                        source=self.root/name;target=staging/name;target.parent.mkdir(parents=True,exist_ok=True)
                        if source.stat().st_size>MAX_FILE:raise BackupError('Un archivio richiede un formato di backup più grande')
                        if name.endswith('.db'):
                            with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as reader:
                                with closing(sqlite3.connect(target)) as writer:
                                    reader.backup(writer,pages=128,progress=lambda *_:check_cancel(cancel_event))
                        else:
                            with source.open('rb') as reader,target.open('xb') as writer:
                                copy_chunks(reader,writer,cancel_event)
                        _check_data(target,name)
                        manifest['files'][name]={'size':target.stat().st_size,'sha256':file_digest(target)}
                    if self._signature()!=signature:
                        raise BackupError('I dati sono cambiati durante la copia; riprova quando ALLMA è libera')
                    archive=staging/'snapshot.zip'
                    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3,allowZip64=True) as zipped:
                        for name in files:
                            with (staging/name).open('rb') as reader,zipped.open('state/'+name,'w',force_zip64=True) as writer:
                                copy_chunks(reader,writer,cancel_event)
                        zipped.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True))
                    verify_archive(archive,primary=self.primary,cancel_event=cancel_event)
                    check_cancel(cancel_event)
                    with archive.open('rb') as reader:os.fsync(reader.fileno())
                    os.replace(archive,final);sync_directory(self.directory)
                entry={'id':identifier,'sequence':index['counter']+1,'created':manifest['created'],
                       'sha256':file_digest(final),'bytes':final.stat().st_size,
                       'source_signature':{k:list(v) for k,v in signature.items()}}
                index['counter']+=1;index['entries'].append(entry)
                atomic_write_json(self.catalog,index)
                self._rotate(index)
                return {'id':identifier,'created':entry['created'],'files':len(files),'bytes':entry['bytes'],'verified':True}
            except Exception:
                # A completely written but unindexed copy is preserved for
                # inspection; never erase a prior known-good snapshot on error.
                raise

    def _rotate(self,index):
        entries=sorted(index['entries'],key=lambda e:e['sequence'],reverse=True)
        keep={e['id'] for e in entries[:7]}
        weeks,months=set(),set()
        for entry in entries:
            date=datetime.fromisoformat(entry['created'])
            week=date.isocalendar()[:2];month=(date.year,date.month)
            if week not in weeks and len(weeks)<4:keep.add(entry['id']);weeks.add(week)
            if month not in months and len(months)<12:keep.add(entry['id']);months.add(month)
        discarded=[e for e in entries if e['id'] not in keep]
        if not discarded:return
        # Publish retention first. An interrupted deletion leaves an extra copy,
        # never an index that promises a file already removed.
        index['entries']=[e for e in index['entries'] if e['id'] in keep]
        atomic_write_json(self.catalog,index)
        for entry in discarded:
            path=self.directory/entry['id']
            if path.is_file() and not path.is_symlink() and file_digest(path)==entry['sha256']:
                path.unlink()
        sync_directory(self.directory)

    def repair_catalog(self):
        """Explicit read-only recheck of files; never delete unrecognized copies."""
        with self.lock:
            self._prepare()
            if self.catalog.exists():preserve_invalid_file(self.catalog)
            entries=[];rejected=0
            for path in self.directory.glob('backup-*.zip'):
                match=re.fullmatch(r'backup-([0-9]{16,})-[a-f0-9]{32}\.zip',path.name)
                if not match or path.is_symlink():continue
                try:
                    manifest=verify_archive(path,primary=self.primary)
                    entries.append({'id':path.name,'sequence':int(match[1]),'created':manifest['created'],
                                    'sha256':file_digest(path),'bytes':path.stat().st_size})
                except Exception:rejected+=1
            if not entries:raise BackupError('Nessuna copia valida trovata; i file sono conservati')
            atomic_write_json(self.catalog,{'version':1,'enabled':True,
                'counter':max(e['sequence'] for e in entries),'entries':entries})
            return {'verified':len(entries),'rejected':rejected}

    def latest(self):
        index=self._index()
        if not index['entries']:raise BackupError('Crea prima una copia verificata')
        entry=max(index['entries'],key=lambda e:e['sequence']);path=self.directory/entry['id']
        if not path.is_file() or path.is_symlink() or file_digest(path)!=entry['sha256']:
            raise BackupError('La copia più recente è mancante o danneggiata; le altre sono conservate')
        return path

    def verify_latest(self):
        with self.lock:
            manifest=verify_archive(self.latest(),primary=self.primary)
            return {'verified':True,'files':len(manifest['files']),'created':manifest['created']}

    def export(self,target,password):
        from .backup_crypto import encrypt_backup
        with self.lock:
            source=self.latest();verify_archive(source,primary=self.primary)
            return encrypt_backup(source,target,password)

    def stage_encrypted_restore(self,archive,password):
        from .backup_crypto import decrypt_backup
        from .state_restore import stage_restore
        with tempfile.TemporaryDirectory(prefix='.allma-import-',dir=self.root.parent) as temporary:
            plain=Path(temporary)/'verified.zip'
            decrypt_backup(archive,plain,password)
            return stage_restore(self.root,plain,primary=self.primary)
