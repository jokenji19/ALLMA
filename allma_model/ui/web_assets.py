"""Offline CSS bundle for the Android WebView's synthetic HTTPS origin."""
import base64
import re
from pathlib import Path


def inline_stylesheets(html, asset_dir):
    """Preserve document stylesheet order and embed local font resources."""
    root = Path(asset_dir).resolve()

    def local_path(name):
        path = (root / name.split('?', 1)[0]).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Asset outside web directory')
        return path

    def font(match):
        name = match.group(1)
        data = base64.b64encode(local_path(name).read_bytes()).decode('ascii')
        return "url('data:font/woff2;base64," + data + "')"

    def sheet(match):
        tag = match.group(0)
        href = re.search(r'href=[\"\']([^\"\']+)[\"\']', tag, re.I)
        if not href:
            raise ValueError('Stylesheet without href')
        css = local_path(href.group(1)).read_text(encoding='utf-8')
        css = re.sub(r"url\(['\"]?(fonts/[^'\")]+\.woff2)['\"]?\)", font, css)
        return '<style>' + css + '</style>'

    return re.sub(r'<link[^>]+rel=[\"\']stylesheet[\"\'][^>]*>', sheet, html, flags=re.I)
