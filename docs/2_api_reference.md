# API Reference ALLMA

## 1. IntegratedALLMA

### 1.1 Inizializzazione
```python
def __init__(
    self,
    config: Optional[ALLMAConfig] = None,
    response_system: Optional[ResponseSystem] = None,
    pattern_recognition: Optional[PatternRecognition] = None,
    emotional_system: Optional[EmotionalSystem] = None,
    memory_system: Optional[MemorySystem] = None,
    cognitive_system: Optional[CognitiveSystem] = None,
    learning_system: Optional[LearningSystem] = None
):
    """
    Inizializza il sistema ALLMA.
    
    Args:
        config: Configurazione personalizzata
        response_system: Sistema di risposta custom
        pattern_recognition: Sistema di riconoscimento pattern
        emotional_system: Sistema emotivo custom
        memory_system: Sistema memoria custom
        cognitive_system: Sistema cognitivo custom
        learning_system: Sistema di apprendimento custom
    
    Raises:
        ValueError: Se la configurazione non è valida
        InitializationError: Se l'inizializzazione fallisce
    """
```

### 1.2 Metodi Principali

#### process_input
```python
def process_input(
    self,
    text: str,
    context: Optional[Dict[str, Any]] = None,
    learning_mode: bool = True
) -> Dict[str, Any]:
    """
    Elabora un input testuale.
    
    Args:
        text: Testo da elaborare
        context: Contesto opzionale
        learning_mode: Se attivare l'apprendimento
    
    Returns:
        Dict con:
            - concepts: Lista di concetti estratti
            - emotional_context: Contesto emotivo
            - confidence: Confidenza elaborazione
            - learning_level: Livello apprendimento
            - unknown_concepts: Concetti sconosciuti
            - questions: Domande generate
    """
```

#### learn_from_feedback
```python
def learn_from_feedback(
    self,
    concept: str,
    explanation: str,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Apprende da feedback dell'utente.
    
    Args:
        concept: Concetto da apprendere
        explanation: Spiegazione del concetto
        context: Contesto opzionale
    
    Returns:
        True se l'apprendimento è riuscito
    """
```

## 2. EmotionalSystem

### 2.1 Inizializzazione
```python
def __init__(
    self,
    emotion_dictionary: Optional[Dict[str, float]] = None,
    valence_sensitivity: float = 1.0
):
    """
    Inizializza il sistema emotivo.
    
    Args:
        emotion_dictionary: Dizionario emozioni custom
        valence_sensitivity: Sensibilità valenza
    
    Raises:
        ValueError: Se sensitivity non è in [0.1, 10.0]
    """
```

### 2.2 Metodi Principali

#### process_stimulus
```python
def process_stimulus(
    self,
    text: str,
    context: Optional[Dict[str, Any]] = None
) -> Emotion:
    """
    Processa uno stimolo emotivo.
    
    Args:
        text: Testo da analizzare
        context: Contesto opzionale
    
    Returns:
        Emotion con:
            - primary_emotion: Emozione principale
            - valence: Valenza [-1.0, 1.0]
            - arousal: Attivazione [0.0, 1.0]
            - dominance: Dominanza [0.0, 1.0]
    
    Raises:
        EmotionProcessingError: Se analisi fallisce
    """
```

## 3. MemorySystem

### 3.1 Inizializzazione
```python
def __init__(
    self,
    capacity: int = 1000,
    consolidation_interval: timedelta = timedelta(hours=1),
    retrieval_threshold: float = 0.3
):
    """
    Inizializza il sistema di memoria.
    
    Args:
        capacity: Capacità massima memorie
        consolidation_interval: Intervallo consolidamento
        retrieval_threshold: Soglia recupero
    
    Raises:
        ValueError: Se parametri non validi
    """
```

### 3.2 Metodi Principali

#### add_memory
```python
def add_memory(
    self,
    memory_item: Dict[str, Any]
) -> bool:
    """
    Aggiunge una nuova memoria.
    
    Args:
        memory_item: Dict con:
            - content: str
            - emotional_valence: float [-1.0, 1.0]
            - importance: float [0.0, 1.0]
            - context: Dict[str, Any]
    
    Returns:
        True se aggiunta con successo
    
    Raises:
        MemoryError: Se aggiunta fallisce
        ValueError: Se dati non validi
    """
```

#### recall_memory
```python
def recall_memory(
    self,
    query: str,
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Recupera memorie rilevanti.
    
    Args:
        query: Query di ricerca
        context: Contesto opzionale
    
    Returns:
        Lista memorie ordinate per rilevanza
    
    Raises:
        MemoryRetrievalError: Se recupero fallisce
    """
```

## 4. CognitiveSystem

### 4.1 Inizializzazione
```python
def __init__(
    self,
    concept_threshold: float = 0.7,
    max_concepts: int = 10
):
    """
    Inizializza il sistema cognitivo.
    
    Args:
        concept_threshold: Soglia confidenza concetti
        max_concepts: Massimo concetti per input
    
    Raises:
        ValueError: Se parametri non validi
    """
```

### 4.2 Metodi Principali

#### process_input
```python
def process_input(
    self,
    text: str,
    context: Optional[Dict[str, Any]] = None
) -> CognitiveResult:
    """
    Elabora input cognitivamente.
    
    Args:
        text: Testo da elaborare
        context: Contesto opzionale
    
    Returns:
        CognitiveResult con:
            - concepts: Lista concetti
            - relations: Relazioni tra concetti
            - confidence: Confidenza elaborazione
    
    Raises:
        CognitiveProcessingError: Se elaborazione fallisce
    """
```

## 5. Gestione Errori

### 5.1 Gerarchia Eccezioni
```python
class ALLMAError(Exception):
    """Classe base errori ALLMA"""

class InitializationError(ALLMAError):
    """Errore inizializzazione"""

class ProcessingError(ALLMAError):
    """Errore elaborazione"""

class EmotionProcessingError(ProcessingError):
    """Errore elaborazione emotiva"""

class MemoryError(ProcessingError):
    """Errore gestione memoria"""

class CognitiveProcessingError(ProcessingError):
    """Errore elaborazione cognitiva"""
```

### 5.2 Best Practices Gestione Errori
```python
try:
    result = allma.process_input(text)
except InitializationError as e:
    # Gestisci errori inizializzazione
    logger.error(f"Inizializzazione fallita: {e}")
except ProcessingError as e:
    # Gestisci errori elaborazione
    logger.error(f"Elaborazione fallita: {e}")
except ALLMAError as e:
    # Gestisci altri errori ALLMA
    logger.error(f"Errore ALLMA: {e}")
except Exception as e:
    # Gestisci errori non previsti
    logger.critical(f"Errore non previsto: {e}")
```

## 6. ResponseSystem

### 6.1 ResponseSystem
```python
class ResponseSystem:
    def process_response(
        self,
        input_data: InputData,
        context: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        Elabora una risposta base.
        
        Args:
            input_data: Dati di input
            context: Contesto opzionale
        
        Returns:
            Response con testo e metadati
        """

    def generate_clarification(
        self,
        unknown_concept: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Genera una richiesta di chiarimento.
        
        Args:
            unknown_concept: Concetto sconosciuto
            context: Contesto opzionale
        
        Returns:
            Testo della richiesta di chiarimento
        """
```

## 7. PatternRecognition

### 7.1 PatternRecognition
```python
class PatternRecognition:
    def recognize_patterns(
        self,
        text: str,
        pattern_types: Optional[List[str]] = None
    ) -> List[Pattern]:
        """
        Identifica pattern nel testo.
        
        Args:
            text: Testo da analizzare
            pattern_types: Tipi di pattern da cercare
        
        Returns:
            Lista di pattern trovati
        """

    def extract_features(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Estrae features dal testo.
        
        Args:
            text: Testo da analizzare
        
        Returns:
            Dizionario di features
        """
```

## 8. LearningSystem

### 8.1 LearningSystem
```python
class LearningSystem:
    def identify_unknown_concepts(
        self,
        input_data: InputData,
        context: Optional[Dict[str, Any]] = None
    ) -> List[UnknownConcept]:
        """
        Identifica concetti sconosciuti.
        
        Args:
            input_data: Dati di input
            context: Contesto opzionale
        
        Returns:
            Lista di concetti sconosciuti
        """
    
    def generate_questions(
        self,
        unknown_concepts: List[UnknownConcept],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Question]:
        """
        Genera domande per chiarimenti.
        
        Args:
            unknown_concepts: Lista concetti sconosciuti
            context: Contesto opzionale
        
        Returns:
            Lista di domande generate
        """
    
    def learn_from_feedback(
        self,
        concept: str,
        explanation: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Apprende da feedback.
        
        Args:
            concept: Concetto da apprendere
            explanation: Spiegazione del concetto
            context: Contesto opzionale
        
        Returns:
            True se apprendimento riuscito
        """
```

## 9. Emotional System

### 9.1 EmotionalSystem
```python
class EmotionalSystem:
    def process_emotion(
        self,
        input_data: InputData,
        context: Optional[Dict[str, Any]] = None
    ) -> Emotion:
        """
        Elabora emozioni dall'input.
        
        Args:
            input_data: Dati di input
            context: Contesto opzionale
        
        Returns:
            Emotion elaborata
        """
    
    def integrate_context(
        self,
        emotion: Emotion,
        context: Context
    ) -> EmotionalContext:
        """
        Integra emozioni con il contesto.
        
        Args:
            emotion: Emozione da integrare
            context: Contesto da integrare
        
        Returns:
            Contesto emotivo integrato
        """
```

## 10. Memory System

### 10.1 MemorySystem
```python
class MemorySystem:
    def store(
        self,
        memory: Memory,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Memorizza una nuova informazione.
        
        Args:
            memory: Memoria da memorizzare
            context: Contesto opzionale
        
        Returns:
            True se memorizzazione riuscita
        """
    
    def recall(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Memory]:
        """
        Recupera memorie rilevanti.
        
        Args:
            query: Query di ricerca
            context: Contesto opzionale
            limit: Limite risultati
        
        Returns:
            Lista di memorie rilevanti
        """
```

## 11. Cognitive System

### 11.1 CognitiveSystem
```python
class CognitiveSystem:
    def extract_concepts(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Concept]:
        """
        Estrae concetti dal testo.
        
        Args:
            text: Testo da analizzare
            context: Contesto opzionale
        
        Returns:
            Lista di concetti estratti
        """
    
    def analyze_relations(
        self,
        concepts: List[Concept],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Relation]:
        """
        Analizza relazioni tra concetti.
        
        Args:
            concepts: Lista di concetti
            context: Contesto opzionale
        
        Returns:
            Lista di relazioni trovate
        """
    
    def process_context(
        self,
        text: str,
        context: Context
    ) -> ContextualUnderstanding:
        """
        Elabora comprensione contestuale.
        
        Args:
            text: Testo da analizzare
            context: Contesto da processare
        
        Returns:
            Comprensione contestuale
        """
```

## 12. Exceptions

```python
class ALLMAError(Exception):
    """Errore base ALLMA"""
    pass

class InitializationError(ALLMAError):
    """Errore inizializzazione"""
    pass

class ProcessingError(ALLMAError):
    """Errore elaborazione"""
    pass

class LearningError(ALLMAError):
    """Errore apprendimento"""
    pass

class MemoryError(ALLMAError):
    """Errore memoria"""
    pass
