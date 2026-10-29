"""Explicit task controls; general conversation never silently opens a goal."""
import re
from allma_model.core.autobiographical_identity import normalized
from allma_model.agency_system.goal_progress import valid_request


def command(text):
    text = text.strip()
    target = re.match(r'^Per l[’\']obiettivo\s+[«“"]([^»”"\n]+)[»”"]\s*:\s*', text, re.I)
    owner = target[1] if target else None
    if target:text = text[target.end():]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:return None
    match = re.fullmatch(r'(Nuovo obiettivo|Progresso(?: dell[’\']obiettivo| obiettivo)?|Criterio(?: dell[’\']obiettivo| obiettivo)?|'
        r'Prossimo passo(?: dell[’\']obiettivo| obiettivo)?|Correggi obiettivo|Risultato(?: dell[’\']obiettivo| obiettivo)?|'
        r'Risultato obiettivo sbagliato|Risultato del passo|Risultato del passo sbagliato|Lezione utile|Lezione non utile|Dimentica lezione)\s*(?::|è)\s*(\S.*)', lines[0], re.I)
    if match:
        label = normalized(match[1])
        kind = ('lesson_positive' if label == 'lezione utile' else 'lesson_negative' if label == 'lezione non utile' else
                'lesson_forget' if label == 'dimentica lezione' else
                'step_reject' if label == 'risultato del passo sbagliato' else 'step_result' if label == 'risultato del passo' else
                'create' if label.startswith('nuovo') else 'progress' if label.startswith('progresso') else
                'criterion' if label.startswith('criterio') else 'next_step' if label.startswith('prossimo') else
                'correct' if label.startswith('correggi') else 'reject' if 'sbagliato' in label else 'result')
        request = {'kind':kind,'text':match[2]}
        for line in lines[1:]:
            field = re.fullmatch(r'(Criterio|Prossimo passo)\s*:\s*(\S.*)',line,re.I)
            if field is None:return None
            key = 'criterion' if normalized(field[1]) == 'criterio' else 'next_step'
            if key in request:return None
            request[key] = field[2]
    elif len(lines) == 1:
        commands = {'confermo il risultato dell’obiettivo':('confirm',None),
                    'confermo il risultato dell\'obiettivo':('confirm',None),
                    'sospendi obiettivo':('pause',None),'riprendi obiettivo':('resume',None),
                    'adotta questo piano':('adopt_plan',None),'adotta il piano':('adopt_plan',None),
                    'confermo il risultato del passo':('step_confirm',None),
                    'riapri obiettivo':('reopen',None),'annulla obiettivo':('cancel',None),
                    'puoi propormi il prossimo passo dell’obiettivo':('initiative',True),
                    'puoi propormi il prossimo passo dell\'obiettivo':('initiative',True),
                    'non propormi il prossimo passo dell’obiettivo':('initiative',False),
                    'non propormi il prossimo passo dell\'obiettivo':('initiative',False)}
        value = commands.get(normalized(text))
        if value is None:return None
        request = {'kind':value[0]}
        if value[0] == 'initiative':request['enabled'] = value[1]
    else:return None
    if owner:request['target'] = owner
    return request if valid_request(request) else None


PHASES = {'active':'in corso','paused':'in pausa','awaiting_verification':'risultato da confermare',
          'completed':'completato su tua conferma','cancelled':'annullato'}


def describe(goal):
    wf = goal['workflow']
    text = (f'Obiettivo: {goal["objective"]}\nStato: {PHASES[wf["phase"]]}\n'
            f'Criterio: {wf["criterion"] or "da definire"}\n'
            f'Progresso che hai indicato: {wf["progress"] or "non ancora registrato"}\n'
            f'Prossimo passo: {wf["next_step"] or "da definire"}')
    if wf['result']:
        text += '\nRisultato che hai dichiarato: '+wf['result']['text']
    if wf['phase'] == 'awaiting_verification':
        text += '\nHo registrato la tua dichiarazione. Per chiudere il compito, controlla il criterio e scrivi «Confermo il risultato dell’obiettivo».'
    plan = wf.get('plan')
    if plan:
        labels = {'pending':'da fare','awaiting_confirmation':'risultato da confermare','confirmed_by_user':'confermato da te'}
        text += '\nPiano: '+{'active':'adottato','needs_review':'da rivedere dopo la correzione','closed':'chiuso'}[plan['status']]
        text += '\n'+'\n'.join(f'{i+1}. [{labels[s["status"]]}] {s["text"]}' for i,s in enumerate(plan['steps']))
        if plan.get('notes'):
            text += '\nNote della proposta, da valutare: '+plan['notes']
        if plan['index'] == len(plan['steps']) and wf['phase'] != 'completed':
            text += '\nTutti i passi sono confermati da te. Resta da verificare il criterio complessivo dell’obiettivo.'
    return text


def prepare(tracker, user, message):
    request = command(message)
    query = normalized(message)
    from allma_model.agency_system.goal_plans import requested as plan_requested
    plan_request = plan_requested(message)
    if query in {'cosa hai imparato dai piani','mostra le lezioni dei piani','mostra le esperienze degli obiettivi'}:
        return {'control':None,'source':'goal_learning_status','answer':tracker.experience_view(user)}
    if request:
        control, clarification = tracker.prepare(user,request)
        return {'control':control,'answer':clarification or '', 'source':'goal_control' if control else 'goal_clarification'}
    if query not in {'quali sono i miei obiettivi','mostra i miei obiettivi','qual e il mio obiettivo',
                     'qual e il nostro obiettivo','a che punto siamo con l’obiettivo',
                     'a che punto siamo con l\'obiettivo','qual e il prossimo passo dell’obiettivo',
                     'qual e il prossimo passo dell\'obiettivo','riprendiamo l’obiettivo','riprendiamo l\'obiettivo',
                     'come gestisco gli obiettivi'}:
        if not plan_request and not re.search(r'\b(?:questo|mio|nostro)\s+obiettivo\b|\b(?:questo|nostro)\s+compito\b',query):
            return None
        goals = [g for g in tracker.goals(user) if g['status'] == 'active']
        if len(goals) != 1:
            return {'control':None,'source':'goal_clarification','answer':
                'Non ho un unico obiettivo attivo a cui collegare la richiesta. Chiedimi «Quali sono i miei obiettivi?» oppure indicane il nome.'}
        goal = goals[0]
        wf = goal['workflow']
        if plan_request and not wf['criterion']:
            return {'control':None,'source':'goal_clarification','answer':
                    'Prima del piano definiamo come riconoscere il risultato. Scrivi «Criterio obiettivo: …».'}
        context = {'id':goal['id'],'revision':wf['revision'],'source':'user_report',
            'objective':goal['objective'][:500], 'criterion':wf['criterion'][:500],
            'progress':wf['progress'][:500],'next_step':wf['next_step'][:500],
            'plan_notes':{'text':wf['plan'].get('notes',''),'source':'user_admitted_model_proposal'}
                if (wf.get('plan') or {}).get('status') == 'active' else None,
            'phase':wf['phase'],'verification':wf['verification'],'plan_request':plan_request}
        if plan_request:
            from allma_model.learning_system.plan_experience import context as experience_context
            from allma_model.agency_system.plan_review import requirements
            context['criterion'] = wf['criterion']
            context['requirements'] = requirements(wf['criterion'])
            context['experiences'] = experience_context(tracker.goals(user),goal)
        return {'context':context}
    if query == 'come gestisco gli obiettivi':
        return {'control':None,'source':'goal_help','answer':
            'Puoi scrivere «Nuovo obiettivo: …», aggiungendo «Criterio: …» e «Prossimo passo: …» su righe separate. '
            'Poi usa «Progresso obiettivo: …», «Risultato obiettivo: …» o «Correggi obiettivo: …». '
            'Con «Quali sono i miei obiettivi?» ritrovi il punto raggiunto anche in un’altra chat. '
            'Puoi chiedere «Proponi un piano per questo obiettivo» e poi scegliere «Adotta questo piano». '
            'Per avanzare registra «Risultato del passo: …» e «Confermo il risultato del passo». '
            'Con «Cosa hai imparato dai piani?» consulti esperienze e ipotesi ricavate dai riscontri. '
            'Se ne hai più di uno, indica «Per l’obiettivo “nome”: …». Le proposte spontanee richiedono un tuo consenso.'}
    goals = tracker.goals(user)
    active = [goal for goal in goals if goal['status'] == 'active']
    selected = active if active else goals[-3:]
    return {'control':None,'source':'goal_status','answer':
            '\n\n'.join(describe(goal) for goal in selected[:8]) if selected else 'Non hai ancora registrato obiettivi persistenti.'}


def applied_reply(tracker, user, report):
    if report and report.get('status') == 'review_required':
        from allma_model.agency_system.plan_review import explanation
        return explanation(report['review'])
    if not report or report.get('status') != 'applied':
        return 'Il messaggio è salvato, ma l’aggiornamento dell’obiettivo non è confermato. Consulta lo stato prima di riprovare.'
    goal = next(g for g in tracker.goals(user) if g['id'] == report['goal_id'])
    prefixes = {'create':'Ho registrato l’obiettivo.', 'confirm':'Ho segnato l’obiettivo come completato su tua conferma.',
                'cancel':'Ho annullato l’obiettivo.', 'reject':'Ho registrato che il risultato non era corretto: la conclusione precedente non è più valida.',
                'initiative':'Ho aggiornato il consenso alle proposte per questo obiettivo. Restano valide le impostazioni generali di iniziativa.'}
    prefixes.update(adopt_plan='Ho adottato i passi del piano su tua richiesta.',
                    step_result='Ho registrato il risultato che hai dichiarato per il passo. Attendo la tua conferma.',
                    step_confirm='Ho confermato il passo sulla base del tuo riscontro.',
                    step_reject='Ho registrato la correzione. Il passo resta da completare.',
                    lesson_positive='Ho registrato che questa precauzione ti è stata utile nel nuovo compito.',
                    lesson_negative='Ho registrato il riscontro contrario: l’ipotesi viene considerata contestata.',
                    lesson_forget='Ho ritirato questa ipotesi dal recupero delle esperienze. Il fatto originario resta documentato nella conversazione.')
    prefix=prefixes.get(report['kind'],'Ho aggiornato l’obiettivo.')
    if report.get('plan_review',{}).get('status')=='not_automatically_checkable':
        prefix+=' Il controllo automatico non copre tutti i requisiti: il contenuto resta da valutare.'
    return prefix+'\n\n'+describe(goal)
