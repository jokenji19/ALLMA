"""
Sistema di Auto-Diagnosi
Simula la capacità del cervello di monitorare il proprio stato e auto-regolarsi
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass
from contextlib import contextmanager
import time

@dataclass
class SystemState:
    """Rappresenta lo stato del sistema in un dato momento"""
    memory_usage: float  # Percentuale di memoria utilizzata
    processing_load: float  # Carico di elaborazione
    response_times: List[float]  # Tempi di risposta recenti
    error_count: int  # Numero di errori recenti
    last_maintenance: datetime  # Ultima manutenzione
    cognitive_load: float  # Carico cognitivo stimato
    attention_level: float  # Livello di attenzione stimato

class DiagnosticSystem:
    def __init__(self):
        """
        Inizializza il sistema di auto-diagnosi.
        Come il cervello umano, parte con la capacità innata di monitorare il proprio stato.
        """
        self.state_history = []
        self.error_log = []
        self.performance_thresholds = {
            'memory_critical': 0.7,    # Abbassiamo la soglia al 70%
            'load_critical': 0.6,      # Abbassiamo la soglia al 60%
            'response_time_max': 0.5,   # Abbassiamo a 0.5 secondi
            'error_rate_max': 0.05     # Abbassiamo al 5%
        }
        self.current_state = SystemState(
            memory_usage=0.0,
            processing_load=0.0,
            response_times=[],
            error_count=0,
            last_maintenance=datetime.now(),
            cognitive_load=0.0,
            attention_level=1.0
        )
        self.recovery_strategies = {}
        self.last_diagnostic = datetime.now()
        
    def monitor_state(self) -> SystemState:
        """
        Monitora lo stato attuale del sistema, come il cervello monitora
        costantemente i propri parametri vitali
        """
        current_time = datetime.now()
        
        # Simula la raccolta di metriche del sistema in modo più sensibile
        memory_usage = min(1.0, len(self.state_history) / 50.0)  # Più sensibile alla memoria
        processing_load = min(1.0, len(self.error_log) / 10.0 + np.random.beta(2, 5))
        
        # Calcola tempi di risposta medi
        if self.current_state and self.current_state.response_times:
            response_times = self.current_state.response_times
        else:
            response_times = []
            
        # Calcola il carico cognitivo
        cognitive_load = self._estimate_cognitive_load()
        
        # Calcola il livello di attenzione
        attention_level = max(0.1, 1.0 - (cognitive_load * 0.8))
        
        self.current_state = SystemState(
            memory_usage=memory_usage,
            processing_load=processing_load,
            response_times=response_times,
            error_count=len(self.error_log),
            last_maintenance=self.last_diagnostic,
            cognitive_load=cognitive_load,
            attention_level=attention_level
        )
        
        self.state_history.append(self.current_state)
        return self.current_state
        
    def _estimate_cognitive_load(self) -> float:
        """
        Stima il carico cognitivo basato su vari fattori,
        simile a come il cervello valuta il proprio sforzo
        """
        if not self.state_history:
            return 0.1  # Carico base minimo
            
        recent_states = self.state_history[-5:]
        
        # Fattori che contribuiscono al carico cognitivo
        avg_memory = np.mean([s.memory_usage for s in recent_states])
        avg_load = np.mean([s.processing_load for s in recent_states])
        error_factor = len(self.error_log) / max(len(self.state_history), 1)
        
        # Combina i fattori con pesi diversi
        cognitive_load = (
            0.4 * avg_memory +
            0.4 * avg_load +
            0.2 * error_factor
        ) + 0.1  # Carico base minimo
        
        return min(1.0, cognitive_load)
        
    def diagnose_issues(self) -> List[Dict]:
        """
        Identifica potenziali problemi, come il cervello che
        riconosce quando qualcosa non va bene
        """
        if not self.current_state:
            return []
            
        issues = []
        state = self.current_state
        
        # Controlla la memoria
        if state.memory_usage > self.performance_thresholds['memory_critical']:
            issues.append({
                'type': 'memory_critical',
                'severity': 'high',
                'description': 'Utilizzo memoria critico'
            })
            
        # Controlla il carico di elaborazione
        if state.processing_load > self.performance_thresholds['load_critical']:
            issues.append({
                'type': 'high_load',
                'severity': 'medium',
                'description': 'Carico di elaborazione elevato'
            })
            
        # Controlla gli errori recenti
        error_rate = len(self.error_log) / max(len(self.state_history), 1)
        if error_rate > self.performance_thresholds['error_rate_max']:
            issues.append({
                'type': 'high_error_rate',
                'severity': 'high',
                'description': 'Tasso di errori elevato'
            })
            
        # Controlla i tempi di risposta
        if state.response_times:
            avg_response = np.mean(state.response_times)
            if avg_response > self.performance_thresholds['response_time_max']:
                issues.append({
                    'type': 'slow_response',
                    'severity': 'medium',
                    'description': 'Tempi di risposta elevati'
                })
                
        # Controlla il carico cognitivo
        if state.cognitive_load > 0.6:  # Abbassiamo la soglia
            issues.append({
                'type': 'cognitive_overload',
                'severity': 'high',
                'description': 'Sovraccarico cognitivo'
            })
            
        # Controlla il livello di attenzione
        if state.attention_level < 0.4:  # Aggiungiamo questo controllo
            issues.append({
                'type': 'low_attention',
                'severity': 'medium',
                'description': 'Livello di attenzione basso'
            })
            
        return issues
        
    def self_repair(self, issues: List[Dict]) -> bool:
        """
        Tenta di risolvere i problemi identificati, come il cervello
        che cerca di ripristinare l'equilibrio
        """
        if not issues:
            return True
            
        repairs_made = False
        for issue in issues:
            if issue['type'] == 'memory_critical':
                # Pulizia memoria
                if len(self.state_history) > 50:
                    self.state_history = self.state_history[-50:]
                if len(self.error_log) > 20:
                    self.error_log = self.error_log[-20:]
                repairs_made = True
                
            elif issue['type'] == 'high_load':
                # Riduce il carico
                self.performance_thresholds['load_critical'] *= 1.1  # Temporaneamente più tollerante
                time.sleep(0.1)  # Breve pausa
                repairs_made = True
                
            elif issue['type'] == 'high_error_rate':
                # Reset error log
                self.error_log = []
                repairs_made = True
                
            elif issue['type'] == 'cognitive_overload':
                # Riduce il carico cognitivo
                self.performance_thresholds['load_critical'] *= 1.2
                if len(self.state_history) > 30:
                    self.state_history = self.state_history[-30:]
                repairs_made = True
                
            elif issue['type'] == 'low_attention':
                # Aumenta il livello di attenzione
                if self.current_state:
                    self.current_state.attention_level = min(1.0, self.current_state.attention_level * 1.5)
                repairs_made = True
                
        self.last_diagnostic = datetime.now()
        return repairs_made
        
    @contextmanager
    def monitoring(self):
        """
        Context manager per monitorare un blocco di codice,
        come il cervello che presta particolare attenzione a un compito
        """
        start_time = time.time()
        try:
            yield
        except Exception as e:
            self.error_log.append({
                'time': datetime.now(),
                'error': str(e),
                'state': self.current_state
            })
            raise
        finally:
            duration = time.time() - start_time
            if self.current_state:
                self.current_state.response_times.append(duration)
                
    def get_health_report(self) -> Dict:
        """
        Genera un rapporto sullo stato di salute del sistema,
        come un check-up completo del cervello
        """
        if not self.current_state:
            return {'status': 'unknown'}
            
        state = self.current_state
        issues = self.diagnose_issues()
        
        return {
            'status': 'healthy' if not issues else 'issues_detected',
            'memory_health': 1.0 - state.memory_usage,
            'processing_health': 1.0 - state.processing_load,
            'cognitive_health': 1.0 - state.cognitive_load,
            'attention_level': state.attention_level,
            'issues_count': len(issues),
            'last_maintenance': state.last_maintenance.isoformat(),
            'recommendations': [issue['description'] for issue in issues]
        }
