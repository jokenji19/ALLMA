"""Disposable operational challenges running inside the Android Python runtime."""
from pathlib import Path
import json
import importlib
import threading
import uuid


class AndroidReliabilityRun:
    battery_module = 'reliability_battery'
    report_prefix = 'ALLMA_OPERATIONAL'
    folder_prefix = 'operational'
    title = 'Affidabilità software su Android'
    scope = 'Android Python runtime; synthetic data; scripted model/iterator, no real GGUF inference'
    method_note = 'Dati temporanei; modello simulato. Non misura qualità del GGUF, voce o UI nativa.'

    def __init__(self):
        self.cancel_event = threading.Event()
        self.manifest = {}
        self.report_path = None
        self.source = None

    def setup_brain(self, existing_brain):
        self.source = existing_brain
        if (self.source._user_active.is_set() or self.source.dream_manager.is_dreaming
                or self.source._shutdown_event.is_set()):
            raise RuntimeError('Attendi che ALLMA sia libera prima della prova')
        self.output = Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'/(self.folder_prefix+'_'+uuid.uuid4().hex)
        self.output.mkdir(parents=True, exist_ok=True)
        self.report_path = str(self.output/'report.md')

    def run_tests(self, progress_callback=None):
        run_battery = importlib.import_module(self.battery_module).run_battery
        with self.source._lock:
            if self.source._user_active.is_set() or getattr(self.source, '_benchmark_active', False):
                raise RuntimeError('ALLMA è occupata')
            self.source._benchmark_active = True
            self.source._user_active.set()
        try:
            summary = run_battery(self.output, scope=self.scope,
                                  cancel_event=self.cancel_event, progress_callback=progress_callback)
            self.manifest = {'cancelled':not summary['complete'], 'summary':summary}
            report = '# '+self.title+'\n\n'
            report += f"Scenari superati: {summary['passed']}/{summary['total']}.\n\n"
            report += f"Riuscita: {summary['percent']:.1f}%.\n\n" if summary['complete'] else 'Prova interrotta: nessuna percentuale completa.\n\n'
            report += self.method_note + '\n\n'
            for group, result in summary['groups'].items():
                report += f"- {group}: {result['passed']}/{result['total']}\n"
            for failure in summary['failures']:
                report += f"\nFallimento {failure['name']}: {failure['error']['detail']}\n"
            Path(self.report_path).write_text(report)
            print(self.report_prefix+'_REPORT '+str(self.output),flush=True)
            print(self.report_prefix+'_SUMMARY '+json.dumps({'passed':summary['passed'],'total':summary['total'],'percent':summary['percent'],'complete':summary['complete']}),flush=True)
        finally:
            self.source._benchmark_active = False
            self.source._user_active.clear()

    def close(self):
        self.cancel_event.set()


class AndroidMemoryRecoveryRun(AndroidReliabilityRun):
    battery_module = 'memory_recovery_battery'
    report_prefix = 'ALLMA_MEMORY_RECOVERY'
    folder_prefix = 'memory_recovery'
    title = 'Memoria e recupero su Android'


class AndroidIncrementalStorageRun(AndroidReliabilityRun):
    battery_module = 'allma_model.memory_system.storage_diagnostics'
    report_prefix = 'ALLMA_INCREMENTAL_STORAGE'
    folder_prefix = 'incremental_storage'
    title = 'Memoria incrementale su Android'


class AndroidRecallStorageRun(AndroidReliabilityRun):
    battery_module = 'allma_model.learning_system.recall_diagnostics'
    report_prefix = 'ALLMA_RECALL_STORAGE'
    folder_prefix = 'recall_storage'
    title = 'Conservazione delle risposte apprese su Android'


class AndroidToolLearningRun(AndroidReliabilityRun):
    battery_module = 'allma_model.learning_system.tool_learning_diagnostics'
    report_prefix = 'ALLMA_TOOL_LEARNING'
    folder_prefix = 'tool_learning'
    title = 'Apprendimento degli strumenti su Android'


class AndroidRelationalRun(AndroidReliabilityRun):
    battery_module = 'allma_model.emotional_system.relational_diagnostics'
    report_prefix = 'ALLMA_RELATIONAL'
    folder_prefix = 'relational'
    title = 'Sensibilità e contesto su Android'


class AndroidPerceptionRun(AndroidReliabilityRun):
    battery_module = 'allma_model.core.perception_diagnostics'
    report_prefix = 'ALLMA_PERCEPTION'
    folder_prefix = 'perception'
    title = 'Emozioni multilingue e urgenza su Android'
    scope = 'Android Python runtime; 24 predefined synthetic text scenarios; local evidence detector, no model inference'
    method_note = 'Testi sintetici: controlla gli indizi rilevati localmente. Non misura la qualità delle risposte del modello né la comprensione di ogni emozione o lingua.'


class AndroidLongHistoryRun(AndroidReliabilityRun):
    battery_module = 'long_history_battery'
    report_prefix = 'ALLMA_LONG_HISTORY'
    folder_prefix = 'long_history'
    title = 'Storia lunga e continuità su Android'


class AndroidPreservationRun(AndroidReliabilityRun):
    battery_module = 'preservation_battery'
    report_prefix = 'ALLMA_PRESERVATION'
    folder_prefix = 'preservation'
    title = 'Conservazione e backup su Android'


class AndroidIdleWorkRun(AndroidReliabilityRun):
    battery_module = 'allma_model.utils.idle_diagnostics'
    report_prefix = 'ALLMA_IDLE_WORK'
    folder_prefix = 'idle_work'
    title = 'Lavoro a riposo su Android'


class AndroidLearningStorageRun(AndroidReliabilityRun):
    battery_module = 'allma_model.learning_system.learning_diagnostics'
    report_prefix = 'ALLMA_LEARNING_STORAGE'
    folder_prefix = 'learning_storage'
    title = 'Apprendimento incrementale su Android'


class AndroidGoalContinuityRun(AndroidReliabilityRun):
    battery_module = 'allma_model.agency_system.goal_diagnostics'
    report_prefix = 'ALLMA_GOAL_CONTINUITY'
    folder_prefix = 'goal_continuity'
    title = 'Obiettivi e continuità su Android'


class AndroidPlanExperienceRun(AndroidReliabilityRun):
    battery_module = 'allma_model.learning_system.plan_experience_diagnostics'
    report_prefix = 'ALLMA_PLAN_EXPERIENCE'
    folder_prefix = 'plan_experience'
    title = 'Apprendimento dai piani su Android'


class AndroidPlanReviewRun(AndroidReliabilityRun):
    battery_module = 'allma_model.agency_system.plan_review_diagnostics'
    report_prefix = 'ALLMA_PLAN_REVIEW'
    folder_prefix = 'plan_review'
    title = 'Requisiti dei piani e collegamenti appresi'


class AndroidLearningEvolutionRun(AndroidReliabilityRun):
    battery_module = 'allma_model.learning_system.evolution_diagnostics'
    report_prefix = 'ALLMA_LEARNING_EVOLUTION'
    folder_prefix = 'learning_evolution'
    title = 'Apprendimento, trasferimento e curiosità'
