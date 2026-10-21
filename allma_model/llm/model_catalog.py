"""Pinned text models; ALLMA's personal state never lives in these files."""
MODELS = {
    'gemma': {  # Historical download key; retained for existing installations.
        'name': 'Qwen 3 · 1.7B', 'quantization': 'Q8_0', 'required': True,
        'url': 'https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/90862c4b9d2787eaed51d12237eafdfe7c5f6077/Qwen3-1.7B-Q8_0.gguf?download=true',
        'filename': 'qwen3-1.7b-q8_0.gguf', 'size_bytes': 1834426016,
        'sha256': '061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a',
        'reasoning': True,
    },
    'qwen35_2b': {
        'name': 'Qwen 3.5 · 2B', 'quantization': 'Q4_K_M', 'required': False,
        'url': 'https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/f6d5376be1edb4d416d56da11e5397a961aca8ae/Qwen3.5-2B-Q4_K_M.gguf?download=true',
        'filename': 'qwen3.5-2b-q4_k_m.gguf', 'size_bytes': 1280835840,
        'sha256': 'aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223',
        'reasoning': True,
    },
}


def catalog():
    return {key: dict(info, size_mb=info['size_bytes']/(1024*1024))
            for key, info in MODELS.items()}
