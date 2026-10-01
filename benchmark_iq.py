
import os
import sys
import json
import time
import re
import unittest
from datetime import datetime
from unittest.mock import MagicMock

# --- MOCKING ANDROID CONTEXT ---
# Since we are running on macOS (desktop), we need to mock Android modules
try:
    import jnius
except ImportError:
    sys.modules['jnius'] = MagicMock()
    sys.modules['jnius'].autoclass = MagicMock()

try:
    import plyer
except ImportError:
    sys.modules['plyer'] = MagicMock()
    sys.modules['plyer'].vibrator = MagicMock()

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# --- IMPORT ALLMA CORE ---
# Adjust path if script is simple at root or sub
sys.path.append(os.getcwd()) # Ensure root is in path
from allma_model.core.allma_core import ALLMACore

class CognitiveBenchmark:
    def __init__(self, db_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        if db_path is None:
            self.db_path = os.path.join(base_dir, "benchmarks", "questions_db.json")
        else:
            self.db_path = db_path
            
        self.results = []
        self.brain = None
        
        reports_dir = os.path.join(base_dir, "benchmarks", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        self.report_path = os.path.join(reports_dir, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")

    def setup_brain(self, existing_brain=None):
        print("🧠 Initializing ALLMA Benchmark Context...")
        if existing_brain:
             self.brain = existing_brain
             state_db = getattr(existing_brain, 'db_path', None)
             if isinstance(state_db, (str, os.PathLike)):
                 reports_dir = os.path.join(os.path.dirname(os.path.abspath(state_db)), 'benchmarks', 'reports')
                 os.makedirs(reports_dir, exist_ok=True)
                 self.report_path = os.path.join(reports_dir, os.path.basename(self.report_path))
             print("✅ Using existing Brain instance.")
        else:
             # Initialize Core with expert settings
             # FORCE MOBILE MODE TO USE LOCAL GGUF PATHS
             self.brain = ALLMACore(mobile_mode=True) 
             # Mock specific Android-only components
             self.brain.tts_engine = MagicMock()
             self.brain.vibrator = MagicMock()
             self.brain.audio_recorder = MagicMock()
             print("✅ Fresh Brain Initialized (Mobile Mode).")

    def load_questions(self):
        with open(self.db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("tests", [])

    def run_tests(self, progress_callback=None):
        self.results = []
        questions = self.load_questions()
        total = len(questions)
        print(f"🚀 Starting Benchmark: {total} questions loaded.\n")
        session_id = f"BENCHMARK_SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        def _loop_signature(text: str):
            t = (text or "").strip().lower()
            if not t:
                return False, None
            t = re.sub(r"\s+", " ", t)
            if len(t) < 240:
                return False, None
            tail = t[-220:]
            head = t[:-220]
            if tail and tail in head:
                return True, "tail_repeated"
            parts = re.split(r"(?<=[\.\!\?])\s+|\n+", t)
            seen = {}
            repeats = 0
            for p in parts:
                p = p.strip()
                if len(p) < 22:
                    continue
                seen[p] = seen.get(p, 0) + 1
                if seen[p] == 3:
                    repeats += 1
            if repeats > 0:
                return True, "sentence_repeat"
            return False, None

        for idx, q in enumerate(questions):
            print(f"[{idx+1}/{total}] Testing: {q['id']} ({q['category']})...")
            
            if progress_callback:
                progress_callback(idx + 1, total, f"Analisi: {q['category']} ({q['id']})...")

            start_time = time.perf_counter()
            
            response_obj = None
            # Send message to Brain
            try:
                msg = q['question']
                # We use process_message directly
                # Dedicated user scope; persisted benchmark history is not a fresh controlled state.
                response_obj = self.brain.process_message(
                    user_id="BENCHMARK_USER",
                    conversation_id=f"{session_id}_{q['id']}",
                    message=msg, context={'disable_answer_recall': True}
                )
                response_content = response_obj.content
                if response_obj.thought_trace:
                     if isinstance(response_obj.thought_trace, dict):
                         thought_trace = response_obj.thought_trace.get("thought", "No thought content")
                     else:
                         thought_trace = str(response_obj.thought_trace)
                else:
                     thought_trace = "Non raccolto dal report; non indica assenza di ragionamento."
            except Exception as e:
                print(f"❌ Error: {e}")
                response_content = f"ERROR: {str(e)}"
                thought_trace = "ERROR"

            end_time = time.perf_counter()
            duration = end_time - start_time

            metadata = getattr(response_obj, 'metadata', None) or {}
            last_gen = metadata.get('generation', {})
            completion_tokens = last_gen.get('completion_tokens')
            tok_s = (completion_tokens / duration) if duration and completion_tokens is not None else None
            stop_reason = last_gen.get('finish_reason', 'not_measured')
            looped, loop_reason = _loop_signature(response_content)
            did_retry = False
            retry_stop_reason = retry_tokens = retry_tok_s = None

            result_frame = {
                "id": q['id'],
                "category": q['category'],
                "question": q['question'],
                "response": response_content,
                "thought": thought_trace,
                "duration": duration,
                "completion_tokens": completion_tokens,
                "tok_s": tok_s,
                "max_new_tokens": last_gen.get("max_tokens"),
                "stop_reason": stop_reason,
                "generation": last_gen,
                "status": last_gen.get('status', 'error' if response_content.startswith('ERROR:') else 'not_measured'),
                "anti_loop_triggered": bool(looped),
                "anti_loop_reason": loop_reason,
                "anti_loop_retry": bool(did_retry),
                "anti_loop_retry_stop_reason": retry_stop_reason,
                "anti_loop_retry_tokens": retry_tokens,
                "anti_loop_retry_tok_s": retry_tok_s,
            }
            self.results.append(result_frame)
            print(f"   -> Result: Elaborato ({duration:.2f}s)\n")
            
            # Sleep briefly to let thermal cool (simulated)
            time.sleep(1)

        self._generate_report()

    def _generate_report(self):
        lines = [
            "# 🧠 ALLMA V5 Semantic Cognitive Benchmark Report",
            f"**Data Esecuzione**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Domande Totali**: {len(self.results)}",
            "",
            "> Una richiesta per domanda attraverso la pipeline ALLMA, senza retry o riscritture del benchmark. Le risposte includono i controlli della pipeline; la qualità richiede valutazione umana. Tok/s end-to-end include l’intera elaborazione. Metriche mancanti non vengono stimate.",
            "",
            "## Riassunto Latenze",
            "| ID | Categoria | Tempo (s) | Tok | Tok/s end-to-end | Stop |",
            "|----|-----------|-----------|-----|-------|------|"
        ]
        
        avg_time = 0
        
        for r in self.results:
            tok = r.get("completion_tokens")
            tok_s = r.get("tok_s")
            stop = r.get("stop_reason")
            tok_cell = f"{tok}" if tok is not None else "-"
            tok_s_cell = f"{tok_s:.2f}" if isinstance(tok_s, (int, float)) else "-"
            stop_cell = stop if stop else "-"
            lines.append(f"| {r['id']} | {r['category']} | {r['duration']:.2f} | {tok_cell} | {tok_s_cell} | {stop_cell} |")
            avg_time += r['duration']
            
        avg_time /= len(self.results) if self.results else 1
        
        lines.append("")
        lines.append(f"**Latenza Media per Risposta**: {avg_time:.2f}s")
        lines.append("")
        lines.append("## Risposte Dettagliate per Valutazione Umana")
        
        for r in self.results:
            lines.append(f"### [{r['id']}] Domanda: {r['question']}")
            formatted_thought = r['thought'].replace('\n', '\n> ')
            lines.append(f"**Flusso di Coscienza (Thought Trace)**:\n>{formatted_thought}")
            lines.append("")
            lines.append("**Metriche**:")
            lines.append(f"- completion_tokens: {r.get('completion_tokens')}")
            lines.append(f"- tok/s: {r.get('tok_s')}")
            lines.append(f"- max_new_tokens: {r.get('max_new_tokens')}")
            lines.append(f"- stop_reason: {r.get('stop_reason')}")
            lines.append(f"- status: {r.get('status')}")
            for key, value in r.get('generation', {}).items():
                lines.append(f"- {key}: {value}")
            if r.get("anti_loop_triggered"):
                lines.append(f"- anti_loop_triggered: True ({r.get('anti_loop_reason')})")
                lines.append(f"- anti_loop_retry: {r.get('anti_loop_retry')}")
                if r.get("anti_loop_retry"):
                    lines.append(f"- anti_loop_retry_tokens: {r.get('anti_loop_retry_tokens')}")
                    lines.append(f"- anti_loop_retry_tok/s: {r.get('anti_loop_retry_tok_s')}")
                    lines.append(f"- anti_loop_retry_stop_reason: {r.get('anti_loop_retry_stop_reason')}")
            lines.append(f"\n**Risposta Finale Elaborata**:\n{r['response']}")
            lines.append("\n---")

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        with open(os.path.splitext(self.report_path)[0] + '.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Report generated: {self.report_path}")

if __name__ == "__main__":
    benchmark = CognitiveBenchmark()
    benchmark.setup_brain()
    benchmark.run_tests()
