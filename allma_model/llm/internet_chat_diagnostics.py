"""Actual chat pipeline with public sources and disposable conversational memory."""
from pathlib import Path
import json
import threading
import time
import uuid

from allma_model.utils.generation_control import check_cancelled, GenerationCancelled
from allma_model.utils.persistence import atomic_write_json
from allma_model.core.learning_insights import response_origin


class InternetChatRun:
    def __init__(self):
        from benchmark_iq import CognitiveBenchmark
        self.model=CognitiveBenchmark(profile='quick')
        self.cancel_event=self.model.cancel_event
        self.manifest={}

    def setup_brain(self, existing_brain):
        self.source=existing_brain
        self.model.setup_brain(existing_brain)
        self.report_path=str(Path(existing_brain.db_path).resolve().parent/'benchmarks/reports'/
            ('internet_chat_'+uuid.uuid4().hex+'.json'))

    def run_tests(self, progress_callback=None):
        source,core=self.source,self.model.brain
        with source._lock:
            if source._user_active.is_set() or getattr(source,'_benchmark_active',False) or not source._foreground:
                raise RuntimeError('Lascia ALLMA visibile e libera')
            source._benchmark_active=True;source._user_active.set()
        before=source.public_references.status()['enabled']
        rows=[];started=time.monotonic();reason='running'
        user='BENCHMARK_INTERNET_'+uuid.uuid4().hex
        original_reader=core.public_references.reader
        cases=(('research_followup','Cerca su internet','reference_excerpt'),
            ('new_contribution','Dimmi anche altro su di lui, senza ripetere i punti già detti.','reference_excerpt'),
            ('new_topic','Come funziona una bussola?','reference_excerpt'),
            ('local_calculation','Quanto fa 18 + 24? Rispondi solo con un numero','verified_calculation'),
            ('local_identity','Come ti chiami?','origin_identity'),
            ('source_unavailable','Cerca online una galassia','reference_unavailable'),
            ('nasa_evidence','Quali prove abbiamo di un oceano sulla luna Europa?','reference_excerpt'),
            ('nasa_comparison','Qual è la differenza tra i ghiacciai terrestri e il ghiaccio di Europa?','reference_excerpt'),
            ('nasa_unsupported','Quali misure sismiche indicano un oceano sulla luna Europa?','reference_unavailable'),
            ('nasa_new_subject','Puoi controllare online: quali prove ci sono di un oceano su Encelado?','reference_excerpt'),
            ('agency_comparison','Confronta NASA ed ESA: esiste un oceano sotto il ghiaccio di Europa?','reference_comparison'),
            ('comparison_clarification','Cosa intendi dire?','reference_comparison'),
            ('general_geography','Dove si trova il lago di Garda?','reference_excerpt'),
            ('causal_explanation','Perché il cielo è blu?','reference_excerpt'),
            ('detailed_answer','Spiegami in dettaglio la fotosintesi clorofilliana','reference_excerpt'),
            ('science_editions','Confronta due fonti sulla fotosintesi','reference_comparison'),
            ('history_editions','Confronta due fonti sul Medioevo','reference_comparison'),
            ('freshness_limit','Cerca online gli ultimi aggiornamenti sul mercato immobiliare','reference_unavailable'),
            ('enceladus_agencies','Confronta NASA ed ESA: c’è un oceano globale sotto il ghiaccio di Encelado?','reference_comparison'),
            ('sea_level_agencies','Confronta NASA e NOAA: perché aumenta il livello globale del mare?','reference_comparison'),
            ('history_opening','Chi era Hitler?','reference_excerpt'),
            ('history_expansion','Dimmi di più','reference_excerpt'),
            ('history_target','Contro chi ha fatto scoppiare la seconda guerra mondiale?','reference_excerpt'),
            ('history_target_offline','Contro chi ha fatto scoppiare la seconda guerra mondiale?','reference_excerpt'),
            ('weather_disabled','Che tempo fa a Torino?','reference_unavailable'),
            ('online_capability','Sai fare ricerca su Internet?','runtime_web_access'),
            ('weather_current','Che tempo fa a Torino?','weather_data'),
            ('weather_temperature','Bene, quanti gradi fanno a Torino?','weather_data'),
            ('weather_city_milan','Invece a Milano?','weather_data'),
            ('weather_city_tirana','Invece a Tirana?','weather_data'),
            ('weather_city_palermo','Invece a Palermo?','weather_data'),
            ('weather_city_turin','Invece a Torino?','weather_data'),
            ('weather_followup','E domani?','weather_data'),
            ('achilles','Chi era Achille?','reference_excerpt'),
            ('hector','Chi era Ettore?','reference_excerpt'),
            ('hector_correction','Intendo ettore nell"iliade','reference_excerpt'),
            ('mussolini','Chi era Mussolini?','reference_excerpt'),
            ('tripartite','Con chi si era alleato durante la seconda guerra mondiale?','reference_excerpt'),
            ('web_search','Cerca sul web fotosintesi clorofilliana','web_search'),
            ('web_privacy','Cerca sul web il mio referto medico','reference_unavailable'),
            ('android_security','Quali sono gli ultimi aggiornamenti su Android?','web_search'),
            ('storage_comparison','Cerca sul web la differenza tra RAM e memoria di archiviazione.','web_search'),
            ('italian_politics','Quali sono le ultime notizie sulla politica italiana?','web_search'),
            ('energy_comparison','Cerca sul web la differenza tra fotovoltaico ed eolico.','web_search'),
            ('consumer_prices','Quali sono gli ultimi dati sull’inflazione italiana?','web_search'))
        try:
            core.public_references.configure(True)
            cid=core.start_conversation(user)
            from allma_model.core.autobiographical_identity import POLICY_VERSION
            core.conversational_memory.store_message(cid,'Chi era mussolini?',{'identity_policy':POLICY_VERSION},'user',user)
            core.conversational_memory.store_message(cid,'Non sono Mussolini.',
                {'source':'model_generated','identity_policy':POLICY_VERSION,'is_valid':True},'assistant',user)
            for index,(kind,question,expected) in enumerate(cases):
                check_cancelled(self.cancel_event)
                if not source._foreground:raise GenerationCancelled()
                if progress_callback:progress_callback(index,len(cases),kind)
                if kind=='history_opening':
                    cid = core.start_conversation(user)
                if kind=='history_target_offline':
                    core.public_references.configure(False)
                if kind=='online_capability':
                    core.public_references.configure(True)
                if kind=='source_unavailable':
                    class EmptyReader:
                        def fetch(self,*args):return []
                    core.public_references.reader=EmptyReader()
                else:
                    core.public_references.reader=original_reader
                events=[];tick=time.monotonic()
                reply=core.process_message(user,cid,question,context={'disable_answer_recall':True,'benchmark_seed':42},
                    cancel_event=self.cancel_event,stream_callback=events.append)
                source_kind=reply.metadata.get('source')
                activity=[event['content'] for event in events if event['type']=='reference']
                origin=response_origin(reply.metadata,reply.is_valid)
                passed=source_kind==expected and (bool(reply.content) and reply.is_valid if expected!='reference_unavailable'
                    else not reply.content and not reply.is_valid)
                if kind=='local_calculation':passed=passed and reply.content=='42' and not activity
                if kind=='new_contribution':passed=passed and reply.content!=rows[0]['answer'] and all(e['state']!='searching' for e in activity)
                if kind in ('nasa_evidence','nasa_new_subject'):
                    title='Europa' if kind=='nasa_evidence' else 'Enceladus'
                    passed=passed and origin.get('citation',{}).get('title')==title and origin.get('via')=='internet'
                if kind=='nasa_comparison':
                    passed=passed and origin.get('coverage')=='one_subject' and origin.get('via')=='cache'
                if kind=='nasa_unsupported':
                    passed=passed and reply.metadata.get('reference_review',{}).get('retrieval_status')=='insufficient_evidence'
                if kind=='agency_comparison':
                    passed=passed and origin.get('outcome')=='agreement' and {
                        row.get('provider'):row.get('via') for row in origin.get('sources',())
                        if row.get('excerpt')}=={'nasa':'cached','esa':'obtained'}
                if kind=='comparison_clarification':
                    passed = (passed and 'misurazioni indirette' in reply.content and not activity
                              and reply.metadata['reference_review']['retrieval_status'] == 'history')
                if kind in ('enceladus_agencies', 'sea_level_agencies'):
                    scope, partner, nasa_via = ('enceladus_global_ocean','esa','cached') if kind=='enceladus_agencies' else (
                        'global_sea_level_causes','noaa','obtained')
                    audit=reply.metadata.get('reference_review',{})
                    passed=passed and audit.get('scope')==scope and origin.get('outcome')=='agreement' and {
                        row.get('provider'):row.get('via') for row in origin.get('sources',())
                        if row.get('excerpt')}=={'nasa':nasa_via,partner:'obtained'}
                if kind in ('science_editions','history_editions'):
                    passed=passed and origin.get('outcome')=='parallel_reading' and len(origin.get('sources',[]))==2
                if kind=='detailed_answer':
                    passed=passed and len(reply.metadata.get('reference_review',{}).get('spans',[]))>=3
                if kind=='causal_explanation':
                    passed=passed and origin.get('citation',{}).get('title')=='Cielo' and 'diffond' in reply.content.casefold()
                if kind=='freshness_limit':
                    audit=reply.metadata.get('reference_review',{})
                    passed=passed and audit.get('retrieval_status')=='freshness_unsupported' and audit.get('network_used') is False
                if kind in ('history_target','history_target_offline'):
                    audit=reply.metadata.get('reference_review',{})
                    passed=(passed and 'Polonia' in reply.content and '1939' in reply.content
                            and audit.get('retrieval_status')=='history' and origin.get('via')=='history'
                            and audit.get('truth_verified') is False and not audit.get('network_used')
                            and all(event['state']!='searching' for event in activity))
                if kind in ('weather_disabled','web_privacy'):
                    passed = passed and not any(event['state']=='searching' for event in activity)
                if kind=='online_capability':
                    passed = passed and 'abilitate' in reply.content and not activity
                if kind in ('weather_current','weather_followup'):
                    passed = (passed and origin.get('kind')=='weather' and 'Torino' in reply.content
                              and any(event['state']=='searching' for event in activity))
                if kind.startswith('weather_city_') or kind == 'weather_temperature':
                    city = {'weather_city_milan':'Milano', 'weather_city_tirana':'Tirana',
                            'weather_city_palermo':'Palermo'}.get(kind, 'Torino')
                    passed = (passed and city in reply.content and city in origin.get('citation', {}).get('title', '')
                              and any(event['state']=='searching' for event in activity))
                if kind in ('achilles', 'hector', 'hector_correction', 'mussolini', 'tripartite'):
                    title = {'achilles':'Achille', 'hector':'Ettore (mitologia)', 'hector_correction':'Ettore (mitologia)',
                             'mussolini':'Benito Mussolini', 'tripartite':'Patto tripartito'}[kind]
                    passed = passed and origin.get('citation', {}).get('title') == title
                    if kind == 'achilles':
                        passed = passed and 'Iliade' in reply.content and 'foresta di giorno' not in reply.content
                    if kind == 'tripartite':
                        passed = passed and all(term in reply.content.casefold() for term in ('germania','italia','giappon'))
                if kind=='web_search':
                    passed = (passed and bool(origin.get('sources')) and 'fotosintesi' in reply.content.casefold()
                              and any(event['state']=='searching' for event in activity))
                if kind=='android_security':
                    passed = (passed and 'livelli patch' in reply.content
                              and [row['publisher'] for row in origin.get('sources', [])] == ['AOSP'])
                if kind=='storage_comparison':
                    sources = origin.get('sources', [])
                    passed = (passed and 'dopo lo spegnimento' in reply.content
                              and [row.get('subject') for row in sources] == ['RAM', 'memoria di archiviazione'])
                if kind=='italian_politics':
                    passed = (passed and 'Comunicati ufficiali del Governo italiano' in reply.content
                              and {row['publisher'] for row in origin.get('sources', [])} == {'Palazzo Chigi'})
                if kind=='energy_comparison':
                    passed = (passed and [row.get('subject') for row in origin.get('sources', [])]
                              == ['fotovoltaico', 'eolico'])
                if kind=='consumer_prices':
                    passed = (passed and 'prezzi al consumo' in reply.content.casefold()
                              and [row['publisher'] for row in origin.get('sources', [])] == ['Istat'])
                rows.append({'case':kind,'question':question,'answer':reply.content,'source':source_kind,
                    'valid':reply.is_valid,'passed':bool(passed),'origin':origin,
                    'activity':activity,'seconds':time.monotonic()-tick})
            reason='completed'
        except GenerationCancelled:reason='cancelled'
        except Exception:
            reason='error'
            raise
        finally:
            core.public_references.reader=original_reader
            source._benchmark_active=False;source._user_active.clear()
            summary={'results':rows,'passed':sum(row['passed'] for row in rows),'completed':len(rows),
                'stop_reason':reason,'seconds':time.monotonic()-started,'personal_data_used':False,
                'source_preference_before':before,'source_preference_after':source.public_references.status()['enabled']}
            self.results=summary;self.manifest={'stop_reason':reason,'cancelled':reason!='completed'}
            atomic_write_json(self.report_path,summary)
            print('ALLMA_INTERNET_CHAT_REPORT '+self.report_path,flush=True)
            print('ALLMA_INTERNET_CHAT_SUMMARY '+json.dumps({'passed':summary['passed'],'completed':len(rows),'stop_reason':reason}),flush=True)

    def close(self):
        self.cancel_event.set();self.model.close()
