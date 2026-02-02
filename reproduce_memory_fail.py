
from allma_model.memory_system.conversational_memory import ConversationalMemory

mem = ConversationalMemory()
user_id = "test_user"

# 1. User states fact
mem.save_interaction(user_id, "Il mio colore preferito è il blu", "user")

# 2. Check extracted facts
print("User Data:", getattr(mem, 'user_data', {}))

# 3. User asks question
print("\n--- Retrieving ---")
context = mem.retrieve_relevant_context("Qual è il mio colore preferito?", user_id=user_id)
print("Retrieved Context:", context)

# 4. Expected: Context contains "Il mio colore preferito è il blu"
# 5. Expected: User Data contains {'favorite_color': 'blu'} (This will FAIL)
