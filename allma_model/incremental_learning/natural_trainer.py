import json
import time
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    Dataset = object
    DataLoader = None
    F = None
    TORCH_AVAILABLE = False

from .metrics import Metrics
from .emotional_system import EmotionalSystem
from .memory_system import Memory
from .curiosity_system import CuriosityDrive
from .initial_experiences import Experience, DevelopmentalStage

@dataclass
class TrainingMetrics:
    """Metriche per monitorare lo sviluppo"""
    stage: DevelopmentalStage
    loss: float
    accuracy: float
    emotional_stability: float
    learning_rate: float
    response_coherence: float
    memory_retention: float
    attention_span: float
    developmental_age: float  # Età di sviluppo stimata (in settimane)

class DevelopmentalDataset(Dataset):
    """Dataset che segue lo sviluppo naturale"""
    def __init__(self, experiences_file: str):
        with open(experiences_file, 'r') as f:
            self.experiences = json.load(f)
        
        # Ordina per stadio di sviluppo
        self.experiences.sort(key=lambda x: list(DevelopmentalStage).index(
            DevelopmentalStage(x['stage'])
        ))

    def __len__(self):
        return len(self.experiences)

    def __getitem__(self, idx):
        exp = self.experiences[idx]
        return {
            'input': exp['input'],
            'response': exp['response'],
            'emotion': exp['emotion'],
            'context': exp['context'],
            'stage': exp['stage']
        }

class NaturalTrainer:
    """Trainer che simula lo sviluppo naturale del cervello"""
    def __init__(
        self,
        experiences_file: Optional[str] = None,
        checkpoint_dir: str = "checkpoints",
        learning_rate: float = 0.001,
        batch_size: int = 32
    ):
        self.metrics = Metrics()
        self.emotional_system = EmotionalSystem()
        self.memory = Memory()
        self.curiosity = CuriosityDrive()
        
        if experiences_file:
            self.dataset = DevelopmentalDataset(experiences_file)
            self.dataloader = DataLoader(
                self.dataset,
                batch_size=batch_size,
                shuffle=True
            )
            
            self.optimizer = torch.optim.Adam(
                self.get_model_parameters(),
                lr=learning_rate
            )
            
            self.checkpoint_dir = Path(checkpoint_dir)
            self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Metriche di sviluppo
        self.metrics = TrainingMetrics(
            stage=DevelopmentalStage.SENSORIMOTOR_EARLY,
            loss=0.0,
            accuracy=0.0,
            emotional_stability=0.5,
            learning_rate=learning_rate,
            response_coherence=0.0,
            memory_retention=0.0,
            attention_span=0.1,
            developmental_age=0.0
        )
        
        # Setup logging
        logging.basicConfig(
            filename='development.log',
            level=logging.INFO,
            format='%(asctime)s - %(message)s'
        )

    def train_developmental_stage(
        self,
        stage: DevelopmentalStage,
        num_experiences: int
    ) -> TrainingMetrics:
        """Addestra il modello per uno specifico stadio di sviluppo"""
        if not hasattr(self, 'dataset'):
            raise ValueError("Il file delle esperienze non è stato specificato")
        
        stage_experiences = [
            exp for exp in self.dataset.experiences
            if DevelopmentalStage(exp['stage']) == stage
        ][:num_experiences]
        
        total_loss = 0
        experiences_processed = 0
        
        for exp in stage_experiences:
            # Verifica se è necessario dormire
            if self.memory.needs_sleep():
                self._sleep_cycle()
            
            # Adatta il learning rate in base al periodo critico
            current_lr = self.get_learning_rate(self.metrics.learning_rate)
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = current_lr
            
            # Processa l'esperienza
            loss = self._process_experience(exp)
            total_loss += loss
            experiences_processed += 1
            
            # Aggiorna le metriche
            self._update_metrics(exp, loss)
            
            # Log dello sviluppo
            if experiences_processed % 10 == 0:
                self._log_development_status(stage, experiences_processed, loss)
        
        return self.metrics

    def _process_experience(self, experience: Dict) -> float:
        """Processa una singola esperienza di apprendimento"""
        input_text = experience['input']
        target_response = experience['response']
        emotion = experience.get('emotion', 'neutral')
        context = experience.get('context', {})
        
        # Forward pass
        output = self.process_input(input_text)
        
        # Calcola la loss
        loss = self._calculate_loss(output, target_response, emotion, context)
        
        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        
        # Aggiorna i parametri con il learning rate modificato dal periodo critico
        current_lr = self.get_learning_rate(self.metrics.learning_rate)
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = current_lr
        
        self.optimizer.step()
        
        # Aggiorna il periodo critico
        self.memory.update()
        
        return loss.item()

    def _calculate_loss(self, output: str, target: str, emotion: str, context: Dict) -> 'torch.Tensor':
        """Calcola la loss considerando l'output, il target e il contesto emotivo"""
        # Tokenizza output e target
        output_tokens = self.tokenize(output)
        target_tokens = self.tokenize(target)
        
        # Padding alla stessa lunghezza
        max_len = max(len(output_tokens), len(target_tokens))
        output_padded = F.pad(output_tokens, (0, max_len - len(output_tokens)), value=0)
        target_padded = F.pad(target_tokens, (0, max_len - len(target_tokens)), value=0)
        
        # Calcola la loss base
        base_loss = nn.MSELoss()(output_padded.float(), target_padded.float())
        
        # Modifica la loss in base all'emozione
        emotional_factor = self.emotional_system.get_learning_factor(emotion)
        
        # Considera il contesto
        context_factor = 1.0
        if context.get('physical_state') == 'tired':
            context_factor = 0.8
        
        return base_loss * emotional_factor * context_factor

    def _adjust_gradients_by_emotion(self):
        """Modifica i gradienti in base allo stato emotivo"""
        emotional_state = self.emotional_system.emotions
        
        # Le emozioni positive aumentano l'apprendimento
        learning_boost = (
            emotional_state['joy'] * 1.2 +
            emotional_state['curiosity'] * 1.5
        ) / 2.0
        
        # Applica il boost ai gradienti
        for param in self.get_model_parameters():
            if param.grad is not None:
                param.grad *= learning_boost

    def _sleep_cycle(self):
        """Esegue un ciclo di sonno per consolidare le memorie"""
        logging.info("Iniziando ciclo di sonno...")
        
        # Salva checkpoint prima del sonno
        self._save_checkpoint("pre_sleep")
        
        # Esegue il consolidamento della memoria
        self.memory.sleep_cycle(
            self.memory,
            self.emotional_system
        )
        
        # Aggiorna le metriche post-sonno
        self.metrics.memory_retention *= 1.1  # Il sonno migliora la ritenzione
        
        logging.info("Ciclo di sonno completato")

    def _update_metrics(self, experience: Dict, loss: float):
        """Aggiorna le metriche di sviluppo"""
        # Aggiorna l'età di sviluppo
        self.metrics.developmental_age += 0.01  # Incremento graduale
        
        # Aggiorna la coerenza delle risposte (inverso della loss)
        self.metrics.response_coherence = 1.0 / (1.0 + loss)
        
        # Aggiorna la stabilità emotiva
        emotion = experience['emotion']
        if emotion in ['happy', 'curious']:
            self.metrics.emotional_stability = min(
                1.0,
                self.metrics.emotional_stability * 1.01
            )
        
        # Aggiorna l'attention span
        self.metrics.attention_span = min(
            1.0,
            self.metrics.attention_span + 0.001
        )

    def _log_development_status(
        self,
        stage: DevelopmentalStage,
        experiences: int,
        loss: float
    ):
        """Registra lo stato di sviluppo"""
        status = (
            f"Stadio: {stage.value}\n"
            f"Esperienze: {experiences}\n"
            f"Loss: {loss:.4f}\n"
            f"Età di sviluppo: {self.metrics.developmental_age:.2f} settimane\n"
            f"Stabilità emotiva: {self.metrics.emotional_stability:.2f}\n"
            f"Coerenza risposte: {self.metrics.response_coherence:.2f}\n"
            f"Attenzione: {self.metrics.attention_span:.2f}\n"
            f"Memoria: {self.metrics.memory_retention:.2f}\n"
            f"Learning rate: {self.metrics.learning_rate:.4f}\n"
        )
        logging.info(status)

    def _save_checkpoint(self, prefix: str = ""):
        """Salva un checkpoint del modello"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        checkpoint_path = self.checkpoint_dir / f"{prefix}_checkpoint_{timestamp}.pt"
        
        torch.save({
            'metrics': self.metrics,
            'memory': self.memory.get_recent_interactions(),
            'curiosity': self.curiosity.get_state()
        }, checkpoint_path)

    def get_model_parameters(self):
        # Implementazione base per i test
        return [torch.randn(1, requires_grad=True)]

    def process_input(self, input_text: str) -> Dict:
        """Processa l'input attraverso i vari sistemi"""
        emotional_state = self.emotional_system.process_emotion(input_text)
        self.memory.add_interaction(input_text, "Test response")
        curiosity_response = self.curiosity.process_input(input_text)
        return {
            'emotional_state': emotional_state,
            'curiosity_response': curiosity_response
        }

    def tokenize(self, text: str) -> List[int]:
        # Implementazione base per i test
        return [1, 2, 3]

    def get_learning_rate(self, learning_rate: float) -> float:
        # Implementazione base per i test
        return learning_rate

def main():
    # Crea il trainer
    trainer = NaturalTrainer(
        experiences_file='data/initial_experiences.json'
    )
    
    # Training per ogni stadio di sviluppo
    stages = [
        (DevelopmentalStage.SENSORIMOTOR_EARLY, 100),    # 100 esperienze
        (DevelopmentalStage.SENSORIMOTOR_MID, 200),      # 200 esperienze
        (DevelopmentalStage.SENSORIMOTOR_LATE, 300),     # 300 esperienze
        (DevelopmentalStage.PREOPERATIONAL_EARLY, 200),  # 200 esperienze
        (DevelopmentalStage.PREOPERATIONAL_LATE, 200)    # 200 esperienze
    ]
    
    for stage, num_experiences in stages:
        logging.info(f"\nIniziando stadio di sviluppo: {stage.value}")
        metrics = trainer.train_developmental_stage(stage, num_experiences)
        trainer._save_checkpoint(f"stage_{stage.value}")
        
        logging.info(
            f"Completato stadio {stage.value}\n"
            f"Età di sviluppo: {metrics.developmental_age:.2f} settimane\n"
            f"Stabilità emotiva: {metrics.emotional_stability:.2f}\n"
            f"Coerenza risposte: {metrics.response_coherence:.2f}"
        )

if __name__ == "__main__":
    main()
