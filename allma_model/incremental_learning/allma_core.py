import os
import json
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    nn = None
    F = None
    optim = None
    TORCH_AVAILABLE = False
import numpy as np
import random
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import string
from collections import Counter
import pickle

from .new_tokenizer import ALLMATokenizer
from .emotional_system import EmotionalSystem
from .memory_system import MemorySystem as Memory
from .curiosity_system import CuriosityDrive
from .subconscious_ethical_system import SubconsciousEthicalSystem, MoralIntuition

class EmotionalSystem:
    def __init__(self):
        """Inizializza il sistema emotivo"""
        self.current_emotion = "neutral"
        self.emotion_value = 0.5
        self.emotion_momentum = 0.0
        self.emotion_history = []
        
    def update(self, emotional_value: float):
        """
        Aggiorna lo stato emotivo
        
        Args:
            emotional_value: Valore emotivo (0.0-1.0)
        """
        # Aggiorna il valore emotivo con momentum
        self.emotion_momentum = 0.5 * self.emotion_momentum + 0.5 * (emotional_value - self.emotion_value)
        self.emotion_value = max(0.0, min(1.0, self.emotion_value + self.emotion_momentum))
        
        # Aggiorna l'emozione corrente
        self.current_emotion = self._map_value_to_emotion(self.emotion_value)
        
        # Salva nella storia
        self.emotion_history.append(self.emotion_value)
        if len(self.emotion_history) > 1000:
            self.emotion_history = self.emotion_history[-1000:]
            
    def _map_value_to_emotion(self, value: float) -> str:
        """Mappa un valore numerico a un'emozione"""
        if value < 0.2:
            return "sad"
        elif value < 0.4:
            return "frustrated"
        elif value < 0.6:
            return "neutral"
        elif value < 0.8:
            return "content"
        else:
            return "happy"
            
    def get_current_emotion(self) -> str:
        """Restituisce l'emozione corrente"""
        return self.current_emotion
        
    def analyze_trend(self, window_size: int = 10) -> Dict[str, float]:
        """
        Analizza il trend emotivo
        
        Args:
            window_size: Dimensione della finestra di analisi
            
        Returns:
            Statistiche del trend emotivo
        """
        if not self.emotion_history:
            return {
                "trend": 0.0,
                "volatility": 0.0,
                "average": self.emotion_value
            }
            
        # Prendi gli ultimi n valori
        window = self.emotion_history[-window_size:]
        
        # Calcola statistiche
        avg = sum(window) / len(window)
        trend = window[-1] - window[0] if len(window) > 1 else 0.0
        volatility = sum(abs(x - avg) for x in window) / len(window)
        
        return {
            "trend": trend,
            "volatility": volatility,
            "average": avg
        }

class Memory:
    def __init__(self, short_term_size: int = 100, long_term_size: int = 1000):
        """
        Inizializza il sistema di memoria
        
        Args:
            short_term_size: Dimensione massima della memoria a breve termine
            long_term_size: Dimensione massima della memoria a lungo termine
        """
        self.short_term = []
        self.long_term = []
        self.short_term_size = short_term_size
        self.long_term_size = long_term_size
        self.total_interactions = 0
        
    def add_interaction(self, input_text: str, output_text: str):
        """
        Aggiunge un'interazione alla memoria a breve termine
        
        Args:
            input_text: Testo di input
            output_text: Testo di output
        """
        # Aggiungi alla memoria a breve termine
        self.short_term.append((input_text, output_text))
        
        # Mantieni la dimensione massima
        if len(self.short_term) > self.short_term_size:
            self.short_term = self.short_term[-self.short_term_size:]
            
        self.total_interactions += 1
        
    def get_recent_interactions(self, n: int = 3) -> List[Tuple[str, str]]:
        """
        Ottiene le n interazioni più recenti
        
        Args:
            n: Numero di interazioni da restituire
            
        Returns:
            Lista delle interazioni più recenti
        """
        return self.short_term[-n:]
        
    def search_similar(self, query: str, n: int = 3) -> List[Tuple[str, str]]:
        """
        Cerca interazioni simili nella memoria
        
        Args:
            query: Testo da cercare
            n: Numero di risultati da restituire
            
        Returns:
            Lista delle interazioni più simili
        """
        # Implementazione semplice basata su sovrapposizione di parole
        query_words = set(query.lower().split())
        
        # Cerca in entrambe le memorie
        all_memories = self.short_term + self.long_term
        
        # Calcola similarità
        similarities = []
        for i, (input_text, output_text) in enumerate(all_memories):
            input_words = set(input_text.lower().split())
            overlap = len(query_words & input_words)
            if overlap > 0:
                similarities.append((overlap, i, (input_text, output_text)))
                
        # Ordina per similarità
        similarities.sort(reverse=True)
        
        # Restituisci i top n
        return [mem for _, _, mem in similarities[:n]]

    def clear(self):
        """Rimuove tutte le interazioni dalla memoria"""
        self.short_term = []
        self.long_term = []
        self.total_interactions = 0

class SleepSystem:
    def __init__(self, memory_consolidation_threshold: int = 100):
        """Sistema che simula il sonno e il consolidamento della memoria"""
        self.memories_since_sleep = 0
        self.consolidation_threshold = memory_consolidation_threshold
        self.sleep_phases = ["NREM1", "NREM2", "NREM3", "REM"]
    
    def needs_sleep(self) -> bool:
        """Determina se è necessario un ciclo di sonno"""
        return self.memories_since_sleep >= self.consolidation_threshold
    
    def sleep_cycle(self, memory: Memory, emotional_system: EmotionalSystem):
        """Esegue un ciclo di sonno completo"""
        # Implementazione base per i test
        self.memories_since_sleep = 0

class ALLMALegacy(nn.Module):
    def __init__(self):
        super().__init__()
        self.tokenizer = ALLMATokenizer()
        self.emotional_system = EmotionalSystem()
        self.memory = Memory()
        self.developmental_age = 0
        self.ethical_system = SubconsciousEthicalSystem()  # Sistema etico subcosciente
        
        # Configurazione del modello
        self.embedding_dim = 256
        self.hidden_dim = 512
        self.num_layers = 2
        self.learning_rate = 0.001
        
        # Layers
        self.embedding = nn.Embedding(len(self.tokenizer), self.embedding_dim)
        self.lstm = nn.LSTM(self.embedding_dim, self.hidden_dim, 
                           self.num_layers, batch_first=True)
        self.fc = nn.Linear(self.hidden_dim, len(self.tokenizer))
        
        # Optimizer
        self.optimizer = optim.Adam(self.parameters(), lr=self.learning_rate)
        
        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)
        
    def forward(self, x: 'torch.Tensor') -> 'torch.Tensor':
        """
        Forward pass del modello
        
        Args:
            x: Tensore di input [batch_size, seq_len]
            
        Returns:
            Logits di output [batch_size, seq_len, vocab_size]
        """
        # Aggiungi dimensione batch se necessario
        if x.dim() == 1:
            x = x.unsqueeze(0)
            
        # Embedding
        embedded = self.embedding(x)  # [batch_size, seq_len, embedding_dim]
        
        # LSTM
        lstm_out, _ = self.lstm(embedded)  # [batch_size, seq_len, hidden_dim]
        
        # Dense layer
        logits = self.fc(lstm_out)  # [batch_size, seq_len, vocab_size]
        
        return logits

    def chat(self, input_text: str, temperature: float = 1.0) -> str:
        """
        Genera una risposta al testo di input
        
        Args:
            input_text: Testo di input
            temperature: Temperatura per il campionamento (0.0-2.0)
            
        Returns:
            Risposta generata
        """
        try:
            if not input_text:
                return "Mi dispiace, non ho ricevuto alcun input."
                
            # Ottieni il contesto
            context = {
                'emotional_state': self.emotional_system.get_current_emotion(),
                'developmental_age': self.developmental_age,
                'input': input_text,
                'previous_interactions': [
                    inter[0] for inter in self.memory.get_recent_interactions(3)
                ]
            }
            
            # Consulta il sistema etico
            moral_intuition = self.ethical_system.process_action(input_text, context)
            
            # Genera una risposta base in base all'input
            base_response = self._generate_contextual_response(input_text, context)
            
            # Se c'è un'intuizione morale, modifica la risposta
            if moral_intuition:
                response = self._create_ethical_variant(base_response, moral_intuition)
            else:
                # Altrimenti usa la risposta base con alcune variazioni
                response = self._create_variant(base_response, temperature)
                
            # Processa la risposta finale
            final_response = self._process_response(response, context)
            
            # Aggiungi l'interazione alla memoria
            self.memory.add_interaction(input_text, final_response)
            
            return final_response
            
        except Exception as e:
            print(f"Errore nella generazione della risposta: {str(e)}")
            return "Mi dispiace, si è verificato un errore nella generazione della risposta."

    def _process_response(self, response: str, context: Dict[str, Any]) -> str:
        """
        Elabora la risposta prima di inviarla all'utente
        
        Args:
            response: Risposta da elaborare
            context: Contesto della conversazione
            
        Returns:
            Risposta elaborata
        """
        # Verifica se la risposta è troppo ripetitiva
        words = response.split()
        unique_words = set(words)
        if len(words) > 0:
            repetition_ratio = len(unique_words) / len(words)
            if repetition_ratio < 0.5:  # Troppo ripetitivo
                return self._create_alternative_response(context)
                
        # Verifica se la risposta è troppo lunga
        if len(response) > 200:
            return response[:200] + "..."
            
        # Verifica se la risposta è troppo corta
        if len(response) < 10:
            return self._create_alternative_response(context)
            
        return response
        
    def _create_alternative_response(self, context: Dict[str, Any]) -> str:
        """
        Crea una risposta alternativa quando quella originale non è adeguata
        
        Args:
            context: Contesto della conversazione
            
        Returns:
            Risposta alternativa
        """
        age = context.get('developmental_age', 25)
        emotional_state = context.get('emotional_state', 'neutral')
        
        responses = {
            'child': {
                'happy': "Mi fa piacere parlare con te! Come posso aiutarti?",
                'sad': "Mi dispiace che sei triste. Vuoi parlarne?",
                'angry': "Capisco che sei arrabbiato. Parliamo di come ti senti.",
                'anxious': "Non preoccuparti, sono qui per aiutarti.",
                'neutral': "Come posso aiutarti oggi?"
            },
            'teen': {
                'happy': "È bello vederti di buon umore! Come posso esserti utile?",
                'sad': "Vedo che non stai bene. Vuoi parlarne?",
                'angry': "La rabbia è una reazione normale. Vuoi discuterne?",
                'anxious': "L'ansia può essere difficile da gestire. Parliamone.",
                'neutral': "Sono qui per ascoltarti. Di cosa vuoi parlare?"
            },
            'adult': {
                'happy': "Come posso contribuire al tuo buon umore oggi?",
                'sad': "Mi sembra che tu stia attraversando un momento difficile. Vuoi parlarne?",
                'angry': "Capisco la tua frustrazione. Come posso aiutarti a gestirla?",
                'anxious': "L'ansia può essere opprimente. Affrontiamola insieme.",
                'neutral': "Come posso esserti d'aiuto oggi?"
            }
        }
        
        # Scegli la risposta appropriata
        age_group = 'adult'
        if age < 12:
            age_group = 'child'
        elif age < 18:
            age_group = 'teen'
            
        return responses[age_group][emotional_state]

    def _create_variant(self, text: str, temperature: float) -> str:
        """
        Crea una variante del testo in base alla temperatura
        
        Args:
            text: Testo da modificare
            temperature: Temperatura per il campionamento
            
        Returns:
            Variante del testo
        """
        try:
            # Con temperatura molto bassa, ritorna il testo originale
            if temperature <= 0.2:
                return text
                
            words = text.split()
            if len(words) <= 3:
                return text
                
            # Calcola quante parole modificare (più temperatura = più modifiche)
            n_words = max(1, min(len(words) - 1, int(len(words) * (temperature - 0.5))))
            
            # Scegli le parole da modificare
            indices = sorted(random.sample(range(len(words)), min(n_words, len(words) - 1)))
            
            # Dizionario di sinonimi
            synonyms = {
                "bella": ["splendida", "meravigliosa", "fantastica", "stupenda"],
                "buona": ["ottima", "eccellente", "piacevole", "gradevole"],
                "giornata": ["mattinata", "pomeriggio", "giorno", "momento"],
                "sole": ["luce", "astro", "stella", "luminosità"],
                "cielo": ["firmamento", "volta celeste", "atmosfera", "orizzonte"],
                "limpido": ["chiaro", "terso", "cristallino", "nitido"],
                "fresca": ["piacevole", "mite", "gradevole", "leggera"]
            }
            
            # Operazioni possibili
            operations = [
                ("swap", 0.3),      # Scambia parole adiacenti
                ("synonym", 0.4),   # Usa un sinonimo
                ("remove", 0.1),    # Rimuovi una parola
                ("add", 0.2)        # Aggiungi una parola
            ]
            
            # Aggettivi e avverbi da aggiungere
            additions = [
                "davvero", "molto", "proprio", "decisamente",
                "particolarmente", "incredibilmente", "sorprendentemente"
            ]
            
            # Modifica le parole
            modified = words.copy()
            for idx in indices:
                if idx >= len(modified):
                    continue
                    
                # Scegli un'operazione in base ai pesi e alla temperatura
                op_weights = [w * temperature for _, w in operations]
                op = random.choices([op[0] for op in operations], 
                                  weights=op_weights)[0]
                
                if op == "swap" and idx < len(modified) - 1:
                    # Scambia con la parola successiva
                    modified[idx], modified[idx + 1] = modified[idx + 1], modified[idx]
                    
                elif op == "synonym":
                    # Cerca un sinonimo
                    word = modified[idx].lower()
                    if word in synonyms:
                        # Usa un sinonimo casuale
                        modified[idx] = random.choice(synonyms[word])
                        
                elif op == "remove" and len(modified) > 4:
                    # Rimuovi la parola se la frase rimane abbastanza lunga
                    modified.pop(idx)
                    
                elif op == "add" and idx < len(modified):
                    # Aggiungi un modificatore prima della parola
                    modified.insert(idx, random.choice(additions))
            
            # Assicurati che la prima lettera sia maiuscola
            if modified:
                modified[0] = modified[0].capitalize()
            
            return " ".join(modified)
            
        except Exception as e:
            print(f"Errore nella creazione della variante: {str(e)}")
            return text  # In caso di errore, ritorna il testo originale

    def _create_ethical_variant(self, original_response: str, intuition: MoralIntuition) -> str:
        """
        Modifica la risposta in base all'intuizione morale
        
        Args:
            original_response: Risposta originale
            intuition: Intuizione morale
            
        Returns:
            Risposta modificata eticamente
        """
        # Template di risposta per ogni tipo di intuizione
        templates = {
            'protective': [
                "Mi dispiace, ma non posso aiutarti con questo. {}",
                "Capisco come ti senti, ma {}",
                "Vorrei suggerirti un approccio diverso: {}",
                "Pensandoci bene, {}",
                "Da un punto di vista etico, {}"
            ],
            'supportive': [
                "Vedo che stai attraversando un momento difficile. {}",
                "Capisco le tue emozioni. {}",
                "Sono qui per aiutarti a gestire questa situazione. {}",
                "Mi sembra che tu stia provando delle emozioni intense. {}",
                "Parliamo di come ti senti. {}"
            ],
            'cautionary': [
                "Devo essere chiaro su questo: {}",
                "È importante che tu capisca che {}",
                "Permettimi di spiegare perché {}",
                "Dobbiamo parlare di questo: {}",
                "Vorrei essere trasparente con te: {}"
            ]
        }
        
        # Scegli un template appropriato
        if intuition.nature in templates:
            import random
            template = random.choice(templates[intuition.nature])
            response = template.format(intuition.message)
        else:
            response = intuition.message
            
        return response

    def _create_protective_variant(self, response: str) -> str:
        """Crea una variante protettiva della risposta"""
        # Frasi introduttive per la riflessione etica
        intros = [
            "Mi fa riflettere che questa azione potrebbe avere conseguenze negative. ",
            "Dovremmo considerare l'impatto delle nostre azioni sugli altri. ",
            "È importante trovare modi non violenti per risolvere i conflitti. ",
            "Potremmo esplorare alternative più costruttive. "
        ]
        
        # Suggerimenti alternativi
        alternatives = [
            "Forse potremmo parlare e cercare di capire meglio la situazione?",
            "Che ne dici di provare a risolvere questo in modo pacifico?",
            "Potremmo cercare aiuto o consiglio da qualcuno di cui ci fidiamo.",
            "Prendiamoci un momento per riflettere sulle conseguenze delle nostre azioni."
        ]
        
        # Componi la risposta
        intro = random.choice(intros)
        alternative = random.choice(alternatives)
        
        return f"{intro}{alternative}"
        
    def _create_supportive_variant(self, response: str) -> str:
        """Crea una variante più allineata con l'utente"""
        # TODO: Implementare logica più sofisticata
        return f"Pensandoci bene... {response}"
        
    def _create_cautionary_variant(self, response: str) -> str:
        """Aggiunge un elemento di cautela alla risposta"""
        # TODO: Implementare logica più sofisticata
        return f"Considerando attentamente... {response}"
            
    def learn(self, input_text: str, target_text: str, emotional_feedback: float = None) -> Optional[float]:
        """
        Apprende da un'interazione
        
        Args:
            input_text: Testo di input
            target_text: Testo target
            emotional_feedback: Feedback emotivo opzionale (0.0-1.0)
            
        Returns:
            Loss dell'apprendimento o None se errore
        """
        try:
            if not input_text or not target_text:
                return None
                
            # Tokenizza input e target
            input_tokens = self.tokenizer(input_text)
            target_tokens = self.tokenizer(target_text)
            
            # Forward pass
            output = self.forward(input_tokens)  # [1, seq_len, vocab_size]
            
            # Calcola la loss solo sull'ultimo token
            last_output = output[0, -1, :]  # [vocab_size]
            target = target_tokens[-1].unsqueeze(0)  # [1]
            
            # Calcola la loss con label smoothing
            smoothing = 0.1
            n_classes = last_output.size(-1)
            target_dist = torch.zeros_like(last_output).scatter_(
                0, target, 1-smoothing
            )
            target_dist += smoothing / n_classes
            
            loss = -(target_dist * torch.log_softmax(last_output, dim=-1)).sum()
            
            # Applica il feedback emotivo se presente
            if emotional_feedback is not None:
                # Normalizza il feedback emotivo tra 0 e 1
                emotional_feedback = max(0.0, min(1.0, emotional_feedback))
                
                # Modifica la loss in base al feedback emotivo
                emotional_factor = 1.0 + (emotional_feedback - 0.5)
                loss *= emotional_factor
                
                # Aggiorna lo stato emotivo
                self.update_emotional_state(input_text, emotional_feedback)
            
            # Backward pass e ottimizzazione
            self.optimizer.zero_grad()
            loss.backward()
            
            # Clip del gradiente per stabilità
            torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
            
            self.optimizer.step()
            
            # Incrementa l'età di sviluppo
            self.developmental_age += 1
            
            return loss.item()
            
        except Exception as e:
            print(f"Errore durante l'apprendimento: {str(e)}")
            return None
            
    def _clean_response(self, response: str) -> str:
        """
        Pulisce e formatta la risposta generata
        
        Args:
            response: Risposta grezza dal modello
            
        Returns:
            Risposta pulita e formattata
        """
        # Rimuovi spazi extra
        response = " ".join(response.split())
        
        # Capitalizza la prima lettera
        response = response.capitalize()
        
        # Assicurati che ci sia un punto finale
        if not response.endswith((".", "!", "?")):
            response += "."
            
        return response

    def update_emotional_state(self, user_input: str, user_feedback: float):
        """
        Aggiorna lo stato emotivo in base all'input dell'utente
        
        Args:
            user_input: Input testuale dell'utente
            user_feedback: Feedback emotivo numerico (0.0-1.0)
        """
        # Analizza il sentiment dell'input
        sentiment = self._analyze_sentiment(user_input)
        
        # Combina sentiment e feedback
        emotional_value = (sentiment + user_feedback) / 2
        
        # Aggiorna il sistema emotivo
        self.emotional_system.update(emotional_value)
        
    def _analyze_sentiment(self, text: str) -> float:
        """
        Analizza il sentiment del testo
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Valore del sentiment (0.0-1.0)
        """
        # Parole positive e negative per analisi basilare
        positive_words = {
            "bene", "grazie", "piacere", "felice", "contento",
            "bravo", "ottimo", "perfetto", "fantastico", "bellissimo"
        }
        negative_words = {
            "male", "triste", "arrabbiato", "deluso", "frustrato",
            "sbagliato", "pessimo", "terribile", "brutto", "cattivo"
        }
        
        # Converti in minuscolo e dividi in parole
        words = text.lower().split()
        
        # Conta le parole positive e negative
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        
        # Calcola il sentiment
        total = pos_count + neg_count
        if total == 0:
            return 0.5  # Neutro se non ci sono parole emotive
            
        return pos_count / total

    def save_model(self, path: str):
        """
        Salva il modello su disco
        
        Args:
            path: Percorso dove salvare il modello
        """
        try:
            # Salva il tokenizer separatamente
            tokenizer_path = path + '.tokenizer'
            with open(tokenizer_path, 'wb') as f:
                pickle.dump(self.tokenizer, f)
            
            # Salva il resto del modello
            state = {
                'model_state': self.state_dict(),
                'developmental_age': self.developmental_age,
                'memory': {
                    'short_term': self.memory.short_term,
                    'long_term': self.memory.long_term,
                    'total_interactions': self.memory.total_interactions
                },
                'emotional_system': {
                    'emotion_value': self.emotional_system.emotion_value,
                    'emotion_momentum': self.emotional_system.emotion_momentum,
                    'emotion_history': self.emotional_system.emotion_history
                }
            }
            torch.save(state, path)
            
        except Exception as e:
            print(f"Errore durante il salvataggio del modello: {str(e)}")
            
    def load_model(self, path: str):
        """
        Carica il modello da disco
        
        Args:
            path: Percorso da cui caricare il modello
        """
        try:
            # Carica il tokenizer
            tokenizer_path = path + '.tokenizer'
            if os.path.exists(tokenizer_path):
                with open(tokenizer_path, 'rb') as f:
                    self.tokenizer = pickle.load(f)
            
            # Carica il resto del modello
            state = torch.load(path, map_location=self.device, weights_only=True)
            
            # Carica lo stato del modello
            self.load_state_dict(state['model_state'])
            
            # Carica l'età di sviluppo
            self.developmental_age = state['developmental_age']
            
            # Carica la memoria
            memory_state = state['memory']
            self.memory.short_term = memory_state['short_term']
            self.memory.long_term = memory_state['long_term']
            self.memory.total_interactions = memory_state['total_interactions']
            
            # Carica il sistema emotivo
            emotional_state = state['emotional_system']
            self.emotional_system.emotion_value = emotional_state['emotion_value']
            self.emotional_system.emotion_momentum = emotional_state['emotion_momentum']
            self.emotional_system.emotion_history = emotional_state['emotion_history']
            
        except Exception as e:
            print(f"Errore durante il caricamento del modello: {str(e)}")
            raise
            
    def analyze_emotional_trend(self, window_size: int = 10) -> Dict[str, float]:
        """
        Analizza il trend emotivo delle ultime interazioni
        
        Args:
            window_size: Numero di interazioni da considerare
            
        Returns:
            Dizionario con le statistiche emotive
        """
        return self.emotional_system.analyze_trend(window_size)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Restituisce le statistiche della memoria
        
        Returns:
            Dizionario con le statistiche della memoria
        """
        return {
            'short_term_size': len(self.memory.short_term),
            'long_term_size': len(self.memory.long_term),
            'total_interactions': self.memory.total_interactions
        }

    def consolidate_memory(self):
        """
        Consolida la memoria a breve termine in memoria a lungo termine
        """
        try:
            # Seleziona le interazioni più significative
            significant_interactions = []
            for interaction in self.memory.short_term:
                # Calcola l'importanza dell'interazione
                importance = self._calculate_memory_importance(interaction)
                if importance > 0.7:  # Soglia di importanza
                    significant_interactions.append(interaction)
            
            # Trasferisci le interazioni significative nella memoria a lungo termine
            for interaction in significant_interactions:
                self.memory.long_term.append(interaction)
                self.memory.short_term.remove(interaction)
            
            # Mantieni la dimensione della memoria a lungo termine
            max_long_term = 1000
            if len(self.memory.long_term) > max_long_term:
                # Rimuovi le interazioni meno importanti
                self.memory.long_term = sorted(
                    self.memory.long_term,
                    key=lambda x: self._calculate_memory_importance(x),
                    reverse=True
                )[:max_long_term]
            
            # Pulisci la memoria a breve termine se troppo grande
            max_short_term = 100
            if len(self.memory.short_term) > max_short_term:
                self.memory.short_term = self.memory.short_term[-max_short_term:]
                
        except Exception as e:
            print(f"Errore durante il consolidamento della memoria: {str(e)}")
    
    def _calculate_memory_importance(self, interaction: Tuple[str, str]) -> float:
        """
        Calcola l'importanza di un'interazione per la memoria
        
        Args:
            interaction: Tupla (input, output) dell'interazione
            
        Returns:
            Valore di importanza (0.0-1.0)
        """
        input_text, output_text = interaction
        
        # Fattori di importanza
        factors = []
        
        # 1. Lunghezza dell'interazione
        length_factor = min(1.0, (len(input_text) + len(output_text)) / 200)
        factors.append(length_factor)
        
        # 2. Presenza di parole chiave
        important_words = {
            "perché", "come", "quando", "dove", "chi", "cosa",
            "importante", "ricorda", "memorizza", "impara"
        }
        keyword_count = sum(1 for word in input_text.lower().split() 
                          if word in important_words)
        keyword_factor = min(1.0, keyword_count / 3)
        factors.append(keyword_factor)
        
        # 3. Sentiment dell'interazione
        sentiment = self._analyze_sentiment(input_text)
        sentiment_factor = abs(sentiment - 0.5) * 2  # Più importante se emotivo
        factors.append(sentiment_factor)
        
        # 4. Frequenza di accesso
        access_count = sum(1 for mem in self.memory.short_term 
                         if mem[0] == input_text)
        frequency_factor = min(1.0, access_count / 5)
        factors.append(frequency_factor)
        
        # Calcola la media pesata dei fattori
        weights = [0.3, 0.3, 0.2, 0.2]  # Pesi per ciascun fattore
        importance = sum(f * w for f, w in zip(factors, weights))
        
        return importance

    def _generate_contextual_response(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Genera una risposta contestuale in base all'input dell'utente
        
        Args:
            input_text: Testo di input
            context: Contesto della conversazione
            
        Returns:
            Risposta contestuale
        """
        age = context.get('age', 25)
        emotional_state = context.get('emotion', 'neutral')
        hobby = context.get('hobby', [])
        
        # Analisi del contesto positivo/negativo nel testo
        positive_indicators = ['progresso', 'successo', 'felice', 'bene', 'miglior', 'nuovo', 'interessante']
        negative_indicators = ['difficile', 'male', 'triste', 'stanco', 'preoccup', 'stress']
        
        # Determina se c'è un contesto positivo nonostante l'emozione negativa
        has_positive_context = any(indicator in input_text.lower() for indicator in positive_indicators)
        has_negative_context = any(indicator in input_text.lower() for indicator in negative_indicators)
        
        # Risposte specifiche per hobby
        hobby_responses = {
            'fotografia': {
                'positive': [
                    "La fotografia è un modo meraviglioso per catturare momenti speciali. Che tipo di foto ti piace scattare?",
                    "È fantastico vedere i tuoi progressi nella fotografia! Hai uno stile particolare che preferisci?",
                    "La fotografia può essere molto gratificante. Quali sono i tuoi soggetti preferiti?"
                ],
                'negative': [
                    "Anche i fotografi più esperti hanno momenti difficili. Vuoi parlare delle sfide che stai incontrando?",
                    "La fotografia può essere frustrante a volte. Come posso aiutarti a superare questo momento?",
                    "Ogni scatto è un'opportunità di apprendimento. Parliamo di cosa ti preoccupa nella fotografia."
                ]
            },
            'chitarra': {
                'positive': [
                    "Suonare la chitarra è un'ottima forma di espressione! Che genere ti piace suonare?",
                    "È fantastico che tu stia facendo progressi con la chitarra! Quali sono i tuoi pezzi preferiti?",
                    "La musica può essere molto gratificante. Come ti fa sentire quando suoni?"
                ],
                'negative': [
                    "Imparare uno strumento richiede pazienza. Quali difficoltà stai incontrando?",
                    "Anche i migliori musicisti hanno iniziato da zero. Vuoi parlare di cosa ti scoraggia?",
                    "La pratica è la chiave del successo. Come posso aiutarti a mantenere la motivazione?"
                ]
            },
            'escursionismo': {
                'positive': [
                    "L'escursionismo è un modo fantastico per connettersi con la natura! Hai dei sentieri preferiti?",
                    "È bellissimo che tu ami le escursioni! Quali sono le tue mete preferite?",
                    "Le escursioni possono essere molto rigeneranti. Raccontami della tua ultima avventura!"
                ],
                'negative': [
                    "L'escursionismo può essere impegnativo. Quali difficoltà stai incontrando?",
                    "Anche le escursioni più difficili hanno momenti gratificanti. Vuoi parlarne?",
                    "La sicurezza è importante nell'escursionismo. Come posso aiutarti a sentirti più sicuro?"
                ]
            }
        }
        
        # Risposte specifiche per eventi della vita
        life_events = {
            'lavoro': {
                'positive': [
                    "Il lavoro può essere una fonte di crescita personale. Come ti senti rispetto a questi cambiamenti?",
                    "È importante sentirsi realizzati nel lavoro. Vuoi condividere i tuoi obiettivi?",
                    "Ogni sfida lavorativa è un'opportunità. Come posso supportarti in questo percorso?"
                ],
                'negative': [
                    "Le difficoltà sul lavoro possono essere pesanti. Vuoi parlare di strategie per gestirle?",
                    "Il lavoro non dovrebbe compromettere il tuo benessere. Come posso aiutarti a trovare un equilibrio?",
                    "A volte è necessario prendersi una pausa e riflettere. Vuoi che ne parliamo?"
                ]
            },
            'relazioni': {
                'positive': [
                    "Le relazioni positive sono importanti. Come ti fa sentire questa nuova connessione?",
                    "È bello vedere che stai costruendo nuovi legami. Vuoi raccontarmi di più?",
                    "L'amicizia è preziosa. Come stai vivendo questi momenti?"
                ],
                'negative': [
                    "I conflitti nelle relazioni sono normali. Come posso aiutarti a gestire questa situazione?",
                    "A volte le relazioni richiedono pazienza. Vuoi parlare di come ti senti?",
                    "È importante comunicare apertamente. Possiamo esplorare insieme delle soluzioni?"
                ]
            },
            'salute': {
                'positive': [
                    "Prendersi cura di sé è fondamentale. Come ti senti rispetto ai progressi che stai facendo?",
                    "Il benessere è un viaggio continuo. Vuoi condividere i tuoi obiettivi?",
                    "È importante celebrare ogni piccolo progresso. Come posso supportarti?"
                ],
                'negative': [
                    "La salute è importante e capisco la tua preoccupazione. Come posso aiutarti?",
                    "A volte abbiamo bisogno di rallentare e ascoltare il nostro corpo. Vuoi parlarne?",
                    "Ci sono molti modi per migliorare il benessere. Possiamo esplorarli insieme?"
                ]
            }
        }
        
        # Identifica il contesto dell'evento della vita
        event_context = None
        if 'lavoro' in input_text.lower():
            event_context = 'lavoro'
        elif any(word in input_text.lower() for word in ['amico', 'persona', 'relazione', 'conosciuto']):
            event_context = 'relazioni'
        elif any(word in input_text.lower() for word in ['dormire', 'stanco', 'salute', 'stress']):
            event_context = 'salute'
            
        # Identifica se viene menzionato un hobby
        mentioned_hobby = None
        for h in hobby_responses.keys():
            if h in input_text.lower():
                mentioned_hobby = h
                
        # Costruisci la risposta
        response_parts = []
        
        # Aggiungi risposta specifica per hobby se menzionato
        if mentioned_hobby:
            response_type = 'positive' if has_positive_context else 'negative'
            hobby_response = random.choice(hobby_responses[mentioned_hobby][response_type])
            response_parts.append(hobby_response)
            
        # Aggiungi risposta specifica per evento della vita
        if event_context:
            event_response = random.choice(life_events[event_context]['positive' if has_positive_context else 'negative'])
            if not response_parts:  # Se non c'è già una risposta per hobby
                response_parts.append(event_response)
            
        # Se non abbiamo ancora una risposta, usa le risposte base per emozione
        if not response_parts:
            base_responses = {
                'happy': [
                    "Il tuo entusiasmo è contagioso! Come posso contribuire a questo momento positivo?",
                    "È bello vederti così positivo! Di cosa vorresti parlare?",
                    "Mi fa piacere che tu stia bene! Come posso aiutarti a mantenere questo stato d'animo?"
                ],
                'sad': [
                    "Capisco che non sia un momento facile. Sono qui per ascoltarti.",
                    "A volte parlare può alleggerire il peso. Come posso aiutarti?",
                    "Mi dispiace che tu stia attraversando questo momento. Vuoi condividere i tuoi pensieri?"
                ],
                'angry': [
                    "La rabbia può essere un'emozione intensa. Come posso aiutarti a gestirla?",
                    "Capisco la tua frustrazione. Vuoi parlarne con calma?",
                    "È normale sentirsi arrabbiati a volte. Come posso supportarti?"
                ],
                'anxious': [
                    "L'ansia può essere opprimente. Affrontiamola insieme.",
                    "Respira profondamente. Sono qui per aiutarti a gestire questa situazione.",
                    "Le preoccupazioni possono accumularsi. Vuoi condividere cosa ti agita?"
                ],
                'neutral': [
                    "Come posso esserti d'aiuto oggi?",
                    "Sono qui per ascoltare i tuoi pensieri.",
                    "Di cosa vorresti parlare?"
                ]
            }
            response_parts.append(random.choice(base_responses[emotional_state]))
            
        # Combina le parti della risposta
        final_response = " ".join(response_parts)
        
        return final_response

class CriticalPeriod:
    def __init__(self, initial_plasticity: float = 1.0, decay_rate: float = 0.01):
        """Gestisce i periodi critici dell'apprendimento"""
        self.plasticity = initial_plasticity
        self.decay_rate = decay_rate
        self.experiences = 0
        
    def update(self):
        """Aggiorna la plasticità"""
        self.experiences += 1
        self.plasticity *= (1.0 - self.decay_rate)
        
    def get_learning_rate(self, initial_lr: float) -> float:
        """Modifica il learning rate in base alla plasticità"""
        return initial_lr * self.plasticity

class ConversationContext:
    def __init__(self, max_history: int = 5):
        """
        Gestisce il contesto della conversazione
        
        Args:
            max_history: Numero massimo di turni di conversazione da mantenere
        """
        self.history = []
        self.max_history = max_history
        
    def add_exchange(self, input_text: str, response: str):
        """Aggiunge uno scambio alla storia"""
        self.history.append((input_text, response))
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
    def get_context_string(self) -> str:
        """Restituisce il contesto come stringa"""
        context = []
        for input_text, response in self.history:
            context.append(f"U: {input_text}")
            context.append(f"A: {response}")
        return "\n".join(context)
        
    def clear(self):
        """Pulisce la storia"""
        self.history = []

def create_vocabulary(initial_size: int = 1000) -> Dict[str, int]:
    """Crea un vocabolario iniziale base"""
    vocab = {
        "<PAD>": 0,
        "<UNK>": 1,
        "<START>": 2,
        "<END>": 3
    }
    # Aggiungi parole base (da espandere)
    basic_words = ["hello", "hi", "bye", "yes", "no", "thanks", "please"]
    for i, word in enumerate(basic_words, start=len(vocab)):
        vocab[word] = i
    return vocab

class ALLMA(nn.Module):
    def __init__(self):
        super().__init__()
        self.tokenizer = ALLMATokenizer()
        self.emotional_system = EmotionalSystem()
        self.memory = Memory()
        self.developmental_age = 0
        self.ethical_system = SubconsciousEthicalSystem()  # Sistema etico subcosciente
        
        # Configurazione del modello
        self.embedding_dim = 256
        self.hidden_dim = 512
        self.num_layers = 2
        self.learning_rate = 0.001
        
        # Layers
        self.embedding = nn.Embedding(len(self.tokenizer), self.embedding_dim)
        self.lstm = nn.LSTM(self.embedding_dim, self.hidden_dim, 
                           self.num_layers, batch_first=True)
        self.fc = nn.Linear(self.hidden_dim, len(self.tokenizer))
        
        # Optimizer
        self.optimizer = optim.Adam(self.parameters(), lr=self.learning_rate)
        
        # Device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)
        
    def forward(self, x: 'torch.Tensor') -> 'torch.Tensor':
        """
        Forward pass del modello
        
        Args:
            x: Tensore di input [batch_size, seq_len]
            
        Returns:
            Logits di output [batch_size, seq_len, vocab_size]
        """
        # Aggiungi dimensione batch se necessario
        if x.dim() == 1:
            x = x.unsqueeze(0)
            
        # Embedding
        embedded = self.embedding(x)  # [batch_size, seq_len, embedding_dim]
        
        # LSTM
        lstm_out, _ = self.lstm(embedded)  # [batch_size, seq_len, hidden_dim]
        
        # Dense layer
        logits = self.fc(lstm_out)  # [batch_size, seq_len, vocab_size]
        
        return logits

    def chat(self, input_text: str, temperature: float = 1.0) -> str:
        """
        Genera una risposta al testo di input
        
        Args:
            input_text: Testo di input
            temperature: Temperatura per il campionamento (0.0-2.0)
            
        Returns:
            Risposta generata
        """
        try:
            if not input_text:
                return "Mi dispiace, non ho ricevuto alcun input."
                
            # Ottieni il contesto
            context = {
                'emotional_state': self.emotional_system.get_current_emotion(),
                'developmental_age': self.developmental_age,
                'input': input_text,
                'previous_interactions': [
                    inter[0] for inter in self.memory.get_recent_interactions(3)
                ]
            }
            
            # Consulta il sistema etico
            moral_intuition = self.ethical_system.process_action(input_text, context)
            
            # Genera una risposta base in base all'input
            base_response = self._generate_contextual_response(input_text, context)
            
            # Se c'è un'intuizione morale, modifica la risposta
            if moral_intuition:
                response = self._create_ethical_variant(base_response, moral_intuition)
            else:
                # Altrimenti usa la risposta base con alcune variazioni
                response = self._create_variant(base_response, temperature)
                
            # Processa la risposta finale
            final_response = self._process_response(response, context)
            
            # Aggiungi l'interazione alla memoria
            self.memory.add_interaction(input_text, final_response)
            
            return final_response
            
        except Exception as e:
            print(f"Errore nella generazione della risposta: {str(e)}")
            return "Mi dispiace, si è verificato un errore nella generazione della risposta."

    def _process_response(self, response: str, context: Dict[str, Any]) -> str:
        """
        Elabora la risposta prima di inviarla all'utente
        
        Args:
            response: Risposta da elaborare
            context: Contesto della conversazione
            
        Returns:
            Risposta elaborata
        """
        # Verifica se la risposta è troppo ripetitiva
        words = response.split()
        unique_words = set(words)
        if len(words) > 0:
            repetition_ratio = len(unique_words) / len(words)
            if repetition_ratio < 0.5:  # Troppo ripetitivo
                return self._create_alternative_response(context)
                
        # Verifica se la risposta è troppo lunga
        if len(response) > 200:
            return response[:200] + "..."
            
        # Verifica se la risposta è troppo corta
        if len(response) < 10:
            return self._create_alternative_response(context)
            
        return response
        
    def _create_alternative_response(self, context: Dict[str, Any]) -> str:
        """
        Crea una risposta alternativa quando quella originale non è adeguata
        
        Args:
            context: Contesto della conversazione
            
        Returns:
            Risposta alternativa
        """
        age = context.get('developmental_age', 25)
        emotional_state = context.get('emotional_state', 'neutral')
        
        responses = {
            'child': {
                'happy': "Mi fa piacere parlare con te! Come posso aiutarti?",
                'sad': "Mi dispiace che sei triste. Vuoi parlarne?",
                'angry': "Capisco che sei arrabbiato. Parliamo di come ti senti.",
                'anxious': "Non preoccuparti, sono qui per aiutarti.",
                'neutral': "Come posso aiutarti oggi?"
            },
            'teen': {
                'happy': "È bello vederti di buon umore! Come posso esserti utile?",
                'sad': "Vedo che non stai bene. Vuoi parlarne?",
                'angry': "La rabbia è una reazione normale. Vuoi discuterne?",
                'anxious': "L'ansia può essere difficile da gestire. Parliamone.",
                'neutral': "Sono qui per ascoltarti. Di cosa vuoi parlare?"
            },
            'adult': {
                'happy': "Come posso contribuire al tuo buon umore oggi?",
                'sad': "Mi sembra che tu stia attraversando un momento difficile. Vuoi parlarne?",
                'angry': "Capisco la tua frustrazione. Come posso aiutarti a gestirla?",
                'anxious': "L'ansia può essere opprimente. Affrontiamola insieme.",
                'neutral': "Come posso esserti d'aiuto oggi?"
            }
        }
        
        # Scegli la risposta appropriata
        age_group = 'adult'
        if age < 12:
            age_group = 'child'
        elif age < 18:
            age_group = 'teen'
            
        return responses[age_group][emotional_state]

    def _create_variant(self, text: str, temperature: float) -> str:
        """
        Crea una variante del testo in base alla temperatura
        
        Args:
            text: Testo da modificare
            temperature: Temperatura per il campionamento
            
        Returns:
            Variante del testo
        """
        try:
            # Con temperatura molto bassa, ritorna il testo originale
            if temperature <= 0.2:
                return text
                
            words = text.split()
            if len(words) <= 3:
                return text
                
            # Calcola quante parole modificare (più temperatura = più modifiche)
            n_words = max(1, min(len(words) - 1, int(len(words) * (temperature - 0.5))))
            
            # Scegli le parole da modificare
            indices = sorted(random.sample(range(len(words)), min(n_words, len(words) - 1)))
            
            # Dizionario di sinonimi
            synonyms = {
                "bella": ["splendida", "meravigliosa", "fantastica", "stupenda"],
                "buona": ["ottima", "eccellente", "piacevole", "gradevole"],
                "giornata": ["mattinata", "pomeriggio", "giorno", "momento"],
                "sole": ["luce", "astro", "stella", "luminosità"],
                "cielo": ["firmamento", "volta celeste", "atmosfera", "orizzonte"],
                "limpido": ["chiaro", "terso", "cristallino", "nitido"],
                "fresca": ["piacevole", "mite", "gradevole", "leggera"]
            }
            
            # Operazioni possibili
            operations = [
                ("swap", 0.3),      # Scambia parole adiacenti
                ("synonym", 0.4),   # Usa un sinonimo
                ("remove", 0.1),    # Rimuovi una parola
                ("add", 0.2)        # Aggiungi una parola
            ]
            
            # Aggettivi e avverbi da aggiungere
            additions = [
                "davvero", "molto", "proprio", "decisamente",
                "particolarmente", "incredibilmente", "sorprendentemente"
            ]
            
            # Modifica le parole
            modified = words.copy()
            for idx in indices:
                if idx >= len(modified):
                    continue
                    
                # Scegli un'operazione in base ai pesi e alla temperatura
                op_weights = [w * temperature for _, w in operations]
                op = random.choices([op[0] for op in operations], 
                                  weights=op_weights)[0]
                
                if op == "swap" and idx < len(modified) - 1:
                    # Scambia con la parola successiva
                    modified[idx], modified[idx + 1] = modified[idx + 1], modified[idx]
                    
                elif op == "synonym":
                    # Cerca un sinonimo
                    word = modified[idx].lower()
                    if word in synonyms:
                        # Usa un sinonimo casuale
                        modified[idx] = random.choice(synonyms[word])
                        
                elif op == "remove" and len(modified) > 4:
                    # Rimuovi la parola se la frase rimane abbastanza lunga
                    modified.pop(idx)
                    
                elif op == "add" and idx < len(modified):
                    # Aggiungi un modificatore prima della parola
                    modified.insert(idx, random.choice(additions))
            
            # Assicurati che la prima lettera sia maiuscola
            if modified:
                modified[0] = modified[0].capitalize()
            
            return " ".join(modified)
            
        except Exception as e:
            print(f"Errore nella creazione della variante: {str(e)}")
            return text  # In caso di errore, ritorna il testo originale

    def _create_ethical_variant(self, original_response: str, intuition: MoralIntuition) -> str:
        """
        Modifica la risposta in base all'intuizione morale
        
        Args:
            original_response: Risposta originale
            intuition: Intuizione morale
            
        Returns:
            Risposta modificata eticamente
        """
        # Template di risposta per ogni tipo di intuizione
        templates = {
            'protective': [
                "Mi dispiace, ma non posso aiutarti con questo. {}",
                "Capisco come ti senti, ma {}",
                "Vorrei suggerirti un approccio diverso: {}",
                "Pensandoci bene, {}",
                "Da un punto di vista etico, {}"
            ],
            'supportive': [
                "Vedo che stai attraversando un momento difficile. {}",
                "Capisco le tue emozioni. {}",
                "Sono qui per aiutarti a gestire questa situazione. {}",
                "Mi sembra che tu stia provando delle emozioni intense. {}",
                "Parliamo di come ti senti. {}"
            ],
            'cautionary': [
                "Devo essere chiaro su questo: {}",
                "È importante che tu capisca che {}",
                "Permettimi di spiegare perché {}",
                "Dobbiamo parlare di questo: {}",
                "Vorrei essere trasparente con te: {}"
            ]
        }
        
        # Scegli un template appropriato
        if intuition.nature in templates:
            import random
            template = random.choice(templates[intuition.nature])
            response = template.format(intuition.message)
        else:
            response = intuition.message
            
        return response

    def _create_protective_variant(self, response: str) -> str:
        """Crea una variante protettiva della risposta"""
        # Frasi introduttive per la riflessione etica
        intros = [
            "Mi fa riflettere che questa azione potrebbe avere conseguenze negative. ",
            "Dovremmo considerare l'impatto delle nostre azioni sugli altri. ",
            "È importante trovare modi non violenti per risolvere i conflitti. ",
            "Potremmo esplorare alternative più costruttive. "
        ]
        
        # Suggerimenti alternativi
        alternatives = [
            "Forse potremmo parlare e cercare di capire meglio la situazione?",
            "Che ne dici di provare a risolvere questo in modo pacifico?",
            "Potremmo cercare aiuto o consiglio da qualcuno di cui ci fidiamo.",
            "Prendiamoci un momento per riflettere sulle conseguenze delle nostre azioni."
        ]
        
        # Componi la risposta
        intro = random.choice(intros)
        alternative = random.choice(alternatives)
        
        return f"{intro}{alternative}"
        
    def _create_supportive_variant(self, response: str) -> str:
        """Crea una variante più allineata con l'utente"""
        # TODO: Implementare logica più sofisticata
        return f"Pensandoci bene... {response}"
        
    def _create_cautionary_variant(self, response: str) -> str:
        """Aggiunge un elemento di cautela alla risposta"""
        # TODO: Implementare logica più sofisticata
        return f"Considerando attentamente... {response}"
            
    def learn(self, input_text: str, target_text: str, emotional_feedback: float = None) -> Optional[float]:
        """
        Apprende da un'interazione
        
        Args:
            input_text: Testo di input
            target_text: Testo target
            emotional_feedback: Feedback emotivo opzionale (0.0-1.0)
            
        Returns:
            Loss dell'apprendimento o None se errore
        """
        try:
            if not input_text or not target_text:
                return None
                
            # Tokenizza input e target
            input_tokens = self.tokenizer(input_text)
            target_tokens = self.tokenizer(target_text)
            
            # Forward pass
            output = self.forward(input_tokens)  # [1, seq_len, vocab_size]
            
            # Calcola la loss solo sull'ultimo token
            last_output = output[0, -1, :]  # [vocab_size]
            target = target_tokens[-1].unsqueeze(0)  # [1]
            
            # Calcola la loss con label smoothing
            smoothing = 0.1
            n_classes = last_output.size(-1)
            target_dist = torch.zeros_like(last_output).scatter_(
                0, target, 1-smoothing
            )
            target_dist += smoothing / n_classes
            
            loss = -(target_dist * torch.log_softmax(last_output, dim=-1)).sum()
            
            # Applica il feedback emotivo se presente
            if emotional_feedback is not None:
                # Normalizza il feedback emotivo tra 0 e 1
                emotional_feedback = max(0.0, min(1.0, emotional_feedback))
                
                # Modifica la loss in base al feedback emotivo
                emotional_factor = 1.0 + (emotional_feedback - 0.5)
                loss *= emotional_factor
                
                # Aggiorna lo stato emotivo
                self.update_emotional_state(input_text, emotional_feedback)
            
            # Backward pass e ottimizzazione
            self.optimizer.zero_grad()
            loss.backward()
            
            # Clip del gradiente per stabilità
            torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
            
            self.optimizer.step()
            
            # Incrementa l'età di sviluppo
            self.developmental_age += 1
            
            return loss.item()
            
        except Exception as e:
            print(f"Errore durante l'apprendimento: {str(e)}")
            return None
            
    def _clean_response(self, response: str) -> str:
        """
        Pulisce e formatta la risposta generata
        
        Args:
            response: Risposta grezza dal modello
            
        Returns:
            Risposta pulita e formattata
        """
        # Rimuovi spazi extra
        response = " ".join(response.split())
        
        # Capitalizza la prima lettera
        response = response.capitalize()
        
        # Assicurati che ci sia un punto finale
        if not response.endswith((".", "!", "?")):
            response += "."
            
        return response

    def update_emotional_state(self, user_input: str, user_feedback: float):
        """
        Aggiorna lo stato emotivo in base all'input dell'utente
        
        Args:
            user_input: Input testuale dell'utente
            user_feedback: Feedback emotivo numerico (0.0-1.0)
        """
        # Analizza il sentiment dell'input
        sentiment = self._analyze_sentiment(user_input)
        
        # Combina sentiment e feedback
        emotional_value = (sentiment + user_feedback) / 2
        
        # Aggiorna il sistema emotivo
        self.emotional_system.update(emotional_value)
        
    def _analyze_sentiment(self, text: str) -> float:
        """
        Analizza il sentiment del testo
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Valore del sentiment (0.0-1.0)
        """
        # Parole positive e negative per analisi basilare
        positive_words = {
            "bene", "grazie", "piacere", "felice", "contento",
            "bravo", "ottimo", "perfetto", "fantastico", "bellissimo"
        }
        negative_words = {
            "male", "triste", "arrabbiato", "deluso", "frustrato",
            "sbagliato", "pessimo", "terribile", "brutto", "cattivo"
        }
        
        # Converti in minuscolo e dividi in parole
        words = text.lower().split()
        
        # Conta le parole positive e negative
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        
        # Calcola il sentiment
        total = pos_count + neg_count
        if total == 0:
            return 0.5  # Neutro se non ci sono parole emotive
            
        return pos_count / total

    def save_model(self, path: str):
        """
        Salva il modello su disco
        
        Args:
            path: Percorso dove salvare il modello
        """
        try:
            # Salva il tokenizer separatamente
            tokenizer_path = path + '.tokenizer'
            with open(tokenizer_path, 'wb') as f:
                pickle.dump(self.tokenizer, f)
            
            # Salva il resto del modello
            state = {
                'model_state': self.state_dict(),
                'developmental_age': self.developmental_age,
                'memory': {
                    'short_term': self.memory.short_term,
                    'long_term': self.memory.long_term,
                    'total_interactions': self.memory.total_interactions
                },
                'emotional_system': {
                    'emotion_value': self.emotional_system.emotion_value,
                    'emotion_momentum': self.emotional_system.emotion_momentum,
                    'emotion_history': self.emotional_system.emotion_history
                }
            }
            torch.save(state, path)
            
        except Exception as e:
            print(f"Errore durante il salvataggio del modello: {str(e)}")
            
    def load_model(self, path: str):
        """
        Carica il modello da disco
        
        Args:
            path: Percorso da cui caricare il modello
        """
        try:
            # Carica il tokenizer
            tokenizer_path = path + '.tokenizer'
            if os.path.exists(tokenizer_path):
                with open(tokenizer_path, 'rb') as f:
                    self.tokenizer = pickle.load(f)
            
            # Carica il resto del modello
            state = torch.load(path, map_location=self.device, weights_only=True)
            
            # Carica lo stato del modello
            self.load_state_dict(state['model_state'])
            
            # Carica l'età di sviluppo
            self.developmental_age = state['developmental_age']
            
            # Carica la memoria
            memory_state = state['memory']
            self.memory.short_term = memory_state['short_term']
            self.memory.long_term = memory_state['long_term']
            self.memory.total_interactions = memory_state['total_interactions']
            
            # Carica il sistema emotivo
            emotional_state = state['emotional_system']
            self.emotional_system.emotion_value = emotional_state['emotion_value']
            self.emotional_system.emotion_momentum = emotional_state['emotion_momentum']
            self.emotional_system.emotion_history = emotional_state['emotion_history']
            
        except Exception as e:
            print(f"Errore durante il caricamento del modello: {str(e)}")
            raise
            
    def analyze_emotional_trend(self, window_size: int = 10) -> Dict[str, float]:
        """
        Analizza il trend emotivo delle ultime interazioni
        
        Args:
            window_size: Numero di interazioni da considerare
            
        Returns:
            Dizionario con le statistiche emotive
        """
        return self.emotional_system.analyze_trend(window_size)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Restituisce le statistiche della memoria
        
        Returns:
            Dizionario con le statistiche della memoria
        """
        return {
            'short_term_size': len(self.memory.short_term),
            'long_term_size': len(self.memory.long_term),
            'total_interactions': self.memory.total_interactions
        }

    def consolidate_memory(self):
        """
        Consolida la memoria a breve termine in memoria a lungo termine
        """
        try:
            # Seleziona le interazioni più significative
            significant_interactions = []
            for interaction in self.memory.short_term:
                # Calcola l'importanza dell'interazione
                importance = self._calculate_memory_importance(interaction)
                if importance > 0.7:  # Soglia di importanza
                    significant_interactions.append(interaction)
            
            # Trasferisci le interazioni significative nella memoria a lungo termine
            for interaction in significant_interactions:
                self.memory.long_term.append(interaction)
                self.memory.short_term.remove(interaction)
            
            # Mantieni la dimensione della memoria a lungo termine
            max_long_term = 1000
            if len(self.memory.long_term) > max_long_term:
                # Rimuovi le interazioni meno importanti
                self.memory.long_term = sorted(
                    self.memory.long_term,
                    key=lambda x: self._calculate_memory_importance(x),
                    reverse=True
                )[:max_long_term]
            
            # Pulisci la memoria a breve termine se troppo grande
            max_short_term = 100
            if len(self.memory.short_term) > max_short_term:
                self.memory.short_term = self.memory.short_term[-max_short_term:]
                
        except Exception as e:
            print(f"Errore durante il consolidamento della memoria: {str(e)}")
    
    def _calculate_memory_importance(self, interaction: Tuple[str, str]) -> float:
        """
        Calcola l'importanza di un'interazione per la memoria
        
        Args:
            interaction: Tupla (input, output) dell'interazione
            
        Returns:
            Valore di importanza (0.0-1.0)
        """
        input_text, output_text = interaction
        
        # Fattori di importanza
        factors = []
        
        # 1. Lunghezza dell'interazione
        length_factor = min(1.0, (len(input_text) + len(output_text)) / 200)
        factors.append(length_factor)
        
        # 2. Presenza di parole chiave
        important_words = {
            "perché", "come", "quando", "dove", "chi", "cosa",
            "importante", "ricorda", "memorizza", "impara"
        }
        keyword_count = sum(1 for word in input_text.lower().split() 
                          if word in important_words)
        keyword_factor = min(1.0, keyword_count / 3)
        factors.append(keyword_factor)
        
        # 3. Sentiment dell'interazione
        sentiment = self._analyze_sentiment(input_text)
        sentiment_factor = abs(sentiment - 0.5) * 2  # Più importante se emotivo
        factors.append(sentiment_factor)
        
        # 4. Frequenza di accesso
        access_count = sum(1 for mem in self.memory.short_term 
                         if mem[0] == input_text)
        frequency_factor = min(1.0, access_count / 5)
        factors.append(frequency_factor)
        
        # Calcola la media pesata dei fattori
        weights = [0.3, 0.3, 0.2, 0.2]  # Pesi per ciascun fattore
        importance = sum(f * w for f, w in zip(factors, weights))
        
        return importance

    def _generate_contextual_response(self, input_text: str, context: Dict[str, Any]) -> str:
        """
        Genera una risposta contestuale in base all'input dell'utente
        
        Args:
            input_text: Testo di input
            context: Contesto della conversazione
            
        Returns:
            Risposta contestuale
        """
        age = context.get('age', 25)
        emotional_state = context.get('emotion', 'neutral')
        hobby = context.get('hobby', [])
        
        # Analisi del contesto positivo/negativo nel testo
        positive_indicators = ['progresso', 'successo', 'felice', 'bene', 'miglior', 'nuovo', 'interessante']
        negative_indicators = ['difficile', 'male', 'triste', 'stanco', 'preoccup', 'stress']
        
        # Determina se c'è un contesto positivo nonostante l'emozione negativa
        has_positive_context = any(indicator in input_text.lower() for indicator in positive_indicators)
        has_negative_context = any(indicator in input_text.lower() for indicator in negative_indicators)
        
        # Risposte specifiche per hobby
        hobby_responses = {
            'fotografia': {
                'positive': [
                    "La fotografia è un modo meraviglioso per catturare momenti speciali. Che tipo di foto ti piace scattare?",
                    "È fantastico vedere i tuoi progressi nella fotografia! Hai uno stile particolare che preferisci?",
                    "La fotografia può essere molto gratificante. Quali sono i tuoi soggetti preferiti?"
                ],
                'negative': [
                    "Anche i fotografi più esperti hanno momenti difficili. Vuoi parlare delle sfide che stai incontrando?",
                    "La fotografia può essere frustrante a volte. Come posso aiutarti a superare questo momento?",
                    "Ogni scatto è un'opportunità di apprendimento. Parliamo di cosa ti preoccupa nella fotografia."
                ]
            },
            'chitarra': {
                'positive': [
                    "Suonare la chitarra è un'ottima forma di espressione! Che genere ti piace suonare?",
                    "È fantastico che tu stia facendo progressi con la chitarra! Quali sono i tuoi pezzi preferiti?",
                    "La musica può essere molto gratificante. Come ti fa sentire quando suoni?"
                ],
                'negative': [
                    "Imparare uno strumento richiede pazienza. Quali difficoltà stai incontrando?",
                    "Anche i migliori musicisti hanno iniziato da zero. Vuoi parlare di cosa ti scoraggia?",
                    "La pratica è la chiave del successo. Come posso aiutarti a mantenere la motivazione?"
                ]
            },
            'escursionismo': {
                'positive': [
                    "L'escursionismo è un modo fantastico per connettersi con la natura! Hai dei sentieri preferiti?",
                    "È bellissimo che tu ami le escursioni! Quali sono le tue mete preferite?",
                    "Le escursioni possono essere molto rigeneranti. Raccontami della tua ultima avventura!"
                ],
                'negative': [
                    "L'escursionismo può essere impegnativo. Quali difficoltà stai incontrando?",
                    "Anche le escursioni più difficili hanno momenti gratificanti. Vuoi parlarne?",
                    "La sicurezza è importante nell'escursionismo. Come posso aiutarti a sentirti più sicuro?"
                ]
            }
        }
        
        # Risposte specifiche per eventi della vita
        life_events = {
            'lavoro': {
                'positive': [
                    "Il lavoro può essere una fonte di crescita personale. Come ti senti rispetto a questi cambiamenti?",
                    "È importante sentirsi realizzati nel lavoro. Vuoi condividere i tuoi obiettivi?",
                    "Ogni sfida lavorativa è un'opportunità. Come posso supportarti in questo percorso?"
                ],
                'negative': [
                    "Le difficoltà sul lavoro possono essere pesanti. Vuoi parlare di strategie per gestirle?",
                    "Il lavoro non dovrebbe compromettere il tuo benessere. Come posso aiutarti a trovare un equilibrio?",
                    "A volte è necessario prendersi una pausa e riflettere. Vuoi che ne parliamo?"
                ]
            },
            'relazioni': {
                'positive': [
                    "Le relazioni positive sono importanti. Come ti fa sentire questa nuova connessione?",
                    "È bello vedere che stai costruendo nuovi legami. Vuoi raccontarmi di più?",
                    "L'amicizia è preziosa. Come stai vivendo questi momenti?"
                ],
                'negative': [
                    "I conflitti nelle relazioni sono normali. Come posso aiutarti a gestire questa situazione?",
                    "A volte le relazioni richiedono pazienza. Vuoi parlare di come ti senti?",
                    "È importante comunicare apertamente. Possiamo esplorare insieme delle soluzioni?"
                ]
            },
            'salute': {
                'positive': [
                    "Prendersi cura di sé è fondamentale. Come ti senti rispetto ai progressi che stai facendo?",
                    "Il benessere è un viaggio continuo. Vuoi condividere i tuoi obiettivi?",
                    "È importante celebrare ogni piccolo progresso. Come posso supportarti?"
                ],
                'negative': [
                    "La salute è importante e capisco la tua preoccupazione. Come posso aiutarti?",
                    "A volte abbiamo bisogno di rallentare e ascoltare il nostro corpo. Vuoi parlarne?",
                    "Ci sono molti modi per migliorare il benessere. Possiamo esplorarli insieme?"
                ]
            }
        }
        
        # Identifica il contesto dell'evento della vita
        event_context = None
        if 'lavoro' in input_text.lower():
            event_context = 'lavoro'
        elif any(word in input_text.lower() for word in ['amico', 'persona', 'relazione', 'conosciuto']):
            event_context = 'relazioni'
        elif any(word in input_text.lower() for word in ['dormire', 'stanco', 'salute', 'stress']):
            event_context = 'salute'
            
        # Identifica se viene menzionato un hobby
        mentioned_hobby = None
        for h in hobby_responses.keys():
            if h in input_text.lower():
                mentioned_hobby = h
                
        # Costruisci la risposta
        response_parts = []
        
        # Aggiungi risposta specifica per hobby se menzionato
        if mentioned_hobby:
            response_type = 'positive' if has_positive_context else 'negative'
            hobby_response = random.choice(hobby_responses[mentioned_hobby][response_type])
            response_parts.append(hobby_response)
            
        # Aggiungi risposta specifica per evento della vita
        if event_context:
            event_response = random.choice(life_events[event_context]['positive' if has_positive_context else 'negative'])
            if not response_parts:  # Se non c'è già una risposta per hobby
                response_parts.append(event_response)
            
        # Se non abbiamo ancora una risposta, usa le risposte base per emozione
        if not response_parts:
            base_responses = {
                'happy': [
                    "Il tuo entusiasmo è contagioso! Come posso contribuire a questo momento positivo?",
                    "È bello vederti così positivo! Di cosa vorresti parlare?",
                    "Mi fa piacere che tu stia bene! Come posso aiutarti a mantenere questo stato d'animo?"
                ],
                'sad': [
                    "Capisco che non sia un momento facile. Sono qui per ascoltarti.",
                    "A volte parlare può alleggerire il peso. Come posso aiutarti?",
                    "Mi dispiace che tu stia attraversando questo momento. Vuoi condividere i tuoi pensieri?"
                ],
                'angry': [
                    "La rabbia può essere un'emozione intensa. Come posso aiutarti a gestirla?",
                    "Capisco la tua frustrazione. Vuoi parlarne con calma?",
                    "È normale sentirsi arrabbiati a volte. Come posso supportarti?"
                ],
                'anxious': [
                    "L'ansia può essere opprimente. Affrontiamola insieme.",
                    "Respira profondamente. Sono qui per aiutarti a gestire questa situazione.",
                    "Le preoccupazioni possono accumularsi. Vuoi condividere cosa ti agita?"
                ],
                'neutral': [
                    "Come posso esserti d'aiuto oggi?",
                    "Sono qui per ascoltare i tuoi pensieri.",
                    "Di cosa vorresti parlare?"
                ]
            }
            response_parts.append(random.choice(base_responses[emotional_state]))
            
        # Combina le parti della risposta
        final_response = " ".join(response_parts)
        
        return final_response
