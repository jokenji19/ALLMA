"""Reproducible local comparison, deliberately separate from an intelligence score.

Run from any directory. Does not instantiate ALLMACore or read private app state.
"""
import argparse
import ast
import hashlib
import json
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from allma_model.emotional_system.emotion_analysis import analyze


def baseline_detector(ref):
    revision = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
    source = subprocess.check_output(['git', 'show', revision+':allma_model/emotional_system/emotional_core.py'], cwd=ROOT, text=True)
    tree = ast.parse(source)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'EmotionalCore')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_heuristic_detect_emotion')
    # Extract only the pure detector; do not initialize old models or storage.
    method.returns = None
    for arg in method.args.args:
        arg.annotation = None
    env = {'re': re, 'EmotionalState': SimpleNamespace}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<frozen-git-detector>', 'exec'), env)
    def detect(text):
        value = env['_heuristic_detect_emotion'](None, text)
        return vars(value) if value is not None else dict(primary_emotion='neutral', secondary_emotions={})
    return revision, hashlib.sha256(source.encode()).hexdigest(), detect


def labels(result):
    values = {result['primary_emotion'], *result.get('secondary_emotions', {})}
    return values - {'neutral'}


def score(rows, prediction):
    exact = sum(set(row['expected_families']) == set(row[prediction]) for row in rows)
    neutral = [row for row in rows if not row['expected_families']]
    mixed = [row for row in rows if len(row['expected_families']) > 1]
    false_positive = sum(bool(row[prediction]) for row in neutral)
    tp = sum(len(set(row['expected_families']) & set(row[prediction])) for row in rows)
    fp = sum(len(set(row[prediction])-set(row['expected_families'])) for row in rows)
    fn = sum(len(set(row['expected_families'])-set(row[prediction])) for row in rows)
    return dict(n=len(rows), exact=exact, exact_pct=100*exact/len(rows) if rows else None,
                micro_f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                false_positive_neutral=false_positive, neutral_n=len(neutral),
                mixed_exact=sum(set(row['expected_families']) == set(row[prediction]) for row in mixed),
                mixed_n=len(mixed))


def latency(detector, cases, repeats=100):
    for case in cases:
        detector(case['text'])
    samples = []
    for repeat in range(repeats):
        ordered = cases if repeat % 2 == 0 else cases[::-1]
        for case in ordered:
            start = time.perf_counter_ns()
            detector(case['text'])
            samples.append((time.perf_counter_ns()-start)/1e6)
    return dict(n=len(samples), mean_ms=statistics.mean(samples), median_ms=statistics.median(samples),
                p95_ms=sorted(samples)[int(.95*(len(samples)-1))])


def run(ref, output):
    dataset_path = ROOT/'benchmarks/evaluation/emotions_v1.json'
    dataset = json.loads(dataset_path.read_text())
    revision, old_hash, old = baseline_detector(ref)
    rows=[]
    for case in dataset['cases']:
        rows.append(dict(**case, before=sorted(labels(old(case['text']))), after=sorted(labels(analyze(case['text'])))))
    common = {'joy', 'sadness', 'fear', 'anger', 'surprise'}
    results = dict(baseline_revision=revision, baseline_file_sha256=old_hash,
        current_file_sha256=hashlib.sha256((ROOT/'allma_model/emotional_system/emotion_analysis.py').read_bytes()).hexdigest(),
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(), provenance=dataset['provenance'],
        scope='Pure local detectors on Mac, not response quality or Android performance',
        before=score(rows,'before'), after=score(rows,'after'),
        common_families_before=score([r for r in rows if set(r['expected_families'])<=common],'before'),
        common_families_after=score([r for r in rows if set(r['expected_families'])<=common],'after'),
        latency_before=latency(old,dataset['cases']), latency_after=latency(analyze,dataset['cases']),
        groups={g: dict(before=score([r for r in rows if r['group']==g],'before'), after=score([r for r in rows if r['group']==g],'after'))
                for g in sorted({r['group'] for r in rows})}, rows=rows)
    output.mkdir(parents=True,exist_ok=True)
    (output/'emotion-comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps({key: value for key,value in results.items() if key not in ('rows','groups')},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline', default='194e69c')
    parser.add_argument('--output', type=Path, default=ROOT/'benchmarks/evaluation/results')
    args=parser.parse_args()
    run(args.baseline,args.output)
