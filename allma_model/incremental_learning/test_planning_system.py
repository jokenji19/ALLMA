import unittest
from datetime import datetime, timedelta
from .planning_system import (
    PlanningSystem, Goal, Task, Resource, Risk,
    PriorityLevel, TaskStatus
)

class TestPlanningSystem(unittest.TestCase):
    def setUp(self):
        self.planning_system = PlanningSystem()
        
    def test_add_goal(self):
        """Testa l'aggiunta di obiettivi"""
        # Crea un obiettivo di test
        goal = Goal(
            id="G1",
            name="Completare il progetto",
            description="Completare il progetto entro la deadline",
            priority=PriorityLevel.ALTA,
            deadline=datetime.now() + timedelta(days=30)
        )
        
        # Test aggiunta obiettivo
        self.assertTrue(self.planning_system.add_goal(goal))
        self.assertEqual(len(self.planning_system.goals), 1)
        
        # Test duplicato
        self.assertFalse(self.planning_system.add_goal(goal))
        
    def test_add_task(self):
        """Testa l'aggiunta di task"""
        # Crea un obiettivo
        goal = Goal(
            id="G1",
            name="Completare il progetto",
            description="Completare il progetto entro la deadline",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        # Crea e aggiungi un task
        task = Task(
            id="T1",
            name="Analisi requisiti",
            description="Analizzare i requisiti del progetto",
            priority=PriorityLevel.ALTA
        )
        
        self.assertTrue(self.planning_system.add_task("G1", task))
        self.assertEqual(len(self.planning_system.active_tasks), 1)
        
        # Test aggiunta task a obiettivo inesistente
        task2 = Task(
            id="T2",
            name="Design",
            description="Design del sistema",
            priority=PriorityLevel.ALTA
        )
        self.assertFalse(self.planning_system.add_task("G2", task2))
        
    def test_task_dependencies(self):
        """Testa la gestione delle dipendenze tra task"""
        # Crea un obiettivo
        goal = Goal(
            id="G1",
            name="Progetto Software",
            description="Sviluppo di un software",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        # Crea task con dipendenze
        task1 = Task(
            id="T1",
            name="Analisi",
            description="Analisi requisiti",
            priority=PriorityLevel.ALTA
        )
        
        task2 = Task(
            id="T2",
            name="Design",
            description="Design sistema",
            priority=PriorityLevel.ALTA,
            dependencies=["T1"]
        )
        
        # Aggiungi i task in ordine
        self.assertTrue(self.planning_system.add_task("G1", task1))
        self.assertTrue(self.planning_system.add_task("G1", task2))
        
        # Verifica gestione stato
        self.planning_system.update_task_status("T1", TaskStatus.BLOCCATO)
        self.assertEqual(
            self.planning_system.active_tasks["T2"].status,
            TaskStatus.BLOCCATO
        )
        
    def test_resource_management(self):
        """Testa la gestione delle risorse"""
        # Crea una risorsa
        resource = Resource(
            name="Sviluppatore",
            quantity=10.0,
            available=10.0,
            unit="ore/giorno"
        )
        
        # Aggiungi la risorsa
        self.assertTrue(self.planning_system.add_resource(resource))
        
        # Crea un task
        goal = Goal(
            id="G1",
            name="Progetto",
            description="Progetto test",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        task = Task(
            id="T1",
            name="Sviluppo",
            description="Sviluppo feature",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_task("G1", task)
        
        # Alloca la risorsa
        self.assertTrue(
            self.planning_system.allocate_resource("T1", "Sviluppatore", 5.0)
        )
        
        # Verifica allocazione
        self.assertEqual(
            self.planning_system.available_resources["Sviluppatore"].available,
            5.0
        )
        
    def test_risk_management(self):
        """Testa la gestione dei rischi"""
        # Crea un task
        goal = Goal(
            id="G1",
            name="Progetto",
            description="Progetto test",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        task = Task(
            id="T1",
            name="Deployment",
            description="Deploy in produzione",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_task("G1", task)
        
        # Aggiungi un rischio
        risk = Risk(
            description="Problemi di compatibilità",
            probability=0.3,
            impact=0.8,
            mitigation_plan="Test approfonditi pre-deploy"
        )
        
        self.assertTrue(self.planning_system.add_risk("T1", risk))
        self.assertEqual(len(self.planning_system.active_tasks["T1"].risks), 1)
        
    def test_progress_tracking(self):
        """Testa il monitoraggio del progresso"""
        # Crea un obiettivo con task
        goal = Goal(
            id="G1",
            name="Progetto",
            description="Progetto test",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        task1 = Task(
            id="T1",
            name="Fase 1",
            description="Prima fase",
            priority=PriorityLevel.ALTA
        )
        task2 = Task(
            id="T2",
            name="Fase 2",
            description="Seconda fase",
            priority=PriorityLevel.ALTA
        )
        
        self.planning_system.add_task("G1", task1)
        self.planning_system.add_task("G1", task2)
        
        # Aggiorna i progressi
        self.planning_system.update_task_status("T1", TaskStatus.IN_CORSO, 0.5)
        self.planning_system.update_task_status("T2", TaskStatus.IN_CORSO, 0.7)
        
        # Verifica il progresso dell'obiettivo
        progress = self.planning_system.update_goal_progress("G1")
        self.assertAlmostEqual(progress, 0.6)
        
    def test_critical_path(self):
        """Testa il calcolo del percorso critico"""
        # Crea un obiettivo con task critici e non
        goal = Goal(
            id="G1",
            name="Progetto",
            description="Progetto test",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        task1 = Task(
            id="T1",
            name="Task Critico 1",
            description="Task critico",
            priority=PriorityLevel.CRITICA
        )
        task2 = Task(
            id="T2",
            name="Task Normale",
            description="Task normale",
            priority=PriorityLevel.MEDIA
        )
        task3 = Task(
            id="T3",
            name="Task Critico 2",
            description="Task critico con dipendenze",
            priority=PriorityLevel.CRITICA,
            dependencies=["T1"]
        )
        
        self.planning_system.add_task("G1", task1)
        self.planning_system.add_task("G1", task2)
        self.planning_system.add_task("G1", task3)
        
        # Verifica il percorso critico
        critical_path = self.planning_system.get_critical_path()
        self.assertEqual(len(critical_path), 2)
        self.assertEqual(critical_path[0].id, "T3")  # Task con dipendenza
        
    def test_status_report(self):
        """Testa la generazione del report di stato"""
        # Aggiungi alcuni dati di test
        goal = Goal(
            id="G1",
            name="Progetto",
            description="Progetto test",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_goal(goal)
        
        task = Task(
            id="T1",
            name="Task",
            description="Task test",
            priority=PriorityLevel.ALTA
        )
        self.planning_system.add_task("G1", task)
        
        resource = Resource(
            name="Risorsa",
            quantity=10.0,
            available=5.0,
            unit="unità"
        )
        self.planning_system.add_resource(resource)
        
        # Genera e verifica il report
        report = self.planning_system.generate_status_report()
        self.assertEqual(report["total_goals"], 1)
        self.assertEqual(report["active_tasks"], 1)
        self.assertEqual(report["available_resources"], 1)
        self.assertIn("G1", report["goals_progress"])
        self.assertIn("Risorsa", report["resource_utilization"])

if __name__ == '__main__':
    unittest.main()
