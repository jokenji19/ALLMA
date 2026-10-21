"""Explicit challenges are requests to recheck, never verified replacement facts."""
import re


def is_explicit_correction(message):
    text = (message or '').strip().casefold()
    return bool(re.match(
        r"(?:no[,!:]?\s+)?(?:hai sbagliato\b|ti sbagli\b|"
        r"sbagliat[oa](?=\s*[,!.:]|\s*$)|non (?:è|e) cos[iì](?=\s*[,!.:]|\s*$)|"
        r"la risposta (?:è|e)\s+[-+]?\d+\b|"
        r"la (?:tua )?risposta (?:corretta|giusta) (?:è|e)\b|"
        r"la tua risposta (?:è|e) (?:sbagliata|errata|falsa)\b|"
        r"quello che hai (?:detto|scritto) (?:è|e) (?:sbagliato|falso)\b|"
        r"your (?:answer|response) is (?:wrong|incorrect)\b|you are wrong\b)", text))
