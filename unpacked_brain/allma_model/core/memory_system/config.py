"""
Configurazione del sistema di memoria avanzato
"""

# Configurazione generale
MEMORY_CONFIG = {
    'max_short_term': 100,
    'max_working_memory': 7,
    'consolidation_threshold': 0.7,
    'similarity_threshold': 0.8,
    'embedding_dim': 768,
    'memory_decay_rate': 0.1,
    'emotional_memory_weight': 0.3,
    'semantic_memory_weight': 0.4,
    'context_memory_weight': 0.3
}

# Configurazione emotiva
EMOTIONAL_CONFIG = {
    'valence_range': (-1.0, 1.0),
    'arousal_range': (0.0, 1.0),
    'dominance_range': (0.0, 1.0),
    'emotion_decay_rate': 0.05
}

# Configurazione del consolidamento
CONSOLIDATION_CONFIG = {
    'min_importance': 0.7,
    'min_access_count': 5,
    'min_connections': 3,
    'consolidation_interval': 3600  # secondi
}

# Configurazione del recupero
RETRIEVAL_CONFIG = {
    'default_top_k': 5,
    'min_relevance': 0.3,
    'context_weight': 0.3,
    'semantic_weight': 0.4,
    'temporal_weight': 0.3
}
