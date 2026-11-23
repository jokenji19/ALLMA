"""Feedback tied to one delivered answer and its original question."""
from dataclasses import replace
import hashlib
import logging
import re

from .autobiographical_identity import response_disputed
from allma_model.learning_system.answer_recall import normalize
from allma_model.utils.saved_references import saved_topic, valid_id


def response_id(metadata):
    return metadata.get('response_feedback_id') or metadata.get('reference_save_id')


def feedback_view(state):
    from .learning_insights import response_origin

    view = {key: state[key] for key in ('vote', 'status', 'note', 'saved') if key in state}
    if check := state.get('check'):
        def passage(row):
            return {'text': row.get('text', ''),
                    'origin': response_origin(row['metadata']) if row.get('metadata') else None}

        view['check'] = {'status': check['status'], **passage(check)}
        if check.get('alternatives'):
            view['check']['alternatives'] = [passage(row) for row in check['alternatives']]
    return view


def _question_key(question):
    return hashlib.sha256(normalize(question).encode()).hexdigest()


def latest_correction(memory, user, question, conversation=None):
    from allma_model.utils.public_references import public_topic

    key = _question_key(question)
    if conversation is not None and public_topic(question):
        # Topics that resolve without an anchor can be recovered across chats.
        conversation = None
    with memory.lock:
        store = getattr(memory, '_history_store', None)
        if store is not None and store.correction_index:
            return store.response_correction(user, key, conversation)
        for row in reversed(memory.messages):
            if row.user_id == user and (conversation is None or row.conversation_id == conversation):
                state = row.metadata.get('response_feedback') or {}
                if state.get('question_key') == key:
                    return state.get('note')
    return None


def _verified_value(text, topic, terms):
    # A bare value can be compared. Several dates, quoted conjectures and
    # sentences containing extra claims require a more specific check.
    match = re.fullmatch(r'\s*\*{0,2}(?:nel )?([12]\d{3})\*{0,2}[.!]?\s*', text, re.I)
    if match or not (topic and terms):
        return match[1] if match else None
    events = '|'.join(map(re.escape, terms))
    name = re.sub(r"^(?:il |lo |la |i |le |gli |l[’'])", '', topic, flags=re.I)
    match = re.fullmatch(rf"\s*(?:(?:il |lo |la |i |le |gli |l[’'])?{re.escape(name)}\s+)?"
                         rf"(?:fu|venne|è stat[oa]|sono stat[ie])\s+(?:{events})\s+nel\s+([12]\d{{3}})[.!]?\s*",
                         text, re.I)
    return match[1] if match else None


def _source_year(text, topic, terms):
    from allma_model.utils.contextual_references import _subject_in

    years = set(re.findall(r'(?<!\w)[12]\d{3}(?!\w)', text))
    if len(years) != 1 or re.search(
        r'\b(?:non|nessun\w*|forse|sarebbe|sarebbero|probabil\w*|ipotesi|prima|dopo|entro|verso|'
        r'incert\w*|circa|presunt\w*|contest\w*|not|possibly|before|after|around|bce|bc|avanti cristo)\b|'
        r'\ba\s*\.\s*c\s*\.', text, re.I):
        return None
    if not topic:
        # Focused requests already require a matching subject and relation.
        return next(iter(years))
    plain = re.sub(r'\([^()\n]*\)', ' ', text).split(';', 1)[0]
    subject = _subject_in(topic, plain)
    if not subject or not terms:
        return None
    events = '|'.join(map(re.escape, terms))
    year = next(iter(years))
    event = (
        rf"\s+(?:o [^,;.!?\d]{{2,82}}?\s+)?(?:fu|venne|è stat[oa]|furono|sono stat[ie])\s+"
        rf"(?:(?:un |una )(?:accordo|patto|trattato|intesa)\s+)?(?:{events})\s+"
        rf"(?:nel\s+|(?:[aA]\s+[^,;.!?\d]{{1,42}}?\s+)?il\s+\d{{1,2}}[º°]?\s+[^\W\d_]+\s+){year}\b"
    )
    return year if re.match(event, plain[subject.end():], re.I) else None


def _check_answer(core, question, event, history):
    from .autobiographical_identity import grounded_reply
    from allma_model.utils.exact_calculation import calculation_reply
    from allma_model.utils.exact_text import text_count_reply
    from allma_model.utils.contextual_references import contextual_identity_question, contextual_reference_request
    from allma_model.utils.contribution_review import history_contribution, select_contribution
    from allma_model.utils.public_references import local_only_request, person_or_group_question, public_topic
    from allma_model.utils.web_search import broad_web_request, compose_web_answer, render_web_passages, search_query
    from allma_model.utils.online_weather import weather_request

    original = event.content
    local = calculation_reply(question) or text_count_reply(question)
    if local is None:
        candidate = grounded_reply(question, core.conversational_memory, event.user_id, core.user_profile)
        if candidate and candidate[1] == 'origin_identity':
            local = candidate
    if local and local[1] in ('verified_calculation', 'verified_text_count', 'origin_identity'):
        answer, source, _ = local
        status = 'supported' if normalize(answer) == normalize(original) else 'corrected'
        return {'status': status, 'text': answer,
                'metadata': {'source': source, 'knowledge_verified': True}}, None

    service = core.public_references
    language = core._detect_language_request(question) or core._guess_language_code(question)
    weather = weather_request(question, history)
    if weather and weather.city:
        result = service.live_lookup(service.weather, question, (weather,))
        if result['status'] == 'obtained':
            return {'status': 'updated', 'text': result['answer'], 'metadata': {'source': 'weather_data',
                    'reference_review': {'citation': result['citation']}}}, result.get('authorization_revision')
        return {'status': 'offline' if result['status'] in ('local_only', 'consent_revoked') else 'unresolved'}, None

    contextual = contextual_identity_question(question, history)
    research_question = contextual if contextual and not local_only_request(question) else question
    focused = contextual_reference_request(research_question, history)
    if focused and not local_only_request(question):
        evidence = history_contribution(history, focused, None)
        if evidence:
            text, review = evidence
            return _source_check(original, text, review, focused.answer_type == 'date'), None

    if broad_web_request(research_question):
        query = search_query(research_question, explicit=True)
        if query:
            from allma_model.utils.public_references import freshness_requested
            fresh = freshness_requested(research_question) or bool(re.search(
                r'\b(?:ultim[ei]|latest)\b', research_question, re.I))
            result = service.search_web(question, query, language, fresh)
            sources = compose_web_answer(query, result.get('results'), fresh)
            if sources:
                text = render_web_passages(sources, language)
                review = {'basis': 'web_passages', 'truth_verified': False, 'sources': sources,
                          'public_topic': query, 'retrieval_status': result['status'], 'fresh': fresh,
                          'network_used': result['network_used']}
                return {'status': 'evidence', 'text': text, 'metadata': {
                    'source': 'web_search', 'reference_review': review}}, result.get('authorization_revision')
            return {'status': 'offline' if result['status'] in ('local_only', 'consent_revoked') else 'unresolved'}, None

    result = service.lookup(research_question, language=language, focused=focused)
    selection = dict(evidence_terms=result.get('evidence_terms', ()),
                     focus_evidence=result.get('focus_evidence', False),
                     year_terms=result.get('year_terms', ()), focused=focused)
    contributions = [item for reference in result['references']
                     if (item := select_contribution([reference], **selection)) is not None]
    if not contributions:
        return {'status': 'offline' if result['status'] in ('local_only', 'consent_revoked') else 'unresolved'}, None
    prior = event.metadata.get('reference_review') or {}
    terms = result.get('year_terms', ())
    topic = public_topic(research_question) if terms else None
    is_year = bool(terms or (focused and focused.answer_type == 'date'))
    candidates, dated = [], {}
    for contribution in contributions:
        review = contribution.audit()
        review.update(retrieval_status=result['status'], network_used=result['network_used'])
        candidate = _source_check(original, contribution.text, review, is_year, topic, terms)
        candidates.append(candidate)
        if is_year and (year := _source_year(contribution.text, topic, terms)):
            dated[year] = candidate
    if len(dated) > 1:
        return {'status': 'conflicting', 'alternatives': list(dated.values())}, result.get('authorization_revision')
    check = next(iter(dated.values()), candidates[0])
    if check['status'] == 'supported' and prior.get('source_id') == check['metadata']['reference_review']['source_id']:
        check['status'] = 'same_source'
    # A qualified identity question is answered by a specific source title,
    # even when comparing the free-text draft would require interpretation.
    if contextual and person_or_group_question(research_question) and check['status'] == 'evidence':
        check['status'] = 'identity'
    return check, result.get('authorization_revision')


def _source_check(original, text, review, is_year, topic=None, terms=()):
    status = 'supported' if normalize(original) == normalize(text) else 'evidence'
    old_year = _verified_value(original, topic, terms) if is_year else None
    if old_year and (year := _source_year(text, topic, terms)):
        status = 'supported' if old_year == year else 'corrected'
    return {'status': status, 'text': text,
            'metadata': {'source': 'reference_excerpt', 'reference_review': review}}


def _persist(memory, event, state):
    with memory.lock:
        previous = event.metadata.get('response_feedback')
        event.metadata['response_feedback'] = state
        try:
            memory.save_memory()
        except Exception:
            if previous is None:
                event.metadata.pop('response_feedback', None)
            else:
                event.metadata['response_feedback'] = previous
            raise


def _learn_usefulness(core, event, identifier, positive):
    try:
        core.coalescence_processor.observe_feedback(
            event.user_id, identifier, positive, event.metadata.get('topics', []))
    except (AttributeError, OSError, ValueError) as error:
        logging.warning('Usefulness feedback unavailable: %s', type(error).__name__)


def apply_feedback(core, user, conversation, identifier, vote, note=None):
    if (not user or not conversation or not valid_id(identifier)
            or vote not in ('up', 'down', 'review_up', 'review_down', 'correction')
            or (vote == 'correction' and (not isinstance(note, str) or not 1 <= len(note.strip()) <= 1000))):
        raise ValueError('Riscontro non valido.')
    memory = core.conversational_memory
    with memory.lock:
        event = None
        for row in reversed(memory.messages):
            if row.user_id != user or row.conversation_id != conversation:
                continue
            if event is None and row.role == 'assistant' and response_id(row.metadata) == identifier:
                event = row
            elif event is not None and row.role == 'user':
                question = row
                break
        else:
            raise ValueError('Questa risposta non è disponibile.')
        if event.metadata.get('is_valid') is not True or not event.content.strip():
            raise ValueError('Rispondi dopo che ALLMA ha terminato il messaggio.')
        state = dict(event.metadata.get('response_feedback') or {})

    if vote in ('up', 'review_up'):
        first_approval = not state
        if vote == 'review_up':
            check = state.get('check') or {}
            if state.get('status') == 'review_disputed' or check.get('status') not in (
                    'supported', 'same_source', 'corrected', 'identity', 'evidence', 'updated'):
                raise ValueError('Indica il punto da correggere prima di salvare.')
            metadata = check['metadata']
            bookmark = identifier
            checked = replace(event, content=check['text'], metadata={
                **metadata, 'is_valid': True, 'reference_save_id': bookmark})
            if saved_topic(metadata['source'], metadata.get('reference_review')):
                core.saved_references.remember(user, checked)
                state.update(review_id=bookmark, saved=True)
            state['status'] = 'review_approved'
        else:
            if state.get('vote') == 'down':
                raise ValueError('La risposta è già stata segnalata. Valuta l’esito della verifica.')
            bookmark = event.metadata.get('reference_save_id')
            if bookmark:
                core.saved_references.remember(user, event)
            state.update(vote='up', status='approved', saved=bool(bookmark))
        _persist(memory, event, state)
        if first_approval:
            _learn_usefulness(core, event, identifier, True)
        return feedback_view(state)

    if state.get('vote') != 'down':
        if vote != 'down':
            raise ValueError('Segnala prima la risposta.')
        if key := event.metadata.get('recall_key'):
            core.answer_recall.feedback(key, user, identifier, False, answer=event.content)
        if bookmark := event.metadata.get('reference_save_id') or event.metadata.get('recalled_reference_id'):
            core.saved_references.forget(user, bookmark)
        state = {'vote': 'down', 'status': 'pending', 'saved': False}
        _persist(memory, event, state)
        _learn_usefulness(core, event, identifier, False)
    if vote == 'correction':
        if bookmark := state.get('review_id'):
            core.saved_references.forget(user, bookmark)
        state.update(status='user_correction', note=note.strip(), saved=False,
                     question_key=_question_key(question.content))
        state.pop('check', None)
        state.pop('review_id', None)
        _persist(memory, event, state)
    elif vote == 'review_down':
        if state['status'] == 'review_approved':
            if bookmark := state.get('review_id'):
                core.saved_references.forget(user, bookmark)
            state.update(status='review_disputed', saved=False)
            state.pop('review_id', None)
            _persist(memory, event, state)
    elif state['status'] == 'pending':
        history = memory.recent_messages(16, predicate=lambda row: row.user_id == user
            and row.conversation_id == conversation and row.timestamp < question.timestamp
            and not response_disputed(row.metadata))
        try:
            check, revision = _check_answer(core, question.content, event, history)
        except Exception as error:
            logging.warning('Response check unavailable: %s', type(error).__name__)
            check, revision = {'status': 'unresolved'}, None
        with core.public_references.delivery_authorized(revision) as allowed:
            if not allowed:
                check = {'status': 'offline'}
            state.update(status='reviewed', check=check)
            _persist(memory, event, state)
        if check.get('metadata', {}).get('source') == 'web_search':
            core.public_references.register_web_links(check['metadata']['reference_review']['sources'])
    return feedback_view(state)
