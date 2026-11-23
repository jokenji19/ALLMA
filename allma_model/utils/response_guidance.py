"""Explicit challenges are requests to recheck, never verified replacement facts."""
import re
import unicodedata

_CORRECTIONS = {
    'it': r"(?:hai sbagliato\b|ti sbagli\b|"
        r"sbagliat[oa](?=\s*[,!.:]|\s*$)|non [èée] cos[iì](?=\s*[,!.:]|\s*$)|"
        r"la risposta [èée]\s+[-+]?\d+\b|"
        r"la (?:tua )?risposta (?:corretta|giusta) [èée]\b|"
        r"la tua risposta [èée] (?:sbagliata|errata|falsa)\b|"
        r"quello che hai (?:detto|scritto) [èée] (?:sbagliato|falso)\b|"
        r"(?:(?:lui|lei) )?non (?:[èée]|era|fu|sono|erano) +[^.!?]+?\bma\s+\S)",
    'en': r"(?:your (?:answer|response) is (?:wrong|incorrect)\b|you are wrong\b|"
        r"(?:he|she|it|they)(?: (?:is|was|are|were) not| (?:is|was|are|were)n't|'s not|'re not)"
        r"\s+[^.!?]+?(?:\bbut\s+|,\s*(?:(?:he|she|it)'s|they're|(?:he|she|it|they) (?:is|was|are|were))\s+)\S)",
    'es': r"(?:(?:él|ella) )?no (?:es|era|fue|son)\s+[^.!?]+?\bsino\s+\S",
    'fr': r"(?:il|elle) (?:n'est|n'était) pas\s+[^.!?]+?(?:\bmais\b|,\s*(?:il|elle) est)\s+\S",
    'de': r"(?:(?:er|sie|es) (?:ist|war|sind|waren) )?nicht\s+[^.!?]+?\bsondern\s+\S",
    'pt': r"(?:(?:ele|ela) )?não (?:é|era|foi|são)\s+[^.!?]+?\b(?:mas|e sim)\s+\S",
    'ru': r"(?:(?:он|она|они|это) )?не\s+[^.!?]+?,\s*а\s+\S",
    'ar': r"(?:(?:هو|هي) )?(?:ليس|ليست)\s+[^.!?؟]+?\bبل\s+\S",
    'zh': r"(?:[他她它牠]|[他她它]們|[他她它]们|这|這)?不是[^。！？!?]+?(?:而是|[,，]\s*是)\s*\S",
    'ja': r"[^。！？!?]+?(?:ではなく|じゃなく)[、,]?\s*\S",
}
_PATTERNS = {language: re.compile(pattern) for language, pattern in _CORRECTIONS.items()}


def correction_language(message):
    text = unicodedata.normalize('NFKC', message or '').strip().casefold().replace('’', "'")
    text = re.sub(r"^(?:no|non|nein|não|нет|لا)[,!:]\s*", '', text)
    return next((language for language, pattern in _PATTERNS.items()
                 if pattern.match(text) or (text.startswith('no ') and pattern.match(text[3:]))), None)


def is_explicit_correction(message):
    return correction_language(message) is not None
