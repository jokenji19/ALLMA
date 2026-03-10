import unittest
from resource_adapter import ResourceAdapter, ResourceAllocation, ResourceThresholds
import psutil
import time

class TestResourceAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = ResourceAdapter()

    def test_initialization(self):
        """Test dell'inizializzazione del sistema"""
        self.assertIsNotNone(self.adapter.thresholds)
        self.assertIsNotNone(self.adapter.resource_lock)
        self.assertIsNotNone(self.adapter.get_current_allocation())

    def test_resource_monitoring(self):
        """Test del monitoraggio delle risorse"""
        resources = self.adapter.get_system_resources()
        
        required_metrics = [
            "cpu_usage", "memory_used_percent", "memory_available",
            "storage_free", "battery_level"
        ]
        
        for metric in required_metrics:
            self.assertIn(metric, resources)
            self.assertIsInstance(resources[metric], (int, float))

    def test_resource_allocation(self):
        """Test dell'allocazione delle risorse"""
        resources = {
            "cpu_usage": 50.0,
            "memory_used_percent": 60.0,
            "memory_available": 4.0,
            "storage_free": 10.0,
            "battery_level": 80.0
        }
        
        allocation = self.adapter.calculate_resource_allocation(resources)
        
        self.assertIsInstance(allocation, ResourceAllocation)
        self.assertGreater(allocation.max_memory_usage, 0)
        self.assertGreater(allocation.storage_quota, 0)
        self.assertGreater(allocation.batch_size, 0)

    def test_resource_adaptation(self):
        """Test dell'adattamento delle risorse"""
        # Test adattamento normale
        allocation1 = self.adapter.adapt_resources()
        self.assertIsInstance(allocation1, ResourceAllocation)
        
        # Test throttling (non dovrebbe adattarsi troppo frequentemente)
        allocation2 = self.adapter.adapt_resources()
        self.assertEqual(allocation1, allocation2)  # Dovrebbe essere la stessa allocazione

    def test_resource_requests(self):
        """Test delle richieste di risorse"""
        # Test richiesta di memoria valida
        self.assertTrue(
            self.adapter.request_resources("memory", 0.5)  # Richiesta piccola
        )
        
        # Test richiesta di memoria eccessiva
        self.assertFalse(
            self.adapter.request_resources("memory", 1000.0)  # Richiesta enorme
        )
        
        # Test richiesta di storage valida
        self.assertTrue(
            self.adapter.request_resources("storage", 1.0)  # Richiesta ragionevole
        )

    def test_critical_conditions(self):
        """Test delle condizioni critiche"""
        # Simula batteria scarica
        original_get_resources = self.adapter.get_system_resources
        
        def mock_low_battery():
            resources = original_get_resources()
            resources["battery_level"] = 10.0
            return resources
        
        self.adapter.get_system_resources = mock_low_battery
        
        # Verifica che l'adattamento gestisca la batteria scarica
        allocation = self.adapter.adapt_resources()
        self.assertIsNotNone(allocation)

if __name__ == '__main__':
    unittest.main()
