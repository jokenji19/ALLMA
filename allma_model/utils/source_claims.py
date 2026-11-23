"""Detect claimed external verification when no source tool ran.

This gate does not decide whether a historical/scientific fact is true.
Ordinary attribution and quoted/code text are not a claim of performed checking.
"""
import re

_WEATHER_NUMBER = r'[+−-]?\d{1,3}(?:[,.]\d{1,2})?\s*(?:°\s*[CF]|gradi\b)'
_WEATHER_REPORT = re.compile(
    rf'\b(?:percepit[ioa]|temperatura apparente)\s+(?:di\s+)?{_WEATHER_NUMBER}|'
    rf'(?:^|[.?!]\s+)\s*(?:a|ad|in)\s+[^\n.!?]{{1,95}}?,\s+'
    rf'(?:(?:(?:cielo |prevalentemente |parzialmente )?(?:sereno|nuvoloso|coperto)|nebbia|pioggia|neve)\s+e\s+{_WEATHER_NUMBER}|'
    rf'{_WEATHER_NUMBER}(?=\s*(?:[.!?]|$))|previsione per (?:il|oggi|domani)\b)|'
    rf'\b(?:oggi|adesso|in questo momento|attualmente|domani)\b[^\n.!?]{{0,110}}'
    rf'\b(?:temperatura|vento|sereno|nuvolos[oa]|pioggia|meteo|ci sono|ci saranno)\b[^\n.!?]{{0,55}}{_WEATHER_NUMBER}',
    re.I,
)
_SOURCE_LABEL = r'(?:font[ei]|sources?|fuentes?|quellen?|fontes|источник|المصدر|来源|來源|出典)'
_CITATION_LABEL = re.compile(rf'(?:^|\n)\s*{_SOURCE_LABEL}\s*[:：]\s*\S'
                             rf'|\[\s*{_SOURCE_LABEL}\s*[:：]', re.I)


def unbacked_source_claim(text):
    # Open quotations are buffered during streaming too; do not reject a
    # legitimate quotation before the closing character has arrived.
    plain = re.sub(r'```.*?(?:```|$)|`[^`\n]*(?:`|$)|"[^"\n]*(?:"|$)|«[^»]*(?:»|$)|“[^”]*(?:”|$)', '', text, flags=re.S)
    plain = re.sub(r'[*_]', '', plain)
    if _WEATHER_REPORT.search(plain) or _CITATION_LABEL.search(plain):
        return True
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
