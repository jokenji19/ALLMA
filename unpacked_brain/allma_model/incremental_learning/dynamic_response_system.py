"""
Sistema di risposte dinamico che combina risposte predefinite con apprendimento dalle interazioni
"""
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import random
from collections import defaultdict
import json
import os
import difflib

@dataclass
class ResponseTemplate:
    text: str
    context: Dict[str, str]
    usage_count: int = 0
    success_rate: float = 1.0
    last_used: int = 0  # Timestamp dell'ultimo utilizzo
    
@dataclass
class LearnedResponse:
    text: str
    context: Dict[str, str]
    user_feedback: float  # -1 a 1
    usage_count: int = 1
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0
    
class DynamicResponseSystem:
    def __init__(self, templates_file: str = None):
        self.templates: Dict[str, List[ResponseTemplate]] = {}
        self.learned_responses: Dict[str, List[LearnedResponse]] = defaultdict(list)
        self.conversation_context: Dict[str, any] = {
            "last_topics": [],
            "last_emotions": [],
            "interaction_count": 0,
            "error_count": 0,
            "consecutive_errors": 0
        }
        self.response_history: Set[str] = set()  # Per evitare ripetizioni
        self.max_history_size = 10  # Numero massimo di risposte da ricordare
        
        # Carica template predefiniti
        if templates_file and os.path.exists(templates_file):
            self._load_templates(templates_file)
            
    def _load_templates(self, file_path: str):
        """Carica template personalizzati da file JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                custom_templates = json.load(f)
            for category, responses in custom_templates.items():
                if category not in self.templates:
                    self.templates[category] = []
                for resp in responses:
                    self.templates[category].append(
                        ResponseTemplate(resp['text'], resp.get('context', {}))
                    )
        except Exception as e:
            print(f"Errore nel caricamento dei template: {str(e)}")
            
    def update_context(self, new_context: Dict[str, any]):
        """Aggiorna il contesto della conversazione"""
        # Aggiorna contatori
        self.conversation_context["interaction_count"] += 1
        
        # Aggiorna topics
        if "topics" in new_context:
            self.conversation_context["last_topics"] = (
                self.conversation_context.get("last_topics", [])[-2:] + 
                [new_context["topics"]]
            )
            
        # Aggiorna emozioni
        if "emotion" in new_context:
            self.conversation_context["last_emotions"] = (
                self.conversation_context.get("last_emotions", [])[-2:] + 
                [new_context["emotion"]]
            )
            
        # Gestione errori
        if new_context.get("is_error", False):
            self.conversation_context["error_count"] += 1
            self.conversation_context["consecutive_errors"] += 1
        else:
            self.conversation_context["consecutive_errors"] = 0
            
        # Aggiorna altri campi del contesto
        for key, value in new_context.items():
            if key not in ["topics", "emotion", "is_error"]:
                self.conversation_context[key] = value
                
    def _context_similarity(self, template_context: Dict[str, str], 
                          current_context: Dict[str, str]) -> float:
        """Calcola la similarità tra due contesti"""
        if not template_context:
            return 0.5  # Contesto vuoto = match neutro
            
        matches = 0
        total = len(template_context)
        
        for key, value in template_context.items():
            if key in current_context:
                # Gestione speciale per valori numerici
                if isinstance(value, (int, float)) and isinstance(current_context[key], (int, float)):
                    diff = abs(value - current_context[key])
                    matches += max(0, 1 - diff)
                # Gestione speciale per liste
                elif isinstance(value, list) and isinstance(current_context[key], list):
                    common = set(value) & set(current_context[key])
                    matches += len(common) / max(len(value), len(current_context[key]))
                # Confronto stringhe
                else:
                    if str(value).lower() == str(current_context[key]).lower():
                        matches += 1
                    else:
                        # Similarità parziale per stringhe
                        similarity = difflib.SequenceMatcher(
                            None, str(value).lower(), 
                            str(current_context[key]).lower()
                        ).ratio()
                        matches += similarity
                        
        return matches / total
        
    def get_response(self, category: str, context: Dict[str, str], 
                    use_learned: bool = True) -> Tuple[str, bool]:
        """Ottiene una risposta appropriata, combinando template predefiniti e risposte apprese"""
        self.update_context(context)
        
        # Arricchisci il contesto con informazioni aggiuntive
        context.update({
            "is_first_interaction": self.conversation_context["interaction_count"] == 1,
            "is_repeated_error": self.conversation_context["consecutive_errors"] > 1,
            "technical_level": context.get("technical_level", "medium")
        })
        
        best_response = None
        best_score = -1
        is_learned = False
        
        # Prova prima le risposte apprese se richiesto
        if use_learned and self.learned_responses[category]:
            learned = self._get_best_learned_response(category, context)
            if learned:
                best_response = learned.text
                best_score = learned.user_feedback
                is_learned = True
                
        # Cerca nei template se non abbiamo trovato una buona risposta appresa
        if not best_response or best_score < 0.7:
            template = self._get_best_template(category, context)
            if template:
                template_score = template.success_rate * self._context_similarity(
                    template.context, context
                )
                if template_score > best_score:
                    best_response = template.text
                    best_score = template_score
                    is_learned = False
                    template.usage_count += 1
                    template.last_used = self.conversation_context["interaction_count"]
                    
        # Se la risposta è già stata usata recentemente, prova a trovarne un'altra
        if best_response in self.response_history:
            alternative = self._find_alternative_response(category, context, best_response)
            if alternative:
                best_response = alternative
                
        # Aggiorna la storia delle risposte
        self.response_history.add(best_response)
        if len(self.response_history) > self.max_history_size:
            self.response_history.pop()
            
        return best_response or self.templates["error"][0].text, is_learned
        
    def _find_alternative_response(self, category: str, context: Dict[str, str], 
                                 current_response: str) -> Optional[str]:
        """Trova una risposta alternativa quando la migliore è stata usata recentemente"""
        alternatives = []
        
        # Cerca nei template
        if category in self.templates:
            for template in self.templates[category]:
                if template.text != current_response:
                    score = template.success_rate * self._context_similarity(
                        template.context, context
                    )
                    alternatives.append((template.text, score))
                    
        # Cerca nelle risposte apprese
        for learned in self.learned_responses[category]:
            if learned.text != current_response:
                score = learned.user_feedback * self._context_similarity(
                    learned.context, context
                )
                alternatives.append((learned.text, score))
                
        # Prendi la migliore alternativa che non è nella storia
        alternatives.sort(key=lambda x: x[1], reverse=True)
        for text, _ in alternatives:
            if text not in self.response_history:
                return text
                
        return None
        
    def _get_best_template(self, category: str, context: Dict[str, str]) -> Optional[ResponseTemplate]:
        """Seleziona il template migliore basato sul contesto e sulla storia d'uso"""
        if category not in self.templates:
            return None
            
        templates = self.templates[category]
        best_template = None
        best_score = -1
        
        for template in templates:
            # Calcola similarità del contesto
            context_score = self._context_similarity(template.context, context)
            
            # Penalizza template usati di recente
            recency_penalty = 1.0
            if template.last_used > 0:
                distance = self.conversation_context["interaction_count"] - template.last_used
                recency_penalty = min(1.0, distance / 5.0)  # Penalità massima per 5 interazioni
                
            # Calcola score finale
            score = (
                context_score * 0.4 +  # Peso del contesto
                template.success_rate * 0.4 +  # Peso del successo passato
                recency_penalty * 0.2  # Peso della recenza
            )
            
            if score > best_score:
                best_score = score
                best_template = template
                
        return best_template
        
    def _get_best_learned_response(self, category: str, context: Dict[str, str]) -> Optional[LearnedResponse]:
        """Seleziona la migliore risposta appresa basata sul feedback e sul contesto"""
        responses = self.learned_responses[category]
        if not responses:
            return None
            
        best_response = None
        best_score = -1
        
        for response in responses:
            # Calcola similarità del contesto
            context_score = self._context_similarity(response.context, context)
            
            # Calcola tasso di successo
            success_rate = (
                response.positive_feedback_count / 
                (response.positive_feedback_count + response.negative_feedback_count)
                if response.positive_feedback_count + response.negative_feedback_count > 0
                else 0.5
            )
            
            # Calcola score finale
            score = (
                context_score * 0.4 +  # Peso del contesto
                success_rate * 0.4 +  # Peso del successo
                response.user_feedback * 0.2  # Peso del feedback generale
            )
            
            if score > best_score:
                best_score = score
                best_response = response
                
        return best_response
        
    def learn_response(self, category: str, response_text: str, 
                      context: Dict[str, str], feedback: float):
        """Impara una nuova risposta dall'interazione"""
        # Cerca se esiste già una risposta simile
        for learned in self.learned_responses[category]:
            if learned.text == response_text:
                # Aggiorna il feedback
                old_feedback = learned.user_feedback
                learned.user_feedback = (
                    old_feedback * learned.usage_count + feedback
                ) / (learned.usage_count + 1)
                
                # Aggiorna contatori di feedback
                if feedback > 0:
                    learned.positive_feedback_count += 1
                elif feedback < 0:
                    learned.negative_feedback_count += 1
                    
                learned.usage_count += 1
                learned.context.update(context)
                return
                
        # Altrimenti aggiungi una nuova risposta
        new_response = LearnedResponse(
            text=response_text,
            context=context,
            user_feedback=feedback,
            positive_feedback_count=1 if feedback > 0 else 0,
            negative_feedback_count=1 if feedback < 0 else 0
        )
        self.learned_responses[category].append(new_response)
        
    def update_template_success(self, category: str, template_text: str, success: bool):
        """Aggiorna il success rate di un template"""
        if category not in self.templates:
            return
            
        for template in self.templates[category]:
            if template.text == template_text:
                template.success_rate = (
                    template.success_rate * template.usage_count + (1 if success else 0)
                ) / (template.usage_count + 1)
                break
