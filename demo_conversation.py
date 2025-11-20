from Model.core.context_understanding import ContextUnderstandingSystem
from Model.core.knowledge_memory import KnowledgeMemory
from Model.core.response_generator import ResponseGenerator
from Model.core.personality_coalescence import PersonalityCoalescence
from Model.core.nlp_processor import NLPProcessor

def simulate_conversation():
    # Inizializza i componenti
    nlp = NLPProcessor()
    context = ContextUnderstandingSystem()
    knowledge = KnowledgeMemory()
    personality = PersonalityCoalescence()
    response_gen = ResponseGenerator(context, knowledge, personality)
    
    # Simula una conversazione
    conversation = [
        "Ciao! Mi piacerebbe sapere qualcosa sulle reti neurali.",
        "Interessante! E come vengono utilizzate nel deep learning?",
        "Puoi farmi un esempio pratico di applicazione?",
        "Ho capito. E quali sono i vantaggi rispetto ad altri approcci di machine learning?"
    ]
    
    print("=== Demo Conversazione con ALLMA ===\n")
    
    for user_message in conversation:
        print(f"Utente: {user_message}")
        
        # Aggiorna il contesto
        context.update_context(user_message)
        
        # Genera la risposta
        response = response_gen.generate_response(user_message)
        
        print(f"ALLMA: {response}\n")

if __name__ == "__main__":
    simulate_conversation()
