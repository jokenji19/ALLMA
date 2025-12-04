from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import random
from datetime import datetime

class ReasoningType(Enum):
    DEDUCTIVE = "deductive"  # Dal generale al particolare
    INDUCTIVE = "inductive"  # Dal particolare al generale
    ABDUCTIVE = "abductive"  # La migliore spiegazione
    ANALOGICAL = "analogical"  # Basato su analogie
    CAUSAL = "causal"  # Causa-effetto

@dataclass
class Premise:
    """Rappresenta una premessa nel ragionamento"""
    statement: str
    confidence: float  # 0-1
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte la premessa in un dizionario"""
        return {
            'statement': self.statement,
            'confidence': self.confidence,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

@dataclass
class Conclusion:
    """Rappresenta una conclusione derivata dal ragionamento"""
    statement: str
    confidence: float  # 0-1
    reasoning_type: ReasoningType
    premises: List[Premise]
    timestamp: datetime
    explanation: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte la conclusione in un dizionario"""
        return {
            'statement': self.statement,
            'confidence': self.confidence,
            'reasoning_type': self.reasoning_type.value,
            'premises': [p.to_dict() for p in self.premises],
            'timestamp': self.timestamp.isoformat(),
            'explanation': self.explanation,
            'metadata': self.metadata
        }

@dataclass
class Rule:
    """Rappresenta una regola di inferenza"""
    if_clause: str
    then_clause: str
    confidence: float  # 0-1
    source: str
    exceptions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ReasoningSystem:
    """Sistema di ragionamento per la gestione della logica e dell'inferenza"""
    
    def __init__(self):
        self.knowledge_base: Dict[str, List[Premise]] = {}
        self.rules: List[Rule] = []
        self.conclusions: List[Conclusion] = []
        self.analogies: Dict[str, List[str]] = {}
        self.causal_relations: Dict[str, List[str]] = {}
        
    def add_premise(self, statement: str, confidence: float, source: str) -> Premise:
        """Aggiunge una premessa alla base di conoscenza"""
        premise = Premise(
            statement=statement,
            confidence=confidence,
            source=source,
            timestamp=datetime.now()
        )
        
        category = self._categorize_statement(statement)
        if category not in self.knowledge_base:
            self.knowledge_base[category] = []
        self.knowledge_base[category].append(premise)
        return premise
        
    def add_rule(self, if_clause: str, then_clause: str, confidence: float, source: str) -> Rule:
        """Aggiunge una regola di inferenza"""
        rule = Rule(
            if_clause=if_clause,
            then_clause=then_clause,
            confidence=confidence,
            source=source
        )
        self.rules.append(rule)
        return rule
        
    def add_analogy(self, source: str, target: str) -> None:
        """Aggiunge una relazione analogica"""
        if source not in self.analogies:
            self.analogies[source] = []
        if target not in self.analogies[source]:
            self.analogies[source].append(target)
            
    def add_causal_relation(self, cause: str, effect: str) -> None:
        """Aggiunge una relazione causale"""
        if cause not in self.causal_relations:
            self.causal_relations[cause] = []
        if effect not in self.causal_relations[cause]:
            self.causal_relations[cause].append(effect)
            
    def deductive_reasoning(self, premises: List[Premise]) -> Optional[Conclusion]:
        """Applica il ragionamento deduttivo"""
        if not premises:
            return None
            
        # Cerca regole applicabili
        applicable_rules = []
        for rule in self.rules:
            if self._matches_rule_condition(premises, rule.if_clause):
                applicable_rules.append(rule)
                
        if not applicable_rules:
            return None
            
        # Usa la regola con la maggiore confidenza
        best_rule = max(applicable_rules, key=lambda r: r.confidence)
        
        # Calcola la confidenza combinata
        # La confidenza diminuisce leggermente nel processo deduttivo
        premises_confidence = sum(p.confidence for p in premises) / len(premises)
        combined_confidence = min(
            best_rule.confidence,
            premises_confidence
        ) * 0.9  # Riduzione del 10% per incertezza
        
        return Conclusion(
            statement=best_rule.then_clause,
            confidence=combined_confidence,
            reasoning_type=ReasoningType.DEDUCTIVE,
            premises=premises,
            timestamp=datetime.now(),
            explanation=f"Dedotto da {', '.join(p.statement for p in premises)} usando la regola: SE {best_rule.if_clause} ALLORA {best_rule.then_clause}"
        )
        
    def inductive_reasoning(self, observations: List[Premise]) -> Optional[Conclusion]:
        """Applica il ragionamento induttivo"""
        if not observations:
            return None
            
        # Cerca pattern comuni
        patterns = self._find_patterns(observations)
        if not patterns:
            return None
            
        # Usa il pattern più frequente
        best_pattern = max(patterns, key=lambda p: p[1])
        pattern_statement, frequency = best_pattern
        
        # Calcola la confidenza basata sulla frequenza e sulla confidenza delle osservazioni
        confidence = frequency * sum(o.confidence for o in observations) / len(observations)
        
        return Conclusion(
            statement=f"Generalmente, {pattern_statement}",
            confidence=confidence,
            reasoning_type=ReasoningType.INDUCTIVE,
            premises=observations,
            timestamp=datetime.now(),
            explanation=f"Indotto da {len(observations)} osservazioni con una frequenza del {frequency*100:.1f}%"
        )
        
    def analogical_reasoning(self, source_premise: Premise, target_domain: str) -> Optional[Conclusion]:
        """Applica il ragionamento analogico"""
        # Normalizza i testi per confronti più robusti
        source_text = self._normalize_text(source_premise.statement)
        target_domain = self._normalize_text(target_domain)
        
        # Cerca analogie rilevanti in tutte le analogie note
        relevant_analogies = []
        analogy_scores = {}
        
        # Prima cerca corrispondenze esatte
        for source, targets in self.analogies.items():
            normalized_source = self._normalize_text(source)
            if normalized_source == source_text:
                for target in targets:
                    normalized_target = self._normalize_text(target)
                    relevant_analogies.append(target)
                    analogy_scores[target] = 1.0
                
        # Poi cerca corrispondenze approssimate
        if not relevant_analogies:  # Solo se non abbiamo trovato corrispondenze esatte
            for source, targets in self.analogies.items():
                normalized_source = self._normalize_text(source)
                similarity = self._statement_similarity(source_text, normalized_source)
                if similarity > 0.3:  # Soglia più bassa per trovare più analogie
                    for target in targets:
                        normalized_target = self._normalize_text(target)
                        if target not in relevant_analogies:
                            relevant_analogies.append(target)
                            analogy_scores[target] = similarity
                
        if not relevant_analogies:
            return None
            
        # Trova l'analogia più pertinente per il dominio target
        target_analogy = None
        max_score = 0
        
        for analogy in relevant_analogies:
            # Calcola la rilevanza rispetto al dominio target
            domain_relevance = self._is_relevant_to_domain(analogy, target_domain)
            
            # Usa una media pesata tra similarità e rilevanza
            # Dà più peso alla similarità (0.7) che alla rilevanza del dominio (0.3)
            total_score = (0.7 * analogy_scores[analogy]) + (0.3 * domain_relevance)
            
            if total_score > max_score:
                max_score = total_score
                target_analogy = analogy
                
        if not target_analogy or max_score < 0.1:  # Soglia minima per considerare valida un'analogia
            return None
            
        # La confidenza è influenzata dalla similarità, dalla rilevanza e dalla confidenza originale
        # Ma manteniamo un minimo di confidenza se l'analogia è stata trovata
        base_confidence = source_premise.confidence * max_score
        confidence = max(0.3, base_confidence)  # Minimo 0.3 di confidenza se troviamo un'analogia
        
        return Conclusion(
            statement=f"Per analogia con {source_premise.statement}, possiamo inferire che {target_analogy}",
            confidence=confidence,
            reasoning_type=ReasoningType.ANALOGICAL,
            premises=[source_premise],
            timestamp=datetime.now(),
            explanation=f"Ragionamento analogico dal dominio {source_premise.statement} al dominio {target_domain} con punteggio {max_score:.2f}"
        )
        
    def abductive_reasoning(self, observation: Premise) -> Optional[Conclusion]:
        """Applica il ragionamento abduttivo (inferenza alla migliore spiegazione)"""
        # Cerca possibili cause in tutte le relazioni causali
        possible_causes = []
        cause_scores = {}
        
        for cause, effects in self.causal_relations.items():
            max_similarity = max(
                (self._statement_similarity(observation.statement, effect)
                for effect in effects),
                default=0
            )
            if max_similarity > 0.5:  # Soglia di similarità più bassa
                possible_causes.append(cause)
                cause_scores[cause] = max_similarity
                
        if not possible_causes:
            return None
            
        # Valuta le cause e trova la migliore spiegazione
        best_cause = max(possible_causes, key=lambda c: cause_scores[c])
        
        # La confidenza è influenzata sia dalla similarità che dalla confidenza dell'osservazione
        confidence = cause_scores[best_cause] * observation.confidence
        
        return Conclusion(
            statement=f"La migliore spiegazione per {observation.statement} è {best_cause}",
            confidence=confidence,
            reasoning_type=ReasoningType.ABDUCTIVE,
            premises=[observation],
            timestamp=datetime.now(),
            explanation=f"Abduzione basata sull'osservazione con similarità {cause_scores[best_cause]:.2f}"
        )
        
    def causal_reasoning(self, event: Premise) -> Optional[Conclusion]:
        """Applica il ragionamento causale"""
        if event.statement not in self.causal_relations:
            return None
            
        effects = self.causal_relations[event.statement]
        if not effects:
            return None
            
        # Predice gli effetti più probabili
        confidence = event.confidence * 0.9  # Leggera diminuzione della confidenza
        
        return Conclusion(
            statement=f"Data la causa {event.statement}, ci aspettiamo: {', '.join(effects)}",
            confidence=confidence,
            reasoning_type=ReasoningType.CAUSAL,
            premises=[event],
            timestamp=datetime.now(),
            explanation=f"Ragionamento causale basato su relazioni causa-effetto note"
        )
        
    def _categorize_statement(self, statement: str) -> str:
        """Categorizza una dichiarazione per l'organizzazione della knowledge base"""
        # Implementazione semplificata - usa la prima parola come categoria
        words = statement.lower().split()
        return words[0] if words else "general"
        
    def _matches_rule_condition(self, premises: List[Premise], condition: str) -> bool:
        """Verifica se le premesse soddisfano la condizione di una regola"""
        # Implementazione semplificata - cerca corrispondenze di stringhe
        premise_texts = [p.statement.lower() for p in premises]
        return any(condition.lower() in text for text in premise_texts)
        
    def _find_patterns(self, observations: List[Premise]) -> List[Tuple[str, float]]:
        """Trova pattern comuni nelle osservazioni"""
        # Implementazione semplificata - cerca parole comuni
        word_frequencies: Dict[str, int] = {}
        total_observations = len(observations)
        
        for obs in observations:
            words = set(obs.statement.lower().split())
            for word in words:
                word_frequencies[word] = word_frequencies.get(word, 0) + 1
                
        # Filtra e normalizza
        patterns = [
            (word, count/total_observations)
            for word, count in word_frequencies.items()
            if count/total_observations > 0.5  # Soglia minima
        ]
        
        return patterns
        
    def _is_relevant_to_domain(self, analogy: str, domain: str) -> float:
        """Valuta quanto un'analogia è rilevante per un dominio"""
        # Normalizza i testi
        analogy = self._normalize_text(analogy)
        domain = self._normalize_text(domain)
        
        # Se il dominio è vuoto, consideriamo l'analogia sempre rilevante
        if not domain:
            return 1.0
            
        # Calcola similarità tra parole
        analogy_words = set(analogy.split())
        domain_words = set(domain.split())
        
        # Calcola il coefficiente di Jaccard
        intersection = len(analogy_words.intersection(domain_words))
        union = len(analogy_words.union(domain_words))
        
        # Aggiungi un bonus se ci sono parole chiave in comune
        relevance = intersection / union if union > 0 else 0.0
        if intersection > 0:
            relevance = min(1.0, relevance * 1.2)  # Bonus del 20% se ci sono parole in comune
            
        return relevance
        
    def _statement_similarity(self, statement1: str, statement2: str) -> float:
        """Calcola la similarità tra due dichiarazioni"""
        # Normalizza i testi
        statement1 = self._normalize_text(statement1)
        statement2 = self._normalize_text(statement2)
        
        # Calcola similarità usando il coefficiente di Jaccard
        words1 = set(statement1.split())
        words2 = set(statement2.split())
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        # Calcola similarità base
        similarity = intersection / union if union > 0 else 0.0
        
        # Aggiungi bonus per sottostringhe comuni lunghe
        longer_statement = max(statement1, statement2, key=len)
        shorter_statement = min(statement1, statement2, key=len)
        if longer_statement.find(shorter_statement) != -1:
            similarity = min(1.0, similarity * 1.3)  # Bonus del 30% per sottostringhe
            
        return similarity
        
    def _normalize_text(self, text: str) -> str:
        """Normalizza il testo per confronti più robusti"""
        return ' '.join(text.lower().split())
        
    def _evaluate_explanation(self, cause: str, observation: Premise) -> float:
        """Valuta quanto bene una causa spiega un'osservazione"""
        # Implementazione semplificata
        # Considera la similarità e la presenza di relazioni causali note
        base_score = self._statement_similarity(cause, observation.statement)
        
        # Bonus se ci sono relazioni causali note
        if cause in self.causal_relations:
            effects = self.causal_relations[cause]
            if any(self._statement_similarity(observation.statement, effect) > 0.7 for effect in effects):
                base_score *= 1.2
                
        return min(1.0, base_score)
        
    def process_input(self, text: str) -> Dict[str, Any]:
        """
        Processa un input testuale e genera una comprensione
        
        Args:
            text: Testo da processare
            
        Returns:
            Dizionario contenente la comprensione generata
            
        Raises:
            ValueError: Se il testo è None o vuoto
        """
        if not text or not isinstance(text, str):
            raise ValueError("Il testo deve essere una stringa non vuota")
            
        # Estrai premesse dal testo
        premises = self._extract_premises(text)
        
        # Applica regole di inferenza
        conclusions = []
        for premise in premises:
            for rule in self.rules:
                if self._matches_rule(premise, rule):
                    conclusions.append(self._apply_rule(premise, rule))
                    
        # Cerca analogie
        analogies = self._find_analogies(text)
        
        # Genera conclusioni finali
        final_conclusions = self._generate_conclusions(premises, conclusions, analogies)
        
        return {
            'premises': [p.to_dict() for p in premises],
            'conclusions': [c.to_dict() for c in final_conclusions],
            'analogies': analogies
        }
        
    def _extract_premises(self, text: str) -> List[Premise]:
        # Implementazione semplificata - estrae frasi separate da punti
        sentences = text.split('.')
        premises = []
        for sentence in sentences:
            if sentence:  # Ignora frasi vuote
                premise = Premise(
                    statement=sentence.strip(),
                    confidence=0.8,  # Confidenza predefinita
                    source='input',
                    timestamp=datetime.now()
                )
                premises.append(premise)
        return premises
        
    def _matches_rule(self, premise: Premise, rule: Rule) -> bool:
        # Implementazione semplificata - cerca corrispondenze di stringhe
        return rule.if_clause.lower() in premise.statement.lower()
        
    def _apply_rule(self, premise: Premise, rule: Rule) -> Conclusion:
        # Implementazione semplificata - applica la regola e genera una conclusione
        conclusion = Conclusion(
            statement=rule.then_clause,
            confidence=premise.confidence * rule.confidence,
            reasoning_type=ReasoningType.DEDUCTIVE,
            premises=[premise],
            timestamp=datetime.now(),
            explanation=f"Applicazione della regola: SE {rule.if_clause} ALLORA {rule.then_clause}"
        )
        return conclusion
        
    def _find_analogies(self, text: str) -> List[str]:
        # Implementazione semplificata - cerca analogie note
        analogies = []
        for source, targets in self.analogies.items():
            if source in text:
                analogies.extend(targets)
        return analogies
        
    def _generate_conclusions(self, premises: List[Premise], conclusions: List[Conclusion], analogies: List[str]) -> List[Conclusion]:
        # Implementazione semplificata - combina conclusioni e analogie
        final_conclusions = conclusions[:]
        for analogy in analogies:
            conclusion = Conclusion(
                statement=analogy,
                confidence=0.7,  # Confidenza predefinita per analogie
                reasoning_type=ReasoningType.ANALOGICAL,
                premises=premises,
                timestamp=datetime.now(),
                explanation=f"Analogia trovata: {analogy}"
            )
            final_conclusions.append(conclusion)
        return final_conclusions
