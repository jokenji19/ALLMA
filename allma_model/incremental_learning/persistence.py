import os
import json
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

class ALLMAPersistence:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.checkpoints_path = os.path.join(base_path, 'checkpoints')
        self.backup_path = os.path.join(base_path, 'backups')
        self.create_directories()
        
    def create_directories(self):
        """Crea le directory necessarie se non esistono"""
        os.makedirs(self.checkpoints_path, exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)
        
    def save_checkpoint(self, model: 'ALLMA', checkpoint_name: str):
        """Salva un checkpoint del modello"""
        checkpoint_path = os.path.join(self.checkpoints_path, checkpoint_name)
        
        # Prepara i dati del modello
        model_state = {
            'model_state_dict': model.state_dict(),
            'tokenizer_vocab': model.tokenizer.vocab,
            'memory_state': {
                'short_term': model.memory.short_term,
                'long_term': model.memory.long_term
            },
            'emotional_state': model.emotional_system.get_current_emotion(),
            'developmental_age': model.developmental_age,
            'timestamp': datetime.now().isoformat()
        }
        
        # Salva il checkpoint
        torch.save(model_state, checkpoint_path)
        
    def load_checkpoint(self, model: 'ALLMA', checkpoint_name: str) -> bool:
        """Carica un checkpoint del modello"""
        checkpoint_path = os.path.join(self.checkpoints_path, checkpoint_name)
        
        if not os.path.exists(checkpoint_path):
            return False
            
        try:
            checkpoint = torch.load(checkpoint_path, weights_only=True)
            
            # Ripristina lo stato del modello
            model.load_state_dict(checkpoint['model_state_dict'])
            model.tokenizer.vocab = checkpoint['tokenizer_vocab']
            model.memory.short_term = checkpoint['memory_state']['short_term']
            model.memory.long_term = checkpoint['memory_state']['long_term']
            model.developmental_age = checkpoint['developmental_age']
            model.emotional_system.set_emotion(checkpoint['emotional_state'])
            
            return True
        except Exception as e:
            print(f"Errore nel caricamento del checkpoint: {e}")
            return False
            
    def create_backup(self) -> str:
        """Crea un backup completo del modello"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'backup_{timestamp}'
        backup_dir = os.path.join(self.backup_path, backup_name)
        
        # Crea directory di backup
        os.makedirs(backup_dir)
        
        # Copia tutti i checkpoint
        shutil.copytree(self.checkpoints_path, 
                       os.path.join(backup_dir, 'checkpoints'),
                       dirs_exist_ok=True)
                       
        return backup_name
        
    def restore_backup(self, backup_name: str) -> bool:
        """Ripristina un backup"""
        backup_dir = os.path.join(self.backup_path, backup_name)
        
        if not os.path.exists(backup_dir):
            return False
            
        try:
            # Ripristina i checkpoint
            shutil.rmtree(self.checkpoints_path)
            shutil.copytree(os.path.join(backup_dir, 'checkpoints'),
                          self.checkpoints_path)
            return True
        except Exception as e:
            print(f"Errore nel ripristino del backup: {e}")
            return False
            
    def list_checkpoints(self) -> Dict[str, Any]:
        """Lista tutti i checkpoint disponibili con i loro metadati"""
        checkpoints = {}
        for checkpoint in os.listdir(self.checkpoints_path):
            path = os.path.join(self.checkpoints_path, checkpoint)
            try:
                metadata = torch.load(path, map_location='cpu', weights_only=True)
                checkpoints[checkpoint] = {
                    'timestamp': metadata.get('timestamp'),
                    'developmental_age': metadata.get('developmental_age'),
                    'emotional_state': metadata.get('emotional_state')
                }
            except:
                continue
        return checkpoints
        
    def list_backups(self) -> Dict[str, datetime]:
        """Lista tutti i backup disponibili"""
        backups = {}
        for backup in os.listdir(self.backup_path):
            path = os.path.join(self.backup_path, backup)
            if os.path.isdir(path):
                try:
                    timestamp = datetime.strptime(backup.split('_')[1], '%Y%m%d_%H%M%S')
                    backups[backup] = timestamp
                except:
                    continue
        return backups
        
    def auto_backup(self, model: 'ALLMA', interval_hours: int = 24):
        """Esegue backup automatico se è passato abbastanza tempo"""
        backups = self.list_backups()
        if not backups:
            self.create_backup()
            self.save_checkpoint(model, 'latest.pt')
            return
            
        latest_backup = max(backups.values())
        hours_since_backup = (datetime.now() - latest_backup).total_seconds() / 3600
        
        if hours_since_backup >= interval_hours:
            self.create_backup()
            self.save_checkpoint(model, 'latest.pt')
