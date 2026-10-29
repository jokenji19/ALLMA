import json
from allma_model.api.allma_api import AllmaAndroidBridge

try:
    bridge = AllmaAndroidBridge(db_path="allma_test.db")
    user_id = "test_user"

    # Let's add something to the memory
    bridge.allma.conversational_memory.store_conversation(user_id, "Test memory")
    if not hasattr(bridge.allma.conversational_memory, 'user_data'):
        bridge.allma.conversational_memory.user_data = {}
    bridge.allma.conversational_memory.user_data[user_id] = {"name": "Test Name", "preference": "Dark Mode"}

    data = bridge.get_memory_data(user_id)
    print("Memory Data Output:", json.dumps(data, indent=2))
except Exception as e:
    print("Error:", e)
