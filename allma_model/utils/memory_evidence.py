"""Conservative retrieval filters; no deletion of conversation history."""
import re


def _recall_only_question(text):
    """Closed recall requests contain no new location/identifier declaration.

    Restrict this to whole locational questions or the existing literal grammar.
    Mixed reports, subordinate facts and requests about past questions survive.
    """
    from allma_model.utils.literal_recall import is_literal_request
    if is_literal_request(text):
        return True
    plain=' '.join(text.casefold().split()).rstrip('?.!')
    if re.search(r'[?!.;\n]|["«»“”]',plain):
        return False
    match=re.fullmatch(r'(?:(?:(?:ti|mi) ricordi|ricordi|sai|puoi ricordarmi)\s+)?'
        r'dove\s+(?:ho\s+(?:messo|lasciato|riposto|sistemato)|tengo|conservo|'
        r'si trov(?:a|ano)|è|sono)\s+(.{1,80})',plain)
    return bool(match and not re.search(r'\b(?:che|perché|perche|quando|ma|ieri|oggi|e)\b',match[1]))


def report_key(text):
    return ' '.join(text.split())


def is_replayed_question(text, query):
    # Exclude only the same question, not questions containing useful reports
    # or a user's request to recall a different earlier question.
    if _recall_only_question(query) and _recall_only_question(text):
        return True
    if report_key(text).casefold() != report_key(query).casefold():
        return False
    if text.rstrip().endswith('?') and query.rstrip().endswith('?'):
        return True
    # A closed literal recall request may end with a formatting instruction.
    # Its parsed grammar contains no personal declaration; do not generalize
    # this to arbitrary messages containing '?' and potentially useful facts.
    from allma_model.utils.literal_recall import is_literal_request
    return is_literal_request(text) and is_literal_request(query)


def explicit_memory_request(message):
    """An attributed past communication requires lookup even if routing errs."""
    import re
    return bool(re.search(r'\bti\s+(?:ho|avevo|abbiamo|avevamo)\s+'
                          r'(?:(?:già|gia|appena|mai)\s+)?'
                          r'(?:detto|indicato|comunicato|raccontato|scritto|spiegato|chiesto)\b',
                          message or '', re.I))
