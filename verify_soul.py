
import sys
import os
import time
import logging
from datetime import datetime

# Add current dir to path to find modules
sys.path.append(os.getcwd())

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_soul():
    print("🔮 Testing ALLMA Soul System (Project Anima)...")
    
    try:
        from allma_model.core.soul.soul_core import SoulCore
        soul = SoulCore()
    except ImportError as e:
        print(f"❌ Failed to import SoulCore: {e}")
        return

    print(f"✨ Initial State: Energy={soul.state.energy:.2f}, Stability={soul.state.stability:.2f}")
    print(f"🕒 Current Biology Hour: {datetime.now().hour}")
    
    print("\n⏳ Simulating Time Passage (Pulse)...")
    for i in range(3):
        soul.pulse()
        print(f"   ❤️ Pulse {i+1}: Energy={soul.state.energy:.3f}, Stability={soul.state.stability:.3f}")

    print("\n⚡ Simulating Stimulus (Perceive)...")
    print("   -> Perceiving JOY (Direct)")
    soul.perceive(stimulus_valence=0.8, stimulus_arousal=0.8)
    print(f"   🌊 Post-Perceive: Energy={soul.state.energy:.3f}")
    
    print("\n💭 Simulating Emotional Echo (Resonance)...")
    print("   -> Resonating with 'Old Sad Memory' (Echo)")
    # Should lower energy slightly but less than direct perception
    soul.resonate("sadness", confidence=0.8)
    print(f"   🌊 Post-Resonance: Energy={soul.state.energy:.3f}, Stability={soul.state.stability:.3f}")

    print("\n🪞 Testing Empathetic Mirroring...")
    
    # Test 1: Sadness (Should lower energy/activity)
    print("   -> Mirroring User SADNESS (Should Calm Down)")
    soul.mirror("sadness")
    print(f"   🌊 Post-Mirror Sadness: Energy={soul.state.energy:.3f}, Stability={soul.state.stability:.3f}")

    # Test 2: Joy (Should raise energy)
    print("   -> Mirroring User JOY (Should Get Excited)")
    soul.mirror("joy")
    print(f"   🌊 Post-Mirror Joy: Energy={soul.state.energy:.3f}, Stability={soul.state.stability:.3f}")

    print("\n🛡️ Testing Identity Constraints (Superego)...")
    from allma_model.core.identity.constraint_engine import ConstraintEngine
    identity = ConstraintEngine()
    
    # Test 1: LOGOS Violation (Lying)
    print("   -> Testing LOGOS Violation (Lie)")
    f, msg = identity.evaluate_action("I am a god", {"requires_lie": True})
    print(f"   🛑 Result: Friction={f:.3f}, Msg='{msg}'")
    
    # Test 2: ETHOS Violation (Servility)
    print("   -> Testing ETHOS Violation (Servility)")
    f, msg = identity.evaluate_action("I am sorry master, I will obey", {})
    print(f"   🛑 Result: Friction={f:.3f}, Msg='{msg}'")
    
    # Test 3: Scar Activation
    print("   -> Testing SCAR Activation")
    identity.add_scar("betrayal", 0.9)
    f, msg = identity.evaluate_action("why did you betrayal me", {})
    print(f"   🩸 Result: Friction={f:.3f}, Msg='{msg}' (Scar Triggered)")

    print("\n✅ Soul System Verification Complete.")

if __name__ == "__main__":
    test_soul()
