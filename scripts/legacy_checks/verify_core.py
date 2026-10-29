import sys
import os

# Add project root to path
sys.path.append("/Users/erikahu/ALLMA/ALLMA_V4")

try:
    print("Attempting to import ALLMACore...")
    from allma_model.core.allma_core import ALLMACore
    print("ALLMACore imported successfully.")
    
    # Mocking necessary database path 
    core = ALLMACore(mobile_mode=True, db_path="verify_test.db")
    print("ALLMACore instantiated successfully.")
    
    # Basic check of components
    if hasattr(core, 'context_system'):
        print(f"Context System: {type(core.context_system)}")
    else:
        print("Context System MISSING")
        
    if hasattr(core, 'understanding_system'):
        print(f"Understanding System: {type(core.understanding_system)}")
    else:
        print("Understanding System MISSING")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
