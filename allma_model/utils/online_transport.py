"""Bounded transport for fixed, read-only providers."""
import json

from .generation_control import check_cancelled


def request_bytes(session, url, cancelled, allowed, *, params=None, headers=None, types, limit):
    check_cancelled(cancelled)
    if not allowed():
        return None
    with session.get(url, params=params, timeout=(3, 3), stream=True, allow_redirects=False,
                     headers={'Accept': ', '.join(types), **(headers or {})}) as response:
        if response.status_code != 200:
            raise ProviderError(response.status_code)
        if response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower() not in types:
            raise ValueError('Unexpected provider response type')
        data = bytearray()
        for chunk in response.iter_content(chunk_size=4096):
            check_cancelled(cancelled)
            if not allowed():
                return None
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError('Provider response exceeds limit')
        return bytes(data)


def request_json(session, url, cancelled, allowed, *, params=None, headers=None, limit=96 * 1024):
    data = request_bytes(session, url, cancelled, allowed, params=params, headers=headers,
                         types=('application/json',), limit=limit)
    if data is None:
        return None
    result = json.loads(data, parse_constant=lambda value: None)
    if not isinstance(result, dict):
        raise ValueError('Unexpected provider response')
    return result


class ProviderError(Exception):
    def __init__(self, status):
        self.status = status
        super().__init__('Provider unavailable')
