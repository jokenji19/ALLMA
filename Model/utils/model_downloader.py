import os
import requests
import logging
from kivy.utils import platform
from threading import Thread

class ModelDownloader:
    """
    Gestisce il download dei modelli AI (GGUF) per l'esecuzione locale su Android.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models_dir = self._get_models_dir()
        
        # URL dei modelli (Gemma 2B IT Quantizzato e Moondream2)
        # Nota: Usiamo link diretti a HuggingFace GGUF
        self.models = {
            "gemma": {
                "url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
                "filename": "gemma-2b-it-q4_k_m.gguf",
                "size_mb": 1800
            },
            "moondream": {
                "url": "https://huggingface.co/vikhyatk/moondream2/resolve/main/moondream2-text-model.gguf", # Placeholder URL, va verificato quello corretto per GGUF
                "filename": "moondream2.gguf",
                "size_mb": 500
            }
        }

    def _get_models_dir(self):
        """Restituisce la cartella dove salvare i modelli."""
        if platform == 'android':
            from android.storage import app_storage_path
            # Salviamo nella cartella privata dell'app per evitare permessi complessi di Scoped Storage
            # o nella cartella files interna
            return os.path.join(app_storage_path(), 'app', 'models')
        else:
            # Desktop (macOS/Linux/Windows)
            return os.path.join(os.getcwd(), 'models')

    def check_models_missing(self):
        """Ritorna la lista dei modelli mancanti."""
        missing = []
        if not os.path.exists(self.models_dir):
            return list(self.models.keys())
            
        for key, info in self.models.items():
            path = os.path.join(self.models_dir, info['filename'])
            if not os.path.exists(path):
                missing.append(key)
            else:
                # Controllo dimensione minima (se il download è fallito ed è 0 byte)
                if os.path.getsize(path) < 1024 * 1024: # < 1MB
                    missing.append(key)
        return missing

    def download_model(self, model_key, progress_callback=None):
        """
        Scarica un modello specifico.
        
        Args:
            model_key: Chiave del modello ('gemma' o 'moondream')
            progress_callback: Funzione(current_bytes, total_bytes) chiamata durante il download
        """
        if model_key not in self.models:
            self.logger.error(f"Modello sconosciuto: {model_key}")
            return False

        info = self.models[model_key]
        url = info['url']
        filename = info['filename']
        
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)
            
        path = os.path.join(self.models_dir, filename)
        self.logger.info(f"Inizio download {model_key} in {path}")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)
                            
            self.logger.info(f"Download completato: {model_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore download {model_key}: {e}")
            if os.path.exists(path):
                os.remove(path) # Rimuovi file parziale
            return False

    def start_background_download(self, model_keys, progress_callback, completion_callback):
        """Avvia il download in un thread separato."""
        def _download_thread():
            success = True
            for key in model_keys:
                if not self.download_model(key, lambda d, t: progress_callback(key, d, t)):
                    success = False
                    break
            completion_callback(success)

        Thread(target=_download_thread).start()
