import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import shutil

def main():
    # Percorso al modello fine-tunato con DailyDialog
    model_base_path = "../models/dailydialog_model"
    model_path = os.path.join(model_base_path, "checkpoint-2085")  # Usa l'ultimo checkpoint
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_path = os.path.join(base_dir, 'app/src/main/assets/chatbot_model')
    
    print("Loading fine-tuned model from:", model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path)
    model.eval()
    
    # Carica il tokenizer dalla directory base (contiene tutti i file del tokenizer)
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_base_path)
    
    # Prepara un input di esempio con il formato corretto
    print("Preparing example input...")
    test_input = "User: Hello\nAssistant:"
    inputs = tokenizer(test_input, return_tensors="pt")
    
    # Definisci una classe wrapper più semplice
    class ModelWrapper(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model
            
        def forward(self, input_ids):
            outputs = self.model.forward(input_ids=input_ids)
            return outputs.logits
    
    # Avvolgi il modello
    print("Wrapping model...")
    wrapped_model = ModelWrapper(model)
    wrapped_model.eval()
    
    # Traccia e scripta il modello
    print("Tracing and scripting model...")
    with torch.no_grad():
        # Prima traccia il modello
        traced_model = torch.jit.trace(wrapped_model, inputs['input_ids'])
        traced_model.eval()
        
        # Poi lo scripta per catturare la logica del controllo di flusso
        scripted_model = torch.jit.script(traced_model)
        scripted_model.eval()
    
    # Crea la directory se non esiste
    os.makedirs(save_path, exist_ok=True)
    
    # Salva il modello e il tokenizer
    print("Saving model and tokenizer...")
    output_model_path = os.path.join(save_path, "dialogpt_mobile.pt")
    scripted_model.save(output_model_path)
    tokenizer.save_pretrained(save_path)
    
    print("Conversion completed!")
    print("Model saved to:", output_model_path)
    print("Tokenizer saved to:", save_path)

if __name__ == '__main__':
    main()
