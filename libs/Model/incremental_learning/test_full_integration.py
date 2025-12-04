import unittest
import time
from Model.incremental_learning.language_system import LanguageSystem
from Model.incremental_learning.performance_optimizer import PerformanceOptimizer, PerformanceMode
from Model.incremental_learning.resource_adapter import ResourceAdapter
from Model.incremental_learning.memory_manager import MemoryManager

class TestFullIntegration(unittest.TestCase):
    def setUp(self):
        self.language_system = LanguageSystem()
        self.performance_optimizer = PerformanceOptimizer()
        self.resource_adapter = ResourceAdapter()
        self.memory_manager = MemoryManager()

    def test_full_system_integration(self):
        """Test completo dell'integrazione di tutti i sistemi"""
        print("\n=== Test di Integrazione Completo ===")
        
        # 1. Test Iniziale Sistema Multilingua
        print("\n1. Test Sistema Multilingua:")
        self.language_system.set_language("it")
        greeting = self.language_system.get_response("greeting")
        print(f"- Risposta in Italiano: {greeting}")
        self.assertIn("Ciao", greeting)

        # 2. Test Performance Optimizer
        print("\n2. Test Performance Optimizer:")
        perf_mode = self.performance_optimizer.current_mode
        print(f"- Modalità Corrente: {perf_mode.value}")
        profile = self.performance_optimizer.get_current_profile()
        print(f"- Profilo Attivo: max_tasks={profile.max_concurrent_tasks}, "
              f"memory_buffer={profile.memory_buffer}GB")

        # 3. Test Resource Adapter
        print("\n3. Test Resource Adapter:")
        resources = self.resource_adapter.get_system_resources()
        print(f"- Risorse Disponibili: CPU={resources['cpu_usage']}%, "
              f"Memory={resources['memory_used_percent']}%")
        
        allocation = self.resource_adapter.adapt_resources()
        print(f"- Allocazione Risorse: max_memory={allocation.max_memory_usage}GB, "
              f"priority={allocation.cpu_priority}")

        # 4. Test Memory Manager con Carico
        print("\n4. Test Memory Manager:")
        
        # Genera alcuni dati di test
        test_data = [
            {"type": "critical", "content": "Dati importanti " + str(i)} 
            for i in range(5)
        ] + [
            {"type": "general", "content": "Dati normali " + str(i)} 
            for i in range(10)
        ]
        
        # Memorizza i dati
        stored_ids = []
        for data in test_data:
            item_id = self.memory_manager.store_item(
                data["content"], 
                category=data["type"]
            )
            stored_ids.append(item_id)
            
            # Simula accessi diversi
            if data["type"] == "critical":
                for _ in range(5):  # Accedi più volte ai dati critici
                    self.memory_manager.retrieve_item(item_id)
        
        # Verifica statistiche memoria
        stats = self.memory_manager.get_memory_stats()
        print(f"- Statistiche Memoria: items={stats['total_items']}, "
              f"active={stats['active_items']}, archived={stats['archived_items']}")

        # 5. Test Integrazione Completa
        print("\n5. Test Integrazione Completa:")
        
        # Simula carico di sistema
        for _ in range(3):
            # Accedi a dati casuali
            if stored_ids:
                random_id = stored_ids[int(time.time()) % len(stored_ids)]
                self.memory_manager.retrieve_item(random_id)
            
            # Verifica adattamento performance
            new_mode = self.performance_optimizer.should_switch_mode()
            if new_mode:
                print(f"- Cambio Modalità: {new_mode.value}")
            
            # Verifica adattamento risorse
            new_allocation = self.resource_adapter.adapt_resources()
            if new_allocation != allocation:
                print("- Nuova Allocazione Risorse")
            
            time.sleep(0.1)
        
        # Verifica finale stato sistema
        final_stats = {
            "language": self.language_system.current_language["name"],
            "performance_mode": self.performance_optimizer.current_mode.value,
            "resource_allocation": self.resource_adapter.get_current_allocation(),
            "memory_stats": self.memory_manager.get_memory_stats()
        }
        
        print("\n=== Stato Finale Sistema ===")
        print(f"- Lingua: {final_stats['language']}")
        print(f"- Modalità: {final_stats['performance_mode']}")
        print(f"- Allocazione: {final_stats['resource_allocation'].max_memory_usage}GB")
        print(f"- Items in Memoria: {final_stats['memory_stats']['total_items']}")
        
        # Verifica che il sistema sia in uno stato coerente
        self.assertGreater(final_stats['memory_stats']['total_items'], 0)
        self.assertIsNotNone(final_stats['resource_allocation'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
