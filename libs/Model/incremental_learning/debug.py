"""
Sistema di debug per ALLMA
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

class ALLMADebugger:
    """Sistema di debug per monitorare e analizzare il comportamento di ALLMA"""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Inizializza il debugger
        
        Args:
            log_file: Percorso del file di log (opzionale)
        """
        self.logger = logging.getLogger('ALLMA')
        self.logger.setLevel(logging.DEBUG)
        
        # Formattatore per i log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Handler per la console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # Handler per il file se specificato
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        # Metriche di debug
        self.metrics = {
            'memory_accesses': 0,
            'emotional_updates': 0,
            'learning_events': 0,
            'errors': 0
        }
        
        # Trace delle operazioni
        self.operation_trace: List[Dict] = []
        
    def log_memory_access(self, operation: str, details: Dict):
        """Registra un accesso alla memoria"""
        self.metrics['memory_accesses'] += 1
        self.logger.debug(f"Memory Access - {operation}: {details}")
        self.operation_trace.append({
            'type': 'memory',
            'operation': operation,
            'details': details,
            'timestamp': datetime.now()
        })
        
    def log_emotional_update(self, state: Dict, trigger: str):
        """Registra un aggiornamento dello stato emotivo"""
        self.metrics['emotional_updates'] += 1
        self.logger.debug(f"Emotional Update - Trigger: {trigger}, State: {state}")
        self.operation_trace.append({
            'type': 'emotional',
            'trigger': trigger,
            'state': state,
            'timestamp': datetime.now()
        })
        
    def log_learning_event(self, event_type: str, details: Dict):
        """Registra un evento di apprendimento"""
        self.metrics['learning_events'] += 1
        self.logger.debug(f"Learning Event - {event_type}: {details}")
        self.operation_trace.append({
            'type': 'learning',
            'event': event_type,
            'details': details,
            'timestamp': datetime.now()
        })
        
    def log_error(self, error: Exception, context: Dict):
        """Registra un errore"""
        self.metrics['errors'] += 1
        self.logger.error(f"Error: {str(error)}, Context: {context}")
        self.operation_trace.append({
            'type': 'error',
            'error': str(error),
            'context': context,
            'timestamp': datetime.now()
        })
        
    def get_metrics(self) -> Dict:
        """Restituisce le metriche correnti"""
        return self.metrics
        
    def get_operation_trace(self) -> List[Dict]:
        """Restituisce la traccia delle operazioni"""
        return self.operation_trace
        
    def analyze_performance(self) -> Dict:
        """Analizza le performance del sistema"""
        total_operations = sum(self.metrics.values())
        error_rate = self.metrics['errors'] / total_operations if total_operations > 0 else 0
        
        return {
            'total_operations': total_operations,
            'error_rate': error_rate,
            'metrics_breakdown': self.metrics
        }
        
    def clear_metrics(self):
        """Resetta le metriche"""
        self.metrics = {k: 0 for k in self.metrics}
        
    def clear_trace(self):
        """Resetta la traccia delle operazioni"""
        self.operation_trace = []
