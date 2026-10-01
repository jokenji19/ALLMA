"""Conservative conversational guidance; hypothetical errors are not corrections."""
import re


def is_explicit_correction(message):
    text = (message or '').strip().lower()
    return bool(re.match(
        r"(?:no[,!:]?\s+)?(?:hai sbagliato\b|ti sbagli\b|la tua risposta (?:è|e) (?:sbagliata|errata|falsa)\b|"
        r"quello che hai (?:detto|scritto) (?:è|e) (?:sbagliato|falso)\b|"
        r"your (?:answer|response) is (?:wrong|incorrect)\b|you are wrong\b)", text))
