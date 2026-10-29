import sys
import os
import shutil
import time

# Add this dir to path
sys.path.append(os.getcwd())

from allma_model.core.module_state_manager import ModuleStateManager
from allma_model.core.meta_learner_lite import MetaLearnerLite
from allma_model.core.cognitive_tracker_lite import CognitiveTrackerLite
from allma_model.core.language_processor_lite import LanguageProcessorLite
from allma_model.incremental_learning.curiosity_system import CuriosityPrioritization

DB_PATH = "allma_modules.db"

def test_persistence():
    print("--- Testing Persistence ---")
    
    # 1. Clean previous DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Cleaned old DB")

    # 2. Instantiate and Modify - Session A
    print("\n[Session A] Initializing modules and changing state...")
    
    # MetaLearner
    meta = MetaLearnerLite()
    print(f"MetaLearner initial strategy: {meta.current_strategy}")
    meta.current_strategy = 'reflection' # Force change
    
    # We need to manually update usage/success to force save if we don't call update_success
    # But update_success calls save_state, so let's use that
    meta.strategies['reflection'].usage_count += 1
    meta.update_success('reflection', True) 
    print("MetaLearner: changed to reflection, success=True")

    # CognitiveTracker
    tracker = CognitiveTrackerLite()
    tracker.abilities['creativity'] = 0.9 # Force manual change base
    # update_ability calls save_state
    tracker.update_ability('creativity', True) 
    print("CognitiveTracker: set creativity base to 0.9, then updated")

    # Curiosity
    curiosity = CuriosityPrioritization()
    # update_topic_priority calls save_state
    curiosity.update_topic_priority('quantum_physics', {'emotional_intensity': 0.8})
    curiosity.archive_topic('ancient_history')
    print("Curiosity: added quantum_physics, archived ancient_history")
    
    # Language
    lang = LanguageProcessorLite()
    lang.add_positive_word('supercalifragilistich')
    print("Language: added custom word")

    # 3. Re-instantiate - Session B
    print("\n[Session B] Re-instantiating modules (simulating restart)...")
    
    # Force fresh instances
    meta_b = MetaLearnerLite()
    tracker_b = CognitiveTrackerLite()
    curiosity_b = CuriosityPrioritization()
    lang_b = LanguageProcessorLite()
    
    # 4. Verify
    print("\n--- Verification Results ---")
    
    # MetaLearner
    # current_strategy IS NOT SAVED explicitely in update_success unless we override _save_state logic?
    # Let's check _save_state in meta_learner_lite:
    # state = {'current_strategy': self.current_strategy, ...}
    # Yes, it saves self.current_strategy.
    success_meta = (
        meta_b.current_strategy == 'reflection' and 
        meta_b.strategies['reflection'].usage_count >= 1
    )
    print(f"MetaLearner Persisted: {success_meta} (Strategy={meta_b.current_strategy})")

    # CognitiveTracker
    # creativity was 0.9, updated (+increase) -> > 0.9
    success_tracker = tracker_b.abilities['creativity'] > 0.9
    print(f"CognitiveTracker Persisted: {success_tracker} (Creativity={tracker_b.abilities['creativity']})")
    
    # Curiosity
    success_curiosity = (
        'quantum_physics' in curiosity_b.topic_priorities and
        'ancient_history' in curiosity_b.archived_topics
    )
    print(f"Curiosity Persisted: {success_curiosity}")
    
    # Language
    success_lang = 'supercalifragilistich' in lang_b.positive_words
    print(f"Language Persisted: {success_lang}")
    
    all_passed = all([success_meta, success_tracker, success_curiosity, success_lang])
    if all_passed:
        print("\n✅ ALL TESTS PASSED: Systemic Amnesia Cured!")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Some states were not restored.")
        sys.exit(1)

if __name__ == "__main__":
    test_persistence()
