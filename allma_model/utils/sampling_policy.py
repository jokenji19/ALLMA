"""Model-specific thinking sampling; leaves unknown models on existing defaults."""
from pathlib import Path


def sampling_options(model_path):
    if isinstance(model_path, (str, Path)) and 'qwen3' in Path(model_path).name.lower():
        # Qwen/Qwen3-1.7B model card, thinking-mode recommendations.
        return {'temperature': 0.6, 'top_p': 0.95, 'top_k': 20, 'min_p': 0.0}
    return {'temperature': 0.4, 'top_p': 0.9}


REASONING_INSTRUCTION = (
    'Ragiona brevemente sul compito effettivo: identifica il punto decisivo, '
    'verifica la conclusione e passa alla risposta. Non consumare il ragionamento '
    'ripetendo la domanda o descrivendo come vorresti rispondere. '
    'Nella risposta usa termini italiani corretti e soltanto spiegazioni che sai sostenere. '
    'Una risposta breve e precisa è preferibile a dettagli inventati.'
)
