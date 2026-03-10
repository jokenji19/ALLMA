try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
from typing import Dict, List, Union
from collections import Counter

class ALLMATokenizer:
    def __init__(self, vocab_size: int = 10000):
        """Inizializza il tokenizer"""
        self.max_vocab_size = vocab_size
        self.vocab: Dict[str, int] = {}
        self.reverse_vocab: Dict[int, str] = {}
        self.special_tokens = {
            '<PAD>': 0,
            '<UNK>': 1,
            '<BOS>': 2,
            '<EOS>': 3
        }
        
        # Inizializza il vocabolario con i token speciali
        self.vocab.update(self.special_tokens)
        self.reverse_vocab.update({v: k for k, v in self.special_tokens.items()})
        self.current_idx = len(self.special_tokens)
        
    def __len__(self) -> int:
        """Restituisce la dimensione del vocabolario"""
        return len(self.vocab)
        
    def __getitem__(self, item: str) -> int:
        """Restituisce l'indice di un token"""
        return self.vocab.get(item, self.special_tokens['<UNK>'])
        
    def tokenize(self, text: str) -> 'torch.Tensor':
        """Converte il testo in una lista di token"""
        words = text.lower().split()
        tokens = [self.vocab.get(word, self.special_tokens['<UNK>']) for word in words]
        if TORCH_AVAILABLE:
            return torch.tensor(tokens, dtype=torch.long)
        return tokens # Return list if torch not available
        
    def decode(self, tokens: Union[List[int], 'torch.Tensor']) -> str:
        """Converte una lista di token in testo"""
        if TORCH_AVAILABLE and isinstance(tokens, torch.Tensor):
            tokens = tokens.cpu().tolist()
        return ' '.join([self.reverse_vocab.get(token, '<UNK>') for token in tokens])
        
    def add_to_vocab(self, word: str) -> int:
        """Aggiunge una parola al vocabolario"""
        if word not in self.vocab and len(self.vocab) < self.max_vocab_size:
            self.vocab[word] = self.current_idx
            self.reverse_vocab[self.current_idx] = word
            self.current_idx += 1
        return self.vocab.get(word, self.special_tokens['<UNK>'])
        
    def update_from_text(self, text: str, min_freq: int = 2):
        """Aggiorna il vocabolario da un testo"""
        words = text.lower().split()
        word_counts = Counter(words)
        
        for word, count in word_counts.items():
            if count >= min_freq:
                self.add_to_vocab(word)
                
    def save_vocab(self, path: str):
        """Salva il vocabolario su file"""
        with open(path, 'w') as f:
            for word, idx in self.vocab.items():
                f.write(f"{word}\t{idx}\n")
                
    def load_vocab(self, path: str):
        """Carica il vocabolario da file"""
        self.vocab.clear()
        self.reverse_vocab.clear()
        
        # Ripristina i token speciali
        self.vocab.update(self.special_tokens)
        self.reverse_vocab.update({v: k for k, v in self.special_tokens.items()})
        self.current_idx = len(self.special_tokens)
        
        with open(path, 'r') as f:
            for line in f:
                word, idx = line.strip().split('\t')
                idx = int(idx)
                self.vocab[word] = idx
                self.reverse_vocab[idx] = word
                self.current_idx = max(self.current_idx, idx + 1)

    def __call__(self, text: str) -> 'torch.Tensor':
        """
        Tokenizza il testo e restituisce un tensore
        
        Args:
            text: Testo da tokenizzare
            
        Returns:
            Tensore con gli indici dei token
        """
        # Tokenizza il testo
        words = text.lower().split()
        
        # Converti in indici
        tokens = [self.vocab.get(word, self.special_tokens['<UNK>']) for word in words]
        
        # Aggiungi i token speciali
        tokens = [self.special_tokens['<BOS>']] + tokens + [self.special_tokens['<EOS>']]
        
        if TORCH_AVAILABLE:
            return torch.tensor(tokens, dtype=torch.long)
        return tokens
