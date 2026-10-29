"""User-requested downloads and motor changes, independent of personal data."""
import os
import threading
from pathlib import Path
from allma_model.utils.model_downloader import ModelDownloader


class ModelManager:
    def __init__(self, core):
        self.core = core
        self.downloader = ModelDownloader(core.models_dir)
        self._operation = threading.Lock()

    def snapshot(self):
        engine = getattr(self.core, '_llm', None)
        active = Path(engine.model_path).name if engine is not None else None
        return {'models': [dict(key=key, name=info['name'], quantization=info['quantization'],
                               size_bytes=info['size_bytes'], reasoning=info['reasoning'],
                               **self.downloader.local_status(os.path.join(self.core.models_dir, info['filename']), info),
                               active=info['filename'] == active and getattr(self.core, '_llm_ready', False))
                           for key, info in self.downloader.models.items()],
                'busy': self._operation.locked(),
                'selection_required':getattr(self.core,'_model_selection_required',False) is True,
                'selection_message':getattr(self.core,'_mobile_llm_error',None)
                    if getattr(self.core,'_model_selection_required',False) is True else None}

    def apply(self, key, notify):
        if key not in self.downloader.models:
            raise ValueError('Modello non presente nel catalogo')
        if not self._operation.acquire(blocking=False):
            raise RuntimeError('Un cambio di modello è già in corso')
        try:
            if (self.core._user_active.is_set() or getattr(self.core, '_benchmark_active', False)
                    or self.core.dream_manager.is_dreaming or self.core._shutdown_event.is_set()):
                raise RuntimeError('Attendi la fine della risposta, del benchmark o del sogno')
            info = self.downloader.models[key]
            notify({'phase': 'verifying', 'key': key})
            success, error = self.downloader.download_model(key,
                lambda current, total: notify({'phase': 'download', 'key': key,
                                              'progress': current/total if total else 0}))
            if not success:
                raise RuntimeError(error or 'Download non riuscito')
            notify({'phase': 'loading', 'key': key})
            result = self.core.switch_model(info['filename'], reasoning=info['reasoning'])
            return result
        finally:
            self._operation.release()
