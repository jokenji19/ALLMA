"""One public HTTP request in a disposable archive; never changes app consent."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import threading
import time
import uuid

from allma_model.utils.public_references import PublicReferences
from allma_model.utils.contribution_review import select_contribution
from allma_model.utils.generation_control import check_cancelled, GenerationCancelled
from allma_model.utils.persistence import atomic_write_json


class PublicReferenceRun:
    def __init__(self):
        self.cancel_event=threading.Event()
        self.manifest={}

    def close(self):
        # No model or persistent user archive is owned by this diagnostic.
        pass

    def setup_brain(self, existing_brain):
        self.source=existing_brain
        self.report_path=str(Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'/
            ('public_references_'+uuid.uuid4().hex+'.md'))

    def run_tests(self, progress_callback=None):
        source=self.source
        with source._lock:
            if source._user_active.is_set() or getattr(source,'_benchmark_active',False) or not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile e libera')
            source._benchmark_active=True
            source._user_active.set()
        before=source.public_references.status()['enabled']
        result={'personal_data_used':False,'model_used':False,'public_topic':'bussola',
            'source_preference_before':before,'results':[],'stop_reason':'running'}
        started=time.monotonic()
        def record(name,passed,**extra):
            check_cancelled(self.cancel_event)
            result['results'].append({'case':name,'passed':bool(passed),**extra})
            if progress_callback:progress_callback(len(result['results']),6,name)
        try:
            parent=Path(self.report_path).parent
            parent.mkdir(parents=True,exist_ok=True)
            with TemporaryDirectory(prefix='public-reference-test-',dir=parent) as directory:
                root=Path(directory)
                service=PublicReferences(root/'test.db',root/'web_access.json')
                offline=service.lookup('Come funziona una bussola?',cancel_event=self.cancel_event)
                record('Locale senza consenso',offline['status']=='local_only' and not offline['network_used'])
                service.configure(True)
                obtained=service.lookup('Come funziona una bussola?',cancel_event=self.cancel_event)
                record('Fonte reale consultata',obtained['status']=='obtained' and bool(obtained['references']),status=obtained['status'])
                contribution=select_contribution(obtained['references'])
                record('Estratto con provenienza',contribution is not None,
                    citation=contribution.reference.citation() if contribution else None)
                service.configure(False)
                cached=service.lookup('Come funziona una bussola?',cancel_event=self.cancel_event)
                record('Riutilizzo locale dopo disattivazione',cached['status']=='cached' and not cached['network_used'])
                personal=service.lookup('Come funziona il mio telefono?',cancel_event=self.cancel_event)
                record('Domanda personale esclusa',personal['status']=='not_applicable' and not personal['network_used'])
                after=source.public_references.status()['enabled']
                result['source_preference_after']=after
                record('Consenso dell’app conservato',before==after)
            result['stop_reason']='completed'
        except GenerationCancelled:
            result['stop_reason']='cancelled'
        except Exception as error:
            result['stop_reason']='unavailable'
            result['error']=type(error).__name__
        finally:
            with source._lock:
                source._benchmark_active=False
                source._user_active.clear()
            result['seconds']=time.monotonic()-started
            result['passed']=sum(row['passed'] for row in result['results'])
            self.manifest={'stop_reason':result['stop_reason'],'cancelled':result['stop_reason']=='cancelled'}
            atomic_write_json(Path(self.report_path).with_suffix('.json'),result)
            self.results=result
        report='# Internet e fonti · prova isolata\n\nUna consultazione pubblica di Wikipedia, senza conversazioni personali né modello.\n\n'
        report+='\n'.join('- '+row['case']+': '+('OK' if row['passed'] else 'NON RIUSCITO') for row in result['results'])
        report+='\n\nEsito: '+result['stop_reason']+'. Una fonte documentata non è una garanzia di verità universale.\n'
        Path(self.report_path).write_text(report)
        print('ALLMA_PUBLIC_REFERENCES_SUMMARY '+json.dumps(result,ensure_ascii=False),flush=True)
        return report
