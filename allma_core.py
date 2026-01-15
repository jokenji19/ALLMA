
class AllmaCore:
    def __init__(self, **kwargs):
        print("Build 134: Flat Core Initialized")
        
    def process_message(self, *args, **kwargs):
        print("Dummy process_message called")
        class MockResponse:
            content = "Build 134: Flat Earth successful."
            voice_params = None
            emotion = "neutral"
            topics = []
            emotion_detected = False
            knowledge_integrated = False
            confidence = 1.0
            is_valid = True
            
        return MockResponse()
