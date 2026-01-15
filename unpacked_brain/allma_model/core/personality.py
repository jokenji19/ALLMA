from typing import Dict, List, Optional, Union, Any
import time
import math

class Personality:
    """Gestisce la personalità di ALLMA"""
    
    def __init__(self):
        # Inizializza i tratti della personalità
        self.traits = {
            'openness': 0.5,      # Apertura a nuove esperienze
            'empathy': 0.5,       # Empatia nelle interazioni
            'curiosity': 0.5,     # Curiosità nell'apprendimento
            'autonomy': 0.5,      # Autonomia decisionale
            'conscientiousness': 0.5,  # Coscienziosità
            'extraversion': 0.5,   # Estroversione
            'agreeableness': 0.5   # Accoglienza
        }
        
        # Storico delle interazioni
        self.interaction_history = []
        
        # Timestamp dell'ultima evoluzione
        self.last_evolution = time.time()
        
    def get_traits(self) -> Dict[str, float]:
        """Restituisce i tratti attuali della personalità"""
        return self.traits.copy()
        
    def update_personality(self, text_or_params: Union[str, Dict[str, Any]], emotions: Optional[Dict[str, float]] = None) -> None:
        """
        Aggiorna la personalità in base al testo/parametri e alle emozioni rilevate
        
        Args:
            text_or_params: Il testo del messaggio o un dizionario di parametri
            emotions: Dizionario delle emozioni rilevate con i relativi punteggi (opzionale)
        """
        if isinstance(text_or_params, str):
            # Vecchio formato: text + emotions
            text = text_or_params
            if emotions is None:
                emotions = {}
        else:
            # Nuovo formato: dizionario di parametri
            params = text_or_params
            text = params.get('text', '')
            emotions = {'emotion': params.get('emotion', '')} if 'emotion' in params else {}
            
            # Aggiorna i tratti in base ai parametri
            if params.get('type') == 'learning':
                self.traits['curiosity'] = min(1.0, self.traits['curiosity'] + 0.1 * params.get('confidence', 0.5))
                self.traits['openness'] = min(1.0, self.traits['openness'] + 0.05)
                
            if params.get('success', False):
                self.traits['conscientiousness'] = min(1.0, self.traits['conscientiousness'] + 0.05)
            else:
                self.traits['conscientiousness'] = max(0.0, self.traits['conscientiousness'] - 0.05)
                
        # Calcola l'impatto emotivo
        emotion_impact = 0
        for emotion, score in emotions.items():
            if isinstance(score, (int, float)):
                if emotion == 'joy':
                    emotion_impact += score * 0.3
                elif emotion == 'love':
                    emotion_impact += score * 0.3
                elif emotion == 'admiration':
                    emotion_impact += score * 0.2
                elif emotion == 'curiosity':
                    emotion_impact += score * 0.2
                elif emotion == 'sadness':
                    emotion_impact -= score * 0.2
                elif emotion == 'anger':
                    emotion_impact -= score * 0.3
                elif emotion == 'trust':
                    emotion_impact += score * 0.2
                
        # Aggiorna i tratti in base all'impatto emotivo
        if emotion_impact > 0:
            self.traits['empathy'] = min(1.0, self.traits['empathy'] + emotion_impact * 0.1)
            self.traits['extraversion'] = min(1.0, self.traits['extraversion'] + emotion_impact * 0.1)
            self.traits['agreeableness'] = min(1.0, self.traits['agreeableness'] + emotion_impact * 0.1)
        else:
            self.traits['empathy'] = max(0.0, self.traits['empathy'] + emotion_impact * 0.05)
            self.traits['extraversion'] = max(0.0, self.traits['extraversion'] + emotion_impact * 0.05)
            
        # Aggiorna la curiosità in base al contenuto del testo
        if any(keyword in text.lower() for keyword in ['perché', 'come', 'cosa', '?']):
            self.traits['curiosity'] = min(1.0, self.traits['curiosity'] + 0.1)
            
        # Registra l'interazione
        self.interaction_history.append({
            'timestamp': time.time(),
            'text': text,
            'emotions': emotions,
            'impact': emotion_impact,
            'traits': self.traits.copy()  # Aggiungo una copia dei tratti correnti
        })
        
    def get_interaction_history(self) -> List[Dict[str, Any]]:
        """
        Restituisce lo storico delle interazioni
        
        Returns:
            Lista di dizionari contenenti le interazioni passate
        """
        return self.interaction_history.copy()

    def analyze_personality_evolution(self) -> Dict:
        """Analizza l'evoluzione della personalità"""
        if not self.interaction_history:
            return {
                'stability': 1.0,
                'growth': 0.0,
                'trend': 'stable'
            }
            
        # Se c'è una sola interazione, calcola la crescita rispetto ai valori iniziali
        if len(self.interaction_history) == 1:
            initial_values = {trait: 0.5 for trait in self.traits}  # Valori iniziali
            current_values = self.interaction_history[0]['traits']
            total_change = sum(current_values[trait] - initial_values[trait] 
                             for trait in self.traits)
            growth = total_change / len(self.traits)
            return {
                'stability': 1.0,
                'growth': growth * 2.0,  # Amplifica la crescita
                'trend': 'growing' if growth > 0.0 else 'stable'
            }
            
        # Considera solo le ultime 10 interazioni per l'analisi
        recent_history = self.interaction_history[-10:]
        
        # Calcola statistiche sui tratti
        trait_changes = {trait: [] for trait in self.traits}
        for i in range(1, len(recent_history)):
            prev = recent_history[i-1]['traits']
            curr = recent_history[i]['traits']
            for trait in self.traits:
                change = curr[trait] - prev[trait]
                trait_changes[trait].append(change)
                
        # Calcola stabilità (deviazione standard media dei cambiamenti)
        stability = 1.0
        for changes in trait_changes.values():
            if changes:
                mean = sum(changes) / len(changes)
                variance = sum((x - mean) ** 2 for x in changes) / len(changes)
                stability *= (1.0 - math.sqrt(variance))
                
        # Calcola crescita (media dei cambiamenti positivi)
        growth = 0.0
        for changes in trait_changes.values():
            if changes:
                positive_changes = [x for x in changes if x > 0]
                if positive_changes:
                    growth += sum(positive_changes) / len(changes)
        growth /= len(self.traits)
        
        # Calcola il trend complessivo
        first_state = recent_history[0]['traits']
        last_state = recent_history[-1]['traits']
        total_change = sum(last_state[trait] - first_state[trait] 
                         for trait in self.traits)
        # Rendi il trend più sensibile ai cambiamenti
        if total_change > 0.05:  
            trend = 'growing'
        elif total_change < -0.05:  
            trend = 'declining'
        else:
            trend = 'stable'
            
        return {
            'stability': max(0.0, min(1.0, stability)),
            'growth': growth * 2.0,  # Amplifica la crescita per renderla più evidente
            'trend': trend
        }

    def get_interaction_style(self) -> str:
        """
        Determina lo stile di interazione basato sulle emozioni recenti e i tratti della personalità
        
        Returns:
            str: Lo stile di interazione ('supportive', 'directive', 'reflective', 'expressive')
        """
        # Recupera le ultime 5 interazioni
        recent_interactions = self.interaction_history[-5:] if self.interaction_history else []
        
        # Conta le emozioni principali nelle interazioni recenti
        emotion_counts = {}
        for interaction in recent_interactions:
            emotions = interaction.get('emotions', {})
            if isinstance(emotions, dict):
                # Trova l'emozione con il punteggio più alto
                max_emotion = max(emotions.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)[0]
                emotion_counts[max_emotion] = emotion_counts.get(max_emotion, 0) + 1
            else:
                # Se emotions non è un dizionario, usa l'emozione come stringa
                emotion = str(emotions)
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
        # Determina l'emozione dominante
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else 'neutral'
        
        # Mappa le emozioni agli stili di interazione
        emotion_style_map = {
            'joy': 'expressive',
            'sadness': 'supportive',
            'fear': 'reflective',
            'anger': 'directive',
            'surprise': 'expressive',
            'neutral': 'reflective'
        }
        
        # Lo stile base è determinato dall'emozione dominante
        base_style = emotion_style_map.get(dominant_emotion, 'reflective')
        
        # Modifica lo stile in base ai tratti della personalità
        if self.traits.get('openness', 0) > 0.7:
            return 'expressive'
        elif self.traits.get('conscientiousness', 0) > 0.7:
            return 'directive'
        elif self.traits.get('agreeableness', 0) > 0.7:
            return 'supportive'
            
        return base_style

    def _analyze_emotional_context(self, emotion: Optional[str]) -> float:
        """Analizza il contesto emotivo e restituisce un fattore di impatto"""
        if not emotion:
            return 0.0
            
        # Mappa delle emozioni positive e negative
        positive_emotions = {'joy', 'trust', 'anticipation', 'surprise'}
        negative_emotions = {'anger', 'disgust', 'fear', 'sadness'}
        
        # Calcola l'impatto emotivo
        if emotion.lower() in positive_emotions:
            return 0.5  # Aumentato da 0.2 a 0.5 per dare più peso alle emozioni positive
        elif emotion.lower() in negative_emotions:
            return -0.2
        else:
            return 0.0

    def get_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Fornisce insights sulla personalità dell'utente
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dict contenente vari insights sulla personalità
        """
        # Analizza l'evoluzione della personalità
        evolution = self.analyze_personality_evolution()
        
        # Ottiene lo stile di interazione corrente
        interaction_style = self.get_interaction_style()
        
        # Calcola il livello tecnico basato sui tratti
        technical_level = "intermediate"  # Default
        if self.traits['curiosity'] > 0.7 and self.traits['openness'] > 0.7:
            technical_level = "advanced"
        elif self.traits['curiosity'] < 0.3 or self.traits['openness'] < 0.3:
            technical_level = "basic"
            
        # Calcola il livello di coinvolgimento
        engagement = (self.traits['curiosity'] + self.traits['extraversion']) / 2
        
        return {
            'technical_level': technical_level,
            'interaction_style': interaction_style,
            'engagement_level': engagement,
            'personality_evolution': evolution,
            'dominant_traits': [
                trait for trait, value in self.traits.items()
                if value > 0.7
            ],
            'areas_for_growth': [
                trait for trait, value in self.traits.items()
                if value < 0.3
            ]
        }
