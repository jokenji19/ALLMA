import logging
import time
from typing import Dict, Any, Optional

# Lazy import to avoid loading transformers on startup
# transformers will count as a heavy dependency, so we only import inside the method or class
# properly handle if transformers is not installed fallback

class MLEmotionalSystem:
    def __init__(self, model_name: str = "AdamCodd/tinybert-emotion-balanced"):
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.classifier = None
        self._load_error = False
        
    def _ensure_loaded(self):
        """Lazy loads the ML model."""
        if self.classifier or self._load_error:
            return

        try:
            self.logger.info(f"🧠 [Deep Empathy] Loading TinyBERT model: {self.model_name}...")
            start_time = time.time()
            
            # Local import to prevent startup lag
            from transformers import pipeline
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            # Force CPU usage for mobile stability (device=-1)
            # Use quantized or raw loading
            self.classifier = pipeline(
                "text-classification",
                model=self.model_name,
                top_k=None, # Return all scores
                device=-1
            )
            
            load_time = time.time() - start_time
            self.logger.info(f"🧠 [Deep Empathy] Model loaded in {load_time:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ [Deep Empathy] Failed to load ML model: {e}")
            self._load_error = True

    def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrator-compatible process method.
        """
        # Orchestrator might call this.
        # Check if we should run (Hybrid Logic could be here or in Orchestrator)
        
        # Load model only if enabled and needed
        self._ensure_loaded()
        
        if self._load_error or not self.classifier:
            return {"error": "Model not loaded"}
            
        try:
            # Run Inference
            start_time = time.time()
            results = self.classifier(user_input)[0]
            inference_time = (time.time() - start_time) * 1000
            
            # Sort emotions
            sorted_emotions = sorted(results, key=lambda x: x['score'], reverse=True)
            top_emotion = sorted_emotions[0]
            
            # Logic: If confidence is high, return it.
            # If low, maybe ignore?
            
            confidence = top_emotion['score']
            label = top_emotion['label']
            
            self.logger.info(f"🧠 [Deep Empathy] Detected: {label} ({confidence:.2f}) in {inference_time:.1f}ms")
            
            # Prepare Output for Orchestrator
            output = {
                "emotion": label,
                "confidence": confidence,
                "all_scores": {res['label']: res['score'] for res in sorted_emotions}
            }
            
            # Create user_prefix/system_instruction based on emotion
            # Only if strong emotion
            if confidence > 0.6:
                if label in ['sadness', 'anger', 'fear']:
                    output['user_prefix'] = [f"[Empathy: {label}]"]
                    output['system_instruction'] = [f"User is feeling {label}. Be supportive and gentle."]
                elif label in ['joy', 'love']:
                    output['user_prefix'] = [f"[Empathy: {label}]"]
                    output['system_instruction'] = [f"User is happy ({label}). Share the excitement."]
            
            return output
            
        except Exception as e:
            self.logger.error(f"Error in ML emotion detection: {e}")
            return {"error": str(e)}

    def analyze(self, text: str) -> str:
        """Simple sync method for direct usage"""
        self._ensure_loaded()
        if not self.classifier:
            return "neutral"
        try:
            res = self.classifier(text)[0]
            top = sorted(res, key=lambda x: x['score'], reverse=True)[0]
            return top['label']
        except:
            return "neutral"
