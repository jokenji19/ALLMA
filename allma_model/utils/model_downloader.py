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
            "vyvotts": {
                "url": "https://huggingface.co/prithivMLmods/VyvoTTS-v0-Qwen3-0.6B-GGUF/resolve/main/VyvoTTS-v0-Qwen3-0.6B.Q4_K_M.gguf",
                "filename": "VyvoTTS-v0-Qwen3-0.6B.Q4_K_M.gguf",
                "size_mb": 402,
                "description": "VyvoTTS (Voce)"
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
                expected_mb = info.get('size_mb', 100)
                expected_bytes_min = (expected_mb * 1024 * 1024) * 0.99
                
                self.logger.info(f"[DEBUG] File size for {key}: {size} bytes (Expected > {expected_bytes_min})")
                
                if size < expected_bytes_min:
                    # File exists but is smaller than expected.
                    # DO NOT DELETE IT. We will try to RESUME it.
                    self.logger.info(f"[DEBUG] File {key} is incomplete ({size} bytes). Marking for Resume.")
                    missing.append(key)
                else:
                    self.logger.info(f"[DEBUG] File {key} seems complete.")
                    
        return missing

    def download_model(self, model_key, progress_callback=None):
        """
        Scarica un modello specifico con supporto RESUME e RETRY.
        """
        if model_key not in self.models:
            return False, f"Modello sconosciuto: {model_key}"

        info = self.models[model_key]
        url = info['url']
        filename = info['filename']
        
        if not os.path.exists(self.models_dir):
            try: os.makedirs(self.models_dir)
            except OSError as e: return False, f"FS Error: {e}"
            
        path = os.path.join(self.models_dir, filename)
        
        # --- RESUME LOGIC ---
        resume_byte_pos = 0
        file_mode = 'wb'
        if os.path.exists(path):
            resume_byte_pos = os.path.getsize(path)
            file_mode = 'ab' # Append mode
            self.logger.info(f"[Resuming] {model_key} from byte {resume_byte_pos}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Android 10; Mobile; rv:91.0) Gecko/91.0 Firefox/91.0'
        }
        if resume_byte_pos > 0:
            headers['Range'] = f"bytes={resume_byte_pos}-"

        # --- RETRY LOOP ---
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.logger.info(f"[Download] {model_key} Attempt {attempt+1}/{max_retries}")
                
                # Timeout increased to 60s for slow starts
                with requests.get(url, stream=True, timeout=60, headers=headers) as response:
                    
                    # Handle Range Not Satisfiable (416) -> Likely file is already done
                    if response.status_code == 416:
                         self.logger.info(f"[Download] 416 Range Not Satisfiable. File likely complete.")
                         return True, None

                    response.raise_for_status()
                    
                    # Content-Length is only the remaining chunk if 206 Partial Content
                    total_size = int(response.headers.get('content-length', 0))
                    total_downloaded = resume_byte_pos
                    full_file_size = total_size + resume_byte_pos
                    
                    with open(path, file_mode) as f:
                        # Increased chunk size to 64KB for better throughput
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                total_downloaded += len(chunk)
                                if progress_callback:
                                    progress_callback(total_downloaded, full_file_size)
                
                # If we get here, download finished cleanly
                self.logger.info(f"Download completato: {model_key}")
                return True, None
                
            except (requests.exceptions.RequestException, IOError) as e:
                self.logger.error(f"[Download Error] Attempt {attempt+1}: {e}")
                # If error, update resume position for next try
                if os.path.exists(path):
                    resume_byte_pos = os.path.getsize(path)
                    headers['Range'] = f"bytes={resume_byte_pos}-"
                    file_mode = 'ab'
                
                # If it was IncompleteRead, the loop continues immediately
                # If it's the last attempt, fail.
                if attempt == max_retries - 1:
                    return False, f"Failed after {max_retries} attempts: {str(e)[:50]}"
                
                import time
                time.sleep(2) # Wait a bit before retry

        return False, "Unknown Error"

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
