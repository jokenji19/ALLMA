from pathlib import Path
import re
import base64
from allma_model.ui.web_assets import inline_stylesheets


def test_android_document_contains_restyle_and_real_font_without_network():
    root = Path(__file__).resolve().parents[2] / 'assets/web'
    html = inline_stylesheets((root / 'index.html').read_text(), root)
    assert not re.search(r'<link[^>]+stylesheet', html)
    assert html.index('/* ALLMA · Cielo.') > html.index('/* Chat Container */')
    assert '.header-brand {' in html
    assert 'class="planet-logo"' not in html
    assert 'class="wordmark"' in html
    encoded = re.search(r'data:font/woff2;base64,([^\']+)', html).group(1)
    assert base64.b64decode(encoded) == (root / 'fonts/InterVariable.woff2').read_bytes()
    assert "url('fonts/" not in html
