
class AllmaCore:
    def __init__(self, **kwargs):
        print("Build 132: Dummy AllmaCore Initialized")
        
    def process_message(self, *args, **kwargs):
        print("Dummy process_message called")
        # Return a mock object if needed, or just let it crash safely at runtime.
        # Main.py expects an object with .content
        class MockResponse:
            content = "Build 132: I am a ghost."
            voice_params = None
            emotion = "neutral"
            topics = []
            emotion_detected = False
            knowledge_integrated = False
            confidence = 1.0
            
        return MockResponse()
