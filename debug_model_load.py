import os
import sys
from llama_cpp import Llama

def debug_load():
    print("=== DEBUG CARICAMENTO MODELLO ===")
    
    model_path = "assets/model.bin"
    abs_path = os.path.abspath(model_path)
    
    print(f"Percorso relativo: {model_path}")
    print(f"Percorso assoluto: {abs_path}")
    
    if not os.path.exists(abs_path):
        print("❌ IL FILE NON ESISTE!")
        return

    print(f"Dimensione file: {os.path.getsize(abs_path) / (1024*1024):.2f} MB")
    
    print("\nTentativo caricamento con verbose=True...")
    try:
        llm = Llama(
            model_path=abs_path,
            n_ctx=2048,
            verbose=True
        )
        print("✅ Modello caricato con successo!")
        
        output = llm("Ciao", max_tokens=10)
        print(f"Output test: {output}")
        
    except Exception as e:
        print(f"❌ Errore caricamento: {e}")

if __name__ == "__main__":
    debug_load()
