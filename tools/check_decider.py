"""Run the real local motor on synthetic probes, outside ALLMA personal state.

Usage: python tools/check_decider.py --model models/decider-0.8b/decider-0.8b-Q4_K_M.gguf
Requires the native llama-cpp-python runtime, no torch/transformers dependency.
"""
import argparse
import json
from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from allma_model.agency_system.decision_engine import LocalDecisionEngine
from allma_model.agency_system.decision_diagnostics import measure


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', default='/private/tmp/allma-decider-report.json')
    args = parser.parse_args()
    engine = LocalDecisionEngine(args.model)
    try:
        engine.load()
        result = measure(engine, threading.Event())
        Path(args.output).write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
    finally:
        engine.close()


if __name__ == '__main__':
    main()
