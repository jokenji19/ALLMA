from typing import List, Dict, Any
import re
from datetime import datetime

class ReasoningEngine:
    def __init__(self, knowledge_base):
        self.kb = knowledge_base
        self.performance_stats = {
            'queries_processed': 0,
            'successful_inferences': 0,
            'total_time': 0.0
        }
    
    def extract_entities(self, query: str) -> List[str]:
        """Estrae entità dalla query"""
        # Implementazione base per il test
        entities = []
        
        # Cerca entità nel knowledge base
        for entity in self.kb.get_all_entities():
            if entity.lower() in query.lower():
                entities.append(entity)
                
        return entities
    
    def identify_relations(self, query: str) -> List[str]:
        """Identifica relazioni nella query"""
        # Pattern base per relazioni
        relation_patterns = {
            'successore': r'successore|dopo|seguì',
            'predecessore': r'predecessore|prima|precedette',
            'contemporaneo': r'durante|stesso periodo|contemporaneo',
            'causa': r'causò|portò a|risultò in',
            'effetto': r'conseguenza|risultato|effetto'
        }
        
        relations = []
        for rel, pattern in relation_patterns.items():
            if re.search(pattern, query, re.IGNORECASE):
                relations.append(rel)
                
        return relations
    
    def retrieve_relevant_facts(self, entities: List[str], relations: List[str]) -> List[Dict[str, Any]]:
        """Recupera fatti rilevanti dal knowledge base"""
        facts = []
        
        for entity in entities:
            fact = self.kb.get_fact(entity)
            if fact:
                facts.append(fact)
                
                # Se ci sono relazioni, cerca fatti correlati
                if relations:
                    for relation in relations:
                        if relation in fact.get('relazioni', {}):
                            related_entity = fact['relazioni'][relation]
                            related_fact = self.kb.get_fact(related_entity)
                            if related_fact:
                                facts.append(related_fact)
                                
        return facts
    
    def extract_premises(self, query: str) -> List[Dict[str, Any]]:
        """Estrae premesse dalla query"""
        entities = self.extract_entities(query)
        relations = self.identify_relations(query)
        facts = self.retrieve_relevant_facts(entities, relations)
        
        premises = []
        for fact in facts:
            premise = {
                'entity': fact.get('tipo', ''),
                'attributes': {k: v for k, v in fact.items() if k not in ['tipo', 'relazioni']}
            }
            premises.append(premise)
            
        return premises
    
    def draw_conclusion(self, premises: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Trae conclusioni dalle premesse"""
        start_time = datetime.now()
        self.performance_stats['queries_processed'] += 1
        
        conclusion = {
            'valid': False,
            'statement': '',
            'confidence': 0.0,
            'supporting_facts': []
        }
        
        if not premises:
            return conclusion
            
        # Logica semplificata per il test
        conclusion['valid'] = True
        conclusion['statement'] = self._generate_conclusion_statement(premises)
        conclusion['confidence'] = self._calculate_confidence(premises)
        conclusion['supporting_facts'] = premises
        
        if conclusion['valid']:
            self.performance_stats['successful_inferences'] += 1
            
        self.performance_stats['total_time'] += (datetime.now() - start_time).total_seconds()
        
        return conclusion
    
    def evaluate_confidence(self, conclusion: Dict[str, Any]) -> float:
        """Valuta la confidenza della conclusione"""
        if not conclusion['valid']:
            return 0.0
            
        return conclusion['confidence']
    
    def _generate_conclusion_statement(self, premises: List[Dict[str, Any]]) -> str:
        """Genera una dichiarazione di conclusione dalle premesse"""
        if not premises:
            return ""
            
        # Semplice concatenazione per il test
        statements = []
        for premise in premises:
            entity_type = premise['entity']
            attributes = premise['attributes']
            
            statement = f"Il {entity_type}"
            for key, value in attributes.items():
                if isinstance(value, (str, int, float)):
                    statement += f" {key}: {value},"
                    
            statements.append(statement)
            
        return " ".join(statements)
    
    def _calculate_confidence(self, premises: List[Dict[str, Any]]) -> float:
        """Calcola la confidenza basata sulle premesse"""
        if not premises:
            return 0.0
            
        # Calcolo semplificato per il test
        base_confidence = 0.7  # Confidenza base
        premise_factor = min(len(premises) * 0.1, 0.3)  # Più premesse = più confidenza
        
        return min(base_confidence + premise_factor, 1.0)
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Restituisce statistiche di performance"""
        total_queries = max(self.performance_stats['queries_processed'], 1)
        
        return {
            'accuracy': self.performance_stats['successful_inferences'] / total_queries,
            'avg_time': self.performance_stats['total_time'] / total_queries
        }
