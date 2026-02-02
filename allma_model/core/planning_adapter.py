"""
PlanningSystemAdapter - Lightweight adapter for ModuleOrchestrator

PHASE 24: Tier 2 Module Integration  
Adapts existing PlanningSystem to work with orchestrator.
Adds `process()` method for compatibility.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class TaskSuggestion:
    """Suggested task based on user input."""
    name: str
    description: str
    estimated_time: str
    priority: str = "medium"


@dataclass
class PlanSuggestion:
    """Plan suggestion for user goal."""
    goal: str
    tasks: List[TaskSuggestion]
    timeline: str
    has_plan: bool = True


class PlanningSystemAdapter:
    """
    Lightweight planning system that suggests task breakdowns.
    
    Cost: ~50ms
    Priority: MEDIUM (6/10)
    """
    
    def __init__(self):
        # Planning intent keywords
        self.planning_keywords = [
            'piano', 'pianifica', 'organizza', 'programma',
            'task', 'compito', 'obiettivo', 'progetto',
            'strategia', 'roadmap', 'passi', 'fasi'
        ]
        
        # Time-related keywords
        self.time_keywords = {
            'oggi': 'today',
            'domani': 'tomorrow',
            'settimana': 'week',
            'mese': 'month',
            'anno': 'year'
        }
    
    def process(self, user_input: str, context: Dict) -> Dict:
        """
        Main entry point for ModuleOrchestrator.
        
        Args:
            user_input: User's message
            context: Conversation context
            
        Returns:
            Dict with plan suggestions or empty dict
        """
        if not self._is_planning_query(user_input):
            return {}
        
        # Extract goal
        goal = self._extract_goal(user_input)
        
        # Generate task suggestions
        tasks = self._suggest_tasks(goal, user_input)
        
        # Estimate timeline
        timeline = self._estimate_timeline(tasks, user_input)
        
        plan = PlanSuggestion(
            goal=goal,
            tasks=tasks,
            timeline=timeline
        )
        
        return {
            'has_plan': True,
            'goal': plan.goal,
            'tasks': [{'name': t.name, 'time': t.estimated_time, 'priority': t.priority} 
                     for t in plan.tasks],
            'timeline': plan.timeline
        }
    
    def _is_planning_query(self, text: str) -> bool:
        """Detects if user is requesting planning help."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.planning_keywords)
    
    def _extract_goal(self, text: str) -> str:
        """
        Extracts the goal from user input.
        
        Examples:
            "Aiutami a pianificare il progetto X" → "progetto X"
            "Organizza la mia giornata" → "organizzare giornata"
        """
        # Remove planning keywords
        cleaned = text.lower()
        for kw in self.planning_keywords:
            cleaned = cleaned.replace(kw, '')
        
        # Remove common words
        stop_words = ['il', 'la', 'un', 'una', 'aiutami', 'a', 'per', 'mio', 'mia']
        words = cleaned.split()
        filtered = [w for w in words if w not in stop_words and len(w) > 2]
        
        goal = ' '.join(filtered[:5])  # Max 5 words
        return goal if goal else "attività"
    
    def _suggest_tasks(self, goal: str, original_text: str) -> List[TaskSuggestion]:
        """
        Generates task suggestions based on goal.
        
        This is a simplified version - production would use ML/LLM.
        """
        tasks = []
        
        # Generic task breakdown (3-5 tasks)
        if 'progetto' in original_text.lower():
            tasks = [
                TaskSuggestion(
                    name=f"Definire obiettivi {goal}",
                    description="Chiarire scope e requisiti",
                    estimated_time="30min",
                    priority="high"
                ),
                TaskSuggestion(
                    name=f"Pianificare milestone {goal}",
                    description="Definire fasi principali",
                    estimated_time="1h",
                    priority="high"
                ),
                TaskSuggestion(
                    name=f"Allocare risorse per {goal}",
                    description="Identificare persone/tools needed",
                    estimated_time="45min",
                    priority="medium"
                ),
                TaskSuggestion(
                    name=f"Eseguire {goal}",
                    description="Implementazione fase per fase",
                    estimated_time="varies",
                    priority="medium"
                ),
                TaskSuggestion(
                    name=f"Rivedere e ottimizzare {goal}",
                    description="Retrospettiva e miglioramenti",
                    estimated_time="30min",
                    priority="low"
                )
            ]
        elif 'giornata' in original_text.lower() or 'oggi' in original_text.lower():
            tasks = [
                TaskSuggestion(
                    name="Priorità mattutine",
                    description="Task più importanti al mattino",
                    estimated_time="2-3h",
                    priority="high"
                ),
                TaskSuggestion(
                    name="Break e ricarica",
                    description="Pause strategiche",
                    estimated_time="30min",
                    priority="medium"
                ),
                TaskSuggestion(
                    name="Task di routine",
                    description="Email, admin, etc.",
                    estimated_time="1-2h",
                    priority="medium"
                ),
                TaskSuggestion(
                    name="Review giornata",
                    description="Pianifica domani",
                    estimated_time="15min",
                    priority="low"
                )
            ]
        else:
            # Generic breakdown
            tasks = [
                TaskSuggestion(
                    name=f"Preparazione {goal}",
                    description="Setup iniziale",
                    estimated_time="30min",
                    priority="high"
                ),
                TaskSuggestion(
                    name=f"Esecuzione {goal}",
                    description="Lavoro principale",
                    estimated_time="2h",
                    priority="high"
                ),
                TaskSuggestion(
                    name=f"Finalizzazione {goal}",
                    description="Review e completamento",
                    estimated_time="30min",
                    priority="medium"
                )
            ]
        
        return tasks
    
    def _estimate_timeline(self, tasks: List[TaskSuggestion], original_text: str) -> str:
        """Estimates overall timeline."""
        
        # Check for time context in original text
        text_lower = original_text.lower()
        
        if any(kw in text_lower for kw in ['oggi', 'giornata']):
            return "1 giornata"
        elif 'settimana' in text_lower:
            return "1 settimana"
        elif 'mese' in text_lower:
            return "1 mese"
        
        # Calculate from tasks
        total_minutes = 0
        for task in tasks:
            time_str = task.estimated_time
            if 'h' in time_str:
                hours = int(re.findall(r'\d+', time_str)[0])
                total_minutes += hours * 60
            elif 'min' in time_str:
                mins = int(re.findall(r'\d+', time_str)[0])
                total_minutes += mins
        
        if total_minutes < 120:
            return f"{total_minutes} minuti"
        elif total_minutes < 480:
            hours = total_minutes / 60
            return f"{hours:.1f} ore"
        else:
            days = total_minutes / (60 * 8)  # 8h workday
            return f"{days:.1f} giorni"
