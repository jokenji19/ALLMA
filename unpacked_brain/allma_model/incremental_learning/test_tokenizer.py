import torch
from allma_model.incremental_learning.training.allma_core import ALLMATokenizer

def test_tokenizer():
    print("Test del tokenizer")
    tokenizer = ALLMATokenizer()
    
    # Test 1: Tokenizzazione base
    test_text = "ciao come stai ?"
    print(f"\nTest 1 - Input: '{test_text}'")
    tokens = tokenizer.tokenize(test_text)
    print(f"Tokens: {tokens}")
    
    # Test 2: Conversione in IDs
    token_ids = [tokenizer.vocab.get(token, tokenizer.vocab["<UNK>"]) for token in tokens]
    print(f"Token IDs: {token_ids}")
    
    # Test 3: Conversione in tensore
    tensor = tokenizer(test_text)
    print(f"Tensor: {tensor}")
    print(f"Tensor shape: {tensor.shape}")
    print(f"Tensor dtype: {tensor.dtype}")
    
    # Test 4: Decodifica
    decoded = tokenizer.decode(token_ids)
    print(f"Decoded text: '{decoded}'")
    
    # Test 5: Gestione parole sconosciute
    test_text_unk = "questa parola non esiste nel vocabolario"
    print(f"\nTest 5 - Input con parole sconosciute: '{test_text_unk}'")
    tokens_unk = tokenizer.tokenize(test_text_unk)
    print(f"Tokens: {tokens_unk}")
    
    # Test 6: Gestione punteggiatura
    test_text_punct = "ciao, come stai? bene!"
    print(f"\nTest 6 - Input con punteggiatura: '{test_text_punct}'")
    tokens_punct = tokenizer.tokenize(test_text_punct)
    print(f"Tokens: {tokens_punct}")
    
    # Test 7: Gestione token speciali
    print("\nTest 7 - Token speciali:")
    print(f"START token ID: {tokenizer.vocab['<START>']}")
    print(f"END token ID: {tokenizer.vocab['<END>']}")
    print(f"PAD token ID: {tokenizer.vocab['<PAD>']}")
    print(f"UNK token ID: {tokenizer.vocab['<UNK>']}")

if __name__ == "__main__":
    test_tokenizer()
