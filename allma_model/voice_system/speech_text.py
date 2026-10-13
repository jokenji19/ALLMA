"""Prepare displayed answers for speech without reading internal text or Markdown syntax."""
import html
import re


def spoken_text(text):
    text = re.sub(r'<think>.*?(?:</think>|$)', '', str(text or ''), flags=re.S | re.I)
    text = re.sub(r'\[\[.*?(?:\]\]|$)', '', text, flags=re.S)
    text = re.sub(r'```.*?(?:```|$)', ' Blocco di codice disponibile nella chat. ', text, flags=re.S)
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'(?m)^\s*(?:#{1,6}\s+|>\s*|[-*]\s+)', '', text)
    text = text.replace('**', '').replace('__', '').replace('`', '').replace('|', ', ')
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def speech_chunks(text, limit=3500):
    if limit < 1:
        raise ValueError('Speech chunk limit must be positive')
    parts = []
    while len(text) > limit:
        cut = max(text.rfind('. ', 0, limit), text.rfind('? ', 0, limit), text.rfind('! ', 0, limit))
        if cut > 0:
            cut += 1
        else:
            cut = text.rfind(' ', 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(text[:cut].strip())
        text = text[cut:].lstrip()
    if text.strip(): parts.append(text.strip())
    return parts
