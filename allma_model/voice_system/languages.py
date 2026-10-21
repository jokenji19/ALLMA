"""Validated voice language preferences, independent from autobiographical memory."""
import re

LANGUAGES = {'it-IT': 'Italiano', 'en-US': 'English', 'fr-FR': 'Français',
             'de-DE': 'Deutsch', 'es-ES': 'Español', 'pt-BR': 'Português',
             'ja-JP': '日本語', 'ko-KR': '한국어', 'zh-CN': '中文',
             'ar-SA': 'العربية', 'hi-IN': 'हिन्दी', 'ru-RU': 'Русский',
             'nl-NL': 'Nederlands', 'pl-PL': 'Polski', 'tr-TR': 'Türkçe',
             'uk-UA': 'Українська'}
DEFAULT_TAGS = {tag.split('-')[0]: tag for tag in LANGUAGES}


def language_tag(value, fallback='it-IT'):
    """Keep BCP-47 languages from Android; never silently map unknowns to Italian."""
    if not isinstance(value, str):
        return fallback
    value = value.strip().replace('_', '-')
    if not re.fullmatch(r'[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8}){0,3}', value):
        return fallback
    parts = value.split('-')
    if len(parts) == 1:
        return DEFAULT_TAGS.get(value.lower(), value.lower())
    return '-'.join([parts[0].lower()] + [p.upper() if len(p) == 2 else p.title() if len(p) == 4 else p for p in parts[1:]])


def voice_options(value=None):
    value = value if isinstance(value, dict) else {}
    language = value.get('language', 'it-IT')
    if language != 'auto':
        language = language_tag(language)
    return {'language': language, 'allow_service_fallback': value.get('allow_service_fallback') is True,
            'voice': value.get('voice') if value.get('voice') in ('android', 'if_sara', 'im_nicola') else 'android'}
