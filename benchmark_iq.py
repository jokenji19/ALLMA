
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

        for idx, q in enumerate(questions):
            print(f"[{idx+1}/{total}] Testing: {q['id']} ({q['category']})...")
            
            if progress_callback:
                progress_callback(idx + 1, total, f"Analisi: {q['category']} ({q['id']})...")

            start_time = time.time()
            
            # Send message to Brain
            try:
                # We use process_message directly
                # User ID 'BENCHMARK_USER' ensures isolated context
                response_obj = self.brain.process_message(
                    user_id="BENCHMARK_USER",
                    conversation_id="BENCHMARK_SESSION",
                    message=q['question']
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
            
            # Scrittura grezza della risposta (nessun filtro a keyword)
            # Affidiamo la valutazione semantica a un essere umano o a un LLM-as-a-judge successivo.
            passed = True # Tutto il testo viene passato intatto
            
            result_frame = {
                "id": q['id'],
                "category": q['category'],
                "question": q['question'],
                "response": response_content,
                "thought": thought_trace,
                "duration": duration
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
            "| ID | Categoria | Tempo (s) |",
            "|----|-----------|-----------|"
        ]
        
        avg_time = 0
        
        for r in self.results:
            lines.append(f"| {r['id']} | {r['category']} | {r['duration']:.2f} |")
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
            lines.append(f"\n**Risposta Finale Elaborata**:\n{r['response']}")
            lines.append("\n---")

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"\n📄 Report generated: {self.report_path}")

if __name__ == "__main__":
    benchmark = CognitiveBenchmark()
    benchmark.setup_brain()
    benchmark.run_tests()
