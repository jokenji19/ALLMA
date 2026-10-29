"""Wire decoding only. A chat's text is never decoded as another command."""
import json


def decode_poll(value):
    if not isinstance(value, str) or len(value) > 512 * 1024:
        raise ValueError('Invalid bridge payload')
    message = json.loads(value)
    # Existing controls serialize their envelopes before queueing them.
    # This is wire compatibility, never applied to a chat envelope's text.
    if isinstance(message, str):
        if message.lstrip().startswith('{'):
            try:
                envelope = json.loads(message)
            except ValueError:
                envelope = None
            if isinstance(envelope, dict):
                message = envelope
        if isinstance(message, str):
            return message
    if not isinstance(message, dict) or message.get('type') not in {'chat', 'action', 'system'}:
        raise ValueError('Invalid bridge envelope')
    if message['type'] == 'chat':
        if set(message) != {'type', 'text'} or not isinstance(message['text'], str):
            raise ValueError('Invalid chat envelope')
    elif not isinstance(message.get('action'), str):
        raise ValueError('Invalid action envelope')
    return message
