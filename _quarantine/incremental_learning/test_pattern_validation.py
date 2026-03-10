"""
Test per il sistema di validazione dei pattern
"""

import unittest
import numpy as np
from dataclasses import dataclass
from pattern_validation import PatternValidator, ValidationResult

@dataclass
class MockPattern:
    """Pattern mock per i test"""
    features: np.ndarray
    category: str
    stability_score: float
    confidence: float
    related_patterns: dict

class TestPatternValidation(unittest.TestCase):
    """Test per il sistema di validazione"""
    
    def setUp(self):
        """Setup per i test"""
        self.validator = PatternValidator()
        
    def test_valid_pattern(self):
        """Verifica la validazione di un pattern valido"""
        pattern = MockPattern(
            features=np.array([1.0, 0.0, 0.0]),
            category="test",
            stability_score=0.8,
            confidence=0.9,
            related_patterns={}
        )
        
        context = {
            "patterns": [
                MockPattern(
                    features=np.array([0.9, 0.1, 0.0]),
                    category="test",
                    stability_score=0.7,
                    confidence=0.8,
                    related_patterns={}
                )
            ]
        }
        
        result = self.validator.validate_pattern(pattern, context)
        
        self.assertTrue(result.is_valid)
        self.assertGreater(result.confidence, 0.8)
        self.assertEqual(len(result.error_messages), 0)
        self.assertGreater(result.validation_score, 0.7)
        self.assertLess(result.validation_time, 1.0)
        
    def test_invalid_features(self):
        """Verifica la validazione con features non valide"""
        pattern = MockPattern(
            features=np.array([]),  # Features vuote
            category="test",
            stability_score=0.8,
            confidence=0.9,
            related_patterns={}
        )
        
        result = self.validator.validate_pattern(pattern, {})
        
        self.assertFalse(result.is_valid)
        self.assertIn("Features non valide", result.error_messages)
        
    def test_low_stability(self):
        """Verifica la validazione con stabilità bassa"""
        pattern = MockPattern(
            features=np.array([1.0, 0.0, 0.0]),
            category="test",
            stability_score=0.2,  # Stabilità troppo bassa
            confidence=0.9,
            related_patterns={}
        )
        
        result = self.validator.validate_pattern(pattern, {})
        
        self.assertFalse(result.is_valid)
        self.assertIn("Stabilità troppo bassa", result.error_messages[0])
        
    def test_context_validation(self):
        """Verifica la validazione nel contesto"""
        pattern = MockPattern(
            features=np.array([1.0, 0.0, 0.0]),
            category="test",
            stability_score=0.8,
            confidence=0.9,
            related_patterns={}
        )
        
        # Contesto con pattern molto diverso
        context = {
            "patterns": [
                MockPattern(
                    features=np.array([0.0, 1.0, 0.0]),
                    category="test",
                    stability_score=0.8,
                    confidence=0.9,
                    related_patterns={}
                )
            ]
        }
        
        result = self.validator.validate_pattern(pattern, context)
        
        self.assertFalse(result.is_valid)
        self.assertIn("Pattern non coerente con il contesto", result.error_messages[0])
        
    def test_validation_score(self):
        """Verifica il calcolo del punteggio di validazione"""
        pattern = MockPattern(
            features=np.array([1.0, 0.0, 0.0]),
            category="test",
            stability_score=1.0,
            confidence=1.0,
            related_patterns={}
        )
        
        context = {
            "patterns": [
                MockPattern(
                    features=np.array([0.95, 0.05, 0.0]),
                    category="test",
                    stability_score=0.9,
                    confidence=0.9,
                    related_patterns={}
                )
            ]
        }
        
        result = self.validator.validate_pattern(pattern, context)
        
        # Con tutti i parametri ottimali, il punteggio dovrebbe essere molto alto
        self.assertGreater(result.validation_score, 0.9)
        
if __name__ == '__main__':
    unittest.main()
