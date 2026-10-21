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
            summary = run_battery(self.output, scope='Android Python runtime; synthetic data; scripted model/iterator, no real GGUF inference',
                                  cancel_event=self.cancel_event, progress_callback=progress_callback)
            self.manifest = {'cancelled':not summary['complete'], 'summary':summary}
            report = '# '+self.title+'\n\n'
            report += f"Scenari superati: {summary['passed']}/{summary['total']}.\n\n"
            report += f"Riuscita: {summary['percent']:.1f}%.\n\n" if summary['complete'] else 'Prova interrotta: nessuna percentuale completa.\n\n'
            report += 'Dati temporanei; modello simulato. Non misura qualità del GGUF, voce o UI nativa.\n\n'
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
