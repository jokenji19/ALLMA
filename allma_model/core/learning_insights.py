"""Read-only explanations from canonical, user-scoped learning records.

These are documented observations and user feedback, not an intelligence score
or an assertion that the model's weights were trained.
"""
from collections import deque
import json


def response_origin(metadata, valid=True):
    meta = metadata if isinstance(metadata, dict) else {}
    source = meta.get('source')
    if not valid or meta.get('is_valid') is False:
        if source=='reference_unavailable':
            state=(meta.get('reference_review') or {}).get('retrieval_status')
            detail={'local_only':'Le ricerche sono disattivate per questa richiesta.',
                'not_applicable':'Non ho identificato un argomento pubblico da cercare.',
                'not_found':'La fonte non ha restituito un estratto pertinente.',
                'consent_revoked':'Il consenso è stato revocato durante la ricerca.'}.get(state,
                    'La consultazione non ha prodotto una fonte utilizzabile.')
            return {'kind':'incomplete','label':'Ricerca senza riscontro','detail':detail+' Non è stata sostituita con fatti generati dal modello.'}
        generation=meta.get('generation') if isinstance(meta.get('generation'),dict) else {}
        guard=meta.get('output_guard') if isinstance(meta.get('output_guard'),dict) else {}
        reason=generation.get('status') or guard.get('reason')
        failures={
            'dialogue_repetition':('Risposta da rielaborare','Il tentativo riproponeva una domanda o un contenuto già affrontato.'),
            'insufficient_progress':('Risposta da rielaborare','Il tentativo non aggiungeva quanto richiesto.'),
            'cancelled':('Risposta interrotta','L’elaborazione è stata annullata. Il tentativo non viene appreso.'),
            'inference_error':('Errore di elaborazione','Si è verificato un errore durante la generazione.'),
            'budget_exhausted':('Limite di elaborazione','La generazione ha raggiunto il limite senza una risposta utilizzabile.'),
            'subject_mismatch':('Risposta non validata','Il tentativo non distingueva correttamente le persone o le esperienze descritte.'),
            'identity_conflict':('Risposta non validata','Il tentativo non rispettava l’identità di ALLMA.'),
            'unsupported_personal_claim':('Risposta non validata','Il tentativo attribuiva ad ALLMA un’esperienza personale senza riscontro.'),
            'validation_unavailable':('Controllo non disponibile','Non è stato possibile completare i controlli richiesti.'),
        }
        if reason in failures:
            label,detail=failures[reason]
            return {'kind':'incomplete','label':label,'detail':detail,'reason':reason}
        return {'kind':'incomplete','label':'Risposta non validata',
            'detail':'La risposta non ha superato tutti i controlli; non è conoscenza verificata.'}
    if source in {'verified_calculation','verified_text_count'} and meta.get('knowledge_verified') is True:
        return {'kind':'computation','label':'Calcolo verificato',
            'detail':'Il risultato è stato calcolato da uno strumento di ALLMA, senza affidarlo alla generazione del modello.'}
    if source == 'reference_excerpt':
        evidence=meta.get('reference_review',{})
        from allma_model.utils.public_references import _url_allowed
        citation=evidence.get('citation') if isinstance(evidence,dict) else None
        if isinstance(citation,dict) and _url_allowed(citation.get('url')):
            return {'kind':'reference','label':'Estratto da una fonte pubblica',
                'detail':('Fonte conservata sul dispositivo. ' if evidence.get('retrieval_status')=='cached' else 'Fonte consultata online. ')+
                    'Il testo è riportato dalla pagina indicata, senza aggiunte del modello. Una fonte può contenere errori.',
                'via':'cache' if evidence.get('retrieval_status')=='cached' else 'internet',
                'citation':citation}
    if source in {'literal_user_memory','personal_fact','personal_fact_memory','personal_fact_recall','user_declaration','user_profile'}:
        return {'kind':'memory','label':'Ricordo riferito da te',
            'detail':'Proviene dalle tue dichiarazioni conservate. È un ricordo di ciò che hai riferito, non una verifica indipendente del fatto.'}
    if source in {'learned_recall','confirmed_answer_recall'}:
        return {'kind':'learned','label':'Risposta appresa',
            'detail':'È una risposta già confermata nei precedenti scambi, recuperata senza una nuova generazione. La conferma personale non prova la verità universale.'}
    review = meta.get('turn_review')
    if source == 'model_revised' or (source == 'model_generated' and isinstance(review,dict)
                                   and review.get('repair_status') == 'accepted'):
        return {'kind':'model','label':'Rielaborata dopo un controllo',
            'detail':'ALLMA ha rilevato un problema nel primo tentativo e richiesto una revisione mirata al modello. '
                'La revisione ha superato i controlli disponibili; non costituisce una verifica indipendente dei fatti.'}
    if source in {'model_generated','model_excerpt'}:
        if source=='model_excerpt' and (meta.get('recovery') or {}).get('reason')=='repeated_checkin':
            return {'kind':'model','label':'Domanda ripetuta rimossa',
                'detail':'È stata conservata la parte utile della risposta del modello e rimossa una domanda già soddisfatta. '
                    'ALLMA non ha aggiunto frasi sostitutive; il testo conservato ha superato i controlli disponibili.'}
        memory_used = bool(meta.get('memory_score',0)) or bool(meta.get('memory_evidence_ids'))
        lookup=(meta.get('turn_review') or {}).get('reference_lookup',{})
        search_note=(' La consultazione online non ha restituito un riscontro utilizzabile.'
            if lookup.get('status') in ('unavailable','not_found','consent_revoked') else '')
        return {'kind':'model','label':'Generata dal modello',
            'detail':('Il modello ha formulato la risposta usando anche il contesto recuperato. ' if memory_used else
                'Il modello ha formulato la risposta nel contesto della conversazione. ')+
                'Questo non equivale a una verifica indipendente di ciò che afferma.'+search_note}
    if source in {'identity_core','origin_identity'}:
        return {'kind':'identity','label':'Identità di ALLMA', 'detail':'Proviene dal nucleo identitario stabile.'}
    if source:
        return {'kind':'system','label':'Gestita da ALLMA',
            'detail':'È un risultato della gestione del dialogo o dello stato persistente. Non indica un nuovo fatto verificato.'}
    return {'kind':'unknown','label':'Origine non disponibile','detail':'Questo messaggio non conserva metadati sufficienti per ricostruirne l’origine.'}


def _answers(recall, user, limit=12):
    if recall is None:
        return []
    with recall.lock:
        if recall.load_error is not None:
            raise ValueError('Learning archive unavailable')
        def collect(rows):
            output = deque(maxlen=limit)
            for key, record in rows:
                if not recall._valid_record(key, record):
                    raise ValueError('Invalid learned answer')
                if record['user'] != user:
                    continue
                votes = len(record['confirmations'])
                if not votes and not record['rejected']:
                    continue
                output.append({'text':record['question'][:180],
                    'detail':('Ritirata dopo una correzione' if record['rejected'] else
                        'Confermata e disponibile al recupero' if votes >= recall.confirmations else
                        'In valutazione: servono altri riscontri indipendenti'),
                    'confirmations':votes, '_key':key})
            return list(output)
        if recall._store is None:
            output = collect(recall.records.items())
        else:
            with recall._store.connect(readonly=True) as db:
                db.execute('BEGIN')
                recall._store._refresh_generation(db)
                output = collect((key,json.loads(raw)) for key,raw in db.execute('SELECT key,record FROM answers ORDER BY rowid'))
        for item in output:
            item['usable'] = recall.lookup(item.pop('_key'), user) is not None
            if not item['usable'] and item['detail'] == 'Confermata e disponibile al recupero':
                item['detail'] = 'Confermata; il recupero resta soggetto ai controlli di contesto e formato'
        return output


def snapshot(core, user):
    """No writes, new model calls, user-selected IDs or synthetic defaults."""
    if not user:
        return {'status':'unavailable','sections':[]}
    if not core._lock.acquire(blocking=False):
        return {'status':'busy','sections':[]}
    try:
        memory = core.conversational_memory
        rows = memory.recent_messages(64, predicate=lambda m: (m.user_id or m.metadata.get('user_id')) == user)
        answers = _answers(getattr(core,'answer_recall',None),user)
        recent, corrections = [], []
        for message in rows:
            if message.role != 'assistant':
                continue
            meta = message.metadata
            if meta.get('source') == 'proactive' and meta.get('proactive_delivery',{}).get('state') != 'queued':
                continue
            origin = response_origin(meta)
            recent.append({'text':message.content[:200], 'detail':origin['label']+' · '+origin['detail']})
            if meta.get('source') in {'learning_feedback','literal_memory_control_ack','personal_fact_control_ack','tool_learning_feedback','literal_user_update_ack','literal_user_revocation_ack','personal_fact_revocation_ack'}:
                corrections.append({'text':message.content[:200],'detail':'Riscontro conservato nella conversazione'})
        strategies = []
        learner = getattr(core,'meta_learner',None)
        tools = getattr(learner,'tool_learning',None)
        if tools is not None:
            view = tools.view(user)
            count = view.get('confirmed_tasks',0)
            if count:
                strategies.append({'text':'Criteri di conteggio',
                    'detail':str(count)+' compiti distinti confermati. '+('ALLMA può proporre il criterio appreso, chiedendoti conferma.'
                        if view.get('suggested_overlap') is not None else 'Non bastano ancora per proporre un criterio stabile.')})
        tracker = getattr(core,'goal_progress',None)
        if tracker is not None:
            from allma_model.learning_system.plan_experience import cases, assessment
            goals = tracker.goals(user)
            for goal, case in cases(goals):
                if goal.get('status') == 'revoked' or case['withdrawn']:
                    continue
                review = assessment(goals,goal,case)
                strategies.append({'text':case['step'][:180],
                    'detail':('Esito confermato da te' if case['outcome']=='confirmed' else 'Precauzione da valutare')+
                        ' · '+str(review['supporting_tasks'])+' altri compiti favorevoli, '+str(review['counterexamples'])+' contrari.'})
        return {'status':'ok','sections':[
            {'title':'Risposte apprese','empty':'Le risposte diventeranno utilizzabili dopo riscontri espliciti e indipendenti.', 'items':answers},
            {'title':'Strategie ed esperienze','empty':'Non ci sono ancora strategie sostenute dai tuoi riscontri.', 'items':strategies[-12:]},
            {'title':'Correzioni recenti','empty':'Nessuna correzione negli ultimi scambi disponibili.', 'items':corrections[-8:]},
            {'title':'Come ho risposto','empty':'Le prossime risposte mostreranno qui la loro origine.', 'items':recent[-10:]}]}
    except Exception:
        return {'status':'unavailable','sections':[]}
    finally:
        core._lock.release()
