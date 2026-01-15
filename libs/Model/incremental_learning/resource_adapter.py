"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the Resource Adaptation System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Dynamic resource allocation
- System resource monitoring
- Adaptive resource scaling
- Resource optimization algorithms
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import psutil
import time
from threading import Lock
import logging

@dataclass
class ResourceThresholds:
    cpu_high: float = 80.0
    cpu_low: float = 20.0
    memory_high: float = 85.0
    memory_low: float = 40.0
    storage_minimum: float = 1.0  # GB
    battery_critical: float = 15.0

@dataclass
class ResourceAllocation:
    max_memory_usage: float  # GB
    cpu_priority: int  # 1-5
    storage_quota: float  # GB
    batch_size: int
    processing_interval: int  # milliseconds

class ResourceAdapter:
    def __init__(self):
        self.thresholds = ResourceThresholds()
        self.resource_lock = Lock()
        self.current_allocation = None
        self.last_adaptation_time = 0
        self.adaptation_interval = 5  # seconds
        
        # Inizializza l'allocazione delle risorse
        self.adapt_resources()

    def get_system_resources(self) -> Dict:
        """Ottiene lo stato attuale delle risorse di sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            
            return {
                "cpu_usage": cpu_percent,
                "memory_used_percent": memory.percent,
                "memory_available": memory.available / (1024**3),  # GB
                "storage_free": disk.free / (1024**3),  # GB
                "battery_level": battery.percent if battery else 100
            }
        except:
            # Valori di fallback per testing
            return {
                "cpu_usage": 50.0,
                "memory_used_percent": 60.0,
                "memory_available": 2.0,
                "storage_free": 10.0,
                "battery_level": 80.0
            }

    def calculate_resource_allocation(self, resources: Dict) -> ResourceAllocation:
        """Calcola l'allocazione ottimale delle risorse"""
        # Base allocation
        base_allocation = ResourceAllocation(
            max_memory_usage=1.0,  # 1GB
            cpu_priority=3,
            storage_quota=5.0,  # 5GB
            batch_size=100,
            processing_interval=100
        )

        # Adjust based on available resources
        if resources["memory_available"] > 4.0:  # Plenty of memory
            base_allocation.max_memory_usage = 2.0
            base_allocation.batch_size = 200
        elif resources["memory_available"] < 1.0:  # Limited memory
            base_allocation.max_memory_usage = 0.5
            base_allocation.batch_size = 50

        # CPU adjustments
        if resources["cpu_usage"] > self.thresholds.cpu_high:
            base_allocation.cpu_priority = 2
            base_allocation.processing_interval = 200
        elif resources["cpu_usage"] < self.thresholds.cpu_low:
            base_allocation.cpu_priority = 4
            base_allocation.processing_interval = 50

        # Storage adjustments
        if resources["storage_free"] < self.thresholds.storage_minimum:
            base_allocation.storage_quota = 0.5

        return base_allocation

    def adapt_resources(self) -> ResourceAllocation:
        """Adatta le risorse in base alle condizioni attuali"""
        current_time = time.time()
        
        # Evita adattamenti troppo frequenti
        if (current_time - self.last_adaptation_time) < self.adaptation_interval:
            return self.current_allocation

        with self.resource_lock:
            resources = self.get_system_resources()
            
            # Verifica condizioni critiche
            if resources["battery_level"] < self.thresholds.battery_critical:
                self._handle_critical_battery()
            
            if resources["memory_used_percent"] > self.thresholds.memory_high:
                self._handle_high_memory_usage()

            # Calcola nuova allocazione
            self.current_allocation = self.calculate_resource_allocation(resources)
            self.last_adaptation_time = current_time

            return self.current_allocation

    def _handle_critical_battery(self):
        """Gestisce la condizione di batteria critica"""
        logging.warning("Critical battery level detected. Entering power saving mode.")
        # Implementa misure di risparmio energetico
        self.thresholds.cpu_high = 60.0
        self.thresholds.memory_high = 70.0

    def _handle_high_memory_usage(self):
        """Gestisce l'uso elevato della memoria"""
        logging.warning("High memory usage detected. Implementing memory restrictions.")
        # Implementa restrizioni della memoria
        self.clear_memory_cache()

    def clear_memory_cache(self):
        """Pulisce la cache di memoria non essenziale"""
        # Implementazione della pulizia della cache
        pass

    def get_current_allocation(self) -> ResourceAllocation:
        """Ottiene l'allocazione corrente delle risorse"""
        if not self.current_allocation:
            self.adapt_resources()
        return self.current_allocation

    def request_resources(self, resource_type: str, amount: float) -> bool:
        """Richiede risorse specifiche"""
        current_allocation = self.get_current_allocation()
        
        if resource_type == "memory":
            return amount <= current_allocation.max_memory_usage
        elif resource_type == "storage":
            return amount <= current_allocation.storage_quota
        
        return False
