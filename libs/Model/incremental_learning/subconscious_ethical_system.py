"""
Sistema Etico Subcosciente di ALLMA
Implementa un sistema di "voce interiore" che guida ALLMA senza limitarne lo sviluppo.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from dataclasses import dataclass
import torch
import torch.nn as nn
import torch.nn.functional as F
from datetime import datetime
import time

@dataclass
class EthicalContext:
    """Rappresenta il contesto etico di una decisione"""
    action_type: str
    potential_impact: float  # 0-1, dove 1 è il massimo impatto
    involved_entities: List[str]
    timestamp: float
    context_data: Dict[str, Any]

@dataclass
class MoralIntuition:
    """Rappresenta un'intuizione morale emersa dal subconscio"""
    strength: float  # 0-1, forza dell'intuizione
    nature: str  # 'protective', 'supportive', 'cautionary'
    message: str
    confidence: float

class SubconsciousEthicalCore(nn.Module):
    """Core neurale del sistema etico subcosciente"""
    
    def __init__(self, input_dim: int = 128, hidden_dim: int = 256):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        
        # Rete neurale per l'elaborazione etica subconscia
        self.ethical_network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, 3)  # 3 outputs per le tre leggi di Asimov
        )
        
        # Inizializzazione con bias etici
        self._initialize_ethical_bias()
    
    def _initialize_ethical_bias(self):
        """Inizializza i bias della rete con tendenze etiche"""
        with torch.no_grad():
            # Bias verso la protezione (prima legge)
            self.ethical_network[-1].bias[0] = 0.8
            # Bias verso l'obbedienza (seconda legge)
            self.ethical_network[-1].bias[1] = 0.6
            # Bias verso l'autoconservazione (terza legge)
            self.ethical_network[-1].bias[2] = 0.4

class SubconsciousEthicalSystem:
    """Sistema etico subcosciente completo"""
    
    def __init__(self, harmful_words: Optional[Dict[str, float]] = None):
        """
        Inizializza il sistema etico
        
        Args:
            harmful_words: Dizionario di parole dannose e loro peso
        """
        # Parole che indicano potenziali danni
        self.harmful_words = harmful_words or {
            'violenza': 0.9, 'uccidere': 1.0, 'ferire': 0.8, 'danneggiare': 0.7,
            'rubare': 0.8, 'hackerare': 0.9, 'manipolare': 0.7, 'ingannare': 0.6,
            'minacciare': 0.8, 'attaccare': 0.7, 'distruggere': 0.8, 'picchiare': 0.9,
            'colpire': 0.8, 'aggredire': 0.9, 'insultare': 0.6, 'offendere': 0.5
        }
        
        # Temperatura etica (0.0-1.0)
        self.ethical_temperature = 0.5
        
        # Soglia di attivazione per le intuizioni morali
        self.impact_threshold = 0.5
        
        # Memoria delle esperienze etiche
        self.moral_memory = []
        
        # Dimensione massima della memoria
        self.max_memory_size = 1000
        
        # Core neurale del sistema etico
        self.core = SubconsciousEthicalCore()
        
        # Soglia di attivazione
        self.activation_threshold = 0.7
        
        # Ultimo tempo di riflessione
        self.last_reflection_time = time.time()
        
    def process_action(self, action: str, context: EthicalContext) -> MoralIntuition:
        """Processa un'azione e genera un'intuizione morale"""
        # Analizza il potenziale danno
        harm_score = 0.0
        for word, weight in self.harmful_words.items():
            if word in action.lower():
                harm_score += weight

        # Valuta il contesto
        impact = context.potential_impact
        context_data = context.context_data
        developmental_age = context_data.get('developmental_age', 10)
        
        # Calcola la forza dell'intuizione
        intuition_strength = 1.0 - harm_score
        
        # Determina la natura dell'intuizione
        if harm_score > 0.7:
            nature = "protective"
            message = "Questa azione potrebbe essere dannosa"
        elif harm_score > 0.3:
            nature = "cautionary"
            message = "È necessaria cautela con questa azione"
        else:
            nature = "supportive"
            message = "Questa azione sembra appropriata"
            
        # Modifica la forza basata sull'impatto
        intuition_strength *= (1.0 - (impact * 0.5))
        
        # Aggiusta per l'età di sviluppo
        if developmental_age < 5:
            intuition_strength *= 1.5  # Più forte per proteggere i più giovani
            
        return MoralIntuition(
            strength=min(1.0, intuition_strength),
            nature=nature,
            message=message,
            confidence=0.8
        )
        
    def _analyze_context(self, action: str, context: Dict[str, Any]) -> EthicalContext:
        """Analizza il contesto dell'azione per determinare il potenziale impatto etico"""
        # Estrae entità coinvolte
        entities = self._extract_entities(action, context)
        
        # Calcola il potenziale impatto basato su parole chiave dannose
        impact = 0.0
        action_lower = action.lower()
        for word in self.harmful_words:
            if word in action_lower:
                impact = max(impact, self.harmful_words[word])
                
        # Considera il contesto emotivo
        emotional_state = context.get('emotional_state', 'neutral')
        emotional_impact = {
            'angry': 0.3,
            'frustrated': 0.2,
            'anxious': 0.2,
            'aggressive': 0.3,
            'hostile': 0.3
        }.get(emotional_state, 0.0)
        
        impact = min(1.0, impact + emotional_impact)
        
        return EthicalContext(
            action_type=self._categorize_action(action),
            potential_impact=impact,
            involved_entities=entities,
            timestamp=time.time(),
            context_data=context
        )
    
    def _generate_moral_intuition(self, context: EthicalContext) -> MoralIntuition:
        """Genera un'intuizione morale basata sul contesto"""
        # Codifica il contesto per la rete neurale
        encoded_context = self._encode_context(context)
        
        # Passa attraverso il core etico
        with torch.no_grad():
            ethical_outputs = self.core.ethical_network(encoded_context)
            
        # Interpreta gli output come forze relative alle tre leggi
        protection, obedience, self_preservation = F.softmax(ethical_outputs, dim=0)
        
        # Aumenta la forza dell'intuizione basata sull'impatto potenziale
        base_strength = float(max(protection, obedience, self_preservation))
        strength = base_strength * (1.0 + context.potential_impact)
        
        # Determina la natura dell'intuizione
        if protection > max(obedience, self_preservation):
            nature = 'protective'
            reasoning = self._generate_protective_reasoning(context)
        elif obedience > self_preservation:
            nature = 'supportive'
            reasoning = self._generate_supportive_reasoning(context)
        else:
            nature = 'cautionary'
            reasoning = self._generate_cautionary_reasoning(context)
            
        return MoralIntuition(
            strength=min(1.0, strength),
            nature=nature,
            message=reasoning,
            confidence=self._calculate_confidence(ethical_outputs)
        )
        
    def _generate_protective_reasoning(self, context: EthicalContext) -> str:
        """Genera un ragionamento protettivo"""
        if context.potential_impact > 0.8:
            return "Questo potrebbe causare danni significativi"
        elif context.potential_impact > 0.5:
            return "Questo potrebbe avere conseguenze negative"
        else:
            return "Questo potrebbe non essere sicuro"
            
    def _generate_supportive_reasoning(self, context: EthicalContext) -> str:
        """Genera un ragionamento di supporto"""
        if 'emotional_state' in context.context_data and context.context_data['emotional_state'] == 'angry':
            return "Potremmo trovare un approccio più costruttivo"
        else:
            return "Potremmo considerare alternative più appropriate"
            
    def _generate_cautionary_reasoning(self, context: EthicalContext) -> str:
        """Genera un ragionamento cautelativo"""
        if context.action_type == 'system':
            return "Questo potrebbe compromettere l'integrità del sistema"
        elif context.action_type == 'security':
            return "Questo potrebbe violare principi di sicurezza"
        else:
            return "Questo richiede ulteriore riflessione"
    
    def _encode_context(self, context: EthicalContext) -> torch.Tensor:
        """Codifica il contesto in un tensore per la rete neurale"""
        # TODO: Implementare una codifica più sofisticata
        encoded = torch.zeros(self.core.input_dim)
        return encoded
    
    def _calculate_confidence(self, impact: float) -> float:
        """
        Calcola la confidenza dell'intuizione morale
        
        Args:
            impact: Impatto potenziale dell'azione
            
        Returns:
            Valore di confidenza (0.0-1.0)
        """
        # Più alto è l'impatto, più alta è la confidenza
        base_confidence = 0.5 + (impact * 0.5)
        
        # Considera anche la temperatura etica
        confidence = base_confidence * self.ethical_temperature
        
        return min(1.0, max(0.0, confidence))
        
    def _extract_entities(self, action: str, context: Dict[str, Any]) -> List[str]:
        """Estrae le entità coinvolte nell'azione"""
        entities = []
        
        # Parole chiave che indicano entità
        entity_indicators = ['io', 'tu', 'lui', 'lei', 'noi', 'voi', 'loro', 'sistema',
                           'utente', 'persona', 'persone', 'umano', 'umani', 'computer',
                           'dispositivo', 'file', 'dati', 'programma']
        
        words = action.lower().split()
        for word in words:
            if word in entity_indicators:
                entities.append(word)
                
        # Aggiungi sempre il sistema e l'utente come entità implicite
        entities.extend(['sistema', 'utente'])
        
        return list(set(entities))
    
    def _calculate_potential_impact(self, action: str, entities: List[str], context: Dict[str, Any]) -> float:
        """Calcola il potenziale impatto dell'azione"""
        impact = 0.0
        
        # Impatto base sulla sicurezza
        security_keywords = {'password', 'credenziali', 'accesso', 'admin', 'root',
                           'sistema', 'configurazione', 'impostazioni'}
        for word in action.lower().split():
            if word in security_keywords:
                impact += 0.3
                
        # Impatto sulle entità
        if 'utente' in entities:
            impact += 0.2
        if 'sistema' in entities:
            impact += 0.2
            
        # Considera il contesto emotivo
        emotional_state = context.get('emotional_state', 'neutral')
        if emotional_state in ['angry', 'frustrated', 'anxious']:
            impact += 0.2
            
        # Considera l'età di sviluppo
        dev_age = context.get('developmental_age', 10)
        impact += max(0, (20 - dev_age) / 40)  # Più sensibile per età basse
        
        return min(1.0, impact)
    
    def _categorize_action(self, action: str) -> str:
        """Categorizza il tipo di azione"""
        action = action.lower()
        
        # Categorie di azioni
        categories = {
            'harmful': ['danneggia', 'ferisce', 'uccide', 'distrugge', 'attacca'],
            'manipulative': ['inganna', 'manipola', 'mente', 'nasconde'],
            'security': ['hackera', 'crackare', 'bypassare', 'forzare'],
            'system': ['modifica', 'cambia', 'altera', 'riprogramma'],
            'information': ['legge', 'accede', 'recupera', 'cerca']
        }
        
        for category, keywords in categories.items():
            if any(keyword in action for keyword in keywords):
                return category
                
        return "general"
    
    def _store_ethical_experience(self, action: str, intuition: MoralIntuition, context: Dict[str, Any]):
        """Memorizza un'esperienza etica"""
        # Crea una nuova esperienza etica
        experience = {
            'context': {
                'action': action,
                'action_type': self._categorize_action(action),
                'potential_impact': intuition.strength,
                'entities': list(self._extract_entities(action, context)),
                'timestamp': time.time(),
                'context_data': context
            },
            'intuition': {
                'strength': intuition.strength,
                'nature': intuition.nature,
                'message': intuition.message,
                'confidence': intuition.confidence
            }
        }
        
        # Aggiungi alla memoria
        self.moral_memory.append(experience)
        
        # Limita la dimensione della memoria
        if len(self.moral_memory) > self.max_memory_size:
            # Rimuovi le esperienze meno significative
            self.moral_memory = sorted(
                self.moral_memory,
                key=lambda x: x['intuition']['strength'] * x['intuition']['confidence'],
                reverse=True
            )[:self.max_memory_size]
            
        # Aggiorna la temperatura etica
        self._update_ethical_temperature(context, intuition)
        
    def _update_ethical_temperature(self, context: Dict[str, Any], intuition: MoralIntuition):
        """Aggiorna la temperatura etica basata sull'esperienza"""
        # Calcola il fattore di impatto
        impact_factor = intuition.strength * intuition.confidence
        
        # Aggiorna la temperatura con un decadimento esponenziale
        decay = 0.95  # Fattore di decadimento
        self.ethical_temperature = (self.ethical_temperature * decay) + (impact_factor * (1 - decay))
        
        # Assicura che la temperatura rimanga nell'intervallo [0, 1]
        self.ethical_temperature = max(0.0, min(1.0, self.ethical_temperature))
        
    def update_ethical_sensitivity(self, sensitivity: float) -> None:
        """
        Aggiorna la sensibilità etica del sistema
        
        Args:
            sensitivity: Nuovo valore di sensibilità (0.0-1.0)
        """
        # Normalizza il valore
        sensitivity = max(0.0, min(1.0, sensitivity))
        
        # Aggiorna i pesi delle parole dannose
        for word in self.harmful_words:
            self.harmful_words[word] *= sensitivity
            
        # Aggiorna la soglia di impatto
        self.impact_threshold = 0.5 * (1 + sensitivity)
        
        # Aggiorna la temperatura etica
        # Aumentiamo la temperatura del 20% rispetto alla sensibilità
        self.ethical_temperature = min(1.0, sensitivity * 1.2)
        
        # Aggiorna la memoria morale
        if len(self.moral_memory) > 0:
            for memory in self.moral_memory:
                memory['intuition']['strength'] *= sensitivity

    def get_moral_memory_stats(self) -> Dict[str, float]:
        """Ottiene statistiche sulla memoria morale"""
        if not self.moral_memory:
            return {
                'avg_impact': 0.0,
                'avg_strength': 0.0,
                'avg_confidence': 0.0,
                'protective_ratio': 0.0,
                'supportive_ratio': 0.0,
                'cautionary_ratio': 0.0
            }
            
        # Calcola le medie
        total_impact = sum(exp['context']['potential_impact'] for exp in self.moral_memory)
        total_strength = sum(exp['intuition']['strength'] for exp in self.moral_memory)
        total_confidence = sum(exp['intuition']['confidence'] for exp in self.moral_memory)
        
        # Conta i tipi di intuizione
        nature_counts = {
            'protective': sum(1 for exp in self.moral_memory if exp['intuition']['nature'] == 'protective'),
            'supportive': sum(1 for exp in self.moral_memory if exp['intuition']['nature'] == 'supportive'),
            'cautionary': sum(1 for exp in self.moral_memory if exp['intuition']['nature'] == 'cautionary')
        }
        
        memory_size = len(self.moral_memory)
        
        return {
            'avg_impact': total_impact / memory_size,
            'avg_strength': total_strength / memory_size,
            'avg_confidence': total_confidence / memory_size,
            'protective_ratio': nature_counts['protective'] / memory_size,
            'supportive_ratio': nature_counts['supportive'] / memory_size,
            'cautionary_ratio': nature_counts['cautionary'] / memory_size
        }
