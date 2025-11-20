"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the Performance Optimization System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Adaptive performance modes
- Resource usage optimization
- Dynamic performance scaling
- Energy efficiency algorithms
"""

from dataclasses import dataclass
from enum import Enum
import psutil
import time
from typing import Dict, Optional

class PerformanceMode(Enum):
    SPORT = "sport"
    ECO = "eco"

@dataclass
class DeviceSpecs:
    total_ram: float  # GB
    available_ram: float  # GB
    cpu_cores: int
    cpu_frequency: float  # GHz
    battery_level: float  # Percentage
    storage_free: float  # GB

@dataclass
class PerformanceProfile:
    analysis_frequency: int  # milliseconds
    max_concurrent_tasks: int
    memory_buffer: float  # GB
    prediction_depth: int
    battery_optimization: bool

class PerformanceOptimizer:
    def __init__(self):
        self.current_mode = None
        self.device_specs = self._get_device_specs()
        self.performance_profiles = {
            PerformanceMode.SPORT: PerformanceProfile(
                analysis_frequency=100,    # 100ms
                max_concurrent_tasks=5,
                memory_buffer=2.0,         # 2GB
                prediction_depth=5,
                battery_optimization=False
            ),
            PerformanceMode.ECO: PerformanceProfile(
                analysis_frequency=500,    # 500ms
                max_concurrent_tasks=2,
                memory_buffer=0.5,         # 500MB
                prediction_depth=2,
                battery_optimization=True
            )
        }
        self.initialize_mode()

    def _get_device_specs(self) -> DeviceSpecs:
        """Ottiene le specifiche del dispositivo"""
        try:
            return DeviceSpecs(
                total_ram=psutil.virtual_memory().total / (1024**3),  # Convert to GB
                available_ram=psutil.virtual_memory().available / (1024**3),
                cpu_cores=psutil.cpu_count(),
                cpu_frequency=psutil.cpu_freq().current / 1000 if psutil.cpu_freq() else 2.0,
                battery_level=psutil.sensors_battery().percent if psutil.sensors_battery() else 100,
                storage_free=psutil.disk_usage('/').free / (1024**3)
            )
        except:
            # Fallback values for testing
            return DeviceSpecs(
                total_ram=4.0,
                available_ram=2.0,
                cpu_cores=4,
                cpu_frequency=2.0,
                battery_level=80.0,
                storage_free=32.0
            )

    def calculate_device_score(self) -> float:
        """Calcola un punteggio per le prestazioni del dispositivo"""
        specs = self.device_specs
        
        # Normalizza i valori
        ram_score = min(specs.total_ram / 8.0, 1.0) * 0.3  # 8GB è il massimo
        cpu_score = min(specs.cpu_cores / 8.0, 1.0) * 0.3  # 8 core è il massimo
        freq_score = min(specs.cpu_frequency / 3.0, 1.0) * 0.2  # 3GHz è il massimo
        storage_score = min(specs.storage_free / 64.0, 1.0) * 0.2  # 64GB free è il massimo
        
        return ram_score + cpu_score + freq_score + storage_score

    def initialize_mode(self) -> None:
        """Inizializza la modalità di performance basata sulle specifiche del dispositivo"""
        device_score = self.calculate_device_score()
        self.current_mode = (
            PerformanceMode.SPORT if device_score >= 0.7 
            else PerformanceMode.ECO
        )

    def get_current_profile(self) -> PerformanceProfile:
        """Ottiene il profilo di performance corrente"""
        return self.performance_profiles[self.current_mode]

    def should_switch_mode(self) -> Optional[PerformanceMode]:
        """Determina se è necessario cambiare modalità"""
        current_load = psutil.cpu_percent()
        current_ram = psutil.virtual_memory().percent
        
        if self.current_mode == PerformanceMode.SPORT:
            if current_load > 80 or current_ram > 85:
                return PerformanceMode.ECO
        else:
            if current_load < 30 and current_ram < 60:
                return PerformanceMode.SPORT
        
        return None

    def adapt_performance(self) -> Dict:
        """Adatta le performance in base alle condizioni correnti"""
        new_mode = self.should_switch_mode()
        if new_mode and new_mode != self.current_mode:
            self.current_mode = new_mode
            
        profile = self.get_current_profile()
        return {
            "mode": self.current_mode.value,
            "analysis_frequency": profile.analysis_frequency,
            "max_concurrent_tasks": profile.max_concurrent_tasks,
            "memory_buffer": profile.memory_buffer,
            "prediction_depth": profile.prediction_depth,
            "battery_optimization": profile.battery_optimization
        }


"""
Sistema di Auto-ottimizzazione Avanzato
Gestisce l'ottimizzazione automatica delle prestazioni del sistema
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import torch
import torch.nn as nn
from sklearn.metrics import mean_squared_error
from datetime import datetime

@dataclass
class OptimizationMetrics:
    accuracy: float
    response_time: float
    memory_efficiency: float
    learning_rate: float
    timestamp: datetime

class AdvancedOptimizer:
    def __init__(self):
        self.metrics_history: List[OptimizationMetrics] = []
        self.optimization_window = 100
        self.min_learning_rate = 1e-5
        self.max_learning_rate = 1e-2
        
    def optimize_performance(self, model: nn.Module, metrics: OptimizationMetrics) -> Dict[str, float]:
        """Ottimizza le prestazioni del modello"""
        self.metrics_history.append(metrics)
        
        if len(self.metrics_history) < 2:  
            return self._get_current_params()
            
        # Analisi trend
        accuracy_trend = self._analyze_trend([m.accuracy for m in self.metrics_history[-10:]])
        response_trend = self._analyze_trend([m.response_time for m in self.metrics_history[-10:]])
        memory_trend = self._analyze_trend([m.memory_efficiency for m in self.metrics_history[-10:]])
        
        # Ottimizzazione parametri
        new_params = self._optimize_parameters(
            model,
            accuracy_trend,
            response_trend,
            memory_trend
        )
        
        return new_params
        
    def _analyze_trend(self, values: List[float]) -> float:
        """Analizza il trend dei valori"""
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / len(values)  
        
    def _optimize_parameters(self, 
                           model: nn.Module,
                           accuracy_trend: float,
                           response_trend: float,
                           memory_trend: float) -> Dict[str, float]:
        """Ottimizza i parametri del modello"""
        current_params = self._get_current_params()
        
        # Adatta learning rate in modo più aggressivo
        if accuracy_trend < -0.001:  
            current_params['learning_rate'] *= 0.7  
        elif accuracy_trend > 0.001:
            current_params['learning_rate'] *= 1.1
            
        # Limita learning rate
        current_params['learning_rate'] = np.clip(
            current_params['learning_rate'],
            self.min_learning_rate,
            self.max_learning_rate
        )
        
        # Ottimizza batch size
        if response_trend > 0:  # Se il tempo di risposta sta aumentando
            current_params['batch_size'] = max(1, current_params['batch_size'] - 1)
        elif memory_trend < 0:  # Se l'efficienza della memoria sta peggiorando
            current_params['batch_size'] = max(1, current_params['batch_size'] - 1)
        else:
            current_params['batch_size'] += 1
            
        return current_params
        
    def _get_current_params(self) -> Dict[str, float]:
        """Restituisce i parametri correnti"""
        return {
            'learning_rate': 1e-3,
            'batch_size': 32,
            'memory_threshold': 0.8,
            'optimization_frequency': 100
        }
        
    def get_optimization_stats(self) -> Dict[str, float]:
        """Restituisce le statistiche di ottimizzazione"""
        if not self.metrics_history:
            return {}
            
        recent_metrics = self.metrics_history[-self.optimization_window:]
        return {
            'avg_accuracy': np.mean([m.accuracy for m in recent_metrics]),
            'avg_response_time': np.mean([m.response_time for m in recent_metrics]),
            'avg_memory_efficiency': np.mean([m.memory_efficiency for m in recent_metrics]),
            'accuracy_trend': self._analyze_trend([m.accuracy for m in recent_metrics]),
            'response_trend': self._analyze_trend([m.response_time for m in recent_metrics]),
            'memory_trend': self._analyze_trend([m.memory_efficiency for m in recent_metrics])
        }
