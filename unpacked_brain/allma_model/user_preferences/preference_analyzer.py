from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import json
import threading
from enum import Enum
import numpy as np
from collections import defaultdict
from allma_model.user_system.user_preferences import LearningPreference, LearningStyle, CommunicationStyle

class PreferenceAnalyzer:
    def __init__(self, db_path: str = "memory.db"):
        """
        Inizializza il sistema di analisi delle preferenze
        
        Args:
            db_path: Percorso del database SQLite
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_db()
    
    def _get_db_connection(self):
        """Crea una nuova connessione al database"""
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_db(self):
        """Inizializza il database SQLite con le tabelle necessarie"""
        with self.lock:
            conn = self._get_db_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        preference_type TEXT NOT NULL,
                        preference_value TEXT NOT NULL,
                        confidence FLOAT NOT NULL,
                        last_updated DATETIME NOT NULL,
                        metadata TEXT,
                        UNIQUE(user_id, preference_type)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS preference_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        interaction_id INTEGER NOT NULL,
                        preference_type TEXT NOT NULL,
                        observed_value TEXT NOT NULL,
                        confidence FLOAT NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(interaction_id) REFERENCES interactions(id)
                    )
                """)
                conn.commit()
            finally:
                conn.close()
    
    def analyze_interaction(self, user_id: str, interaction: dict) -> Dict[str, Dict]:
        """
        Analizza un'interazione per identificare preferenze
        
        Args:
            user_id: ID dell'utente
            interaction: Dizionario contenente i dettagli dell'interazione
        
        Returns:
            Dizionario con le preferenze identificate
        """
        preferences = {}
        
        # Analizza stile di comunicazione
        comm_style = self._analyze_communication_style(interaction)
        if comm_style and comm_style['confidence'] >= 0.3:
            preferences['communication_style'] = comm_style
            # Salva nella storia
            self._store_preference_history(
                user_id,
                interaction.get('id'),
                'communication_style',
                comm_style
            )
        
        # Analizza stile di apprendimento
        learning_style = self._analyze_learning_style(interaction)
        if learning_style and learning_style['confidence'] >= 0.3:
            preferences['learning_style'] = learning_style
            # Salva nella storia
            self._store_preference_history(
                user_id,
                interaction.get('id'),
                'learning_style',
                learning_style
            )
        
        # Se sono state identificate preferenze valide, salvale
        if preferences:
            self._store_preferences(user_id, preferences)
        
        return preferences
    
    def _analyze_communication_style(self, interaction: dict) -> Optional[Dict]:
        """
        Analizza lo stile di comunicazione da un'interazione
        
        Args:
            interaction: Dizionario contenente i dettagli dell'interazione
        
        Returns:
            Dizionario con stile e confidenza o None
        """
        content = interaction.get('content', '').lower()
        context = interaction.get('context', {})
        
        # Indicatori per ogni stile
        style_indicators = {
            CommunicationStyle.DIRECT: [
                'breve' in content,
                'brevemente' in content,
                'in breve' in content,
                'direttamente' in content,
                len(content.split()) < 15  # frasi molto brevi
            ],
            CommunicationStyle.DETAILED: [
                'dettagli' in content,
                'dettagliatamente' in content,
                'approfonditamente' in content,
                'spiegami' in content and ('tutto' in content or 'bene' in content),
                len(content.split()) > 30  # frasi lunghe
            ],
            CommunicationStyle.TECHNICAL: [
                'tecnicamente' in content,
                'specifiche' in content,
                'documentazione' in content,
                'api' in content,
                'implementazione' in content
            ],
            CommunicationStyle.SIMPLIFIED: [
                'semplice' in content,
                'base' in content,
                'facilmente' in content,
                'esempio semplice' in content,
                'spiegami semplicemente' in content
            ]
        }
        
        # Calcola score per ogni stile
        style_scores = {}
        for style, indicators in style_indicators.items():
            score = sum(1 for ind in indicators if ind) / len(indicators)
            if score >= 0.2:  # ignora score troppo bassi
                style_scores[style] = score
        
        # Se non ci sono score significativi, ritorna None
        if not style_scores:
            return None
        
        # Seleziona lo stile con score più alto
        best_style = max(style_scores.items(), key=lambda x: x[1])
        
        return {
            'style': best_style[0].value,
            'confidence': best_style[1]
        }
    
    def _analyze_learning_style(self, interaction: dict) -> Optional[Dict]:
        """
        Analizza lo stile di apprendimento da un'interazione
        
        Args:
            interaction: Dizionario contenente i dettagli dell'interazione
        
        Returns:
            Dizionario con stile e confidenza o None
        """
        content = interaction.get('content', '').lower()
        context = interaction.get('context', {})
        
        # Indicatori per ogni stile
        style_indicators = {
            LearningStyle.VISUAL: [
                'mostra' in content,
                'vedi' in content,
                'diagramma' in content,
                'immagine' in content,
                'grafico' in content,
                'visivamente' in content
            ],
            LearningStyle.KINESTHETIC: [
                'esempio' in content,
                'prova' in content,
                'pratica' in content,
                'come si fa' in content,
                'implementare' in content,
                'fare' in content
            ],
            LearningStyle.THEORETICAL: [
                'teoria' in content,
                'concetto' in content,
                'principio' in content,
                'perché' in content,
                'fondamenti' in content,
                'spiegazione teorica' in content
            ],
            LearningStyle.AUDITORY: [
                'proviamo' in content,
                'insieme' in content,
                'interattivo' in content,
                'posso provare' in content,
                'facciamo' in content,
                'interagiamo' in content
            ]
        }
        
        # Calcola score per ogni stile
        style_scores = {}
        for style, indicators in style_indicators.items():
            score = sum(1 for ind in indicators if ind) / len(indicators)
            if score >= 0.2:  # ignora score troppo bassi
                style_scores[style] = score
        
        # Se non ci sono score significativi, ritorna None
        if not style_scores:
            return None
        
        # Seleziona lo stile con score più alto
        best_style = max(style_scores.items(), key=lambda x: x[1])
        
        return {
            'style': best_style[0].value,
            'confidence': best_style[1]
        }
    
    def analyze_learning_style(self, user_id: str) -> LearningPreference:
        """
        Analizza lo stile di apprendimento dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Preferenze di apprendimento
        """
        # Recupera le preferenze salvate
        saved_preferences = self.get_user_preferences(user_id)
        
        if saved_preferences and "learning_style" in saved_preferences:
            learning_style = saved_preferences["learning_style"]
            style_value = learning_style.get("primary_style")
            confidence = learning_style.get("confidence", 0.0)
            
            try:
                # Converti il valore dello stile in LearningStyle
                if isinstance(style_value, LearningStyle):
                    primary_style = style_value
                elif isinstance(style_value, str):
                    # Se è una stringa, cerca di convertirla in LearningStyle
                    primary_style = LearningStyle(style_value.lower())
                else:
                    # Se non è né LearningStyle né stringa, usa lo stile bilanciato
                    primary_style = LearningStyle.BALANCED
            except (ValueError, AttributeError):
                # In caso di errore, usa lo stile bilanciato
                primary_style = LearningStyle.BALANCED
            
            # Crea una nuova preferenza con lo stile salvato
            return LearningPreference(
                primary_style=primary_style,
                confidence=confidence,
                last_updated=datetime.now()
            )
            
        # Se non ci sono preferenze salvate, usa lo stile bilanciato
        return LearningPreference(
            primary_style=LearningStyle.BALANCED,
            confidence=0.0,
            last_updated=datetime.now()
        )
    
    def _store_preferences(self, user_id: str, preferences: Dict[str, Dict]) -> bool:
        """
        Memorizza le preferenze identificate
        
        Args:
            user_id: ID dell'utente
            preferences: Dizionario con le preferenze identificate
        
        Returns:
            bool: True se l'operazione è riuscita
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                now = datetime.now().isoformat()
                
                for pref_type, pref_value in preferences.items():
                    # Se il valore è un dizionario con style e confidence, usali
                    if isinstance(pref_value, dict) and 'style' in pref_value and 'confidence' in pref_value:
                        style = pref_value['style']
                        confidence = pref_value['confidence']
                    else:
                        # Altrimenti usa il valore direttamente come style e confidence=1.0
                        style = str(pref_value)
                        confidence = 1.0
                    
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO user_preferences
                        (user_id, preference_type, preference_value, confidence, last_updated, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            pref_type,
                            style,
                            confidence,
                            now,
                            '{}'
                        )
                    )
                
                conn.commit()
                return True
            except Exception as e:
                print(f"Errore durante il salvataggio delle preferenze: {e}")
                return False
            finally:
                conn.close()
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Dict]:
        """
        Recupera le preferenze dell'utente
        
        Args:
            user_id: ID dell'utente
        
        Returns:
            Dizionario con le preferenze dell'utente
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT preference_type, preference_value, confidence, metadata
                    FROM user_preferences
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )
                
                preferences = {}
                for row in cursor:
                    preferences[row['preference_type']] = {
                        'style': row['preference_value'],
                        'confidence': row['confidence'],
                        'metadata': json.loads(row['metadata'])
                    }
                
                return preferences
            except Exception as e:
                print(f"Errore durante il recupero delle preferenze: {e}")
                return {}
            finally:
                conn.close()
    
    def get_preference_history(self, user_id: str, preference_type: str) -> List[Dict]:
        """
        Recupera la storia delle preferenze per un tipo specifico
        
        Args:
            user_id: ID dell'utente
            preference_type: Tipo di preferenza
        
        Returns:
            Lista di preferenze osservate nel tempo
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT observed_value, confidence, created_at
                    FROM preference_history
                    WHERE user_id = ? AND preference_type = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id, preference_type)
                )
                
                history = []
                for row in cursor:
                    history.append({
                        'value': row['observed_value'],
                        'confidence': row['confidence'],
                        'timestamp': row['created_at']
                    })
                
                return history
            except Exception as e:
                print(f"Errore durante il recupero della storia delle preferenze: {e}")
                return []
            finally:
                conn.close()

    def _store_preference_history(self, user_id: str, interaction_id: Optional[int],
                                preference_type: str, preference_data: Dict) -> bool:
        """
        Salva una preferenza nella storia
        
        Args:
            user_id: ID dell'utente
            interaction_id: ID dell'interazione (può essere None)
            preference_type: Tipo di preferenza
            preference_data: Dati della preferenza
        
        Returns:
            bool: True se l'operazione è riuscita
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO preference_history
                    (user_id, interaction_id, preference_type, observed_value,
                     confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        interaction_id or 0,  # usa 0 se None
                        preference_type,
                        preference_data['style'],
                        preference_data['confidence'],
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Errore durante il salvataggio della storia delle preferenze: {e}")
                return False
            finally:
                conn.close()

    def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict
    ) -> bool:
        """
        Aggiorna le preferenze dell'utente
        
        Args:
            user_id: ID dell'utente
            preferences: Dizionario delle preferenze da aggiornare
            
        Returns:
            True se l'aggiornamento è riuscito, False altrimenti
        """
        conn = None
        try:
            with self.lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                # Rimuovi le vecchie preferenze
                cursor.execute(
                    "DELETE FROM user_preferences WHERE user_id = ?",
                    (user_id,)
                )
                
                # Inserisci le nuove preferenze
                for pref_type, pref_data in preferences.items():
                    if isinstance(pref_data, dict) and 'style' in pref_data:
                        cursor.execute("""
                            INSERT INTO user_preferences 
                            (user_id, preference_type, preference_value, confidence)
                            VALUES (?, ?, ?, ?)
                        """, (
                            user_id,
                            pref_type,
                            pref_data['style'],
                            1.0  # Massima confidenza per preferenze esplicite
                        ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Errore durante l'aggiornamento delle preferenze: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def has_user_preferences(self, user_id: str) -> bool:
        """
        Verifica se un utente ha preferenze salvate.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            True se l'utente ha preferenze, False altrimenti
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM user_preferences
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )
                result = cursor.fetchone()
                return result['count'] > 0
            finally:
                conn.close()
