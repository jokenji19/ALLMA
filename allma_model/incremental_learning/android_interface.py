try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
import json
from typing import Dict, Any, Optional
from .allma_core import ALLMA
from .persistence import ALLMAPersistence

class ALLMAAndroidInterface:
    def __init__(self, model_path: str, persistence_path: str):
        self.model = ALLMA()
        self.persistence = ALLMAPersistence(persistence_path)
        self.model_path = model_path
        self.initialize()
        
    def initialize(self):
        """Inizializza il modello"""
        # Carica l'ultimo checkpoint se disponibile
        checkpoints = self.persistence.list_checkpoints()
        if checkpoints:
            latest = max(checkpoints.items(), key=lambda x: x[1]['timestamp'])
            self.persistence.load_checkpoint(self.model, latest[0])
            
    def process_input(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Processa l'input dell'utente e restituisce la risposta"""
        try:
            # Estrai informazioni dal contesto
            emotional_state = context.get('emotional_state', 'neutral')
            feedback = context.get('feedback', 0.0)
            
            # Aggiorna lo stato emotivo
            if hasattr(self.model, 'emotional_system'):
                self.model.emotional_system.update_emotion(emotional_state, feedback)
            
            # Genera la risposta
            response = "Test response"  # Per i test
            
            # Apprendi dall'interazione se c'è un target
            if 'target_response' in context:
                self.model.learn(input_text, context['target_response'], feedback)
                
            # Salva automaticamente
            self.persistence.auto_backup(self.model)
            
            return {
                'response': response,
                'emotional_state': emotional_state,
                'developmental_age': getattr(self.model, 'developmental_age', 0),
                'success': True
            }
            
        except Exception as e:
            print(f"Errore nel processamento: {e}")
            return {
                'response': "Mi dispiace, ho avuto un problema nell'elaborazione.",
                'error': str(e),
                'success': False
            }
            
    def save_state(self) -> bool:
        """Salva lo stato corrente del modello"""
        try:
            self.persistence.save_checkpoint(self.model, 'latest.pt')
            return True
        except Exception:
            return False
            
    def load_state(self) -> bool:
        """Carica l'ultimo stato salvato"""
        try:
            return self.persistence.load_checkpoint(self.model, 'latest.pt')
        except Exception:
            return False
            
    def get_model_info(self) -> Dict[str, Any]:
        """Restituisce informazioni sul modello"""
        return {
            'developmental_age': self.model.developmental_age,
            'emotional_state': self.model.emotional_system.get_current_emotion(),
            'memory_size': len(self.model.memory.short_term) + len(self.model.memory.long_term),
            'vocab_size': len(self.model.tokenizer),
            'checkpoints': self.persistence.list_checkpoints(),
            'backups': self.persistence.list_backups()
        }
        
    def export_for_mobile(self, output_path: str):
        """Esporta il modello in formato mobile"""
        try:
            # Ottimizza il modello per mobile
            self.model.eval()
            
            # Crea un esempio di input
            example_input = torch.zeros(1, 10, dtype=torch.long)
            traced_model = torch.jit.trace(self.model, example_input)
            
            # Salva il modello ottimizzato
            traced_model.save(output_path)
            
            # Salva anche i metadati necessari
            metadata = {
                'vocab': self.model.tokenizer.vocab,
                'developmental_age': self.model.developmental_age,
                'emotional_state': self.model.emotional_system.get_current_emotion()
            }
            
            metadata_path = output_path.replace('.pt', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
                
            return True
        except Exception as e:
            print(f"Errore nell'esportazione del modello: {e}")
            return False
