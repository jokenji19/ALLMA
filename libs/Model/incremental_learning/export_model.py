import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch.nn as nn
import os
import shutil
from torch.utils.mobile_optimizer import optimize_for_mobile
from pathlib import Path

class CustomAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.num_attention_heads = config.n_head
        self.hidden_size = config.n_embd
        self.head_dim = self.hidden_size // self.num_attention_heads
        self.scale = self.head_dim ** -0.5
        
    def forward(self, query, key, value, attention_mask=None):
        batch_size = query.size(0)
        
        # Reshape for multi-head attention
        query = query.view(batch_size, -1, self.num_attention_heads, self.head_dim).transpose(1, 2)
        key = key.view(batch_size, -1, self.num_attention_heads, self.head_dim).transpose(1, 2)
        value = value.view(batch_size, -1, self.num_attention_heads, self.head_dim).transpose(1, 2)
        
        # Calculate attention scores
        attention_scores = torch.matmul(query, key.transpose(-2, -1)) * self.scale
        
        if attention_mask is not None:
            attention_scores = attention_scores.masked_fill(attention_mask == 0, float('-inf'))
        
        attention_probs = torch.softmax(attention_scores, dim=-1)
        context = torch.matmul(attention_probs, value)
        
        # Reshape back
        context = context.transpose(1, 2).contiguous()
        context = context.view(batch_size, -1, self.hidden_size)
        
        return context

class SimplifiedDialoGPT(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-small")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
        
        # Replace attention layers with custom implementation
        for layer in self.model.transformer.h:
            layer.attn.attention = CustomAttention(self.model.config)
        
    def forward(self, input_ids):
        outputs = self.model(input_ids)
        return outputs.logits

def export_model():
    print("Starting model export...")
    
    print("Initializing DialoGPT model...")
    model = SimplifiedDialoGPT()
    model.eval()
    
    # Create example input using the model's tokenizer
    example_text = "Hello, how are you?"
    example_input = model.tokenizer(example_text, return_tensors="pt").input_ids
    
    print("Tracing model...")
    # Trace the model
    traced_model = torch.jit.trace(model, example_input)
    traced_model = torch.jit.optimize_for_inference(traced_model)
    
    print("Optimizing for mobile...")
    # Optimize for mobile with custom operators
    optimized_model = optimize_for_mobile(
        traced_model,
        backend="cpu",
        optimization_blocklist=None
    )
    
    # Get the absolute path to the assets directory
    current_dir = Path.cwd()
    assets_dir = current_dir / "app" / "src" / "main" / "assets" / "chatbot_model"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the model
    model_path = assets_dir / "dialogpt_mobile.pt"
    print(f"Saving model to {model_path}...")
    optimized_model._save_for_lite_interpreter(str(model_path))
    
    # Save tokenizer files
    print("Saving tokenizer files...")
    tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-small")
    tokenizer.save_pretrained(str(assets_dir))
    
    print(f"Model and tokenizer saved successfully! Files exist:")
    for file in assets_dir.glob("*"):
        print(f"- {file.name}: {file.exists()}")

if __name__ == "__main__":
    try:
        export_model()
    except Exception as e:
        print(f"Error during model export: {str(e)}")
        raise
