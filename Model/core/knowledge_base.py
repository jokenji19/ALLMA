from typing import Dict, Any, List, Optional
from datetime import datetime

class KnowledgeBase:
    def __init__(self):
        self.facts = {}
        self.knowledge = []
        self.performance_stats = {
            'facts_added': 0,
            'facts_retrieved': 0,
            'total_time': 0.0
        }
    
    def add_fact(self, entity: str, fact: Dict[str, Any]):
        """Aggiunge un fatto al knowledge base"""
        start_time = datetime.now()
        
        self.facts[entity] = fact
        self.performance_stats['facts_added'] += 1
        
        self.performance_stats['total_time'] += (datetime.now() - start_time).total_seconds()
    
    def get_fact(self, entity: str) -> Dict[str, Any]:
        """Recupera un fatto dal knowledge base"""
        start_time = datetime.now()
        
        fact = self.facts.get(entity, {})
        if fact:
            self.performance_stats['facts_retrieved'] += 1
            
        self.performance_stats['total_time'] += (datetime.now() - start_time).total_seconds()
        return fact
        
    def get_relevant_knowledge(self, query: str, topic: str = '') -> List[Dict[str, Any]]:
        """
        Recupera conoscenza rilevante per una query e un topic
        
        Args:
            query: La query per cui cercare conoscenza
            topic: Il topic di riferimento (opzionale)
            
        Returns:
            List[Dict[str, Any]]: Lista di fatti rilevanti
        """
        start_time = datetime.now()
        relevant_facts = []
        
        # Se abbiamo un topic specifico, cerca prima lì
        if topic and topic in self.facts:
            relevant_facts.append(self.facts[topic])
            
        # Cerca nei fatti quelli che contengono parole della query
        query_words = set(query.lower().split())
        for entity, fact in self.facts.items():
            # Controlla se le parole della query sono presenti nel fatto
            fact_text = str(fact).lower()
            if any(word in fact_text for word in query_words):
                if fact not in relevant_facts:  # Evita duplicati
                    relevant_facts.append(fact)
                    
        self.performance_stats['facts_retrieved'] += len(relevant_facts)
        self.performance_stats['total_time'] += (datetime.now() - start_time).total_seconds()
        
        return relevant_facts
    
    def get_all_entities(self) -> List[str]:
        """Restituisce tutte le entità nel knowledge base"""
        return list(self.facts.keys())
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Restituisce statistiche di performance"""
        total_operations = max(
            self.performance_stats['facts_added'] + 
            self.performance_stats['facts_retrieved'],
            1
        )
        
        return {
            'avg_time': self.performance_stats['total_time'] / total_operations,
            'success_rate': self.performance_stats['facts_retrieved'] / total_operations
        }
    
    def add_knowledge(self, knowledge_item: Dict) -> None:
        """Aggiunge una nuova conoscenza alla knowledge base"""
        timestamp = datetime.now().isoformat()
        knowledge_item['timestamp'] = timestamp
        self.knowledge.append(knowledge_item)
    
    def query_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Cerca informazioni nella base di conoscenza.
        
        Args:
            query: Testo o pattern da cercare
            category: Categoria specifica dove cercare
            threshold: Soglia minima di similarità per i risultati
            
        Returns:
            Dict con i risultati della ricerca
        """
        start_time = datetime.now()
        query = str(query).lower()
        
        results = {
            'found': False,
            'matches': [],
            'confidence': 0.0,
            'category': category
        }
        
        try:
            # Se specificata una categoria, cerca solo in quella
            if category:
                if category in self.facts:
                    relevant_facts = [self.facts[category]]
                else:
                    relevant_facts = []
            else:
                # Cerca nei fatti quelli che contengono parole della query
                query_words = set(query.split())
                relevant_facts = []
                
                for entity, fact in self.facts.items():
                    # Converti il fatto in stringa in modo sicuro
                    if isinstance(fact, dict):
                        fact_text = ' '.join(str(v) for v in fact.values()).lower()
                    else:
                        fact_text = str(fact).lower()
                        
                    if any(word in fact_text for word in query_words):
                        relevant_facts.append({
                            'entity': entity,
                            'fact': fact
                        })
            
            # Aggiunge i fatti trovati ai risultati
            if relevant_facts:
                results['matches'] = relevant_facts
                results['found'] = True
                results['confidence'] = 1.0 if len(relevant_facts) == 1 else 0.8
                
            # Cerca anche nella knowledge generale
            for item in self.knowledge:
                # Converti l'item in stringa in modo sicuro
                if isinstance(item, dict):
                    item_text = ' '.join(str(v) for v in item.values()).lower()
                else:
                    item_text = str(item).lower()
                    
                if query in item_text:
                    results['matches'].append({
                        'type': 'knowledge',
                        'value': item
                    })
                    results['found'] = True
            
        except Exception as e:
            # Log dell'errore ma continua l'esecuzione
            print(f"Errore durante la query della knowledge base: {str(e)}")
            results['error'] = str(e)
        
        # Aggiorna statistiche
        self.performance_stats['facts_retrieved'] += len(results['matches'])
        self.performance_stats['total_time'] += (datetime.now() - start_time).total_seconds()
        
        return results
