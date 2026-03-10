from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
import math

class PriorityLevel(Enum):
    BASSA = 1
    MEDIA = 2
    ALTA = 3
    CRITICA = 4

class TaskStatus(Enum):
    NON_INIZIATO = "non_iniziato"
    IN_CORSO = "in_corso"
    COMPLETATO = "completato"
    BLOCCATO = "bloccato"
    CANCELLATO = "cancellato"

@dataclass
class Resource:
    """Rappresenta una risorsa necessaria per un task"""
    name: str
    quantity: float
    available: float
    unit: str = "unità"
    
@dataclass
class Risk:
    """Rappresenta un rischio associato a un task o obiettivo"""
    description: str
    probability: float  # 0-1
    impact: float      # 0-1
    mitigation_plan: str
    
@dataclass
class Task:
    """Rappresenta un singolo task nel piano"""
    id: str
    name: str
    description: str
    priority: PriorityLevel
    status: TaskStatus = TaskStatus.NON_INIZIATO
    progress: float = 0.0  # 0-1
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)  # Lista di ID dei task da cui dipende
    resources: List[Resource] = field(default_factory=list)
    risks: List[Risk] = field(default_factory=list)
    sub_tasks: List['Task'] = field(default_factory=list)
    
@dataclass
class Goal:
    """Rappresenta un obiettivo"""
    id: str
    name: str
    description: str
    priority: PriorityLevel
    deadline: Optional[datetime] = None
    tasks: List[Task] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    progress: float = 0.0  # 0-1

class PlanningSystem:
    """Sistema di pianificazione per la gestione di obiettivi e task"""
    
    def __init__(self):
        self.goals: Dict[str, Goal] = {}
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.available_resources: Dict[str, Resource] = {}
        
    def add_goal(self, goal: Goal) -> bool:
        """Aggiunge un nuovo obiettivo"""
        if goal.id in self.goals:
            return False
        self.goals[goal.id] = goal
        # Aggiunge i task dell'obiettivo ai task attivi
        for task in goal.tasks:
            self.active_tasks[task.id] = task
        return True
        
    def update_goal_progress(self, goal_id: str) -> float:
        """Aggiorna e restituisce il progresso di un obiettivo"""
        if goal_id not in self.goals:
            return 0.0
            
        goal = self.goals[goal_id]
        if not goal.tasks:
            return goal.progress
            
        # Calcola il progresso medio dei task
        total_progress = sum(task.progress for task in goal.tasks)
        goal.progress = total_progress / len(goal.tasks)
        return goal.progress
        
    def add_task(self, goal_id: str, task: Task) -> bool:
        """Aggiunge un nuovo task a un obiettivo"""
        if goal_id not in self.goals:
            return False
            
        # Verifica le dipendenze
        for dep_id in task.dependencies:
            if dep_id not in self.active_tasks and dep_id not in self.completed_tasks:
                return False
                
        self.goals[goal_id].tasks.append(task)
        self.active_tasks[task.id] = task
        return True
        
    def update_task_status(self, task_id: str, status: TaskStatus, progress: float = None) -> bool:
        """Aggiorna lo stato di un task"""
        if task_id not in self.active_tasks:
            return False
            
        task = self.active_tasks[task_id]
        old_status = task.status
        task.status = status
        
        if progress is not None:
            task.progress = max(0.0, min(1.0, progress))
            
        # Gestione completamento
        if status == TaskStatus.COMPLETATO:
            task.progress = 1.0
            task.end_date = datetime.now()
            self.completed_tasks[task_id] = task
            del self.active_tasks[task_id]
            
        # Aggiorna i task dipendenti
        self._update_dependent_tasks(task_id, old_status, status)
        return True
        
    def _update_dependent_tasks(self, task_id: str, old_status: TaskStatus, new_status: TaskStatus):
        """Aggiorna lo stato dei task dipendenti"""
        for task in self.active_tasks.values():
            if task_id in task.dependencies:
                if new_status == TaskStatus.BLOCCATO:
                    task.status = TaskStatus.BLOCCATO
                elif old_status == TaskStatus.BLOCCATO and new_status == TaskStatus.IN_CORSO:
                    task.status = TaskStatus.NON_INIZIATO
                    
    def add_resource(self, resource: Resource) -> bool:
        """Aggiunge una nuova risorsa al sistema"""
        if resource.name in self.available_resources:
            return False
        self.available_resources[resource.name] = resource
        return True
        
    def allocate_resource(self, task_id: str, resource_name: str, quantity: float) -> bool:
        """Alloca una risorsa a un task"""
        if task_id not in self.active_tasks or resource_name not in self.available_resources:
            return False
            
        resource = self.available_resources[resource_name]
        if resource.available < quantity:
            return False
            
        # Aggiorna la disponibilità della risorsa
        resource.available -= quantity
        
        # Aggiunge la risorsa al task
        task_resource = Resource(
            name=resource.name,
            quantity=quantity,
            available=quantity,
            unit=resource.unit
        )
        self.active_tasks[task_id].resources.append(task_resource)
        return True
        
    def add_risk(self, task_id: str, risk: Risk) -> bool:
        """Aggiunge un rischio a un task"""
        if task_id not in self.active_tasks:
            return False
            
        self.active_tasks[task_id].risks.append(risk)
        return True
        
    def get_critical_path(self) -> List[Task]:
        """Calcola e restituisce il percorso critico dei task"""
        # Implementazione semplificata del percorso critico
        critical_tasks = []
        for task in self.active_tasks.values():
            if (task.priority == PriorityLevel.ALTA or 
                task.priority == PriorityLevel.CRITICA):
                critical_tasks.append(task)
        return sorted(critical_tasks, key=lambda x: len(x.dependencies), reverse=True)
        
    def optimize_resource_allocation(self) -> bool:
        """Ottimizza l'allocazione delle risorse tra i task"""
        critical_path = self.get_critical_path()
        
        # Riallocazione delle risorse ai task critici
        for task in critical_path:
            for resource in task.resources:
                # Cerca risorse aggiuntive da task non critici
                for other_task in self.active_tasks.values():
                    if other_task not in critical_path:
                        for other_resource in other_task.resources:
                            if other_resource.name == resource.name:
                                # Trasferisce il 50% della risorsa al task critico
                                transfer = other_resource.available * 0.5
                                other_resource.available -= transfer
                                resource.available += transfer
        return True
        
    def generate_status_report(self) -> Dict:
        """Genera un report sullo stato del sistema di pianificazione"""
        return {
            "total_goals": len(self.goals),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "available_resources": len(self.available_resources),
            "goals_progress": {
                goal_id: goal.progress 
                for goal_id, goal in self.goals.items()
            },
            "critical_path_length": len(self.get_critical_path()),
            "resource_utilization": {
                res.name: 1 - (res.available / res.quantity)
                for res in self.available_resources.values()
            }
        }
