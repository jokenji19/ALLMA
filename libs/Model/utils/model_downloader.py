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
                # Update to Gemma 3n (Google's latest efficient model)
                "url": "https://huggingface.co/bartowski/google_gemma-3n-E2B-it-GGUF/resolve/main/google_gemma-3n-E2B-it-Q4_K_M.gguf",
                "filename": "gemma-3n-e2b-it-q4_k_m.gguf",
                "size_mb": 1600 # Approx size for 2B Q4
            },
            "moondream": {
                "url": "https://huggingface.co/ggml-org/moondream2-20250414-GGUF/resolve/main/moondream2-mmproj-f16-20250414.gguf",
                "filename": "moondream2-mmproj-f16-20250414.gguf",
                "size_mb": 910,
                "description": "Moondream (Visione)"
            },
            "emotion": {
                "url": "https://huggingface.co/j-hartmann/emotion-english-distilroberta-base/resolve/main/pytorch_model.bin", # Scarichiamo il binario PyTorch standard
                # Nota: Per usarlo con ONNX o GGUF servirebbe conversione, ma per ora proviamo a scaricare la cartella o il file principale.
                # Meglio: Usiamo una versione ONNX quantizzata se esiste, o scarichiamo i file config.
                # Per semplicità ora, scarichiamo un pacchetto zip che poi estraiamo, o simuliamo il download se usiamo API online.
                # MA dato che siamo offline-first, scarichiamo il modello ONNX che è più portabile su Android.
                "url": "https://huggingface.co/Xenova/emotion-english-distilroberta-base/resolve/main/onnx/model_quantized.onnx",
                "filename": "emotion_model.onnx",
                "size_mb": 80
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
            response = requests.get(url, stream=True, timeout=30) # Add timeout
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

    def start_background_download(self, model_keys, progress_callback, completion_callback):
        """Avvia il download in un thread separato. completion_callback(success, error_msg)"""
        def _download_thread():
            success_all = True
            last_error = None
            
            for key in model_keys:
                success, error = self.download_model(key, lambda d, t: progress_callback(key, d, t))
                if not success:
                    success_all = False
                    last_error = error
                    break
            
            completion_callback(success_all, last_error)

        Thread(target=_download_thread).start()
