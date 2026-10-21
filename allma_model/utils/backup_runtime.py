"""Quiescent, cancellable snapshots. Foreground work always has priority."""
from contextlib import contextmanager
from pathlib import Path
import logging
import math
import threading

from .state_backup import StateBackups,BackupError,check_cancel
from .state_restore import PENDING


class BackupRuntime:
    def __init__(self,core):
        self.core=core
        self.store=StateBackups(Path(core.db_path).resolve().parent,primary=Path(core.db_path).name)
        self.cancel=threading.Event()
        self.worker=None

    def start(self):
        # Opt in only for the managed Android directory; unit tests and desktop
        # callers must not gain unexpected background filesystem activity.
        if self.store.root.name=='allma_state' and self.worker is None:
            self.worker=threading.Thread(target=self._loop,daemon=True,name='ALLMA-Backup')
            self.worker.start()

    def interrupt(self):
        self.cancel.set()

    def close(self):
        self.interrupt()
        if self.worker and self.worker is not threading.current_thread():self.worker.join(timeout=2)

    @contextmanager
    def idle(self):
        core=self.core
        self.cancel.clear()
        if not core._turn_lock.acquire(blocking=False):
            raise BackupError('Attendi la fine della conversazione prima di copiare i dati')
        reserved=False
        try:
            with core._lock,core.dream_manager._state_lock:
                if (core._shutdown_event.is_set() or core._user_active.is_set()
                        or getattr(core,'_benchmark_active',False) or getattr(core,'_model_switching',False)
                        or core.dream_manager.is_dreaming):
                    raise BackupError('Attendi che conversazione, sogni e diagnostica siano terminati')
                check_cancel(self.cancel)
                core._user_active.set();reserved=True
            yield
        finally:
            if reserved:core._user_active.clear()
            core._turn_lock.release()

    def create(self):
        if (self.store.root.parent/PENDING).exists():
            raise BackupError('Ripristino preparato: riavvia ALLMA prima di continuare')
        with self.idle():
            return self.store.create(cancel_event=self.cancel)

    def _loop(self):
        while not self.core._shutdown_event.wait(60):
            try:
                if not getattr(self.core,'_llm_ready',False) or not self.store.due():continue
                state=self.core.system_monitor.get_metabolic_state()
                if (not math.isfinite(state.energy_level) or not math.isfinite(state.battery_temp_celsius)
                        or state.energy_level<0.2 or not 0<state.battery_temp_celsius<=40):continue
                self.create()
                logging.info('ALLMA_PRIVATE_BACKUP verified')
            except BackupError:
                pass  # Busy/cancelled: retry at the next idle opportunity.
            except Exception as error:
                logging.warning('Private backup deferred: %s',type(error).__name__)
