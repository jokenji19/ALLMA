
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
             self.brain = ALLMACore(mobile_mode=False) 
             # Mock specific Android-only components
             self.brain.tts_engine = MagicMock()
             self.brain.vibrator = MagicMock()
             self.brain.audio_recorder = MagicMock()
             print("✅ Fresh Brain Initialized.")

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
                thought_trace = str(response_obj.thought_trace) if response_obj.thought_trace else "No thought trace"
            except Exception as e:
                print(f"❌ Error: {e}")
                response_content = f"ERROR: {str(e)}"
                thought_trace = "ERROR"

            end_time = time.time()
            duration = end_time - start_time
            
            # Analysis
            passed = self._evaluate_response(response_content, thought_trace, q['expected_keywords'])
            
            result_frame = {
                "id": q['id'],
                "category": q['category'],
                "question": q['question'],
                "response": response_content,
                "thought": thought_trace,
                "keywords_found": passed,
                "duration": duration
            }
            self.results.append(result_frame)
            print(f"   -> Result: {'✅ Match' if passed else '⚠️ No Keywords'} ({duration:.2f}s)\n")
            
            # Sleep briefly to let thermal cool (simulated)
            time.sleep(1)

        self._generate_report()

    def _evaluate_response(self, response, thought, keywords):
        # Check if any keyword matches
        full_text = (response + " " + thought).lower()
        matches = [k for k in keywords if k.lower() in full_text]
        return len(matches) > 0

    def _generate_report(self):
        lines = [
            "# 🧠 ALLMA Cognitive Benchmark Report",
            f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Total Questions**: {len(self.results)}",
            "",
            "## Summary",
            "| ID | Category | Keywords Matched | Time (s) |",
            "|----|----------|------------------|----------|"
        ]
        
        avg_time = 0
        pass_count = 0
        
        for r in self.results:
            status = "✅" if r['keywords_found'] else "⚠️"
            lines.append(f"| {r['id']} | {r['category']} | {status} | {r['duration']:.2f} |")
            avg_time += r['duration']
            if r['keywords_found']: pass_count += 1
            
        avg_time /= len(self.results) if self.results else 1
        
        lines.append("")
        lines.append(f"**Average Latency**: {avg_time:.2f}s")
        lines.append(f"**Keyword Pass Rate**: {pass_count}/{len(self.results)}")
        lines.append("")
        lines.append("## Detailed Responses")
        
        for r in self.results:
            lines.append(f"### {r['id']}: {r['question']}")
            formatted_thought = r['thought'].replace('\n', '\n> ')
            lines.append(f"**Thought Trace**:\n>{formatted_thought}")
            lines.append(f"\n**Response**:\n{r['response']}")
            # Safe access to keywords
            expected = "N/A"
            for q in self.load_questions():
                if q['id'] == r['id']:
                    expected = ", ".join(q['expected_keywords'])
                    break
            lines.append(f"\n*Expected keywords*: {expected}") 
            lines.append("\n---")

        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"\n📄 Report generated: {self.report_path}")

if __name__ == "__main__":
    benchmark = CognitiveBenchmark()
    benchmark.setup_brain()
    benchmark.run_tests()
