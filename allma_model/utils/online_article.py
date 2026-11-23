"""Read only prose paragraphs from an already identified Wikimedia revision."""
from html.parser import HTMLParser


class ArticleParagraphs(HTMLParser):
    _SKIP = frozenset({'sup', 'script', 'style', 'table', 'nav', 'figure', 'math'})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self._blocked = []
        self._text = None

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._blocked.append(tag)
        elif not self._blocked and tag == 'p':
            self._text = []
        elif not self._blocked and tag == 'br' and self._text is not None:
            self._text.append(' ')

    def handle_endtag(self, tag):
        if self._blocked:
            if tag == self._blocked[-1]:
                self._blocked.pop()
            return
        if tag == 'p' and self._text is not None:
            text = ' '.join(''.join(self._text).split())
            self._text = None
            if 25 <= len(text) <= 6000 and len(self.paragraphs) < 1000:
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self._text is not None and not self._blocked:
            self._text.append(data)


def find_passage(html, request):
    if not isinstance(html, str):
        return None
    parser = ArticleParagraphs()
    parser.feed(html)
    parser.close()
    return next((text for paragraph in parser.paragraphs
                 if (text := request.article_passage(paragraph)) is not None), None)
