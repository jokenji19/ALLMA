"""Compare the same public questions using real sources and disposable settings."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
import time
import unicodedata
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from allma_model.utils.public_references import PublicReferences
from allma_model.utils.searx_research import SearxResearch
from allma_model.utils.web_search import compose_web_answer, search_query


def missing_markers(text, expected):
    def fold(value):
        letters = unicodedata.normalize('NFKD', value.casefold())
        return ' '.join(''.join(char for char in letters if not unicodedata.combining(char)).split())

    body = fold(text)
    missing = []
    for item in expected:
        alternatives = (item,) if isinstance(item, str) else item
        if not any(re.search(r'(?<!\w)' + re.escape(fold(value)) + r'(?!\w)', body)
                   for value in alternatives):
            missing.append(item)
    return missing


def evaluate(cases, *, use_companion):
    results = []
    with TemporaryDirectory() as folder:
        root = Path(folder)
        service = PublicReferences(root / 'test.db', root / 'web_access.json')
        service.configure(True, expanded=True)
        service.general_search = SearxResearch(use_companion=use_companion)
        for case in cases:
            query = search_query(case['query'], allow_symbols=True)
            started = time.monotonic()
            response = service.search_public_pages(
                case['query'], query, case['language'], case.get('fresh', False)) if query else {'status': 'not_applicable'}
            elapsed = round(time.monotonic() - started, 2)
            sources = compose_web_answer(query, response.get('results'), case.get('fresh', False),
                                         read_pages=True) if query else []
            missing = missing_markers(' '.join(source['excerpt'] for source in sources), case['expected'])
            expected_hosts = case.get('hosts', [])
            host_match = not expected_hosts or any(
                urlsplit(source['url']).hostname in expected_hosts for source in sources)
            outcome = ('no_evidence' if not sources else 'partial' if missing or not host_match
                       or response.get('coverage') == 'partial_scope' else 'markers_found')
            row = {'id': case['id'], 'language': case['language'], 'category': case.get('category'),
                   'status': response['status'], 'outcome': outcome,
                   'seconds': elapsed, 'missing_markers': missing, 'sources': sources}
            results.append(row)
            print(f"{row['id']:18s} {outcome:15s} {elapsed:5.2f}s  {response['status']}", flush=True)
    return {'companion_enabled': use_companion, 'summary': dict(Counter(row['outcome'] for row in results)),
            'results': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-companion', action='store_true')
    parser.add_argument('--cases', type=Path, default=ROOT / 'benchmarks/evaluation/internet_retrieval_v1.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    report = evaluate(cases, use_companion=args.with_companion)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False))


if __name__ == '__main__':
    main()
