"""Recognize bounded public identity questions in the chat's supported languages."""
import re
import unicodedata


_IDENTITY_FORMS = {
    'it': r"(?:chi (?:era|fu|[èé]|erano|sono|furono)|(?:invece )?conosci)\s+(.+)",
    'en': r"who (?:is|are|was|were)\s+(.+)",
    'es': r"qui[eé]n(?:es)? (?:es|era|fue|son|eran|fueron)\s+(.+)",
    'fr': r"qui (?:est|était|sont|étaient)\s*[- ]\s*(.+)",
    'de': r"wer (?:ist|war|sind|waren)\s+(.+)",
    'pt': r"quem (?:é|era|foi|são|eram|foram)\s+(.+)",
    'ru': r"кто (?:такой |такая |такие |это )?(.+)",
    'ar': r"من\s+(?:هو|هي|كان|كانت|هم)\s+(.+)",
    'zh': r"(?:[谁誰]是\s*(.+)|(.+?)\s*(?:是[谁誰]|是什[么麼]人)(?:呢|呀)?)",
    'ja': r"(.+?)(?:とは|は)\s*誰(?:ですか|でしょうか|なの|です|だ)?",
}
WIKIPEDIA_EDITIONS = frozenset(_IDENTITY_FORMS)
_IDENTITY = {language: re.compile(pattern, re.I) for language, pattern in _IDENTITY_FORMS.items()}

_PRIVATE_TOPICS = {
    'es': r"\b(?:yo|mi|mis|tu|tus|nuestr\w*|contraseña|domicilio|paciente)\b",
    'fr': r"\b(?:moi|mon|ma|mes|ton|ta|tes|notre|nos|mot de passe|domicile|patient)\b",
    'de': r"\b(?:ich|mein\w*|dein\w*|unser\w*|passwort|wohnadresse|patient\w*)\b",
    'pt': r"\b(?:eu|meu|minha|meus|minhas|teu|tua|noss\w*|senha|endereço|paciente)\b",
    'ru': r"\b(?:я|мо[йяеиё]\w*|тво\w*|ваш\w*|наш\w*|пароль|адрес|пациент\w*)\b",
    'ar': r"(?:^|\s)(?:أنا|أنت|جاري|جارتي|صديقي|صديقتي|طبيبي|أخي|أختي|أبي|أمي|زوجي|زوجتي|عنواني|كلمة المرور)(?=\s|$)|(?:لي|لديك|عندي)$",
    'zh': r"我的|我们的|我們的|你[们們]?的|我家|[邻鄰]居|[密秘]码|密碼|患者|^我$",
    'ja': r"私の|僕の|俺の|あなたの|自分の|わたしの|隣人|パスワード|患者|^(?:私|僕|俺|あなた)$",
}
_PRIVATE = {language: re.compile(pattern, re.I) for language, pattern in _PRIVATE_TOPICS.items()}
_LOCAL_ONLY = re.compile(
    r"\b(?:sin (?:internet|buscar|consultar)|no (?:busques|consultes)|"
    r"sans (?:internet|recherche|consulter)|ne (?:cherche|consulte) pas|"
    r"ohne (?:internet|suche|recherche)|(?:suche|such) nicht|"
    r"sem (?:internet|pesquisar|consultar)|não (?:pesquise|busque|consulte)|"
    r"без (?:интернета|поиска)|не (?:ищи|искать))\b|"
    r"(?:لا (?:تبحث|تستخدم الإنترنت)|دون (?:بحث|إنترنت)|"
    r"(?:不要|别|別|无需|無需|不必)(?:上网|上網|联网|聯網|搜索|搜尋|查网|查網)|"
    r"(?:ネット|ウェブ|Web|インターネット)(?:を使わず|は使わない|で検索しない|で調べない)|"
    r"検索(?:しない|せず))", re.I)


def identity_question(message):
    """Return language and subject text. Topic admission is a separate check."""
    text = unicodedata.normalize('NFKC', message or '').strip(' \t¿¡?؟!.。')
    for language, pattern in _IDENTITY.items():
        match = pattern.fullmatch(text)
        if match:
            return language, next(group for group in match.groups() if group is not None)
    return None


def private_identity_topic(language, text):
    pattern = _PRIVATE.get(language)
    if pattern is None:
        return False
    if language == 'ar':
        text = ''.join(char for char in text if not unicodedata.combining(char))
    return bool(pattern.search(text))


def multilingual_local_only(message):
    return bool(_LOCAL_ONLY.search(message))
