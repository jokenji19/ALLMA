import json

# Simulated bridge logic
value = '"{\\"type\\":\\"action\\",\\"action\\":\\"set_voice_mode\\",\\"enabled\\":true}"'
clean_val = json.loads(value)

# ChatView logic
message = clean_val
print(f"Message received: {repr(message)}")

try:
    data = json.loads(message)
    print(f"Parsed data: {data}")
    
    if isinstance(data, dict):
        msg_type = data.get('type')
        action = data.get('action')
        
        print(f"msg_type: {msg_type}, action: {action}")
        
        if msg_type == 'action':
            if action == 'set_voice_mode':
                enabled = data.get('enabled', False)
                print(f"ChatView: Voice Mode Set -> {enabled}")
except Exception as e:
    print(f"Error: {e}")
