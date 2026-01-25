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
        
        # URL dei modelli (Gemma 3n E2B IT Quantizzato e Moondream2)
        # Nota: Usiamo link diretti a HuggingFace GGUF
        self.models = {
            "gemma": {
                # Hermes 3 (Llama 3.2 3B) Q4_K_M - The "Rebel" AI (Uncensored/Creative)
                "url": "https://huggingface.co/NousResearch/Hermes-3-Llama-3.2-3B-GGUF/resolve/main/Hermes-3-Llama-3.2-3B.Q4_K_M.gguf",
                "filename": "Hermes-3-Llama-3.2-3B.Q4_K_M.gguf",
                "size_mb": 2000 
            },
            "moondream": {
                "url": "https://huggingface.co/ggml-org/moondream2-20250414-GGUF/resolve/main/moondream2-mmproj-f16-20250414.gguf",
                "filename": "moondream2-mmproj-f16-20250414.gguf",
                "size_mb": 910,
                "description": "Moondream (Visione)"
            },

        }

    def _get_models_dir(self):
        """Restituisce la cartella dove salvare i modelli."""
        if platform == 'android':
            from android.storage import app_storage_path
            # Salviamo nella root di files/ per persistenza sicura
            # app_storage_path returns /data/user/0/org.../files
            return os.path.join(app_storage_path(), 'models')
        else:
            # Desktop (macOS/Linux/Windows)
            return os.path.join(os.getcwd(), 'models')

    def check_models_missing(self):
        """Ritorna la lista dei modelli mancanti."""
        self.logger.info(f"[DEBUG] Models Dir: {self.models_dir}")
        missing = []
        if not os.path.exists(self.models_dir):
            self.logger.info(f"[DEBUG] Models dir does not exist.")
            return list(self.models.keys())
            
        for key, info in self.models.items():
            path = os.path.join(self.models_dir, info['filename'])
            exists = os.path.exists(path)
            self.logger.info(f"[DEBUG] Checking {key} at {path} -> Exists: {exists}")
            
            if not exists:
                missing.append(key)
            else:
                size = os.path.getsize(path)
                self.logger.info(f"[DEBUG] File size for {key}: {size} bytes")
                # Controllo dimensione minima (tolleranza 10%)
                expected_mb = info.get('size_mb', 100)
                min_size = (expected_mb * 1024 * 1024) * 0.9
                if size < min_size: 
                    self.logger.warning(f"[DEBUG] File for {key} is too small ({size} bytes < {min_size}), marking as missing/corrupt.")
                    try:
                        os.remove(path) # Remove corrupt file immediately
                        self.logger.info(f"[DEBUG] Corrupt file {path} deleted.")
                    except OSError:
                        pass
                    missing.append(key)
        return missing

    def download_model(self, model_key, progress_callback=None):
        """
        Scarica un modello specifico.
        
        Args:
            model_key: Chiave del modello ('gemma' o 'moondream')
            progress_callback: Funzione(current_bytes, total_bytes) chiamata durante il download
            
        Returns:
            (bool, str): (Successo, Messaggio Errore)
        """
        if model_key not in self.models:
            msg = f"Modello sconosciuto: {model_key}"
            self.logger.error(msg)
            return False, msg

        info = self.models[model_key]
        url = info['url']
        filename = info['filename']
        
        if not os.path.exists(self.models_dir):
            try:
                os.makedirs(self.models_dir)
            except OSError as e:
                return False, f"FS Error: {e}"
            
        path = os.path.join(self.models_dir, filename)
        self.logger.info(f"Inizio download {model_key} in {path}")

        try:
            # FIX: Add headers to look like a browser to avoid 401 on some HF repos
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, stream=True, timeout=30, headers=headers) 
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
            return True, None
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error {e.response.status_code}"
            self.logger.error(f"Errore download {model_key}: {e}")
            if os.path.exists(path): os.remove(path)
            return False, error_msg
        except requests.exceptions.ConnectionError:
            error_msg = "No Internet / Connection Failed"
            if os.path.exists(path): os.remove(path)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)[:50]}" # Truncate long errors
            self.logger.error(f"Errore download {model_key}: {e}")
            if os.path.exists(path): os.remove(path)
            return False, error_msg

    def start_background_download(self, model_keys, progress_callback, completion_callback, on_model_complete=None):
        """Avvia il download in un thread separato. completion_callback(success, error_msg)"""
        def _download_thread():
            success_all = True
            last_error = None
            
            for key in model_keys:
                success, error = self.download_model(key, lambda d, t: progress_callback(key, d, t))
                if success:
                    if on_model_complete:
                        try:
                            on_model_complete(key)
                        except Exception as e:
                            self.logger.error(f"Error in on_model_complete: {e}")
                else:
                    success_all = False
                    last_error = error
                    break
            
            completion_callback(success_all, last_error)

        Thread(target=_download_thread).start()
