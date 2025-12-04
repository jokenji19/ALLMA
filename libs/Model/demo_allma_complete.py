import sys
import os
from datetime import datetime, timedelta
import time
import json
from typing import Dict, Any, List, Optional

# Aggiungi il percorso della directory principale al PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa i sistemi core
from Model.incremental_learning.emotional_system import EmotionalSystem, EmotionType
from Model.incremental_learning.memory_system import EnhancedMemorySystem
from Model.incremental_learning.cognitive_evolution_system import CognitiveEvolutionSystem
from Model.incremental_learning.language_system import LanguageSystem
from Model.core.knowledge_base import KnowledgeBase
from Model.incremental_learning.emotional_memory_integration import EmotionalMemoryIntegration

# Importa gli enum
# from Model.enums import EmotionType

class ALLMADemo:
    def __init__(self):
        print("\n=== Inizializzazione ALLMA ===")
        
        # Cache per i risultati
        self._cache = {}
        
        # Inizializzazione dei sistemi core
        print("Inizializzazione sistema emotivo...")
        self.emotional_system = EmotionalSystem()
        
        print("Inizializzazione sistema di memoria...")
        self.memory_system = EnhancedMemorySystem()
        
        print("Inizializzazione sistema cognitivo...")
        self.cognitive_system = CognitiveEvolutionSystem()
        
        print("Inizializzazione comprensione del linguaggio...")
        self.language_understanding = LanguageSystem()
        
        print("Inizializzazione knowledge base...")
        self.knowledge_base = KnowledgeBase()
        
        print("Inizializzazione integrazione emotiva-memoria...")
        self.emotional_memory = EmotionalMemoryIntegration()
        self.emotional_memory.emotional_system = self.emotional_system
        self.emotional_memory.memory_system = self.memory_system
        
        print("Tutti i sistemi inizializzati correttamente!")
        
    def process_input(self, user_input, context=None):
        """Elabora l'input dell'utente attraverso tutti i sistemi di ALLMA"""
        if not context:
            context = {}
            
        # Aggiorna il contesto con l'input corrente
        context['last_input'] = user_input
        context['interaction_count'] = context.get('interaction_count', 0) + 1
        
        # 1. Comprensione del linguaggio
        print("\nInput utente:", user_input)
        print("Contesto:", context)
        print("\n1. Comprensione del linguaggio:")
        understanding = self.language_understanding.process_input(user_input)
        print("Analisi:", understanding)
        
        # 2. Elaborazione emotiva
        print("\n2. Elaborazione emotiva:")
        emotion = self.emotional_system.process_stimulus(user_input, understanding)
        print("Emozione rilevata:", emotion)
        
        # 3. Elaborazione cognitiva
        print("\n3. Elaborazione cognitiva:")
        cognitive_result = self.cognitive_system.process_experience({
            'input': user_input,
            'understanding': understanding,
            'emotion': emotion,
            'context': context
        })
        print("Risultato:", cognitive_result)
        
        # 4. Memoria
        print("\n4. Memoria:")
        memory_result = self.memory_system.process_experience(
            experience=user_input,
            emotional_valence=emotion.valence
        )
        print("Risultato:", memory_result)
        
        # 5. Integrazione emotiva-memoria
        print("\n5. Integrazione emotiva-memoria:")
        # Aggiorniamo il contesto con l'emozione
        context.update({
            'emotion': emotion,
            'understanding': understanding
        })
        integration_result = self.emotional_memory.process_input(user_input, context)
        print("Risultato:", integration_result)
        
        # 6. Knowledge Base
        print("\n6. Knowledge Base aggiornata\n")
        self.knowledge_base.add_knowledge({
            'input': user_input,
            'understanding': understanding,
            'emotion': emotion,
            'cognitive': cognitive_result,
            'memory': memory_result,
            'integration': integration_result,
            'timestamp': datetime.now().isoformat()
        })
        
        # 7. Genera risposta
        response = self.generate_response(
            understanding,
            emotion,
            cognitive_result,
            memory_result,
            integration_result
        )
        
        return response

    def generate_response(self, understanding, emotion, cognitive_result, memory_result, integration_result):
        """Genera una risposta basata su tutti i sistemi di ALLMA"""
        # 1. Usa il sistema cognitivo
        cognitive_level = cognitive_result  # cognitive_result è già un float
        
        # 2. Recupera memorie rilevanti
        relevant_memories = []
        if memory_result and isinstance(memory_result, dict) and 'memory_item' in memory_result:
            relevant_memories = self.memory_system.recall_memory(
                memory_result['memory_item'].get('content', ''),
                memory_result['memory_item'].get('context', {})
            )
        
        # 3. Usa la knowledge base per arricchire la risposta
        kb_query = understanding.get('text', '') if isinstance(understanding, dict) else str(understanding)
        kb_result = self.knowledge_base.query_knowledge(kb_query)
        
        # 4. Genera una risposta appropriata
        response = ""
        
        # Se abbiamo un'emozione, adatta la risposta
        if emotion and hasattr(emotion, 'primary_emotion'):
            if emotion.primary_emotion == EmotionType.NEUTRAL:
                response = "Ciao! Come posso aiutarti oggi?"
            elif emotion.primary_emotion == EmotionType.HAPPINESS:
                response = "Sono felice di parlare con te! Come posso esserti utile?"
            elif emotion.primary_emotion == EmotionType.SADNESS:
                response = "Mi dispiace se c'è qualcosa che non va. Posso aiutarti in qualche modo?"
            else:
                response = "Sono qui per aiutarti. Come posso farlo?"
        
        # Se abbiamo risultati dalla knowledge base, usali
        if kb_result and kb_result.get('found', False):
            matches = kb_result.get('matches', [])
            if matches:
                # Usa il primo match come risposta
                match = matches[0]
                if isinstance(match, dict):
                    if 'value' in match:
                        response = str(match['value'])
                    elif 'fact' in match:
                        response = str(match['fact'])
                else:
                    response = str(match)
        
        # Se abbiamo memorie rilevanti, aggiungile alla risposta
        if relevant_memories:
            memory_text = relevant_memories[0].get('content', '') if isinstance(relevant_memories[0], dict) else str(relevant_memories[0])
            response = f"{response}\nQuesto mi ricorda: {memory_text}"
        
        # Se non abbiamo generato una risposta, usa una risposta di default
        if not response:
            response = "Mi dispiace, non ho una risposta specifica per questo. Come posso aiutarti diversamente?"
            
        return response

    def run_interactive(self):
        """Avvia una sessione interattiva con ALLMA"""
        print("\n=== Sessione Interattiva ALLMA ===")
        print("Scrivi 'exit' per terminare la sessione")
        
        context = {
            'session_start': datetime.now().isoformat(),
            'interaction_count': 0
        }
        
        while True:
            try:
                user_input = input("\n👤 Tu: ").strip()
                if user_input.lower() == 'exit':
                    print("\n🤖 ALLMA: Arrivederci! È stato un piacere interagire con te.")
                    break
                    
                # Aggiorna il contesto
                context['interaction_count'] += 1
                context['last_input'] = user_input
                
                # Processa l'input attraverso tutti i sistemi
                result = self.process_input(user_input, context)
                
                # Genera e mostra la risposta
                response = result
                
                print(f"\n🤖 ALLMA: {response}")
                
            except Exception as e:
                print(f"\n🤖 ALLMA: Mi dispiace, ho avuto un problema nell'elaborazione. Dettagli: {str(e)}")
                continue

    def run_demo(self):
        print("\n=== Demo Completa ALLMA ===")
        
        # Test 1: Prima Interazione
        print("\n=== Test 1: Prima Interazione ===")
        result1 = self.process_input(
            "Ciao! Sono felice di conoscerti!",
            {'time': '09:00', 'context': 'greeting'}
        )
        
        # Test 2: Apprendimento
        print("\n=== Test 2: Apprendimento ===")
        result2 = self.process_input(
            "Mi piace molto programmare in Python e sviluppare sistemi di AI",
            {'time': '10:00', 'context': 'learning'}
        )
        
        # Test 3: Emozione Complessa
        print("\n=== Test 3: Emozione Complessa ===")
        result3 = self.process_input(
            "Sono molto orgoglioso di aver completato il mio progetto ALLMA!",
            {'time': '11:00', 'context': 'achievement'}
        )
        
        # Test 4: Memoria e Richiamo
        print("\n=== Test 4: Memoria e Richiamo ===")
        memories = self.memory_system.recall_memory("progetto")
        print("\nMemorie recuperate:")
        for memory in memories[:3]:  # Mostra solo le prime 3
            print(f"- {memory}")
            
        # Test 5: Evoluzione Cognitiva
        print("\n=== Test 5: Evoluzione Cognitiva ===")
        result5 = self.process_input(
            "Ho imparato che la programmazione richiede pazienza e dedizione",
            {'time': '12:00', 'context': 'reflection'}
        )
        
        # Statistiche finali
        print("\n=== Statistiche Finali ===")
        print("1. Sistema Emotivo:")
        print(f"- Ultima emozione: {result5}")
        
        print("\n2. Sistema di Memoria:")
        memory_stats = self.memory_system.get_memory_stats()
        print(f"- Memorie totali: {memory_stats.get('total_memories', 0)}")
        print(f"- Memorie consolidate: {memory_stats.get('consolidated_memories', 0)}")
        print(f"- Memorie recuperate: {memory_stats.get('retrieved_memories', 0)}")
        
        print("\n3. Sistema Cognitivo:")
        print(f"- Livello cognitivo: {result5}")
        
        print("\n4. Knowledge Base:")
        print(f"- Conoscenze acquisite: {len(self.knowledge_base.get_all_knowledge())}")
        
        print("\n=== Demo Completata ===")

if __name__ == "__main__":
    demo = ALLMADemo()
    demo.run_interactive()
