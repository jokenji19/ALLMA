from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
import numpy as np

@dataclass
class Question:
    """Rappresenta una domanda generata"""
    text: str
    concept: str
    difficulty: float
    type: str
    context: Dict[str, Any]
    confidence: float

class QuestionGenerator:
    """Sistema per la generazione di domande contestuali"""
    
    def __init__(self):
        # Carica il modello T5 per la generazione di domande
        self.model_name = "gsarti/it5-base"
        self.tokenizer = T5Tokenizer.from_pretrained(self.model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(self.model_name)
        
        # Template per diversi tipi di domande
        self.question_templates = {
            "definition": [
                "Cosa significa {concept}?",
                "Puoi spiegare cosa è {concept}?",
                "Qual è il significato di {concept}?"
            ],
            "example": [
                "Puoi fare un esempio di {concept}?",
                "Come si usa {concept} nella pratica?",
                "In quale contesto si utilizza {concept}?"
            ],
            "relationship": [
                "Come si collega {concept} con {related_concept}?",
                "Qual è la relazione tra {concept} e {related_concept}?",
                "In che modo {concept} influenza {related_concept}?"
            ],
            "application": [
                "Come si applica {concept} in {context}?",
                "Quando è utile utilizzare {concept}?",
                "Quali sono i vantaggi di utilizzare {concept}?"
            ]
        }
        
    def generate_questions(self, 
                         concept: str,
                         context: Dict[str, Any],
                         related_concepts: List[str] = None,
                         num_questions: int = 3) -> List[Question]:
        """
        Genera domande per un concetto specifico
        
        Args:
            concept: Concetto su cui generare domande
            context: Contesto attuale
            related_concepts: Lista di concetti correlati
            num_questions: Numero di domande da generare
            
        Returns:
            Lista di domande generate
        """
        questions = []
        
        # 1. Genera domanda di definizione
        definition_q = self._generate_definition_question(concept)
        questions.append(definition_q)
        
        # 2. Genera domanda di esempio se c'è contesto
        if context:
            example_q = self._generate_example_question(concept, context)
            questions.append(example_q)
        
        # 3. Genera domanda di relazione se ci sono concetti correlati
        if related_concepts:
            relation_q = self._generate_relationship_question(
                concept, 
                related_concepts[0]
            )
            questions.append(relation_q)
        
        # 4. Genera domanda di applicazione
        application_q = self._generate_application_question(concept, context)
        questions.append(application_q)
        
        # Seleziona le migliori domande in base alla confidenza
        questions.sort(key=lambda x: x.confidence, reverse=True)
        return questions[:num_questions]
    
    def _generate_definition_question(self, concept: str) -> Question:
        """Genera una domanda di definizione"""
        template = np.random.choice(self.question_templates["definition"])
        question_text = template.format(concept=concept)
        
        return Question(
            text=question_text,
            concept=concept,
            difficulty=0.3,  # Domande di definizione sono più semplici
            type="definition",
            context={},
            confidence=0.9
        )
    
    def _generate_example_question(self, 
                                 concept: str, 
                                 context: Dict[str, Any]) -> Question:
        """Genera una domanda che richiede un esempio"""
        template = np.random.choice(self.question_templates["example"])
        question_text = template.format(concept=concept)
        
        # La confidenza dipende dalla ricchezza del contesto
        confidence = min(0.8, 0.5 + len(context) * 0.1)
        
        return Question(
            text=question_text,
            concept=concept,
            difficulty=0.5,
            type="example",
            context=context,
            confidence=confidence
        )
    
    def _generate_relationship_question(self, 
                                     concept: str,
                                     related_concept: str) -> Question:
        """Genera una domanda sulla relazione tra concetti"""
        template = np.random.choice(self.question_templates["relationship"])
        question_text = template.format(
            concept=concept,
            related_concept=related_concept
        )
        
        return Question(
            text=question_text,
            concept=concept,
            difficulty=0.7,  # Domande di relazione sono più complesse
            type="relationship",
            context={"related_concept": related_concept},
            confidence=0.7
        )
    
    def _generate_application_question(self,
                                    concept: str,
                                    context: Dict[str, Any]) -> Question:
        """Genera una domanda sull'applicazione pratica"""
        template = np.random.choice(self.question_templates["application"])
        
        # Cerca un contesto rilevante
        relevant_context = next(
            (k for k, v in context.items() if isinstance(v, str)),
            "questo contesto"
        )
        
        question_text = template.format(
            concept=concept,
            context=relevant_context
        )
        
        return Question(
            text=question_text,
            concept=concept,
            difficulty=0.6,
            type="application",
            context=context,
            confidence=0.75
        )
    
    def generate_followup_question(self,
                                 concept: str,
                                 previous_answer: str,
                                 context: Dict[str, Any]) -> Optional[Question]:
        """
        Genera una domanda di follow-up basata sulla risposta precedente
        
        Args:
            concept: Concetto principale
            previous_answer: Risposta alla domanda precedente
            context: Contesto attuale
            
        Returns:
            Nuova domanda generata o None se non necessaria
        """
        # Prepara l'input per il modello T5
        input_text = f"genera domanda di approfondimento: {concept} | {previous_answer}"
        input_ids = self.tokenizer(
            input_text,
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).input_ids
        
        # Genera la domanda
        outputs = self.model.generate(
            input_ids,
            max_length=64,
            num_return_sequences=1,
            temperature=0.7
        )
        question_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Valuta la qualità della domanda generata
        if len(question_text.split()) < 4:  # Domanda troppo corta
            return None
            
        return Question(
            text=question_text,
            concept=concept,
            difficulty=0.8,  # Domande di follow-up sono più complesse
            type="followup",
            context={"previous_answer": previous_answer},
            confidence=0.6
        )
    
    def evaluate_answer(self,
                       question: Question,
                       answer: str) -> float:
        """
        Valuta la qualità della risposta
        
        Args:
            question: Domanda originale
            answer: Risposta fornita
            
        Returns:
            Punteggio tra 0 e 1
        """
        # Criteri di valutazione
        criteria = {
            "length": 0.3,  # Lunghezza minima
            "relevance": 0.4,  # Rilevanza al concetto
            "complexity": 0.3  # Complessità appropriata
        }
        
        scores = {}
        
        # 1. Valuta lunghezza
        min_length = 10
        max_length = 200
        answer_length = len(answer.split())
        if answer_length < min_length:
            scores["length"] = answer_length / min_length
        elif answer_length > max_length:
            scores["length"] = max_length / answer_length
        else:
            scores["length"] = 1.0
            
        # 2. Valuta rilevanza
        concept_mentioned = question.concept.lower() in answer.lower()
        context_words = set(
            word.lower() 
            for word in " ".join(str(v) for v in question.context.values()).split()
        )
        context_relevance = len(
            [w for w in answer.lower().split() if w in context_words]
        ) / len(answer.split())
        
        scores["relevance"] = (
            0.7 * float(concept_mentioned) +
            0.3 * min(1.0, context_relevance * 2)
        )
        
        # 3. Valuta complessità
        target_complexity = question.difficulty
        answer_complexity = min(1.0, len(set(answer.split())) / len(answer.split()))
        complexity_diff = abs(target_complexity - answer_complexity)
        scores["complexity"] = max(0, 1 - complexity_diff)
        
        # Calcola punteggio finale
        final_score = sum(
            score * criteria[criterion]
            for criterion, score in scores.items()
        )
        
        return final_score
