from pathlib import Path
import re
import base64
from allma_model.ui.web_assets import inline_stylesheets


def test_android_document_contains_restyle_and_real_font_without_network():
    root = Path(__file__).resolve().parents[2] / 'assets/web'
    html = inline_stylesheets((root / 'index.html').read_text(), root)
    assert not re.search(r'<link[^>]+stylesheet', html)
    assert html.index('/* ALLMA · Paper.') > html.index('/* Chat Container */')
    assert '.header-brand {' in html
    assert 'class="planet-logo"' not in html
    assert 'class="wordmark"' in html
    encoded = re.search(r'data:font/woff2;base64,([^\']+)', html).group(1)
    assert base64.b64decode(encoded) == (root / 'fonts/InterVariable.woff2').read_bytes()
    assert "url('fonts/" not in html
    image = re.search(r'data:image/png;base64,([^\"]+)', html).group(1)
    assert base64.b64decode(image) == (root/'images/startup-connection.png').read_bytes()
    assert 'src="startup_transition.js"' in html
    bridge=(root.parents[1]/'allma_model/ui/webview_bridge.py').read_text()
    assert "os.path.join(base_path, 'startup_transition.js')" in bridge


def test_brain_explorer_is_offline_and_only_wordmark_opens_it():
    root=Path(__file__).resolve().parents[2]/'assets/web'
    html=(root/'index.html').read_text()
    bundled=inline_stylesheets(html,root)
    assert 'id="brain-open" class="wordmark"' in html
    assert html.count('onclick="brainView.open()"')==1
    assert 'id="brain-explorer"' in html and 'aria-modal="true"' in html
    assert 'id="brain-stop" hidden onpointerdown="armCancelGeneration()"' in html
    assert '/* ALLMA · a quiet observatory' in bundled
    js=(root/'brain_view.js').read_text()
    assert 'fetch(' not in js and 'https://' not in js
    assert 'cancelAnimationFrame' in js and 'visibilitychange' in js
    bridge=(root.parents[1]/'allma_model/ui/webview_bridge.py').read_text()
    assert "'brain_view.js'" in bridge


def test_brain_opens_directly_without_loading_the_retired_portrait():
    root=Path(__file__).resolve().parents[2]/'assets/web'
    html=(root/'index.html').read_text()
    assert 'id="brain-anatomy-canvas"' in html
    assert 'id="avatar-setup"' not in html and 'id="avatar-canvas"' not in html
    assert 'src="avatar_mesh.js"' not in html and 'src="avatar_view.js"' not in html
    assert html.index('src="brain_geometry.js"')<html.index('src="brain_anatomy.js"')<html.index('src="brain_view.js"')
    bridge=(root.parents[1]/'allma_model/ui/webview_bridge.py').read_text()
    assert "os.path.join(base_path, 'brain_anatomy.js')" in bridge
    assert bridge.index("os.path.join(base_path, 'brain_geometry.js')")<bridge.index("os.path.join(base_path, 'brain_anatomy.js')")
    assert "os.path.join(base_path, 'avatar_mesh.js')" not in bridge
    assert "os.path.join(base_path, 'avatar_view.js')" not in bridge
    js=(root/'brain_anatomy.js').read_text()
    assert 'fetch(' not in js and 'https://' not in js
    assert (root/'brain_anatomy.js').stat().st_size<25000
    assert (root/'brain_geometry.js').stat().st_size<300000
    assert 'BSD-3-Clause' in (root/'licenses/brain-geometry.txt').read_text()
