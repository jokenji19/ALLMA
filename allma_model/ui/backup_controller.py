"""User-directed encrypted document transfer; passwords remain in memory only."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile
import threading

from allma_model.utils.backup_crypto import decrypt_backup,MAX_ARCHIVE,BackupCryptoError
from allma_model.utils.state_backup import BackupError,verify_archive,check_cancel,BLOCK
from allma_model.utils.state_restore import stage_restore,PENDING


class BackupController:
    CREATE=7841
    OPEN=7842

    def __init__(self,bridge):
        self.bridge=bridge
        self.lock=threading.Lock()
        self.busy=False
        self.pending=None
        self.preview=None
        self.bound=False
        self.closed=False

    @property
    def runtime(self):
        if self.bridge.core is None or not getattr(self.bridge.core,'backups',None):
            raise BackupError('Attendi il caricamento di ALLMA')
        return self.bridge.core.backups

    def update(self,**extra):
        if self.closed:return
        try:payload=self.runtime.store.status()
        except Exception:payload={'available':False,'error':'Attendi il caricamento di ALLMA'}
        payload.update(busy=self.busy,**extra)
        self.bridge.execute_js('window.backupUI && window.backupUI.update('+json.dumps(payload)+')')

    def handle(self,action,request):
        if action=='backup_status':self.update();return
        with self.lock:
            if self.busy:return
            self.busy=True
        self.update(message='Operazione in corso…')
        # Only these fields reach the worker; never log requests/passwords.
        password=request.get('password')
        enabled=request.get('enabled')
        threading.Thread(target=self._run,args=(action,password,enabled),daemon=True,name='ALLMA-BackupUI').start()

    def _run(self,action,password,enabled):
        waiting=False
        try:
            runtime=self.runtime;store=runtime.store
            if action=='backup_configure':
                store.configure(enabled);self.update(message='Preferenza salvata.')
            elif action=='backup_create':
                runtime.create();self.update(message='Copia privata creata e verificata.')
            elif action=='backup_verify':
                store.verify_latest();self.update(message='L’ultima copia ha superato tutti i controlli di integrità.')
            elif action=='backup_repair':
                result=store.repair_catalog()
                self.update(message=f"Copie valide: {result['verified']}. Copie da controllare: {result['rejected']}. Nessun file rimosso.")
            elif action in ('backup_export','backup_import'):
                from allma_model.utils.backup_crypto import _password
                _password(password)  # Reject before opening the document picker.
                self._clear_preview()
                temporary=tempfile.mkdtemp(prefix='.allma-transfer-',dir=store.root.parent)
                self.pending={'directory':temporary,'password':password,'action':action}
                if action=='backup_export':
                    runtime.create()
                    store.export(Path(temporary)/'copy.allma',password)
                    self.pending.pop('password',None)
                self._picker(action=='backup_export');waiting=True
            elif action=='backup_confirm_restore':
                if self.preview is None:raise BackupError('Seleziona e verifica prima un backup cifrato')
                with runtime.idle():
                    # Preserve a known-good snapshot before preparing replacement.
                    previous_verified=True
                    try:
                        store.create(cancel_event=runtime.cancel)
                    except (ValueError,sqlite3.DatabaseError):
                        # A damaged source is a reason to restore. Preserve its
                        # entire directory at startup, without calling it valid.
                        previous_verified=False
                    check_cancel(runtime.cancel)
                    if self.closed:raise BackupError('Operazione interrotta')
                    stage_restore(store.root,Path(self.preview['directory'])/'verified.zip')
                self._clear_preview()
                self.update(restart_required=True,previous_copy_verified=previous_verified,
                    message='Ripristino preparato. Chiudi ALLMA dalle app recenti e riaprila. '+
                    ('Lo stato precedente resta conservato.' if previous_verified else
                     'Lo stato attuale contiene errori: conserveremo integralmente anche quei file per il recupero, senza dichiararli verificati.'))
            elif action=='backup_cancel_restore':
                self._clear_preview();self.update(preview=None,message='Ripristino annullato. I dati attuali restano attivi.')
            else:raise BackupError('Comando di backup non disponibile')
        except (BackupError,BackupCryptoError) as error:
            self._clear_pending()
            self.update(error=str(error))
        except Exception:
            self._clear_pending()
            self.update(error='Operazione non completata. I dati attuali e le copie precedenti sono conservati.')
        finally:
            if not waiting:
                self.busy=False;self.update()

    def _picker(self,export):
        if self.closed:raise BackupError('Operazione interrotta')
        if not self.bridge.is_android:raise BackupError('Il salvataggio nei documenti è disponibile nell’app Android')
        from android import activity
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
        if not self.bound:
            activity.bind(on_activity_result=self._result);self.bound=True
        @run_on_ui_thread
        def launch():
            if self.closed:return
            try:
                Intent=autoclass('android.content.Intent')
                intent=Intent(Intent.ACTION_CREATE_DOCUMENT if export else Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType('application/octet-stream' if export else '*/*')
                if export:intent.putExtra(Intent.EXTRA_TITLE,'ALLMA-backup.allma')
                autoclass('org.kivy.android.PythonActivity').mActivity.startActivityForResult(intent,self.CREATE if export else self.OPEN)
            except Exception:
                self._clear_pending();self.busy=False
                self.update(error='Non riesco ad aprire i documenti Android. Riprova.')
        launch()

    def _result(self,request_code,result_code,intent):
        if request_code not in (self.CREATE,self.OPEN):return
        if self.closed:return
        if result_code!=-1 or intent is None or intent.getData() is None:
            self._clear_pending();self.busy=False;self.update(message='Selezione annullata.');return
        uri=intent.getData()
        threading.Thread(target=self._transfer,args=(uri,request_code==self.CREATE),daemon=True,name='ALLMA-DocumentTransfer').start()

    def _transfer(self,uri,export):
        try:
            if not self.pending:raise BackupError('Selezione scaduta. Riprova.')
            from jnius import autoclass
            resolver=autoclass('org.kivy.android.PythonActivity').mActivity.getContentResolver()
            descriptor=resolver.openFileDescriptor(uri,'wt' if export else 'r')
            if descriptor is None:raise BackupError('Documento non disponibile')
            try:
                # Own only a duplicate. Android retains ownership of the original.
                with os.fdopen(os.dup(descriptor.getFd()),'wb' if export else 'rb') as remote:
                    path=Path(self.pending['directory'])/'copy.allma'
                    with path.open('rb' if export else 'wb') as local:
                        reader,writer=(local,remote) if export else (remote,local)
                        total=0
                        while True:
                            if self.closed:raise BackupError('Operazione interrotta')
                            block=reader.read(BLOCK)
                            if not block:break
                            total+=len(block)
                            if total>MAX_ARCHIVE+1024**2:raise BackupError('Backup oltre il limite del formato')
                            writer.write(block)
                        writer.flush()
                        if not export:os.fsync(writer.fileno())
            finally:descriptor.close()
            if export:
                self.update(message='Copia cifrata salvata nella posizione scelta. Conserva anche la password.')
            else:
                plain=Path(self.pending['directory'])/'verified.zip'
                decrypt_backup(path,plain,self.pending.pop('password'))
                manifest=verify_archive(plain)
                self.preview={'directory':self.pending['directory']}
                self.pending=None
                self.update(preview={'created':manifest['created'],'files':len(manifest['files'])},
                    message='Backup decifrato e verificato. Conferma per sostituire lo stato al prossimo avvio; l’attuale sarà conservato.')
        except (BackupError,BackupCryptoError) as error:self.update(error=str(error))
        except Exception:self.update(error='Trasferimento non completato. I dati attuali restano protetti; elimina l’eventuale file esterno incompleto.')
        finally:
            self._clear_pending();self.busy=False;self.update()

    def _clear_pending(self):
        value,self.pending=self.pending,None
        if value:shutil.rmtree(value['directory'],ignore_errors=True)

    def _clear_preview(self):
        value,self.preview=self.preview,None
        if value:shutil.rmtree(value['directory'],ignore_errors=True)

    def close(self):
        self.closed=True
        if self.bound:
            from android import activity
            activity.unbind(on_activity_result=self._result);self.bound=False
        # A worker may still be using a file; unlinking temporary copies is safe
        # for open descriptors. No authoritative state or exported file removed.
        self._clear_pending();self._clear_preview()
