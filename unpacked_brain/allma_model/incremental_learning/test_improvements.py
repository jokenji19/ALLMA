import unittest
import torch
import numpy as np
from allma_model.incremental_learning.training.allma_core import ALLMA, Memory

class TestALLMAImprovements(unittest.TestCase):
    def setUp(self):
        self.allma = ALLMA()
        self.memory = Memory()

    def test_memory_system(self):
        # Test empty inputs
        self.memory.add_interaction("", "")
        self.assertEqual(len(self.memory.short_term), 0, "Empty interactions should not be stored")

        # Test valid interactions
        self.memory.add_interaction("Hello", "Hi there!")
        self.assertEqual(len(self.memory.short_term), 1, "Valid interaction should be stored")

        # Test recent interactions retrieval
        interactions = self.memory.get_recent_interactions(3)
        self.assertEqual(len(interactions), 1, "Should return all available interactions up to n")

    def test_learning_improvements(self):
        # Test basic learning
        input_text = "How are you?"
        target_output = "I'm doing well, thank you!"
        success = self.allma.learn(input_text, target_output, feedback=1.0)
        self.assertGreater(success, 0, "Learning should show some success")

        # Test learning with negative feedback
        success_neg = self.allma.learn(input_text, target_output, feedback=-0.5)
        self.assertLess(success_neg, success, "Negative feedback should result in lower success")

        # Test momentum
        params_before = []
        for param in self.allma.parameters():
            params_before.append(param.clone())

        # Multiple learning steps
        for _ in range(5):
            self.allma.learn(input_text, target_output, feedback=1.0)

        params_after = []
        for param in self.allma.parameters():
            params_after.append(param)

        # Check if parameters changed due to momentum
        any_param_changed = False
        for before, after in zip(params_before, params_after):
            if not torch.equal(before, after):
                any_param_changed = True
                break
        self.assertTrue(any_param_changed, "Parameters should change due to momentum")

    def test_chat_improvements(self):
        # Test basic chat functionality
        response = self.allma.chat("Hello!")
        self.assertIsInstance(response, str, "Chat should return a string")
        self.assertTrue(response[0].isupper(), "Response should start with capital letter")
        self.assertTrue(response[-1] in ".!?", "Response should end with punctuation")

        # Test chat with context
        self.allma.chat("How are you?")
        second_response = self.allma.chat("What's your name?")
        self.assertIsInstance(second_response, str, "Chat should handle multiple interactions")

    def test_response_cleaning(self):
        # Test response cleaning
        test_response = "  hello  world  "
        cleaned = self.allma._clean_response(test_response)
        self.assertEqual(cleaned, "Hello world.", "Response should be properly cleaned")

        # Test empty response
        self.assertEqual(self.allma._clean_response(""), "", "Empty response should remain empty")

if __name__ == '__main__':
    unittest.main()
