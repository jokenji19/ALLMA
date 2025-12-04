"""ResponseGenerator - Sistema di generazione delle risposte"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from Model.memory_system.knowledge_memory import KnowledgeMemory
from Model.response_system.contextual_response import ResponseContext
from Model.personality_system.personality import Personality
from Model.core.context_understanding import ContextUnderstandingSystem
import random

class ResponseGenerator:
    def __init__(
        self, 
        knowledge_memory: Optional[KnowledgeMemory] = None,
        context_system: Optional[ContextUnderstandingSystem] = None,
        personality: Optional[Personality] = None
    ):
        """
        Inizializza il generatore di risposte
        
        Args:
            knowledge_memory: Sistema di memoria per la conoscenza
            context_system: Sistema di comprensione del contesto
            personality: Sistema di personalità
        """
        self.knowledge_memory = knowledge_memory
        self.context_system = context_system
        self.personality = personality
        self.performance_stats = {
            'responses_generated': 0,
            'total_quality_score': 0.0,
            'total_time': 0.0
        }
        
    def generate_response(
        self,
        query: str,
        context: Optional[ResponseContext] = None
    ) -> str:
        """
        Genera una risposta basata sulla query e il contesto
        
        Args:
            query: Query dell'utente
            context: Contesto della risposta
            
        Returns:
            str: La risposta generata
        """
        try:
            # Analizza il contesto se disponibile
            if self.context_system and context:
                context_info = self.context_system.analyze_context(query, context)
            else:
                context_info = {}

            # Recupera la conoscenza rilevante
            if self.knowledge_memory:
                knowledge = self.knowledge_memory.get_knowledge_for_text(query)
            else:
                knowledge = []
                
            # Applica la personalità se disponibile
            if self.personality:
                response_style = self.personality.get_response_style(context)
            else:
                response_style = "neutral"
                
            # Genera una risposta informata se c'è conoscenza disponibile
            if knowledge:
                base_response = self._generate_informed_response(query, knowledge, context)
            else:
                # Altrimenti genera una risposta base
                base_response = self._generate_basic_response(query, context)
                
            # Adatta la risposta in base al contesto e alla personalità
            final_response = self._adapt_response(
                base_response,
                context_info=context_info,
                response_style=response_style
            )
            
            return final_response
            
        except Exception as e:
            print(f"Errore nella generazione della risposta: {e}")
            return f"Mi dispiace, si è verificato un errore: {str(e)}"
        
    def _generate_informed_response(self, query: str, knowledge: List[str], context=None) -> str:
        """
        Genera una risposta informata basata sulla conoscenza disponibile
        
        Args:
            query: La query dell'utente
            knowledge: Lista di conoscenze rilevanti
            context: Il contesto della risposta
            
        Returns:
            str: La risposta generata
        """
        # Analizza la query per identificare il tipo di informazione richiesta
        query_lower = query.lower()
        is_requirements_query = any(word in query_lower for word in ["requirements", "technical", "specifications"])
        is_technology_query = any(word in query_lower for word in ["technology", "stack", "framework"])
        is_performance_query = any(word in query_lower for word in ["performance", "speed", "time"])
        
        # Organizza la conoscenza per categoria
        requirements = []
        technologies = []
        performance = []
        
        for info in knowledge:
            info_lower = info.lower()
            if any(word in info_lower for word in ["requirement", "must", "should", "need"]):
                requirements.append(info)
            if any(word in info_lower for word in ["framework", "library", "stack", "technology", "tensorflow"]):
                technologies.append(info)
            if any(word in info_lower for word in ["performance", "speed", "time", "latency"]):
                performance.append(info)
                
        # Genera una risposta basata sul tipo di query e la conoscenza disponibile
        response_parts = []
        
        if is_requirements_query:
            if requirements:
                response_parts.append("Key requirements include: " + ", ".join(requirements))
            if technologies:
                response_parts.append("Technology requirements include: " + ", ".join(technologies))
            if performance:
                response_parts.append("Performance requirements: " + ", ".join(performance))
                
        elif is_technology_query:
            if technologies:
                response_parts.append("Technology stack includes: " + ", ".join(technologies))
                
        elif is_performance_query:
            if performance:
                response_parts.append("Performance requirements: " + ", ".join(performance))
                
        else:
            # Se la query non è specifica, includi tutte le informazioni rilevanti
            if technologies:
                response_parts.append("Technology stack includes: " + ", ".join(technologies))
            if requirements:
                response_parts.append("Key requirements include: " + ", ".join(requirements))
            if performance:
                response_parts.append("Performance requirements: " + ", ".join(performance))
                
        if not response_parts:
            return self._generate_basic_response(query, context)
            
        return " ".join(response_parts)
        
    def _generate_basic_response(self, query: str, context=None) -> str:
        """
        Genera una risposta base quando non c'è conoscenza disponibile
        
        Args:
            query: La query dell'utente
            context: Il contesto della risposta
            
        Returns:
            str: La risposta generata
        """
        # Estrai il topic dal contesto se disponibile
        current_topic = None
        if context and hasattr(context, "current_topic"):
            current_topic = context.current_topic
            
        # Genera una risposta base
        if current_topic:
            return f"I understand you're asking about {current_topic}. Could you provide more specific information?"
        else:
            return "Could you provide more specific information about your question?"
    
    def _extract_topics(self, text: str) -> List[str]:
        """Estrae i topic dal testo"""
        topics = []
        
        # Lista di topic e sinonimi
        topic_mapping = {
            'neural_networks': ['reti neurali', 'neural networks', 'rete neurale', 'neuroni artificiali'],
            'deep_learning': ['deep learning', 'apprendimento profondo', 'dl', 'reti profonde'],
            'machine_learning': ['machine learning', 'ml', 'apprendimento automatico', 'apprendimento'],
            'artificial_intelligence': ['intelligenza artificiale', 'ai', 'artificial intelligence', 'intelligenza']
        }
        
        # Cerca i topic nel testo
        for main_topic, synonyms in topic_mapping.items():
            if any(syn in text for syn in synonyms):
                topics.append(main_topic)
                
        return topics
        
    def _formalize_response(self, text: str) -> str:
        """Rende la risposta più formale"""
        # Sostituisci espressioni informali con formali
        text = text.replace("ciao", "salve")
        text = text.replace("ok", "va bene")
        text = text.replace("!", ".")
        return text
        
    def _informalize_response(self, text: str) -> str:
        """Rende la risposta più informale"""
        # Sostituisci espressioni formali con informali
        text = text.replace("salve", "ciao")
        text = text.replace("cordialmente", "ciao")
        text = text.replace("La ringrazio", "grazie")
        return text + " :)"
        
    def _add_enthusiasm(self, text: str) -> str:
        """Aggiunge entusiasmo alla risposta"""
        enthusiastic_starts = [
            "Fantastico! ",
            "Ottimo! ",
            "Che bello! "
        ]
        return random.choice(enthusiastic_starts) + text
        
    def adapt_to_context(self, query: str, facts: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """Adatta la risposta al contesto dell'utente"""
        start_time = datetime.now()
        self.performance_stats['responses_generated'] += 1
        
        if not facts:
            response = "Mi dispiace, non ho informazioni rilevanti per rispondere."
            self._update_stats(0.5, start_time)
            return response
            
        # Adatta in base al livello di conoscenza
        knowledge_level = context.get('knowledge_level', 'base')
        style = context.get('preferred_style', 'informale')
        interests = context.get('interests', [])
        
        # Seleziona fatti rilevanti agli interessi
        relevant_facts = []
        for fact in facts:
            if any(interest.lower() in str(fact).lower() for interest in interests):
                relevant_facts.append(fact)
                
        if not relevant_facts:
            relevant_facts = facts
            
        # Genera risposta adattata
        response = self._generate_adapted_response(
            relevant_facts,
            knowledge_level,
            style
        )
        
        quality = len(relevant_facts) / len(facts) if facts else 0.5
        self._update_stats(quality, start_time)
        
        return response
    
    def _generate_adapted_response(self, facts: List[Dict[str, Any]], knowledge_level: str, style: str) -> str:
        """Genera una risposta adattata dai fatti"""
        # Costruisce la risposta base
        base_response = ""
        for fact in facts:
            if isinstance(fact, dict):
                for key, value in fact.items():
                    if isinstance(value, (str, int, float)):
                        base_response += f"{key}: {value}. "
                        
        # Adatta la risposta
        return self._format_response(base_response, knowledge_level, style)
    
    def _format_response(self, content: str, knowledge_level: str, style: str) -> str:
        """Formatta la risposta in base al livello e stile"""
        # Adattamento per livello di conoscenza
        if knowledge_level == 'base':
            content = self._simplify_content(content)
        elif knowledge_level == 'avanzato':
            content = self._enhance_content(content)
            
        # Adattamento per stile di interazione
        if style == 'formale':
            content = self._formalize_content(content)
        else:
            content = self._informalize_content(content)
            
        return content
    
    def _simplify_content(self, content: str) -> str:
        """Semplifica il contenuto per livello base"""
        # Sostituisce termini tecnici con spiegazioni più semplici
        simplifications = {
            'machine learning': 'apprendimento automatico dei computer',
            'deep learning': 'sistema avanzato di apprendimento dei computer',
            'neural network': 'rete che simula il funzionamento del cervello',
            'training': 'fase di apprendimento',
            'dataset': 'insieme di dati',
            'algorithm': 'serie di istruzioni',
            'model': 'sistema di apprendimento'
        }
        
        simplified = content
        for term, simple in simplifications.items():
            simplified = simplified.replace(term, f"{simple} ({term})")
            
        return simplified
    
    def _enhance_content(self, content: str) -> str:
        """Arricchisce il contenuto per livello avanzato"""
        # Aggiunge dettagli tecnici e collegamenti
        enhancements = {
            'machine learning': 'machine learning (inclusi algoritmi di ottimizzazione e analisi statistica)',
            'deep learning': 'deep learning (architetture neurali profonde con multiple layer di astrazione)',
            'training': 'training (processo di ottimizzazione iterativa dei parametri)',
            'model': 'modello computazionale (con parametri ottimizzabili)'
        }
        
        enhanced = content
        for term, detail in enhancements.items():
            enhanced = enhanced.replace(term, detail)
            
        return enhanced
    
    def _formalize_content(self, content: str) -> str:
        """Formalizza il contenuto"""
        # Sostituisce espressioni informali con equivalenti formali
        formalizations = {
            'molto': 'significativamente',
            'bello': 'apprezzabile',
            'fantastico': 'notevole',
            'capito': 'compreso',
            'cosa': 'argomento',
            'come': 'in quale modo'
        }
        
        formal = content
        for informal, formal_term in formalizations.items():
            formal = formal.replace(informal, formal_term)
            
        return formal
    
    def _informalize_content(self, content: str) -> str:
        """Rende il contenuto più informale e amichevole"""
        # Aggiunge espressioni informali e emoji
        informal_starts = [
            "Sai, ",
            "Interessante! ",
            "Guarda, ",
            "Ti spiego, ",
            "In pratica, "
        ]
        
        informal_ends = [
            " È affascinante, vero?",
            " Che ne pensi?",
            " Ti piacerebbe saperne di più?",
            " È davvero interessante!",
            " Continua pure a farmi domande!"
        ]
        
        import random
        content = random.choice(informal_starts) + content.lower()
        if not any(end in content for end in informal_ends):
            content += random.choice(informal_ends)
            
        return content

    def generate_contextual_response(self, query: str, context: Dict[str, Any], conversation_history: List[Dict[str, Any]]) -> str:
        """Genera una risposta considerando il contesto completo della conversazione"""
        # Analizza il contesto corrente
        current_topic = context.get('current_topic', '')
        user_knowledge = context.get('user_knowledge_level', 'base')
        emotion = context.get('current_emotion', 'neutral')
        
        # Recupera conoscenza rilevante dalla knowledge base
        relevant_knowledge = self.knowledge_memory.get_relevant_knowledge(query, current_topic)
        
        # Considera la storia della conversazione
        previous_topics = [msg.get('topic', '') for msg in conversation_history[-3:]]
        topic_continuity = current_topic in previous_topics
        
        # Seleziona template appropriato
        if not relevant_knowledge:
            templates = [
                "Mi piacerebbe saperne di più su questo argomento. Puoi dirmi qualcosa in più?",
                "È un argomento interessante! Cosa ne pensi?",
                "Non ho molte informazioni su questo, ma sono curioso/a di imparare!"
            ]
            return random.choice(templates)
            
        # Costruisce risposta base
        base_response = self._build_base_response(relevant_knowledge, topic_continuity)
        
        # Adatta al livello di conoscenza
        if user_knowledge == 'base':
            response = self._simplify_content(base_response)
        else:
            response = self._enhance_content(base_response)
            
        # Adatta allo stile emotivo
        if emotion in ['joy', 'surprise']:
            response = self._informalize_content(response)
        else:
            response = self._formalize_content(response)
            
        return response
        
    def _build_base_response(self, knowledge: List[Dict[str, Any]], topic_continuity: bool) -> str:
        """Costruisce una risposta base dalla conoscenza disponibile"""
        # Estrae informazioni chiave
        key_points = []
        for item in knowledge:
            point = item.description if hasattr(item, 'description') else item.get('description', '')
            confidence = item.confidence if hasattr(item, 'confidence') else item.get('confidence', 0.0)
            if confidence > 0.7 and point:
                key_points.append(point)
                    
        if not key_points:
            return "Non ho abbastanza informazioni sicure su questo argomento."
            
        # Costruisce risposta progressiva
        if topic_continuity:
            # Se è una continuazione, approfondisce
            response = "Per approfondire quanto detto prima, "
        else:
            # Se è un nuovo topic, introduce
            response = "Per quanto riguarda questo argomento, "
            
        # Aggiunge i punti chiave
        response += ". ".join(key_points[:2])  # Limita a 2 punti per non essere troppo prolisso
        
        return response
    
    def _update_stats(self, quality: float, start_time: datetime):
        """Aggiorna le statistiche di performance"""
        self.performance_stats['total_quality_score'] += quality
        self.performance_stats['total_time'] += (datetime.now() - start_time).total_seconds()
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Restituisce statistiche di performance"""
        total_responses = max(self.performance_stats['responses_generated'], 1)
        
        return {
            'quality': self.performance_stats['total_quality_score'] / total_responses,
            'avg_time': self.performance_stats['total_time'] / total_responses
        }

    def _adapt_response(self, base_response: str, context_info: Dict[str, Any], response_style: str) -> str:
        """Adatta la risposta in base al contesto e alla personalità"""
        # Adatta la risposta in base al contesto
        if context_info.get('user_emotion', '') == 'joy':
            base_response = self._add_enthusiasm(base_response)
        elif context_info.get('user_emotion', '') == 'sadness':
            base_response = self._add_sympathy(base_response)
            
        # Adatta la risposta in base alla personalità
        if response_style == 'formale':
            base_response = self._formalize_response(base_response)
        elif response_style == 'informale':
            base_response = self._informalize_response(base_response)
            
        return base_response

    def _add_sympathy(self, text: str) -> str:
        """Aggiunge simpatia alla risposta"""
        # Aggiungi espressioni di simpatia
        sympathetic_starts = [
            "Mi dispiace sentire questo. ",
            "Spero che tu stia bene. ",
            "È davvero spiacevole. "
        ]
        
        return random.choice(sympathetic_starts) + text
