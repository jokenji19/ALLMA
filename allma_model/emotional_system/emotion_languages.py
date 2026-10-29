"""Explicit ES/FR/DE lexical evidence; this is not universal emotion recognition.

The shared detector still checks subject, negation, time and uncertainty. Labels
retain the existing families so voice, personality and persisted state agree.
"""

LANGUAGES = ('it', 'en', 'es', 'fr', 'de')

EXTRA_LEXICON = {
    'joy': r'feliz|felices|alegr[ea]s?|heureu(?:x|se|ses)|content(?:e|es|s)?|glücklich|gluecklich|froh|fröhlich',
    'excitement': r'entusiasmado?s?|entusiasmadas?|emocionad[oa]s?|enthousiaste?s?|begeistert',
    'gratitude': r'agradecid[oa]s?|gracias|reconnaissant(?:e|es|s)?|merci|dankbar|danke',
    'pride': r'orgullos[oa]s?|fier|fière?s?|stolz',
    'love': r'enamorad[oa]s?|te quiero|te amo|amoureu(?:x|se)|je t.aime|verliebt|ich liebe dich',
    'relief': r'aliviad[oa]s?|soulagé(?:e|es|s)?|erleichtert',
    'sadness': r'tristes?|tristesse|traurig|unglücklich|ungluecklich',
    'loneliness': r'me siento sol[oa]|soledad|solitude|je me sens seul(?:e)?|einsam',
    'grief': r'duelo|deuil|trauer|ich trauere',
    'nostalgia': r'nostalgia|nostalgique|nostalgisch|sehnsucht',
    'disappointment': r'decepcionad[oa]s?|decepción|déçu(?:e|es|s)?|enttäuscht|enttaeuscht',
    'helplessness': r'desesperad[oa]s?|sin esperanza|désespéré(?:e|es|s)?|impuissant(?:e|es|s)?|hilflos|hoffnungslos',
    'guilt': r'culpable?s?|culpabilité|schuldig|schuldgefühle',
    'shame': r'avergonzad[oa]s?|vergüenza|honte|je me sens honteu(?:x|se)|ich schäme mich|beschämt',
    'anger': r'enfadad[oa]s?|enojad[oa]s?|furios[oa]s?|en colère|furieu(?:x|se)|wütend|wuetend|ärgerlich',
    'frustration': r'frustrad[oa]s?|frustré(?:e|es|s)?|frustriert',
    'annoyance': r'molest[oa]s?|agacé(?:e|es|s)?|énervé(?:e|es|s)?|genervt|gereizt',
    'jealousy': r'celos[oa]s?|jalou(?:x|se)|eifersüchtig|neidisch',
    'fear': r'miedo|asustad[oa]s?|peur|effrayé(?:e|es|s)?|angst|ängstlich|verängstigt',
    'anxiety': r'ansios[oa]s?|preocupad[oa]s?|inquiet(?:s|e|es)?|anxieu(?:x|se)|besorgt|nervös|nervoes',
    'insecurity': r'insegur[oa]s?|peu s[uû]r(?:e)? de moi|unsicher',
    'overwhelm': r'abrumad[oa]s?|débordé(?:e|es|s)?|submergé(?:e|es|s)?|überfordert|ueberfordert|überwältigt',
    'surprise': r'sorprendid[oa]s?|surpris(?:e|es)?|überrascht|ueberrascht',
    'confusion': r'confundid[oa]s?|perdu(?:e|es|s)?|désorienté(?:e|es|s)?|verwirrt|ratlos',
    'disgust': r'asquead[oa]s?|dégoûté(?:e|es|s)?|angewidert|ekel',
    'trust': r'confío|confiance|ich vertraue|vertrauen',
    'calm': r'tranquil[oa]s?|relajad[oa]s?|serein(?:e|es|s)?|détendu(?:e|es|s)?|ruhig|entspannt|gelassen',
    'hope': r'esperanzad[oa]s?|espoir|plein(?:e)? d.espoir|hoffnungsvoll|zuversichtlich',
    'curiosity': r'curios[oa]s?|curieu(?:x|se)|neugierig',
    'motivation': r'motivad[oa]s?|motivé(?:e|es|s)?|motivier(?:t|te)|entschlossen',
    'fatigue': r'cansad[oa]s?|agotad[oa]s?|fatigué(?:e|es|s)?|épuisé(?:e|es|s)?|müde|muede|erschöpft',
    'numbness': r'me siento vací[oa]|je me sens vide|ich fühle mich leer|gefühllos',
}

SELF_EXTRA = r'yo|estoy|soy|estaba|estuve|tengo|siento|me siento|je|j[’\x27](?:ai|étais)|moi|ich|mir|mich'
OTHER_EXTRA = (r'él|ella|ellos|ellas|tú|usted|mi (?:madre|padre|herman[oa]|amig[oa])|'
               r'il(?=\s+(?:est|était|se sent)\b)|elle|ils|elles|vous|mon (?:père|frère|ami)|ma (?:mère|sœur|soeur|amie)|'
               r'er|sie|du|mein(?:e)? (?:mutter|vater|bruder|schwester|freund|freundin)')
GENERIC_EXTRA = r'explica|explicar|define|definir|traduce|traducir|significa|palabra|escribe|expliquer|explique|définis|définir|traduis|traduire|signifie|mot|écris|erkläre|erklären|übersetze|übersetzen|bedeutet|wort|schreibe'
SCOPE_EXTRA = r'pero|sino|y|mais|et|aber|sondern|jedoch|und'
HYPOTHETICAL_EXTRA = r'si\s+(?:yo|estoy|estuviera|fuera|soy|je|j[’\x27])|cuando|quand|si jamais|wenn|falls|wäre|wäre ich'
PAST_EXTRA = r'ayer|antes|estaba|estuve|me sentía|hier|autrefois|avant|étais|était|gestern|früher|ich war|ich fühlte'
PRESENT_EXTRA = r'ahora|hoy|estoy|soy|me siento|maintenant|aujourd.hui|je suis|je me sens|jetzt|heute|ich bin|ich fühle'
UNCERTAIN_EXTRA = r'quizás?|tal vez|creo|peut.être|je crois|vielleicht|vermutlich|ich glaube'
NEGATIVE_EXTRA = r'nunca|jamás|sin|pas|plus|jamais|sans|nicht|nie|ohne|kein(?:e|en|em|er|es)?'
INTENSE_EXTRA = r'muy|muchísimo|muchisimo|très|tellement|extrêmement|sehr|äußerst'
MILD_EXTRA = r'un poco|un peu|ein wenig|etwas'


def ambiguous_usage(word, before, has_subject):
    """Polysemous additions require an affective construction or a subject.

    Do not turn English content, a lost key or a sporting duel into a feeling.
    This is deliberately conservative; unrecognized text stays uncertain.
    """
    import re
    if re.fullmatch(r'content(?:e|es|s)?', word):
        return not re.search(r'\b(?:je|tu|il|elle|nous|vous|ils|elles)\b.*\b(?:suis|es|est|sommes|êtes|sont|sens|sent)\b', before)
    if re.fullmatch(r'perdu(?:e|es|s)?', word):
        return not re.search(r'\b(?:suis|es|est|sens|sent|sentons|sentez)\b', before)
    if word in {'duelo', 'confiance', 'vertrauen', 'trauer', 'espoir'}:
        return not has_subject
    return False
