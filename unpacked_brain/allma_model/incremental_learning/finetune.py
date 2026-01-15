import json
import torch
import time
import os
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import Dataset
import logging
from typing import Dict

# Abilita fallback su CPU per operazioni non supportate da MPS
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

logging.basicConfig(level=logging.INFO)

def prepare_dataset(file_path):
    """Prepara il dataset per il training"""
    try:
        # Leggi il contenuto del file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Estrai le conversazioni dal dizionario
        if isinstance(data, dict) and 'conversations' in data:
            conversations = data['conversations']
        else:
            conversations = data  # Prova a usare direttamente il contenuto
            
        if not isinstance(conversations, list):
            raise ValueError("Non riesco a trovare una lista di conversazioni valida nel file")
        
        # Limita a 1000 conversazioni per test
        max_conversations = min(1000, len(conversations))
        selected_conversations = conversations[:max_conversations]
        print(f"\nUsando {len(selected_conversations)} conversazioni per il training")
        
        formatted_data = []
        for conv in selected_conversations:
            input_text = conv.get('input', '')
            output_text = conv.get('output', '') or conv.get('response', '')  # Prova entrambi i campi
            
            if input_text and output_text:
                text = f"User: {input_text}\nAssistant: {output_text}\n"
                formatted_data.append({"text": text})
        
        print(f"Formattate {len(formatted_data)} conversazioni correttamente")
        if len(formatted_data) == 0:
            raise ValueError("Nessuna conversazione valida trovata nel dataset")
            
        return Dataset.from_list(formatted_data)
    
    except json.JSONDecodeError as e:
        print(f"\nErrore nel parsing JSON: {str(e)}")
        raise
    except Exception as e:
        print(f"\nErrore nella preparazione del dataset: {str(e)}")
        raise

class CustomTrainer(Trainer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_log_time = time.time()
        self.best_loss = float('inf')
        
    def log(self, logs: Dict[str, float], start_time=None) -> None:
        """Stampa informazioni dettagliate durante il training"""
        current_time = time.time()
        
        if current_time - self.last_log_time >= 5:  # Log ogni 5 secondi
            self.last_log_time = current_time
            logs["step"] = self.state.global_step
            logs["epoch"] = round(self.state.epoch, 2)
            logs["learning_rate"] = self.lr_scheduler.get_last_lr()[0]
            
            # Traccia la migliore loss
            if logs["loss"] < self.best_loss:
                self.best_loss = logs["loss"]
                logs["best_loss"] = self.best_loss
            
            # Formatta il log in modo leggibile
            log_str = f"\n{'='*50}"
            log_str += f"\nStep: {logs['step']}/{self.state.max_steps} "
            log_str += f"({(logs['step']/self.state.max_steps*100):.1f}%)"
            log_str += f"\nEpoch: {logs['epoch']:.2f}"
            log_str += f"\nLoss: {logs['loss']:.4f} (Best: {self.best_loss:.4f})"
            log_str += f"\nLR: {logs['learning_rate']:.2e}"
            
            if 'train/steps_per_second' in logs:
                log_str += f"\nSpeed: {logs['train/steps_per_second']:.1f} steps/s"
            
            memory = torch.cuda.memory_allocated() / 1024**2 if torch.cuda.is_available() else 0
            log_str += f"\nGPU Memory: {memory:.1f} MB"
            log_str += f"\n{'='*50}"
            
            print(log_str, flush=True)
        
        super().log(logs, start_time)

def main():
    # Initialize model and tokenizer
    print("\n=== Inizializzazione Modello ===")
    model_name = "microsoft/DialoGPT-small"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # Forza l'uso della CPU per evitare problemi con MPS
    device = torch.device("cpu")
    print(f"\nUsando device: {device}")
    
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
    
    # Add special tokens and set padding token
    special_tokens = {
        'additional_special_tokens': ['User:', 'Assistant:'],
        'pad_token': '[PAD]'
    }
    tokenizer.add_special_tokens(special_tokens)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Resize embeddings without mean resizing
    model.resize_token_embeddings(len(tokenizer))
    print("Token embeddings ridimensionati")
    
    # Enable gradient checkpointing for memory efficiency
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
        print("Gradient checkpointing abilitato")
    
    # Prepare dataset
    print("\n=== Preparazione Dataset ===")
    dataset = prepare_dataset('conversations.json')
    print(f"Dataset preparato con {len(dataset)} esempi")
    
    def tokenize_function(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=128,
            padding="max_length"
        )
    
    # Tokenize dataset
    print("\n=== Tokenizzazione Dataset ===")
    tokenized_dataset = dataset.map(
        tokenize_function,
        batched=True,
        remove_columns=dataset.column_names
    )
    print("Dataset tokenizzato con successo!")
    
    # Training arguments
    print("\n=== Configurazione Training ===")
    training_args = TrainingArguments(
        output_dir="./results",
        overwrite_output_dir=True,
        num_train_epochs=5,
        per_device_train_batch_size=2,
        save_steps=100,
        save_total_limit=2,
        logging_steps=10,
        learning_rate=2e-5,
        warmup_steps=50,
        gradient_accumulation_steps=8,
        fp16=False,  # Disabilitato per Mac
        gradient_checkpointing=True,
        report_to="none",
        logging_first_step=True,
        logging_dir="./logs",
        disable_tqdm=True,
        dataloader_num_workers=0,  # Ridotto per Mac
        group_by_length=True,
        prediction_loss_only=True,
        use_mps_device=False  # Disabilitato per forzare l'uso della CPU
    )
    
    print("\nParametri di training:")
    print(f"- Batch size: {training_args.per_device_train_batch_size}")
    print(f"- Batch size effettivo: {training_args.per_device_train_batch_size * training_args.gradient_accumulation_steps}")
    print(f"- Learning rate: {training_args.learning_rate}")
    print(f"- Epoche: {training_args.num_train_epochs}")
    print(f"- Gradient accumulation: {training_args.gradient_accumulation_steps}")
    print(f"- FP16: {training_args.fp16}")
    print(f"- Gradient checkpointing: {training_args.gradient_checkpointing}")
    
    # Initialize trainer
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        data_collator=DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False
        ),
        train_dataset=tokenized_dataset
    )
    
    # Train model
    print("\n=== Avvio Training ===")
    trainer.train()
    
    # Save model
    print("\n=== Salvataggio Modello ===")
    os.makedirs('chatbot_model', exist_ok=True)
    trainer.save_model('./chatbot_model')
    tokenizer.save_pretrained('./chatbot_model')
    print("Training completato! Modello salvato in ./chatbot_model")

if __name__ == "__main__":
    main()
