"""Detect claimed external verification when no source tool ran.

This gate does not decide whether a historical/scientific fact is true.
Ordinary attribution and quoted/code text are not a claim of performed checking.
"""
import re


def unbacked_source_claim(text):
    # Open quotations are buffered during streaming too; do not reject a
    # legitimate quotation before the closing character has arrived.
    plain = re.sub(r'```.*?(?:```|$)|"[^"\n]*(?:"|$)|«[^»]*(?:»|$)|“[^”]*(?:”|$)', '', text, flags=re.S)
    plain = re.sub(r'[*_]', '', plain)
    matches = re.finditer(
        r'\b(?:ho (?:verificato|consultato|controllato|cercato) (?:le |delle |su )?(?:fonti|internet|il web|online)|'
        r'(?:informazioni|dati|affermazioni|notizie)(?:\s+\w+){0,5}\s+(?:sono|risultano)\s+'
        r'(?:state\s+)?(?:confermat[ei]|verificat[ei])\s+da(?:lle)?\s+(?:fonti|ricerche)|'
        r'(?:fonti|ricerche)\s+(?:storiche\s+)?(?:che ho|da me)\s+(?:consultat[eo]|verificat[eo]))\b',
        plain, re.I)
    return any(not re.search(r'\bnon\b', match[0], re.I)
               and not re.search(r'\bnon\s+(?:(?:è|e)\s+vero\s+che\s+)?$',
                                 plain[max(0,match.start()-40):match.start()], re.I)
               for match in matches)
