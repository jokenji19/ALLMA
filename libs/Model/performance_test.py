"""
Test delle performance di ALLMA
"""
from performance_profiler import PerformanceProfiler
from incremental_learning.emotional_system import EmotionalSystem
from incremental_learning.integrated_allma import IntegratedALLMA
from incremental_learning.memory_system import Memory, MemoryItem
import random
from datetime import datetime

def run_performance_test():
    """Esegue un test completo delle performance"""
    profiler = PerformanceProfiler()
    allma = IntegratedALLMA()  # Usa direttamente IntegratedALLMA
    
    # Test scenari
    test_inputs = [
        "Sono molto felice oggi!",
        "Mi sento un po' triste...",
        "Che ne pensi dell'intelligenza artificiale?",
        "Ti ricordi cosa ti ho detto prima?",
        "Parliamo di qualcosa di completamente diverso",
    ]
    
    print("Iniziando il test delle performance...")
    profiler.start_profiling()
    
    # Test elaborazione emotiva
    @profiler.profile_operation('emotional_processing')
    def test_emotional_processing():
        for _ in range(10):
            input_text = random.choice(test_inputs)
            emotion = allma.emotional_system.process_stimulus(input_text)
    
    # Test operazioni di memoria
    @profiler.profile_operation('memory_operations')
    def test_memory_operations():
        for i in range(10):
            # Test aggiunta memoria
            content = f"Memoria di test {i}"
            context = {
                "timestamp": datetime.now(),
                "type": "test",
                "importance": random.random()
            }
            emotional_valence = random.uniform(-1, 1)
            
            # Crea un oggetto Memory
            memory = Memory(
                content=content,
                context=context,
                emotional_valence=emotional_valence,
                importance=random.random()
            )
            
            # Aggiunge memoria
            allma.memory_system.add_memory(memory.to_dict())
            
            # Test recupero memoria
            memories = allma.memory_system.recall_memory(
                query=content,
                context=context
            )
    
    # Test operazioni cognitive
    @profiler.profile_operation('cognitive_operations')
    def test_cognitive_operations():
        for _ in range(10):
            input_text = random.choice(test_inputs)
            response = allma.cognitive_processor.process_input(input_text)
    
    # Test integrazione emotivo-cognitiva
    @profiler.profile_operation('emotional_cognitive_integration')
    def test_integration():
        for _ in range(10):
            input_text = random.choice(test_inputs)
            # Processa input con integrazione completa
            allma.process_input(input_text)
    
    # Esegui i test
    print("\nEsecuzione test elaborazione emotiva...")
    test_emotional_processing()
    
    print("Esecuzione test operazioni di memoria...")
    test_memory_operations()
    
    print("Esecuzione test operazioni cognitive...")
    test_cognitive_operations()
    
    print("Esecuzione test integrazione emotivo-cognitiva...")
    test_integration()
    
    # Genera e mostra il report
    stats = profiler.stop_profiling()
    print("\nStatistiche dettagliate:")
    stats.print_stats(20)  # Mostra le top 20 funzioni più lente
    
    print("\nReport delle performance:")
    print(profiler.generate_report())

if __name__ == "__main__":
    run_performance_test()
