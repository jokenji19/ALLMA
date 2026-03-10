"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the tokenizer for ALLMA.
Author: Cristof Bano
Created: January 2025
"""

from typing import List, Dict, Optional
import re

class ALLMATokenizer:
    def __init__(self):
        self.vocab = {}
        self.reverse_vocab = {}
        self.token_pattern = re.compile(r'\w+|[^\w\s]')
        
    def tokenize(self, text: str) -> List[str]:
        return self.token_pattern.findall(text)
        
    def encode(self, text: str) -> List[int]:
        tokens = self.tokenize(text)
        return [self.vocab.get(token, 0) for token in tokens]
        
    def decode(self, ids: List[int]) -> str:
        tokens = [self.reverse_vocab.get(id, '') for id in ids]
        return ' '.join(tokens)
        
    def add_tokens(self, tokens: List[str]) -> None:
        for token in tokens:
            if token not in self.vocab:
                idx = len(self.vocab)
                self.vocab[token] = idx
                self.reverse_vocab[idx] = token
