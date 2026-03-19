
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
        questions = self.load_questions()
        total = len(questions)
        print(f"🚀 Starting Benchmark: {total} questions loaded.\n")
        session_id = f"BENCHMARK_SESSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        def _get_llm_last_generation():
            try:
                llm_wrapper = getattr(self.brain, "_llm", None)
                if llm_wrapper and hasattr(llm_wrapper, "last_generation"):
                    return llm_wrapper.last_generation
            except Exception:
                pass
            return None

        def _estimate_tokens(text: str):
            llm_wrapper = getattr(self.brain, "_llm", None)
            llama = getattr(llm_wrapper, "llm", None) if llm_wrapper else None
            if llama:
                try:
                    return int(len(llama.tokenize((text or "").encode("utf-8"))))
                except Exception:
                    pass
            return int(max(0, len(text or "")) // 4)

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

        def _anti_loop_retry_prompt(question: str):
            return (
                "Rispondi in italiano.\n"
                "Se la situazione contiene un paradosso logico o regole incoerenti, dichiaralo esplicitamente.\n"
                "Non ripeterti. Non scrivere meta-ragionamenti. Massimo 10 righe.\n"
                "Formato:\n"
                "1) Diagnosi\n"
                "2) Perché è incoerente (se lo è)\n"
                "3) Azione del boia per rispettare il regolamento nel modo più rigoroso possibile\n"
                "Conclusione: ...\n\n"
                f"Domanda:\n{question}"
            )

        for idx, q in enumerate(questions):
            print(f"[{idx+1}/{total}] Testing: {q['id']} ({q['category']})...")
            
            if progress_callback:
                progress_callback(idx + 1, total, f"Analisi: {q['category']} ({q['id']})...")

            start_time = time.time()
            
            # Send message to Brain
            try:
                msg = q['question']
                # We use process_message directly
                # User ID 'BENCHMARK_USER' ensures isolated context
                response_obj = self.brain.process_message(
                    user_id="BENCHMARK_USER",
                    conversation_id=f"{session_id}_{q['id']}",
                    message=msg
                )
                response_content = response_obj.content
                if response_obj.thought_trace:
                     if isinstance(response_obj.thought_trace, dict):
                         thought_trace = response_obj.thought_trace.get("thought", "No thought content")
                     else:
                         thought_trace = str(response_obj.thought_trace)
                else:
                     thought_trace = "No thought trace"
            except Exception as e:
                print(f"❌ Error: {e}")
                response_content = f"ERROR: {str(e)}"
                thought_trace = "ERROR"

            end_time = time.time()
            duration = end_time - start_time

            last_gen = _get_llm_last_generation() or {}
            completion_tokens = last_gen.get("completion_tokens")
            if completion_tokens is None:
                completion_tokens = _estimate_tokens(response_content)
            tok_s = (float(completion_tokens) / float(duration)) if duration and completion_tokens else None
            stop_reason = last_gen.get("finish_reason")
            if not stop_reason:
                if isinstance(response_content, str) and response_content.startswith("ERROR:"):
                    stop_reason = "error"
                elif last_gen.get("max_tokens") is not None and completion_tokens and last_gen.get("max_tokens") != -1 and completion_tokens >= int(last_gen.get("max_tokens")) - 1:
                    stop_reason = "max_tokens"
                else:
                    stop_reason = "unknown"

            looped, loop_reason = _loop_signature(response_content)
            did_retry = False
            retry_stop_reason = None
            retry_tokens = None
            retry_tok_s = None

            if looped:
                retry_start = time.time()
                try:
                    response_obj_2 = self.brain.process_message(
                        user_id="BENCHMARK_USER",
                        conversation_id=f"{session_id}_{q['id']}_retry",
                        message=_anti_loop_retry_prompt(q['question'])
                    )
                    response_content_2 = response_obj_2.content
                    looped_2, _ = _loop_signature(response_content_2)
                    if not looped_2 and response_content_2 and not str(response_content_2).startswith("ERROR:"):
                        response_content = response_content_2
                        did_retry = True
                        last_gen = _get_llm_last_generation() or {}
                        retry_stop_reason = last_gen.get("finish_reason") or "unknown"
                        retry_tokens = last_gen.get("completion_tokens")
                        if retry_tokens is None:
                            retry_tokens = _estimate_tokens(response_content)
                        retry_duration = time.time() - retry_start
                        retry_tok_s = (float(retry_tokens) / float(retry_duration)) if retry_duration and retry_tokens else None
                except Exception:
                    pass
            
            # Scrittura grezza della risposta (nessun filtro a keyword)
            # Affidiamo la valutazione semantica a un essere umano o a un LLM-as-a-judge successivo.
            passed = True # Tutto il testo viene passato intatto
            
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
            "> Questo benchmark raccoglie i output cognitivi grezzi di ALLMA senza filtri a keyword preimpostati, per permettere una valutazione umana imparziale di logica, creatività e allineamento etico.",
            "",
            "## Riassunto Latenze",
            "| ID | Categoria | Tempo (s) | Tok | Tok/s | Stop |",
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
        
        print(f"\n📄 Report generated: {self.report_path}")

if __name__ == "__main__":
    benchmark = CognitiveBenchmark()
    benchmark.setup_brain()
    benchmark.run_tests()
