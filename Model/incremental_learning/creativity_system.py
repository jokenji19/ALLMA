from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import random
import math

class CreativeApproach(Enum):
    ANALOGIA = "analogia"
    COMBINAZIONE = "combinazione"
    ASTRAZIONE = "astrazione"
    TRASFORMAZIONE = "trasformazione"
    ASSOCIAZIONE_CASUALE = "associazione_casuale"

@dataclass
class Idea:
    """Rappresenta un'idea generata dal sistema"""
    id: str
    description: str
    approach: CreativeApproach
    components: List[str]
    timestamp: datetime
    score: float = 0.0  # 0-1
    tags: List[str] = field(default_factory=list)
    inspirations: List[str] = field(default_factory=list)
    
@dataclass
class Problem:
    """Rappresenta un problema da risolvere creativamente"""
    id: str
    description: str
    constraints: List[str]
    context: Dict[str, str]
    solutions: List[Idea] = field(default_factory=list)

class CreativitySystem:
    """Sistema di creatività per la generazione di idee e risoluzione di problemi"""
    
    def __init__(self):
        self.knowledge_base: Dict[str, List[str]] = {
            "concetti": [],
            "pattern": [],
            "analogie": [],
            "metafore": []
        }
        self.ideas: Dict[str, Idea] = {}
        self.problems: Dict[str, Problem] = {}
        self.evaluation_criteria: Dict[str, float] = {
            "novità": 0.3,
            "utilità": 0.3,
            "fattibilità": 0.2,
            "impatto": 0.2
        }
        
    def add_to_knowledge_base(self, category: str, items: List[str]) -> bool:
        """Aggiunge elementi alla base di conoscenza"""
        if category not in self.knowledge_base:
            return False
        
        # Filtra duplicati
        new_items = [item for item in items if item not in self.knowledge_base[category]]
        self.knowledge_base[category].extend(new_items)
        return True
        
    def generate_random_combinations(self, elements: List[str], n: int) -> List[List[str]]:
        """Genera combinazioni casuali di elementi"""
        if not elements or n <= 0:
            return []
            
        combinations = []
        for _ in range(n):
            size = random.randint(2, min(len(elements), 4))
            combination = random.sample(elements, size)
            combinations.append(combination)
        return combinations
        
    def find_analogies(self, concept: str) -> List[str]:
        """Trova analogie per un concetto"""
        analogies = []
        
        # Cerca nelle analogie esistenti
        for analogy in self.knowledge_base["analogie"]:
            if concept.lower() in analogy.lower():
                analogies.append(analogy)
                
        # Cerca pattern simili
        for pattern in self.knowledge_base["pattern"]:
            if self._calculate_similarity(concept, pattern) > 0.5:
                analogies.append(pattern)
                
        return analogies
        
    def _calculate_similarity(self, a: str, b: str) -> float:
        """Calcola la similarità tra due stringhe (implementazione semplificata)"""
        # Converti in set di caratteri per un confronto approssimativo
        set_a = set(a.lower())
        set_b = set(b.lower())
        
        # Calcola coefficiente di Jaccard
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        
        return intersection / union if union > 0 else 0.0
        
    def generate_idea(self, context: Dict[str, str], approach: Optional[CreativeApproach] = None) -> Idea:
        """Genera una nuova idea basata sul contesto"""
        if not approach:
            approach = random.choice(list(CreativeApproach))
            
        components = []
        description = ""
        
        # Assicura che ci siano sempre alcuni componenti di base disponibili
        available_concepts = self.knowledge_base["concetti"]
        if not available_concepts:
            available_concepts = ["concetto_base"]
            
        if approach == CreativeApproach.ANALOGIA:
            # Usa analogie dalla knowledge base
            concept = context.get("concetto", random.choice(available_concepts))
            analogies = self.find_analogies(concept)
            if analogies:
                components = random.sample(analogies, min(2, len(analogies)))
            else:
                # Se non ci sono analogie, usa concetti casuali
                components = random.sample(available_concepts, min(2, len(available_concepts)))
            description = f"Analogia tra {concept} e {', '.join(components)}"
                
        elif approach == CreativeApproach.COMBINAZIONE:
            # Combina elementi dalla knowledge base
            combinations = self.generate_random_combinations(available_concepts, 1)
            if combinations:
                components = combinations[0]
            else:
                # Se non ci sono combinazioni, usa almeno due concetti
                components = random.sample(available_concepts, min(2, len(available_concepts)))
            description = f"Combinazione di {' + '.join(components)}"
                
        elif approach == CreativeApproach.ASTRAZIONE:
            # Astrae concetti dal contesto
            patterns = self.knowledge_base["pattern"]
            if patterns:
                components = random.sample(patterns, min(2, len(patterns)))
            else:
                # Se non ci sono pattern, usa concetti
                components = random.sample(available_concepts, min(2, len(available_concepts)))
            description = f"Astrazione basata su {' e '.join(components)}"
                
        elif approach == CreativeApproach.TRASFORMAZIONE:
            # Trasforma concetti esistenti
            base_concept = context.get("concetto", random.choice(available_concepts))
            transformations = ["inverso", "estremo", "miniatura", "gigante"]
            transform = random.choice(transformations)
            components = [base_concept, f"{transform}_{base_concept}"]
            description = f"Trasformazione {transform} di {base_concept}"
            
        else:  # ASSOCIAZIONE_CASUALE
            # Associa elementi casuali
            all_elements = []
            for category in self.knowledge_base.values():
                all_elements.extend(category)
            if all_elements:
                components = random.sample(all_elements, min(3, len(all_elements)))
            else:
                # Se non ci sono elementi, usa concetti base
                components = random.sample(available_concepts, min(3, len(available_concepts)))
            description = f"Associazione tra {', '.join(components)}"
                
        # Assicura che ci siano sempre almeno due componenti
        while len(components) < 2:
            components.append(random.choice(available_concepts))
            
        # Genera ID unico
        idea_id = f"IDEA_{len(self.ideas) + 1}"
        
        # Crea l'idea
        idea = Idea(
            id=idea_id,
            description=description or "Idea generica",
            approach=approach,
            components=components,
            timestamp=datetime.now(),
            tags=list(context.keys())
        )
        
        # Valuta l'idea
        idea.score = self._evaluate_idea(idea)
        
        # Memorizza l'idea
        self.ideas[idea_id] = idea
        return idea
        
    def _evaluate_idea(self, idea: Idea) -> float:
        """Valuta un'idea secondo i criteri stabiliti"""
        scores = {
            "novità": self._evaluate_novelty(idea),
            "utilità": self._evaluate_utility(idea),
            "fattibilità": self._evaluate_feasibility(idea),
            "impatto": self._evaluate_impact(idea)
        }
        
        # Calcola il punteggio pesato
        weighted_score = sum(
            score * self.evaluation_criteria[criterion]
            for criterion, score in scores.items()
        )
        
        return min(1.0, max(0.0, weighted_score))
        
    def _evaluate_novelty(self, idea: Idea) -> float:
        """Valuta la novità di un'idea"""
        # Confronta con idee esistenti
        similarity_scores = []
        for existing_idea in self.ideas.values():
            if existing_idea.id != idea.id:
                # Calcola similarità media tra componenti
                comp_similarities = []
                for comp1 in idea.components:
                    for comp2 in existing_idea.components:
                        comp_similarities.append(self._calculate_similarity(comp1, comp2))
                if comp_similarities:
                    similarity_scores.append(sum(comp_similarities) / len(comp_similarities))
                    
        # Più è dissimile dalle idee esistenti, più è nuova
        if similarity_scores:
            avg_similarity = sum(similarity_scores) / len(similarity_scores)
            return 1.0 - avg_similarity
        return 1.0  # Prima idea
        
    def _evaluate_utility(self, idea: Idea) -> float:
        """Valuta l'utilità di un'idea"""
        # Implementazione semplificata
        # Considera il numero di componenti e la loro presenza nella knowledge base
        utility_score = 0.0
        
        if idea.components:
            relevant_components = 0
            for component in idea.components:
                # Verifica presenza nelle categorie rilevanti
                for category in ["concetti", "pattern"]:
                    if component in self.knowledge_base[category]:
                        relevant_components += 1
                        break
                        
            utility_score = relevant_components / len(idea.components)
            
        return utility_score
        
    def _evaluate_feasibility(self, idea: Idea) -> float:
        """Valuta la fattibilità di un'idea"""
        # Implementazione semplificata
        # Considera la complessità (numero di componenti) e l'approccio
        complexity_penalty = len(idea.components) * 0.1
        
        # Alcuni approcci sono considerati più fattibili di altri
        approach_scores = {
            CreativeApproach.ANALOGIA: 0.8,
            CreativeApproach.COMBINAZIONE: 0.7,
            CreativeApproach.ASTRAZIONE: 0.6,
            CreativeApproach.TRASFORMAZIONE: 0.5,
            CreativeApproach.ASSOCIAZIONE_CASUALE: 0.4
        }
        
        base_score = approach_scores[idea.approach]
        return max(0.0, base_score - complexity_penalty)
        
    def _evaluate_impact(self, idea: Idea) -> float:
        """Valuta l'impatto potenziale di un'idea"""
        # Implementazione semplificata
        # Considera il numero di tag e la diversità dei componenti
        tag_score = len(idea.tags) * 0.2
        
        # Calcola la diversità dei componenti
        unique_categories = set()
        for component in idea.components:
            for category, items in self.knowledge_base.items():
                if component in items:
                    unique_categories.add(category)
                    
        diversity_score = len(unique_categories) * 0.25
        
        return min(1.0, tag_score + diversity_score)
        
    def solve_problem(self, problem: Problem, num_solutions: int = 3) -> List[Idea]:
        """Genera soluzioni creative per un problema"""
        if problem.id not in self.problems:
            self.problems[problem.id] = problem
            
        context = {
            "problema": problem.description,
            **problem.context
        }
        
        # Genera diverse soluzioni usando approcci diversi
        solutions = []
        approaches = list(CreativeApproach)
        for _ in range(num_solutions):
            # Alterna tra approcci diversi
            approach = approaches[_ % len(approaches)]
            idea = self.generate_idea(context, approach)
            solutions.append(idea)
            problem.solutions.append(idea)
            
        # Ordina per punteggio
        solutions.sort(key=lambda x: x.score, reverse=True)
        return solutions
        
    def refine_idea(self, idea_id: str) -> Optional[Idea]:
        """Raffina un'idea esistente"""
        if idea_id not in self.ideas:
            return None
            
        original_idea = self.ideas[idea_id]
        
        # Crea un nuovo contesto basato sull'idea originale
        context = {
            "concetto": original_idea.description,
            "approccio": original_idea.approach.value
        }
        
        # Genera una nuova idea usando l'idea originale come ispirazione
        refined_idea = self.generate_idea(context)
        refined_idea.inspirations.append(idea_id)
        
        return refined_idea
        
    def combine_ideas(self, idea_ids: List[str]) -> Optional[Idea]:
        """Combina più idee esistenti"""
        ideas = []
        for idea_id in idea_ids:
            if idea_id in self.ideas:
                ideas.append(self.ideas[idea_id])
                
        if len(ideas) < 2:
            return None
            
        # Unisce i componenti e i tag
        all_components = []
        all_tags = set()
        for idea in ideas:
            all_components.extend(idea.components)
            all_tags.update(idea.tags)
            
        # Crea un nuovo contesto
        context = {
            "concetto": " + ".join(idea.description for idea in ideas),
            "approccio": "combinazione"
        }
        
        # Genera una nuova idea combinata
        combined_idea = self.generate_idea(context, CreativeApproach.COMBINAZIONE)
        combined_idea.components = list(set(all_components))  # Rimuove duplicati
        combined_idea.tags = list(all_tags)
        combined_idea.inspirations = idea_ids
        
        return combined_idea
