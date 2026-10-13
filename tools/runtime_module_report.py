"""Exercise registered adapters with isolated storage; no model inference or user data."""
import json
import os
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def run_report():
    from allma_model.core.allma_core import ALLMACore
    previous = os.getcwd()
    with tempfile.TemporaryDirectory(prefix='allma-module-audit-') as directory:
        core = None
        try:
            os.chdir(directory)
            core = ALLMACore(mobile_mode=True, db_path=str(Path(directory) / 'core.db'))
            scenarios = [
                ('neutral', 'Ciao', 'statement', 'neutral'),
                ('emotional', 'Mi sento triste', 'emotional', 'sadness'),
                ('creative', 'Inventa una poesia sul mare', 'request', 'neutral'),
                ('planning', 'Pianifica il progetto della bicicletta', 'request', 'neutral'),
            ]
            turns = []
            for name, text, intent, emotion in scenarios:
                result = core.module_orchestrator.process(text, {
                    'intent': intent, 'user_id': 'audit_user', 'conversation_id': 'audit_session',
                    'emotional_state': {'primary_emotion': emotion, 'intensity': .7},
                }, intent=intent)
                turns.append({'scenario': name, **result['execution_report']})
            return {
                'scope': 'Registered adapters only, isolated temporary database. No native model, phone, quality evaluation or proof of all project modules.',
                'registered_count': len(core.module_orchestrator.modules),
                'stats': core.module_orchestrator.get_stats(), 'turns': turns,
            }
        finally:
            if core is not None:
                core.close()
            os.chdir(previous)


if __name__ == '__main__':
    output = Path(sys.argv[1]).resolve()
    report = run_report()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    failed = {name for turn in report['turns'] for name, outcome in turn['outcomes'].items()
              if outcome['status'] == 'failed'}
    print(json.dumps({'registered': report['registered_count'], 'failed': sorted(failed), 'output': str(output)}))
    sys.exit(bool(failed))
