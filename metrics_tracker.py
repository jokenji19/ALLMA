"""
Metrics Tracker per ALLMA
==========================

Sistema di tracking per monitorare l'evoluzione di ALLMA nel tempo.
Traccia:
- Confidence evolution per topic
- Gemma vs Independent response ratio
- Average response times
- Memory usage trends
- Success rate
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

@dataclass
class InteractionMetrics:
    """Metriche per una singola interazione"""
    timestamp: str
    user_id: str
    conversation_id: str
    topic: str
    used_gemma: bool
    knowledge_integrated: bool
    confidence: float
    response_time_ms: float
    success: bool = True
    error: Optional[str] = None

class MetricsTracker:
    """Tracker per metriche di ALLMA"""
    
    def __init__(self, db_path: str = "allma_metrics.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inizializza database metriche"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    used_gemma INTEGER NOT NULL,
                    knowledge_integrated INTEGER NOT NULL,
                    confidence REAL NOT NULL,
                    response_time_ms REAL NOT NULL,
                    success INTEGER NOT NULL,
                    error TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions(timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_topic ON interactions(topic)
            ''')
    
    def record_interaction(self, metrics: InteractionMetrics):
        """Registra un'interazione"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO interactions (
                    timestamp, user_id, conversation_id, topic,
                    used_gemma, knowledge_integrated, confidence,
                    response_time_ms, success, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.user_id,
                metrics.conversation_id,
                metrics.topic,
                1 if metrics.used_gemma else 0,
                1 if metrics.knowledge_integrated else 0,
                metrics.confidence,
                metrics.response_time_ms,
                1 if metrics.success else 0,
                metrics.error
            ))
    
    def get_topic_evolution(self, topic: str, limit: int = 100) -> List[Dict]:
        """Ottiene evoluzione confidence per un topic"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    timestamp,
                    confidence,
                    knowledge_integrated,
                    response_time_ms
                FROM interactions
                WHERE topic = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (topic, limit))
            
            return [
                {
                    'timestamp': row[0],
                    'confidence': row[1],
                    'independent': bool(row[2]),
                    'response_time_ms': row[3]
                }
                for row in cursor.fetchall()
            ]
    
    def get_independence_ratio(
        self,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """Calcola ratio indipendenza negli ultimi N giorni"""
        query = '''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN knowledge_integrated = 1 THEN 1 ELSE 0 END) as independent,
                AVG(response_time_ms) as avg_time,
                AVG(confidence) as avg_confidence
            FROM interactions
            WHERE datetime(timestamp) >= datetime('now', '-' || ? || ' days')
        '''
        params = [days]
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            total = row[0] if row[0] else 0
            independent = row[1] if row[1] else 0
            
            return {
                'total_interactions': total,
                'independent_responses': independent,
                'gemma_responses': total - independent,
                'independence_ratio': independent / total if total > 0 else 0,
                'avg_response_time_ms': row[2] if row[2] else 0,
                'avg_confidence': row[3] if row[3] else 0
            }
    
    def get_topic_stats(self, limit: int = 10) -> List[Dict]:
        """Ottiene statistiche per topic"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    topic,
                    COUNT(*) as total_interactions,
                    SUM(CASE WHEN knowledge_integrated = 1 THEN 1 ELSE 0 END) as independent_count,
                    AVG(confidence) as avg_confidence,
                    MAX(confidence) as max_confidence
                FROM interactions
                GROUP BY topic
                ORDER BY total_interactions DESC
                LIMIT ?
            ''', (limit,))
            
            return [
                {
                    'topic': row[0],
                    'total_interactions': row[1],
                    'independent_count': row[2],
                    'independence_ratio': row[2] / row[1] if row[1] > 0 else 0,
                    'avg_confidence': row[3],
                    'max_confidence': row[4]
                }
                for row in cursor.fetchall()
            ]
    
    def export_metrics(self, output_file: str = "metrics_export.json"):
        """Esporta tutte le metriche in JSON"""
        stats = {
            'export_date': datetime.now().isoformat(),
            'independence_ratio_7d': self.get_independence_ratio(days=7),
            'independence_ratio_30d': self.get_independence_ratio(days=30),
            'top_topics': self.get_topic_stats(limit=20)
        }
        
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logging.info(f"📊 Metriche esportate in {output_file}")
        return stats

# Singleton instance
_tracker_instance = None

def get_metrics_tracker(db_path: str = "allma_metrics.db") -> MetricsTracker:
    """Ottiene istanza singleton del tracker"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = MetricsTracker(db_path)
    return _tracker_instance

if __name__ == "__main__":
    # Test
    tracker = MetricsTracker("test_metrics.db")
    
    # Simula interazioni
    for i in range(5):
        metrics = InteractionMetrics(
            timestamp=datetime.now().isoformat(),
            user_id="test_user",
            conversation_id="test_conv",
            topic="python",
            used_gemma=i < 2,  # Prime 2 usano Gemma
            knowledge_integrated=i >= 2,  # Ultime 3 indipendenti
            confidence=0.5 + (i * 0.1),  # Confidence cresce
            response_time_ms=100 - (i * 10)  # Tempo diminuisce
        )
        tracker.record_interaction(metrics)
    
    # Test queries
    print("Topic Evolution:")
    print(json.dumps(tracker.get_topic_evolution("python"), indent=2))
    
    print("\nIndependence Ratio:")
    print(json.dumps(tracker.get_independence_ratio(), indent=2))
    
    print("\nTopic Stats:")
    print(json.dumps(tracker.get_topic_stats(), indent=2))
