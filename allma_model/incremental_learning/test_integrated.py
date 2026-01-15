import sys
import torch
from Model.incremental_learning.training.allma_core import BasicIncrementalModel, ALLMATokenizer

def test_tokenizer():
    """Test del tokenizer"""
    print("\nTest del tokenizer:")
    tokenizer = ALLMATokenizer()
    
    # Test di tokenizzazione
    test_text = "Ciao come stai?"
    print(f"\nInput text: {test_text}")
    
    # Tokenizza
    tokens = tokenizer.tokenize(test_text)
    print(f"Tokens: {tokens}")
    
    # Converti in IDs
    token_ids = [tokenizer.vocab.get(token, tokenizer.vocab["<UNK>"]) for token in tokens]
    print(f"Token IDs: {token_ids}")
    
    # Converti in tensore
    input_tensor = torch.tensor(token_ids, dtype=torch.long)
    print(f"Input tensor: {input_tensor}")
    print(f"Input tensor shape: {input_tensor.shape}")
    print(f"Input tensor dtype: {input_tensor.dtype}")
    
    # Test di decodifica
    decoded_text = tokenizer.decode(token_ids)
    print(f"Decoded text: {decoded_text}")

def test_model():
    # Reindirizza l'output su un file
    sys.stdout = open("test_output.log", "w")
    
    print("Inizializzazione del modello...")
    model = BasicIncrementalModel()
    
    # Test del tokenizer
    test_tokenizer()
    
    # Test di apprendimento
    print("\nTest di apprendimento:")
    conversations = [
        ("Ciao", "Ciao! Come stai?"),
        ("Bene grazie, tu?", "Sto bene anche io, grazie! Come posso aiutarti oggi?"),
        ("Mi piace programmare", "È fantastico! Anche io amo la programmazione. Quale linguaggio preferisci?"),
        ("Python è il mio preferito", "Python è eccellente! È molto versatile e potente."),
    ]
    
    print("\nAddestramento su conversazioni di esempio:")
    for input_text, target_text in conversations:
        print(f"\nInput: {input_text}")
        print(f"Target: {target_text}")
        
        # Training step
        model.train()
        
        # Tokenizza input e target
        input_ids = model.tokenizer(input_text)
        target_ids = model.tokenizer(target_text)
        
        # Aggiungi START e END token
        input_ids = torch.tensor([[model.tokenizer.vocab["<START>"]] + input_ids.tolist() + [model.tokenizer.vocab["<END>"]]])
        target_ids = torch.tensor([[model.tokenizer.vocab["<START>"]] + target_ids.tolist() + [model.tokenizer.vocab["<END>"]]])
        
        # Debug info
        print(f"Input IDs: {input_ids}")
        print(f"Target IDs: {target_ids}")
        print(f"Input IDs shape: {input_ids.shape}")
        print(f"Target IDs shape: {target_ids.shape}")
        print(f"Input IDs dtype: {input_ids.dtype}")
        print(f"Target IDs dtype: {target_ids.dtype}")
        sys.stdout.flush()
        
        # Training step
        _, loss = model(input_ids, target_ids)
        print(f"Loss: {loss:.4f}")
    
    # Test di generazione
    print("\nTest di generazione:")
    test_inputs = [
        "Ciao",
        "Come stai?",
        "Mi piace l'intelligenza artificiale"
    ]
    
    model.eval()
    for test_input in test_inputs:
        print(f"\nGenerazione risposta per: {test_input}")
        with torch.no_grad():
            response = model.generate_response(test_input)
            print(f"Risposta generata: {response}")
    
    # Test salvataggio e caricamento
    print("\nTest salvataggio e caricamento del modello:")
    torch.save(model.state_dict(), "test_model.pt")
    print("Modello salvato")
    
    new_model = BasicIncrementalModel()
    new_model.load_state_dict(torch.load("test_model.pt", weights_only=True))
    print("Modello caricato")
    
    # Verifica che il modello caricato funzioni
    test_input = "Ciao"
    print(f"\nTest dopo caricamento:")
    print(f"Input: {test_input}")
    with torch.no_grad():
        response = new_model.generate_response(test_input)
        print(f"Risposta generata: {response}")
    
    # Chiudi il file di output
    sys.stdout.close()
    sys.stdout = sys.__stdout__

if __name__ == "__main__":
    test_model()
