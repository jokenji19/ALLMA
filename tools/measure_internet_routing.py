"""Measure Internet routing with synthetic prompts and transport spies.

Each turn starts with an empty cache. No prompt leaves the process. Expected
topics describe when the configured public sources could be useful, not
whether those sources can actually answer the question.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from allma_model.utils.public_references import PublicReferences


def evaluate(cases):
    rows = []
    for case in cases:
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            spy = Mock()
            spy.fetch.return_value = []
            service = PublicReferences(folder / 'cache.sqlite', folder / 'consent.json', spy)
            service.nasa_reader = service.esa_reader = spy
            if case['enabled']:
                service.configure(True)
            result = service.lookup(case['message'], anchor=case['anchor'])
            queries = [call.args[0] for call in spy.fetch.call_args_list]
            expected = case['topic']
            if expected is None:
                outcome = 'unnecessary' if queries else 'correct_local'
            elif not queries:
                outcome = 'missed'
            elif all(query.casefold() == expected.casefold() for query in queries):
                outcome = 'correct_search'
            else:
                outcome = 'wrong_topic'
            rows.append({**case, 'status': result['status'], 'queries': queries, 'outcome': outcome})
    summaries = {}
    for label in ('all', 'development', 'holdout'):
        group = [row for row in rows if label == 'all' or row['split'] == label]
        if group:
            summaries[label] = dict(Counter(row['outcome'] for row in group))
    return {'summaries': summaries, 'cases': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--split', choices=('all', 'development', 'holdout'), default='all')
    args = parser.parse_args()
    cases = json.loads((ROOT / 'benchmarks/evaluation/internet_routing_v1.json').read_text())
    report = evaluate(case for case in cases if args.split == 'all' or case['split'] == args.split)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['summaries'], ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
