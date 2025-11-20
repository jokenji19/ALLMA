import os
import requests
from tqdm import tqdm

def download_file(url, filename):
    """Scarica un file con barra di avanzamento"""
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    print(f"Scaricamento di {filename}...")
    print(f"Dimensione: {total_size / (1024*1024):.2f} MB")
    
    block_size = 1024
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True)
    
    with open(filename, 'wb') as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()
    
    if total_size != 0 and progress_bar.n != total_size:
        print("ERRORE: Lo scaricamento potrebbe essere incompleto.")
    else:
        print("Scaricamento completato con successo!")

def main():
    # URL diretto per Gemma 3n E2B Instruct (Quantized Q4_K_M - circa 1.8GB)
    # Repository: second-state/gemma-3n-E2B-it-GGUF
    model_url = "https://huggingface.co/second-state/gemma-3n-E2B-it-GGUF/resolve/main/gemma-3n-E2B-it-Q4_K_M.gguf"
    
    # Crea cartella assets se non esiste
    assets_dir = "assets"
    os.makedirs(assets_dir, exist_ok=True)
    
    output_path = os.path.join(assets_dir, "model.bin")
    
    if os.path.exists(output_path):
        print(f"Il modello esiste già in {output_path}")
        choice = input("Vuoi riscaricarlo? (s/n): ")
        if choice.lower() != 's':
            return

    try:
        download_file(model_url, output_path)
        print(f"\nModello salvato in: {output_path}")
        print("Ora puoi compilare l'APK!")
    except Exception as e:
        print(f"Errore durante il download: {e}")

if __name__ == "__main__":
    main()
