from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import pytz
from langdetect import detect
import cv2
import numpy as np
from PIL import Image
from transformers import pipeline
import requests
from .visual_memory import VisualMemorySystem
from .ocr_processor import OCRProcessor
from .information_extractor import InformationExtractor
import os
import uuid
import re
import time

class ContextUnderstandingSystem:
    def __init__(self):
        """Inizializza il sistema di comprensione del contesto"""
        self.context_memory = []
        self.visual_memory = VisualMemorySystem()
        self.ocr_processor = OCRProcessor()
        self._current_context = {
            'entities': {
                'persons': [],
                'organizations': [],
                'locations': []
            },
            'topics': [],
            'timestamp': time.time()
        }
        self.information_extractor = InformationExtractor()
        
        try:
            # Carica i modelli di ML
            self.emotion_detector = pipeline("text-classification", 
                                          model="j-hartmann/emotion-english-distilroberta-base", 
                                          top_k=None)
        except Exception as e:
            print(f"Error loading models: {e}")
            self.emotion_detector = None
            
        # Dizionario delle espressioni temporali per lingua
        self.temporal_expressions = {
            'it': {
                'past': ['ieri', 'scorsa', 'scorso', 'fa', 'prima'],
                'present': ['oggi', 'ora', 'adesso', 'momento'],
                'future': ['domani', 'dopodomani', 'prossima', 'prossimo', 'tra']
            },
            'en': {
                'past': ['yesterday', 'last', 'ago', 'before'],
                'present': ['today', 'now', 'current', 'moment'],
                'future': ['tomorrow', 'next', 'in']
            }
        }
        
        # Pattern per il riconoscimento di orari
        self.time_patterns = {
            'it': [
                r'(\d{1,2})[:\.](\d{2})(?:\s*(?:am|pm))?',  # 15:30, 3.45pm
                r'(\d{1,2})\s*(?:am|pm)',  # 3 pm
                r'(?:alle|ore)\s+(\d{1,2})(?:[:\.](\d{2}))?' # alle 15, ore 15:30
            ],
            'en': [
                r'(\d{1,2})[:\.](\d{2})(?:\s*(?:am|pm))?',  # 15:30, 3.45pm
                r'(\d{1,2})\s*(?:am|pm)',  # 3 pm
                r'(?:at)\s+(\d{1,2})(?:[:\.](\d{2}))?' # at 15, at 15:30
            ]
        }

    def translate_text(self, text: str, source_lang: str, target_lang: str = 'en') -> str:
        """Traduce il testo usando un servizio di traduzione"""
        # Per semplicità, se la lingua sorgente è già quella target, ritorna il testo originale
        if source_lang == target_lang:
            return text
            
        # Altrimenti simula una traduzione basata su regole semplici
        # Questo è solo un esempio, in produzione usare un vero servizio di traduzione
        translations = {
            'it': {
                'Sono molto felice oggi!': 'I am very happy today!',
                'Ci vediamo domani': 'See you tomorrow'
            }
        }
        
        if source_lang in translations and text in translations[source_lang]:
            return translations[source_lang][text]
            
        return text  # Fallback al testo originale
        
    def analyze_emotions(self, text: str) -> Dict[str, Any]:
        """Analizza le emozioni nel testo"""
        try:
            if not text or not isinstance(text, str):
                return {'label': 'unknown', 'score': 0.0}
                
            if self.emotion_detector is None:
                return {'label': 'unknown', 'score': 0.0}
                
            # Traduci in inglese se necessario
            try:
                lang = detect(text)
                if lang != 'en':
                    text = self.translate_text(text, lang, 'en') or text
            except:
                pass  # Usa il testo originale
                
            # Analizza le emozioni
            result = self.emotion_detector(text)
            if result and len(result[0]) > 0:
                # Ordina per score e prendi la più alta
                emotions = sorted(result[0], key=lambda x: x['score'], reverse=True)
                return {
                    'label': emotions[0]['label'],
                    'score': emotions[0]['score']
                }
                
            return {'label': 'unknown', 'score': 0.0}
            
        except Exception as e:
            print(f"Error analyzing emotions: {e}")
            return {'label': 'unknown', 'score': 0.0}
            
    def analyze_multilingual_input(self, text: str) -> Dict[str, Any]:
        """Analizza input multilingua"""
        try:
            # Rileva la lingua
            detected_lang = detect(text)
            
            # Traduci in inglese per l'analisi
            if detected_lang != 'en':
                english_text = self.translate_text(text, detected_lang, 'en')
            else:
                english_text = text
                
            # Analizza emozioni
            emotion_data = self.analyze_emotions(english_text)
            
            return {
                'original_text': text,
                'detected_language': detected_lang,
                'english_translation': english_text,
                'emotions': emotion_data,
                'confidence': float(emotion_data['score'])
            }
            
        except Exception as e:
            print(f"Error in analyze_multilingual_input: {e}")
            return {
                'error': str(e),
                'original_text': text
            }
            
    def process_image(self, image_path: str, label: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Analizza un'immagine e opzionalmente la memorizza"""
        try:
            # Carica e preprocessa l'immagine
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Impossibile caricare l'immagine")
                
            result = {}
            
            # Estrai testo se l'OCR è disponibile
            if self.ocr_processor:
                ocr_results = self.ocr_processor.extract_text_from_image(image)
                result['ocr_analysis'] = ocr_results
                
                # Se abbiamo trovato del testo, evidenzialo nell'immagine
                if ocr_results.get('text') or ocr_results.get('numbers'):
                    regions = self.ocr_processor.detect_text_regions(image)
                    highlighted_image = self.ocr_processor.highlight_text_regions(image, regions)
                    highlighted_path = image_path.replace('.', '_highlighted.')
                    cv2.imwrite(highlighted_path, highlighted_image)
                    result['highlighted_image_path'] = highlighted_path
            
            # Se abbiamo un'etichetta, memorizziamo l'immagine
            if label and self.visual_memory:
                success = self.visual_memory.learn_visual_concept(
                    image_path=image_path,
                    label=label,
                    description=description
                )
                result['learned'] = success
                
                # Trova immagini simili
                similar_images = self.visual_memory.find_similar_images(image_path)
                if similar_images:
                    result['similar_images'] = similar_images
                    
            # Analisi base dell'immagine
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            mean = np.mean(gray)
            std = np.std(gray)
            edges = cv2.Canny(gray, 100, 200)
            num_edges = np.count_nonzero(edges)
            
            result.update({
                'image_stats': {
                    'mean_intensity': float(mean),
                    'std_intensity': float(std),
                    'edge_complexity': float(num_edges) / (gray.shape[0] * gray.shape[1])
                },
                'image_size': {
                    'width': image.shape[1],
                    'height': image.shape[0]
                }
            })
            
            return result
            
        except Exception as e:
            print(f"Error in process_image: {e}")
            return {'error': str(e)}
            
    def analyze_temporal_context(self, text: str, reference_time: datetime) -> Dict[str, Any]:
        """Analizza il contesto temporale nel testo"""
        try:
            # Inizializza il risultato
            result = {
                'reference_time': reference_time,
                'detected_times': [],
                'temporal_relations': []
            }
            
            # Controlla input valido
            if not text or not isinstance(text, str):
                return result
                
            # Rileva la lingua
            try:
                lang = detect(text)
                if lang not in self.temporal_expressions:
                    lang = 'en'  # default a inglese
            except:
                lang = 'en'  # default a inglese
                
            # Cerca espressioni temporali
            expressions = self.temporal_expressions[lang]
            text_lower = text.lower()
            
            for timeframe, words in expressions.items():
                for word in words:
                    # Cerca la parola nel testo
                    index = text_lower.find(word)
                    if index >= 0:
                        # Calcola il tempo relativo
                        if timeframe == 'past':
                            detected_time = reference_time - timedelta(days=1)
                        elif timeframe == 'future':
                            detected_time = reference_time + timedelta(days=1)
                        else:
                            detected_time = reference_time
                            
                        # Aggiungi l'espressione temporale trovata
                        result['detected_times'].append({
                            'text': text[index:index + len(word)],
                            'timeframe': timeframe,
                            'estimated_time': detected_time,
                            'start': index,
                            'end': index + len(word)
                        })
                        
            # Cerca pattern di orari
            time_patterns = self.time_patterns[lang]
            for pattern in time_patterns:
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    # Estrai l'ora dal match
                    if ':' in match.group() or '.' in match.group():
                        # Formato HH:MM o HH.MM
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                    else:
                        # Formato H am/pm
                        hour = int(match.group(1))
                        minute = 0
                        
                    # Gestisci AM/PM
                    if 'pm' in match.group().lower() and hour < 12:
                        hour += 12
                    elif 'am' in match.group().lower() and hour == 12:
                        hour = 0
                        
                    # Crea il datetime
                    time_str = f"{hour:02d}:{minute:02d}"
                    detected_time = datetime.combine(
                        reference_time.date(),
                        datetime.strptime(time_str, "%H:%M").time()
                    )
                    
                    # Aggiungi l'orario trovato
                    result['detected_times'].append({
                        'text': match.group(),
                        'timeframe': 'time',
                        'estimated_time': detected_time,
                        'start': match.start(),
                        'end': match.end()
                    })
                    
            return result
            
        except Exception as e:
            print(f"Error in analyze_temporal_context: {e}")
            return result

    def add_to_context_memory(self, context: Dict[str, Any]) -> str:
        """Aggiunge un contesto alla memoria contestuale"""
        try:
            # Genera un ID univoco
            memory_id = str(uuid.uuid4())
            
            # Aggiungi timestamp se non presente
            if 'timestamp' not in context:
                context['timestamp'] = datetime.now().isoformat()
                
            # Aggiungi l'ID al contesto
            context['id'] = memory_id
            
            # Aggiungi alla memoria
            self.context_memory.append(context)
            
            return memory_id
            
        except Exception as e:
            print(f"Error in add_to_context_memory: {e}")
            return None
            
    def get_recent_context(self, n: int = 5) -> List[Dict[str, Any]]:
        """Recupera i contesti più recenti"""
        try:
            if n <= 0:
                return []
            return self.context_memory[-min(n, len(self.context_memory)):]
        except Exception as e:
            print(f"Error in get_recent_context: {e}")
            return []
            
    def analyze_complete_context(self, 
                               text: Optional[str] = None,
                               image_path: Optional[str] = None,
                               image_label: Optional[str] = None,
                               image_description: Optional[str] = None) -> Dict[str, Any]:
        """Analisi completa del contesto multimodale"""
        context = {}
        
        try:
            # Se non ci sono input, ritorna un dizionario vuoto
            if not any([text, image_path, image_label, image_description]):
                return {}
                
            # Analizza testo se presente
            if text:
                context['text_analysis'] = self.analyze_multilingual_input(text)
                context['temporal_analysis'] = self.analyze_temporal_context(text, datetime.now())
                
            # Analizza immagine se presente
            if image_path:
                context['image_analysis'] = self.process_image(
                    image_path,
                    label=image_label,
                    description=image_description
                )
                
            # Aggiorna la memoria del contesto solo se ci sono dati
            if context:
                self.update_context_memory(context)
            
        except Exception as e:
            print(f"Error in analyze_complete_context: {e}")
            context['error'] = str(e)
            
        return context

    def analyze_visual_context(self, image_path: str) -> Dict[str, Any]:
        """Analizza il contesto visivo di un'immagine"""
        try:
            if not os.path.exists(image_path):
                return {
                    'error': 'File non trovato',
                    'success': False
                }
                
            # Carica l'immagine
            image = cv2.imread(image_path)
            if image is None:
                return {
                    'error': "Impossibile caricare l'immagine",
                    'success': False
                }
                
            # Analizza la scena
            scene_type = self._analyze_scene(image)
            
            # Rileva oggetti
            objects = self._detect_objects(image)
            
            # Analizza i colori dominanti
            colors = self._analyze_colors(image)
            
            return {
                'objects': objects,
                'scene_type': scene_type,
                'colors': colors,
                'confidence': self._calculate_confidence(objects, scene_type),
                'success': True
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'success': False
            }
            
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """Estrae testo da un'immagine usando OCR"""
        try:
            if not os.path.exists(image_path):
                return {
                    'error': 'File non trovato',
                    'success': False
                }
                
            if self.ocr_processor:
                result = self.ocr_processor.process_image(image_path)
                return {
                    'text': result.get('text', []),
                    'confidence': result.get('statistics', {}).get('average_confidence', 0),
                    'success': True
                }
            else:
                return {
                    'error': 'OCR processor non disponibile',
                    'success': False
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'success': False
            }
            
    def get_context_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Recupera un contesto dalla memoria"""
        try:
            for context in self.context_memory:
                if context.get('id') == memory_id:
                    return context
            return None
        except Exception as e:
            print(f"Error in get_context_memory: {e}")
            return None
            
    def update_context_memory(self, context: Dict[str, Any]) -> bool:
        """Aggiorna un contesto nella memoria"""
        try:
            for i, stored_context in enumerate(self.context_memory):
                if stored_context.get('id') == context.get('id'):
                    # Aggiorna il contesto
                    self.context_memory[i] = context
                    return True
            return False
        except Exception as e:
            print(f"Error in update_context_memory: {e}")
            return False
            
    def search_context(self, query: str) -> List[Dict[str, Any]]:
        """Cerca nei contesti memorizzati"""
        try:
            if not query:
                return []
                
            results = []
            query = query.lower()
            
            for context in self.context_memory:
                # Cerca nel testo del contesto
                if 'text' in context and query in context['text'].lower():
                    results.append(context)
                    continue
                    
                # Cerca nell'analisi testuale
                if 'text_analysis' in context:
                    text_analysis = context['text_analysis']
                    if 'original_text' in text_analysis and query in text_analysis['original_text'].lower():
                        results.append(context)
                        continue
                        
                # Cerca nelle emozioni
                if 'emotions' in context and query in context['emotions']['label'].lower():
                    results.append(context)
                    continue
                    
            return results
            
        except Exception as e:
            print(f"Error in search_context: {e}")
            return []

    def integrate_contexts(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Integra più contesti in uno unico"""
        try:
            integrated = {}
            
            for context in contexts:
                # Integra le emozioni (prendi quella con score più alto)
                if 'emotions' in context:
                    current_score = integrated.get('emotions', {}).get('score', 0)
                    if context['emotions']['score'] > current_score:
                        integrated['emotions'] = context['emotions']
                        
                # Integra i tempi rilevati
                if 'detected_times' in context:
                    if 'detected_times' not in integrated:
                        integrated['detected_times'] = []
                    integrated['detected_times'].extend(context['detected_times'])
                    
                # Integra il testo
                if 'text' in context:
                    if 'text' not in integrated:
                        integrated['text'] = []
                    if isinstance(integrated['text'], list):
                        integrated['text'].append(context['text'])
                    else:
                        integrated['text'] = [integrated['text'], context['text']]
                        
                # Mantieni l'ultima lingua rilevata
                if 'language' in context:
                    integrated['language'] = context['language']
                    
            # Aggiungi timestamp dell'integrazione
            integrated['timestamp'] = datetime.now().isoformat()
            
            return integrated
            
        except Exception as e:
            print(f"Error in integrate_contexts: {e}")
            return {}
            
    def _analyze_scene(self, image: np.ndarray) -> Dict[str, Any]:
        """Analizza il tipo di scena in un'immagine"""
        try:
            # Calcola istogramma dei colori
            hist = cv2.calcHist([image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            # Analisi semplificata basata su istogramma
            # In produzione, usare un modello di ML più sofisticato
            if np.mean(image) < 50:  # Immagine molto scura
                return {'type': 'night_scene', 'confidence': 0.8}
            elif np.mean(image) > 200:  # Immagine molto chiara
                return {'type': 'bright_scene', 'confidence': 0.8}
            else:
                return {'type': 'normal_scene', 'confidence': 0.6}
                
        except Exception as e:
            print(f"Error in _analyze_scene: {e}")
            return {'type': 'unknown', 'confidence': 0.0}
            
    def _detect_objects(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Rileva oggetti in un'immagine"""
        try:
            # Converti in scala di grigi
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Applica soglia
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            # Trova contorni
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            objects = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 100:  # Filtra oggetti troppo piccoli
                    x, y, w, h = cv2.boundingRect(contour)
                    objects.append({
                        'type': 'unknown_object',
                        'confidence': 0.5,
                        'bbox': [x, y, w, h],
                        'area': area
                    })
                    
            return objects
            
        except Exception as e:
            print(f"Error in _detect_objects: {e}")
            return []
            
    def _analyze_colors(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """Analizza i colori dominanti in un'immagine"""
        try:
            # Converti in RGB per una migliore analisi dei colori
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Reshape per l'analisi
            pixels = image_rgb.reshape(-1, 3)
            
            # Calcola i colori dominanti (versione semplificata)
            unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)
            total_pixels = len(pixels)
            
            # Prendi i top 5 colori
            top_indices = np.argsort(counts)[-5:][::-1]
            
            colors = []
            for idx in top_indices:
                color = unique_colors[idx]
                percentage = (counts[idx] / total_pixels) * 100
                colors.append({
                    'rgb': color.tolist(),
                    'percentage': float(percentage)
                })
                
            return colors
            
        except Exception as e:
            print(f"Error in _analyze_colors: {e}")
            return []
            
    def _calculate_confidence(self, objects: List[Dict[str, Any]],
                            scene_type: Dict[str, Any]) -> float:
        """Calcola la confidenza complessiva dell'analisi"""
        try:
            confidences = []
            
            # Aggiungi confidenza della scena
            if scene_type and 'confidence' in scene_type:
                confidences.append(scene_type['confidence'])
                
            # Aggiungi confidenza degli oggetti
            for obj in objects:
                if 'confidence' in obj:
                    confidences.append(obj['confidence'])
                    
            # Calcola media se ci sono valori
            if confidences:
                return sum(confidences) / len(confidences)
            return 0.0
            
        except Exception as e:
            print(f"Error in _calculate_confidence: {e}")
            return 0.0

    def update_context(self, text: str, current_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Aggiorna il contesto con le informazioni dal testo
        
        Args:
            text: Il testo da analizzare
            current_context: Il contesto corrente da aggiornare (opzionale)
            
        Returns:
            Il nuovo contesto aggiornato
        """
        if current_context is None:
            current_context = self._current_context.copy()
            
        # Estrai concetti e aggiornali come topics
        concepts = self.information_extractor.extract_concepts(text)
        if concepts:
            if 'topics' not in current_context:
                current_context['topics'] = []
            current_context['topics'].extend(concepts)
            if len(concepts) > 0:
                current_context['topic'] = concepts[0]  # Topic principale
            
        # Estrai entità
        entities = self.information_extractor.extract_entities(text)
        if entities:
            if 'entities' not in current_context:
                current_context['entities'] = {}
            for entity_type, values in entities.items():
                if entity_type not in current_context['entities']:
                    current_context['entities'][entity_type] = []
                current_context['entities'][entity_type].extend(values)
                    
        # Aggiorna il timestamp
        current_context['timestamp'] = time.time()
        
        # Aggiorna anche il contesto interno
        self._current_context = current_context.copy()
        
        return current_context

    def get_current_context(self) -> Dict:
        """Restituisce il contesto corrente"""
        return self._current_context

    def analyze_context(self, text: str) -> Dict[str, Any]:
        """Analizza il contesto del testo"""
        # Estrae le informazioni dal testo
        entities = self.extract_entities(text)
        topics = self.extract_topics(text)
        
        # Aggiorna il contesto corrente
        self._current_context.update({
            'entities': entities,
            'topics': topics,
            'timestamp': time.time()
        })
        
        return self._current_context
        
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Estrae le entità dal testo"""
        # Crea un estrattore di informazioni
        extractor = InformationExtractor()
        return extractor.extract_entities(text)
        
    def extract_topics(self, text: str) -> List[str]:
        """Estrae i topic dal testo"""
        # Crea un estrattore di informazioni
        extractor = InformationExtractor()
        return extractor.extract_concepts(text)

    def get_current_topic(self) -> str:
        """Ottiene il topic corrente dalla conversazione"""
        if not self._current_context['topics']:
            return ''
            
        # Prendi il topic più recente
        return self._current_context['topics'][-1]
