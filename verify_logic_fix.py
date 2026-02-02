import sys
import os

# Add this dir to path
sys.path.append(os.getcwd())

from allma_model.incremental_learning.emotional_adaptation_system import EmotionalAdaptationSystem, EmotionalState
from allma_model.incremental_learning.curiosity_system import UnknownConceptDetector

def test_emotional_logic():
    print("\n--- Testing Emotional Logic ---")
    emotional_system = EmotionalAdaptationSystem()
    
    # 1. Test Valence Calculation
    # Case A: High Intensity Anger -> Should be LOW valence (negative)
    # Old logic: sigmoid(0.9) -> ~0.7 (positive) -> WRONG
    # New logic: base(anger=0.2) - (0.9 * 0.2) + clamp -> ~0.02 -> CORRECT
    
    # We need to simulate passing features. 
    # The adapt_to_emotion method expects an object with 'intensity' and 'primary_emotion'
    class MockFeatures:
        def __init__(self, intensity, emotion_type):
            self.intensity = intensity
            self.primary_emotion = emotion_type
            self.complexity = 0.5

    features_anger = MockFeatures(0.9, 'anger')
    state_anger = emotional_system.adapt_to_emotion(features_anger)
    
    print(f"High Intensity Anger (0.9): Valence = {state_anger.valence:.2f}")
    if state_anger.valence < 0.4:
        print("✅ Correct: Anger correctly mapped to negative valence.")
    else:
        print(f"❌ FAILED: Anger mapped to positive valence ({state_anger.valence})")
        return False

    # Case B: High Intensity Joy
    features_joy = MockFeatures(0.9, 'joy')
    state_joy = emotional_system.adapt_to_emotion(features_joy)
    print(f"High Intensity Joy (0.9): Valence = {state_joy.valence:.2f}")
    if state_joy.valence > 0.6:
        print("✅ Correct: Joy correctly mapped to positive valence.")
    else:
        print("❌ FAILED: Joy mapped to low valence.")
        return False
        
    # 2. Test Response Variety
    print("\n--- Testing Response Library ---")
    # Sample 20 responses for sadness to curb repetition
    responses = set()
    mock_state = {'primary_emotion': 'sadness'}
    for _ in range(20):
        responses.add(emotional_system.generate_response(mock_state))
    
    print(f"Unique responses for Sadness in 20 tries: {len(responses)}")
    if len(responses) > 5:
         print("✅ Correct: Response library is expanded.")
    else:
         print("❌ FAILED: Response library seems limited.")
         return False
         
    return True

def test_curiosity_logic():
    print("\n--- Testing Curiosity Logic ---")
    detector = UnknownConceptDetector()
    
    # Test Sentence: "Corro velocemente verso il Supercalifragilistichespiralidoso per programmare."
    # Expectations:
    # - "Corro" -> Common/short
    # - "velocemente" -> ignored (mente)
    # - "verso" -> common
    # - "il" -> stopword
    # - "Supercalifragilistichespiralidoso" -> Unknown (Long > 9)
    # - "per" -> stopword
    # - "programmare" -> ignored (are - verb)
    
    text = "Corro velocemente verso il Supercalifragilistichespiralidoso per programmare."
    concepts = detector.detect_unknown_concepts(text)
    
    print(f"Input: '{text}'")
    print(f"Detected Concepts: {concepts}")
    
    success = True
    
    if "velocemente" in concepts:
        print("❌ FAILED: 'velocemente' was flagged (Adverb filter failed)")
        success = False
    else:
        print("✅ 'velocemente' correctly ignored.")
        
    if "programmare" in concepts:
        print("❌ FAILED: 'programmare' was flagged (Verb filter failed)")
        success = False
    else:
        print("✅ 'programmare' correctly ignored.")
        
    if "supercalifragilistichespiralidoso" in concepts:
        print("✅ 'Supercalifragilistichespiralidoso' correctly detected.")
    else:
        print("❌ FAILED: Long unknown word NOT detected.")
        success = False
        
    return success

if __name__ == "__main__":
    emotional_pass = test_emotional_logic()
    curiosity_pass = test_curiosity_logic()
    
    if emotional_pass and curiosity_pass:
        print("\n✅ LOGIC FIX VERIFIED!")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED")
        sys.exit(1)
