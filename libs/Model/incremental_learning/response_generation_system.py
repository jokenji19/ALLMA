"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

Sistema avanzato di generazione delle risposte con supporto per:
- Generazione dinamica basata sul contesto
- Varietà linguistica adattiva
- Contestualizzazione profonda
- Integrazione con sistema emotivo e personalità
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from enum import Enum
from datetime import datetime
import numpy as np
from collections import defaultdict
import random
import logging

from .emotional_system import EmotionalSystem, EmotionType, EmotionalState
from .user_profile import UserProfile
from .pattern_recognition_system import PatternRecognitionSystem

class ResponseStyle(Enum):
    """Stili di risposta supportati"""
    FORMAL = "formal"
    INFORMAL = "informal"
    TECHNICAL = "technical"
    SIMPLE = "simple"
    EMPATHETIC = "empathetic"
    PROFESSIONAL = "professional"
    EDUCATIONAL = "educational"
    MOTIVATIONAL = "motivational"

@dataclass
class ResponseTemplate:
    """Template per la generazione delle risposte"""
    style: ResponseStyle
    patterns: List[str]
    context_requirements: Set[str]
    emotion_compatibility: Set[EmotionType]
    min_formality: float = 0.0
    max_formality: float = 1.0
    technical_level: float = 0.5
    
    def matches_context(self, context: Dict[str, Any]) -> bool:
        """Verifica se il template è compatibile con il contesto"""
        return all(req in context for req in self.context_requirements)
    
    def matches_emotion(self, emotion: EmotionType) -> bool:
        """Verifica se il template è compatibile con l'emozione"""
        return emotion in self.emotion_compatibility
    
    def matches_style(self, formality: float, technical_level: float) -> bool:
        """Verifica se il template è compatibile con lo stile richiesto"""
        return (self.min_formality <= formality <= self.max_formality and
                abs(self.technical_level - technical_level) <= 0.3)

class ResponseGenerator:
    """Sistema avanzato di generazione delle risposte"""
    
    def __init__(self, emotional_system: EmotionalSystem = None, 
                 pattern_recognition: PatternRecognitionSystem = None,
                 knowledge_memory = None, 
                 personality = None):
        """
        Inizializza il generatore di risposte
        
        Args:
            emotional_system: Sistema emotivo per l'analisi delle emozioni
            pattern_recognition: Sistema di riconoscimento dei pattern
            knowledge_memory: Sistema di memoria e conoscenza
            personality: Sistema di gestione della personalità
        """
        self.emotional_system = emotional_system
        self.pattern_recognition = pattern_recognition
        self.knowledge = knowledge_memory
        self.personality = personality
        
        # Inizializza i componenti base
        self.templates = self._initialize_templates()
        self.response_history = []
        self.style_adaptation = defaultdict(float)
        self.context_memory = {}
        self.interest_usage_count = {}  # Per tenere traccia dell'uso degli interessi
        self.last_responses = []  # Per evitare ripetizioni ravvicinate
        
    def _initialize_templates(self):
        """Inizializza i template di risposta predefiniti"""
        self.templates = {style: [] for style in ResponseStyle}
        
        # Template empatici
        self.templates[ResponseStyle.EMPATHETIC].extend([
            ResponseTemplate(
                style=ResponseStyle.EMPATHETIC,
                patterns=[
                    "Capisco come ti senti. Parliamone insieme.",
                    "È normale sentirsi così. Sono qui per ascoltarti.",
                    "Mi dispiace che tu ti senta così. Vuoi parlarne?",
                    "Ti ascolto e capisco la tua situazione.",
                    "Sono qui per supportarti. Come posso aiutarti?"
                ],
                context_requirements={"emotion"},
                emotion_compatibility={
                    EmotionType.EMPATHY, EmotionType.TRUST, 
                    EmotionType.JOY, EmotionType.SADNESS
                },
                max_formality=0.6,
                technical_level=0.3
            ),
            ResponseTemplate(
                style=ResponseStyle.EMPATHETIC,
                patterns=[
                    "È bello vedere il tuo entusiasmo! Cosa ti rende così felice?",
                    "Mi fa piacere che tu sia felice! Raccontami di più.",
                    "Il tuo stato d'animo positivo è contagioso! Continuiamo questa bella conversazione.",
                    "Che bello sentirti così positivo! Di cosa vorresti parlare?",
                    "La tua energia positiva è fantastica! Cosa ti entusiasma di più?"
                ],
                context_requirements={"emotion"},
                emotion_compatibility={
                    EmotionType.JOY, EmotionType.CURIOSITY, 
                    EmotionType.ANXIETY, EmotionType.FEAR
                },
                min_formality=0.0,
                max_formality=0.6,
                technical_level=0.4
            ),
            ResponseTemplate(
                style=ResponseStyle.EMPATHETIC,
                patterns=[
                    "La tua curiosità è stimolante! Esploriamo insieme questo argomento in dettaglio.",
                    "Mi piace il tuo interesse! Quale aspetto vorresti approfondire?",
                    "È bello vedere la tua voglia di saperne di più! Da dove vuoi iniziare?"
                ],
                context_requirements={"topics"},
                emotion_compatibility={
                    EmotionType.JOY, EmotionType.CURIOSITY, 
                    EmotionType.ANXIETY, EmotionType.FEAR, EmotionType.SADNESS
                },
                min_formality=0.0,
                max_formality=0.6,
                technical_level=0.4
            ),
            # Template per saluti
            ResponseTemplate(
                style=ResponseStyle.EMPATHETIC,
                patterns=[
                    "Che bello {action} con {emotion} in questo {situation}!",
                    "È un piacere {action} in questo momento di {situation}",
                    "Mi fa piacere {action} in questa occasione di {situation}"
                ],
                context_requirements={"action", "situation", "emotion"},
                emotion_compatibility={EmotionType.JOY, EmotionType.TRUST},
                max_formality=0.8,
                technical_level=0.3
            ),
            # Template per saluti tristi
            ResponseTemplate(
                style=ResponseStyle.EMPATHETIC,
                patterns=[
                    "Capisco la tua {emotion} per questo {situation}",
                    "Condivido la tua {emotion} in questo {situation}",
                    "Ti sono vicino in questo momento di {situation}"
                ],
                context_requirements={"action", "situation", "emotion"},
                emotion_compatibility={EmotionType.SADNESS, EmotionType.EMPATHY},
                max_formality=0.8,
                technical_level=0.3
            )
        ])
        
        # Template formali
        self.templates[ResponseStyle.FORMAL].extend([
            ResponseTemplate(
                style=ResponseStyle.FORMAL,
                patterns=[
                    "Mi permetta di {action}",
                    "Vorrei cortesemente {action}",
                    "Sarebbe opportuno {action}"
                ],
                context_requirements={"intent", "action"},
                emotion_compatibility={EmotionType.NEUTRAL, EmotionType.TRUST},
                min_formality=0.7,
                technical_level=0.6
            ),
            ResponseTemplate(
                style=ResponseStyle.FORMAL,
                patterns=[
                    "Comprendo il suo interesse per {topics[0]}. Posso fornirle maggiori dettagli su questo argomento.",
                    "La sua esperienza con {topics[0]} è molto interessante. Vorrebbe approfondire qualche aspetto specifico?",
                    "Mi permetta di suggerirle alcuni approfondimenti su {topics[0]}.",
                    "Apprezzo molto il suo punto di vista su {topics[0]}. Potremmo esplorare ulteriormente questo aspetto."
                ],
                context_requirements={"topics"},
                emotion_compatibility={EmotionType.CURIOSITY, EmotionType.NEUTRAL},
                min_formality=0.6,
                max_formality=1.0,
                technical_level=0.5
            )
        ])
        
        # Template tecnici
        self.templates[ResponseStyle.TECHNICAL].extend([
            ResponseTemplate(
                style=ResponseStyle.TECHNICAL,
                patterns=[
                    "L'analisi indica che {technical_detail}",
                    "Secondo i dati disponibili, {technical_detail}",
                    "Le specifiche tecniche mostrano {technical_detail}",
                    "Analizzando il contesto di {topics[0]}, posso fornire informazioni tecniche dettagliate su questo argomento.",
                    "Basandomi sui pattern rilevati, posso espandere la discussione su {topics[0]} con dettagli tecnici specifici.",
                    "Dal punto di vista tecnico, {topics[0]} presenta diverse caratteristiche interessanti da analizzare.",
                    "Le implementazioni più avanzate di {topics[0]} richiedono una comprensione approfondita dei concetti base."
                ],
                context_requirements={"technical_detail", "data", "topics"},
                emotion_compatibility={EmotionType.NEUTRAL, EmotionType.CURIOSITY},
                min_formality=0.4,
                technical_level=0.8
            ),
            ResponseTemplate(
                style=ResponseStyle.TECHNICAL,
                patterns=[
                    "Analizzando il contesto di {topics[0]}, posso fornire informazioni tecniche dettagliate su questo argomento.",
                    "Basandomi sui pattern rilevati, posso espandere la discussione su {topics[0]} con dettagli tecnici specifici.",
                    "Dal punto di vista tecnico, {topics[0]} presenta diverse caratteristiche interessanti da analizzare.",
                    "Le implementazioni più avanzate di {topics[0]} richiedono una comprensione approfondita dei concetti base."
                ],
                context_requirements={"topics"},
                emotion_compatibility={EmotionType.NEUTRAL, EmotionType.CURIOSITY},
                min_formality=0.4,
                max_formality=1.0,
                technical_level=0.8
            )
        ])
        
        return self.templates
    
    def generate_response(self, context: Dict[str, Any], user_profile: UserProfile, 
                         emotion: EmotionType = None, conversation_history: List[str] = None) -> str:
        """
        Genera una risposta appropriata basata sul contesto, profilo utente ed emozione
        
        Args:
            context: Dizionario con informazioni sul contesto
            user_profile: Profilo dell'utente
            emotion: Emozione principale da considerare
            conversation_history: Storico della conversazione
            
        Returns:
            str: La risposta generata
        """
        if conversation_history is None:
            conversation_history = []
            
        # Aggiorna la memoria del contesto
        self.context_memory.update(context)
        
        # Prepara lo stato emotivo
        emotional_state = EmotionalState(
            primary_emotion=emotion or EmotionType.NEUTRAL,
            intensity=0.8,
            language="it",
            context=context
        )
        
        # Estrai i topic dal contesto
        topics = [context.get("topic", ""), context.get("action", "")]
        topics = [t for t in topics if t]
        
        # Genera la risposta usando il metodo esistente
        response = self._generate_response(emotional_state, topics, user_profile, conversation_history)
        
        # Aggiungi alla storia delle risposte
        self.last_responses.append(response)
        if len(self.last_responses) > 5:
            self.last_responses.pop(0)
            
        return response

    def adapt_to_feedback(self, feedback: Dict[str, Any]) -> None:
        """
        Adatta il sistema in base al feedback ricevuto
        
        Args:
            feedback: Dizionario con il feedback, deve contenere:
                     - style_feedback: stile di risposta (str)
                     - score: punteggio del feedback (-1.0 a 1.0)
        """
        style = feedback.get("style_feedback")
        score = feedback.get("score", 0.0)
        
        if style and isinstance(score, (int, float)):
            # Aggiorna l'adattamento dello stile
            self.style_adaptation[style] += score
            
            # Limita i valori tra -1 e 1
            self.style_adaptation[style] = max(-1.0, min(1.0, self.style_adaptation[style]))

    def _is_response_too_similar(self, response: str, recent_responses: List[str]) -> bool:
        """
        Verifica se una risposta è troppo simile alle risposte recenti
        """
        # Converti tutto in minuscolo per il confronto
        response = response.lower()
        
        for recent in recent_responses:
            recent = recent.lower()
            # Calcola similarità usando sequenze comuni più lunghe
            similarity = self._sequence_similarity(response, recent)
            if similarity > 0.6:  # Ridotto da 0.7 a 0.6 per essere più selettivi
                return True
        return False

    def _sequence_similarity(self, s1: str, s2: str) -> float:
        """
        Calcola la similarità tra due stringhe usando la sottosequenza comune più lunga
        """
        if not s1 or not s2:
            return 0.0
            
        # Trova la sottosequenza comune più lunga
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m):
            for j in range(n):
                if s1[i] == s2[j]:
                    dp[i + 1][j + 1] = dp[i][j] + 1
                else:
                    dp[i + 1][j + 1] = max(dp[i + 1][j], dp[i][j + 1])
        
        # Calcola similarità normalizzata
        lcs_length = dp[m][n]
        return 2.0 * lcs_length / (len(s1) + len(s2))

    def _generate_response(self, emotional_state: EmotionalState,
                          topics: List[str],
                          user_profile: UserProfile,
                          conversation_history: List[str],
                          technical_level: float = 0.5) -> str:
        """
        Genera una risposta appropriata basata sullo stato emotivo, i topic e il profilo utente
        """
        # Inizializza lista delle parti della risposta
        response_parts = []
        
        # 1. Genera risposta emotiva primaria
        primary_response = self._generate_primary_emotional_response(emotional_state)
        if primary_response:
            response_parts.append(primary_response)

        # 2. Genera risposta per topic se presenti
        if topics:
            topic_response = self._generate_topic_response(topics, technical_level, "it")
            if topic_response and not self._is_response_too_similar(topic_response, self.last_responses):
                response_parts.append(topic_response)

        # 3. Aggiungi risposta personalizzata se appropriato
        # Evitiamo di aggiungere troppe parti alla risposta
        if len(response_parts) < 2:
            personalized_response = self._generate_personalized_response(user_profile, "it")
            if personalized_response and not self._is_response_too_similar(personalized_response, self.last_responses):
                response_parts.append(personalized_response)

        # 4. Aggiungi risposta per emozioni secondarie se presenti e significative
        if emotional_state.secondary_emotions:
            secondary_response = self._generate_secondary_emotion_response(emotional_state.secondary_emotions, "it")
            if secondary_response and not self._is_response_too_similar(secondary_response, self.last_responses):
                response_parts.append(secondary_response)

        # 5. Se l'emozione è ansia o paura, aggiungi una risposta di supporto
        if emotional_state.primary_emotion in [EmotionType.ANXIETY, EmotionType.FEAR]:
            support_response = self._generate_supportive_response(emotional_state)
            if support_response and not self._is_response_too_similar(support_response, self.last_responses):
                response_parts.append(support_response)

        # Limita il numero di parti della risposta per evitare risposte troppo lunghe
        if len(response_parts) > 2:  # Ridotto da 3 a 2 per risposte più concise
            response_parts = response_parts[:2]

        # Unisci le parti della risposta
        final_response = " ".join(response_parts)

        # Verifica se la risposta è troppo simile alle ultime risposte nella conversazione
        if self._is_response_too_similar(final_response, self.last_responses):
            # Genera una risposta alternativa più varia
            alternative_response = self._generate_alternative_response(emotional_state)
            if alternative_response:
                final_response = alternative_response

        return final_response

    def _generate_alternative_response(self, emotional_state: EmotionalState) -> str:
        """
        Genera una risposta alternativa quando la risposta standard è troppo simile alle precedenti
        """
        templates = {
            EmotionType.JOY: [
                "Mi piace molto questo tuo entusiasmo! Raccontami di più.",
                "Che bello vederti così positivo! Condividi i tuoi pensieri.",
                "Il tuo buonumore è contagioso! Continuiamo su questa strada."
            ],
            EmotionType.SADNESS: [
                "Sono qui per ascoltarti, se vuoi parlarne.",
                "A volte fa bene esprimere ciò che si prova.",
                "Prendiamoci un momento per parlare di come ti senti."
            ],
            EmotionType.ANXIETY: [
                "Respira profondamente, affrontiamolo insieme.",
                "Parliamo con calma di ciò che ti preoccupa.",
                "Sono qui per aiutarti a trovare chiarezza."
            ],
            EmotionType.ANGER: [
                "Capisco la tua frustrazione. Vuoi parlarne?",
                "È importante esprimere ciò che ci turba.",
                "Parliamo di cosa possiamo fare per migliorare la situazione."
            ],
            EmotionType.CURIOSITY: [
                "Il tuo interesse è stimolante! Esploriamo insieme.",
                "Che bell'argomento hai sollevato! Approfondiamo.",
                "La tua curiosità ci porta in direzioni interessanti."
            ],
            EmotionType.NEUTRAL: [
                "Dimmi pure cosa ti passa per la mente.",
                "Sono qui per ascoltare i tuoi pensieri.",
                "Parliamo di ciò che preferisci."
            ]
        }

        emotion = emotional_state.primary_emotion
        if emotion in templates:
            return random.choice(templates[emotion])
        return self._generate_neutral_response(emotional_state)

    def _generate_primary_emotional_response(self, emotional_state: EmotionalState) -> str:
        """Genera la risposta primaria basata sull'emozione principale"""
        emotion = emotional_state.primary_emotion
        intensity = emotional_state.intensity

        if intensity < 0.2:
            return self._generate_neutral_response(emotional_state)
        
        if emotion == EmotionType.JOY:
            return self._generate_positive_response(emotional_state)
        elif emotion == EmotionType.SADNESS:
            return self._generate_empathetic_response(emotional_state)
        elif emotion == EmotionType.ANXIETY:
            return self._generate_supportive_response(emotional_state)
        elif emotion == EmotionType.ANGER:
            return self._generate_empathetic_response(emotional_state)
        elif emotion == EmotionType.CURIOSITY:
            return self._generate_curious_response(emotional_state)
        else:
            return self._generate_neutral_response(emotional_state)

    def _generate_topic_response(self, topics: List[str], technical_level: float, language: str) -> str:
        """Genera una risposta basata sui topic"""
        templates = {
            "tecnologia": [
                "Parliamo di questo aspetto della tecnologia.",
                "Qual è l'aspetto tecnologico che ti interessa di più?",
                "Mi appassiona molto questo tema tecnologico.",
                "La tecnologia offre infinite possibilità di discussione.",
                "Questo argomento tecnologico è molto interessante."
            ],
            "emozioni": [
                "Le emozioni sono fondamentali per comprenderci.",
                "Cosa vorresti condividere dei tuoi sentimenti?",
                "È importante parlare di come ci sentiamo.",
                "Le emozioni ci aiutano a crescere insieme.",
                "I sentimenti sono una parte essenziale del dialogo."
            ],
            "preferenze": [
                "Le tue preferenze sono preziose per personalizzare l'esperienza.",
                "Dimmi di più su cosa preferisci.",
                "I tuoi gusti mi aiutano a capirti meglio.",
                "È importante conoscere le tue preferenze.",
                "Le tue scelte guidano la nostra interazione."
            ],
            "feedback": [
                "Il tuo feedback è fondamentale per migliorare.",
                "Grazie per condividere la tua opinione.",
                "I tuoi commenti sono molto utili.",
                "Il tuo parere è prezioso per crescere insieme.",
                "Apprezzo molto i tuoi suggerimenti."
            ],
            "apprendimento": [
                "Ogni conversazione è un'opportunità per crescere.",
                "Impariamo qualcosa di nuovo insieme.",
                "La curiosità è il motore dell'apprendimento.",
                "Cresciamo insieme attraverso il dialogo.",
                "L'apprendimento è un viaggio condiviso."
            ]
        }

        responses = []
        for topic in topics[:2]:  # Limita a massimo 2 topic per evitare risposte troppo lunghe
            if topic in templates:
                response = random.choice(templates[topic])
                if response not in responses:  # Evita duplicati
                    responses.append(response)
        
        return " ".join(responses) if responses else ""

    def _generate_empathetic_response(self, emotional_state: EmotionalState) -> str:
        """Genera una risposta empatica appropriata"""
        templates = [
            "Capisco come ti senti. Parliamone insieme.",
            "È normale sentirsi così. Sono qui per ascoltarti.",
            "Mi dispiace che tu ti senta così. Vuoi parlarne?",
            "Ti ascolto e capisco la tua situazione.",
            "Sono qui per supportarti. Come posso aiutarti?",
            "La tua sensazione è comprensibile. Vuoi approfondire?",
            "Ti capisco perfettamente. Come posso esserti d'aiuto?",
            "Sono al tuo fianco. Vuoi condividere i tuoi pensieri?"
        ]
        
        return random.choice(templates)

    def _generate_positive_response(self, emotional_state: EmotionalState) -> str:
        """Genera una risposta positiva appropriata"""
        templates = [
            "È bello vedere il tuo entusiasmo! Cosa ti rende così felice?",
            "Mi fa piacere che tu sia felice! Raccontami di più.",
            "Il tuo stato d'animo positivo è contagioso! Continuiamo questa bella conversazione.",
            "Che bello sentirti così positivo! Di cosa vorresti parlare?",
            "La tua energia positiva è fantastica! Cosa ti entusiasma di più?",
            "Mi rallegro del tuo buon umore! Cosa ti ha reso così contento?",
            "È un piacere vederti così sereno! Condividi con me questa gioia.",
            "Il tuo ottimismo è stimolante! Cosa ti rende così entusiasta?"
        ]
        
        return random.choice(templates)

    def _generate_curious_response(self, emotional_state: EmotionalState) -> str:
        """Genera una risposta per la curiosità appropriata"""
        templates = [
            "Mi piace il tuo interesse! Quale aspetto vorresti approfondire?",
            "La tua curiosità è stimolante! Cosa ti interessa di più?",
            "È bello vedere la tua voglia di saperne di più! Da dove vuoi iniziare?",
            "Adoro la tua curiosità! Cosa vorresti scoprire?",
            "Il tuo desiderio di conoscenza è fantastico! Su cosa ti piacerebbe concentrarti?",
            "La tua sete di sapere è contagiosa! Cosa ti incuriosisce maggiormente?",
            "Apprezzo molto la tua curiosità! Quale aspetto ti affascina di più?",
            "È stimolante il tuo interesse! Da dove preferisci partire?"
        ]

        return random.choice(templates)

    def _generate_neutral_response(self, emotional_state: EmotionalState) -> str:
        """Genera una risposta neutra appropriata"""
        templates = [
            "Sono qui per aiutarti. Cosa vorresti approfondire?",
            "Dimmi di più su cosa hai in mente.",
            "Raccontami meglio cosa stai pensando.",
            "Sono tutto orecchi. Di cosa vorresti parlare?",
            "Sono qui per ascoltarti. Cosa ti interessa esplorare?",
            "Parliamone insieme. Da dove vuoi iniziare?",
            "Ti ascolto con interesse. Qual è il tuo pensiero?",
            "Sono qui per te. Cosa ti piacerebbe discutere?"
        ]
        
        return random.choice(templates)

    def _generate_supportive_response(self, emotional_state: EmotionalState) -> str:
        """Genera una risposta di supporto per emozioni di paura o preoccupazione"""
        templates = [
            "Capisco la tua preoccupazione. Sono qui per aiutarti a trovare una soluzione.",
            "È normale sentirsi così in queste situazioni. Possiamo affrontarla insieme.",
            "La tua preoccupazione è comprensibile. Parliamo di come possiamo gestirla."
        ]
        
        return random.choice(templates)

    def _generate_personalized_response(self, user_profile: UserProfile, language: str) -> str:
        """Genera una risposta personalizzata basata sul profilo utente"""
        # Ottieni gli interessi dell'utente
        interests = user_profile.get_interests()
        if not interests:
            return ""

        # Evita di parlare sempre degli stessi interessi usando un approccio pesato
        weighted_interests = {}
        for interest in interests:
            # Peso inversamente proporzionale alla frequenza di utilizzo
            weight = 1.0 / (1.0 + self.interest_usage_count.get(interest, 0))
            weighted_interests[interest] = weight

        # Seleziona un interesse in modo casuale ma pesato
        total_weight = sum(weighted_interests.values())
        if total_weight == 0:
            return ""

        r = random.uniform(0, total_weight)
        cumulative_weight = 0
        selected_interest = None
        for interest, weight in weighted_interests.items():
            cumulative_weight += weight
            if r <= cumulative_weight:
                selected_interest = interest
                break

        if not selected_interest:
            return ""

        # Aggiorna il conteggio di utilizzo
        self.interest_usage_count[selected_interest] = self.interest_usage_count.get(selected_interest, 0) + 1

        templates = [
            "Mi interessa il tuo punto di vista su {}.",
            "Potremmo approfondire {}.",
            "La tua esperienza con {} è preziosa.",
            "Parliamo di {}?",
            "Cosa ne pensi di {}?",
            "Mi piacerebbe conoscere la tua opinione su {}.",
            "Hai qualche spunto interessante su {}?",
            "Come vedi l'evoluzione di {}?"
        ]

        return random.choice(templates).format(selected_interest)

    def _generate_secondary_emotion_response(self, secondary_emotions: Union[List[Tuple[EmotionType, float]], Dict[EmotionType, float]],
                                          language: str) -> str:
        """Genera una risposta basata sulle emozioni secondarie"""
        templates = {
            EmotionType.CURIOSITY: [
                "Vedo anche una certa curiosità nelle tue parole.",
                "Noto anche un interesse a saperne di più."
            ],
            EmotionType.ANXIETY: [
                "Percepisco anche un po' di preoccupazione.",
                "Sento anche una leggera ansia nella tua voce."
            ],
            EmotionType.HOPE: [
                "Ma vedo anche un barlume di speranza.",
                "Noto anche un senso di ottimismo."
            ]
        }
        
        responses = []
        if isinstance(secondary_emotions, dict):
            emotions_list = secondary_emotions.items()
        else:
            emotions_list = secondary_emotions
            
        for emotion, intensity in emotions_list:
            if emotion in templates and intensity > 0.3:
                responses.append(random.choice(templates[emotion]))
                
        return " ".join(responses) if responses else ""
