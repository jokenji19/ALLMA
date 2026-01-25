import os
import json
import shutil
import time
from datetime import datetime
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    
    # Mock Numpy to prevent type hint crashes
    class MockNumpy:
        class ndarray: pass
    np = MockNumpy()
from PIL import Image
from typing import Dict, List, Optional, Tuple, Any
import pickle
import uuid

class VisualMemorySystem:
    def __init__(self, storage_dir: str = "visual_memory"):
        """Inizializza il sistema di memoria visiva"""
        self.storage_dir = storage_dir
        self.features_db_path = os.path.join(storage_dir, "features.pkl")
        self.metadata_db_path = os.path.join(storage_dir, "metadata.json")
        self.images_dir = os.path.join(storage_dir, "images")
        self.memory_dir = os.path.join(storage_dir, "memory")
        self.memories = {}
        
        # Crea le directory necessarie
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.memory_dir, exist_ok=True)
        
        # Carica o inizializza il database
        self.features_db = self._load_features_db()
        self.metadata_db = self._load_metadata_db()
        
    def _load_features_db(self) -> Dict[str, np.ndarray]:
        """Carica il database delle features"""
        if os.path.exists(self.features_db_path):
            with open(self.features_db_path, 'rb') as f:
                return pickle.load(f)
        return {}
        
    def _load_metadata_db(self) -> Dict[str, Dict[str, Any]]:
        """Carica il database dei metadata"""
        if os.path.exists(self.metadata_db_path):
            with open(self.metadata_db_path, 'r') as f:
                return json.load(f)
        return {}
        
    def _save_features_db(self):
        """Salva il database delle features"""
        with open(self.features_db_path, 'wb') as f:
            pickle.dump(self.features_db, f)
            
    def _save_metadata_db(self):
        """Salva il database dei metadata"""
        with open(self.metadata_db_path, 'w') as f:
            json.dump(self.metadata_db, f, indent=2)
            
    def _extract_features(self, image: np.ndarray) -> np.ndarray:
        """Estrae le features dall'immagine"""
        # Converti in scala di grigi
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Ridimensiona per uniformità
        resized = cv2.resize(gray, (224, 224))
        
        # Calcola features base
        features = []
        
        # Istogramma normalizzato
        hist = cv2.calcHist([resized], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        features.extend(hist)
        
        # Media e deviazione standard per regioni
        cell_size = 32
        for i in range(0, resized.shape[0], cell_size):
            for j in range(0, resized.shape[1], cell_size):
                cell = resized[i:i+cell_size, j:j+cell_size]
                features.extend([np.mean(cell), np.std(cell)])
        
        # Bordi con Canny
        edges = cv2.Canny(resized, 100, 200)
        edge_features = cv2.resize(edges, (32, 32)).flatten() / 255.0
        features.extend(edge_features)
        
        # Normalizza il vettore finale
        features = np.array(features)
        if np.any(features):  # Evita divisione per zero
            features = features / np.linalg.norm(features)
            
        return features
        
    def learn_visual_concept(self, image_path: str, label: str, description: Optional[str] = None) -> bool:
        """Impara un nuovo concetto visivo"""
        try:
            # Leggi l'immagine
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Impossibile leggere l'immagine: {image_path}")
                
            # Genera un ID univoco usando uuid per evitare collisioni
            image_id = f"{label}_{str(uuid.uuid4())[:8]}"
            
            # Estrai features
            features = self._extract_features(image)
            
            # Salva l'immagine nella directory delle immagini
            image_filename = f"{image_id}.jpg"
            image_save_path = os.path.join(self.images_dir, image_filename)
            cv2.imwrite(image_save_path, image)
            
            # Salva features e metadata
            self.features_db[image_id] = features
            self.metadata_db[image_id] = {
                'label': label,
                'description': description,
                'original_path': image_path,
                'stored_path': image_save_path,
                'timestamp': datetime.now().isoformat(),
                'features_shape': features.shape[0],
                'id': image_id  # Aggiungi l'ID nei metadata per riferimento
            }
            
            # Salva i database
            self._save_features_db()
            self._save_metadata_db()
            
            return True
            
        except Exception as e:
            print(f"Errore nell'apprendimento del concetto visivo: {e}")
            return False
            
    def find_similar_images(self, image_path: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Trova immagini simili nel database"""
        try:
            # Leggi l'immagine query
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Impossibile leggere l'immagine: {image_path}")
                
            # Estrai features
            query_features = self._extract_features(image)
            
            # Calcola similarità con tutte le immagini nel database
            similarities = []
            for image_id, features in self.features_db.items():
                similarity = np.dot(query_features, features) / (
                    np.linalg.norm(query_features) * np.linalg.norm(features)
                )
                similarities.append((image_id, similarity))
                
            # Ordina per similarità
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Prendi i top_k risultati
            results = []
            for image_id, similarity in similarities[:top_k]:
                result = self.metadata_db[image_id].copy()
                result['similarity_score'] = float(similarity)
                results.append(result)
                
            return results
            
        except Exception as e:
            print(f"Errore nella ricerca di immagini simili: {e}")
            return []
            
    def get_visual_concepts(self, label: Optional[str] = None) -> List[Dict[str, Any]]:
        """Recupera i concetti visivi memorizzati"""
        try:
            results = []
            for image_id, metadata in self.metadata_db.items():
                if label is None or metadata['label'] == label:
                    results.append(metadata)
            return results
        except Exception as e:
            print(f"Errore nel recupero dei concetti visivi: {e}")
            return []
            
    def delete_visual_concept(self, image_id: str) -> bool:
        """Elimina un concetto visivo dal database"""
        try:
            if image_id in self.metadata_db:
                # Elimina l'immagine salvata
                image_path = self.metadata_db[image_id]['stored_path']
                if os.path.exists(image_path):
                    os.remove(image_path)
                    
                # Elimina dai database
                del self.features_db[image_id]
                del self.metadata_db[image_id]
                
                # Salva i database
                self._save_features_db()
                self._save_metadata_db()
                
                return True
            return False
        except Exception as e:
            print(f"Errore nell'eliminazione del concetto visivo: {e}")
            return False
            
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analizza un'immagine e restituisce una descrizione della scena e gli oggetti rilevati"""
        try:
            # Leggi l'immagine
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Impossibile leggere l'immagine: {image_path}")
                
            # Estrai features
            features = self._extract_features(image)
            
            # Cerca immagini simili nel database
            similar_images = self.find_similar_images(image_path, top_k=3)
            
            # Genera una descrizione basata sulle immagini simili
            description = ""
            objects = set()
            if similar_images:
                # Usa le descrizioni delle immagini simili
                descriptions = [img.get('description', '') for img in similar_images if img.get('description')]
                labels = [img.get('label', '') for img in similar_images]
                
                if descriptions:
                    description = max(descriptions, key=len)  # Usa la descrizione più lunga
                if labels:
                    objects.update(labels)
            else:
                # Descrizione di default se non ci sono immagini simili
                description = "Immagine non riconosciuta"
                
            return {
                'objects': list(objects),
                'description': description,
                'features': features.tolist(),
                'similar_images': similar_images,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Errore nell'analisi dell'immagine: {e}")
            return {
                'objects': [],
                'description': f"Errore nell'analisi: {str(e)}",
                'features': [],
                'similar_images': [],
                'timestamp': datetime.now().isoformat()
            }

    def store_visual_memory(self, image_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Memorizza un'immagine con il suo contesto"""
        try:
            if not os.path.exists(image_path):
                return {
                    'success': False,
                    'error': 'File non trovato'
                }
                
            # Genera un ID univoco
            memory_id = str(uuid.uuid4())
            
            # Crea una copia dell'immagine nella memoria
            memory_path = os.path.join(self.memory_dir, f"{memory_id}.jpg")
            shutil.copy2(image_path, memory_path)
            
            # Salva il contesto
            context['image_path'] = memory_path
            context['memory_id'] = memory_id
            
            # Aggiungi alla memoria
            self.memories[memory_id] = context
            
            return {
                'success': True,
                'memory_id': memory_id
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
