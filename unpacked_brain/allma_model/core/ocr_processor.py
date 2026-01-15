import cv2
import numpy as np
import pytesseract
from PIL import Image
from typing import Dict, List, Optional, Any
import re
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TextRegion:
    text: str
    confidence: float
    box: tuple  # (x, y, width, height)
    type: str  # 'text', 'number', 'date', etc.

class OCRProcessor:
    def __init__(self):
        """Inizializza il processore OCR"""
        # Configura pytesseract
        self.langs = 'ita+eng'  # Supporto per italiano e inglese
        
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocessa l'immagine per migliorare l'OCR"""
        # Converti in scala di grigi
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Ridimensiona se l'immagine è troppo piccola
        min_width = 1000
        scale = max(min_width / gray.shape[1], 1.0)
        if scale > 1.0:
            width = int(gray.shape[1] * scale)
            height = int(gray.shape[0] * scale)
            gray = cv2.resize(gray, (width, height), interpolation=cv2.INTER_CUBIC)
            
        # Denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Aumenta il contrasto
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Binarizzazione di Otsu
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Dilatazione per connettere componenti del testo
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        return dilated
        
    def detect_text_regions(self, image: np.ndarray) -> List[TextRegion]:
        """Rileva e classifica le regioni di testo nell'immagine"""
        # Preprocessa l'immagine
        processed = self.preprocess_image(image)
        
        # Esegui OCR con dati dettagliati
        data = pytesseract.image_to_data(processed, lang=self.langs, output_type=pytesseract.Output.DICT)
        
        regions = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            # Salta box vuoti
            if int(data['conf'][i]) < 0 or not data['text'][i].strip():
                continue
                
            # Estrai coordinate e dimensioni
            x = data['left'][i]
            y = data['top'][i]
            w = data['width'][i]
            h = data['height'][i]
            
            text = data['text'][i]
            conf = float(data['conf'][i]) / 100.0
            
            # Classifica il tipo di testo
            text_type = self._classify_text_type(text)
            
            regions.append(TextRegion(
                text=text,
                confidence=conf,
                box=(x, y, w, h),
                type=text_type
            ))
            
        return regions
        
    def _classify_text_type(self, text: str) -> str:
        """Classifica il tipo di testo"""
        # Rimuovi spazi e converti in minuscolo per l'analisi
        clean_text = text.strip().lower()
        
        # Controlla se è una data
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # dd/mm/yyyy
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',    # yyyy/mm/dd
        ]
        for pattern in date_patterns:
            if re.match(pattern, clean_text):
                return 'date'
                
        # Controlla se è un numero
        if clean_text.replace('.', '').replace(',', '').isdigit():
            return 'number'
            
        # Controlla se è un'email
        if '@' in clean_text and '.' in clean_text:
            return 'email'
            
        # Controlla se è un URL
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        if re.match(url_pattern, clean_text):
            return 'url'
            
        return 'text'
        
    def extract_text_from_image(self, image: np.ndarray) -> Dict[str, Any]:
        """Estrae e analizza il testo da un'immagine"""
        try:
            # Rileva le regioni di testo
            regions = self.detect_text_regions(image)
            
            # Organizza i risultati per tipo
            results = {
                'text': [],
                'numbers': [],
                'dates': [],
                'emails': [],
                'urls': []
            }
            
            # Raggruppa i risultati per tipo
            for region in regions:
                if region.type == 'text':
                    results['text'].append({
                        'text': region.text,
                        'confidence': region.confidence,
                        'position': region.box
                    })
                elif region.type == 'number':
                    results['numbers'].append({
                        'value': region.text,
                        'confidence': region.confidence,
                        'position': region.box
                    })
                elif region.type == 'date':
                    results['dates'].append({
                        'date': region.text,
                        'confidence': region.confidence,
                        'position': region.box
                    })
                elif region.type == 'email':
                    results['emails'].append({
                        'email': region.text,
                        'confidence': region.confidence,
                        'position': region.box
                    })
                elif region.type == 'url':
                    results['urls'].append({
                        'url': region.text,
                        'confidence': region.confidence,
                        'position': region.box
                    })
                    
            # Calcola statistiche generali
            results['statistics'] = {
                'total_regions': len(regions),
                'average_confidence': np.mean([r.confidence for r in regions]) if regions else 0,
                'processed_timestamp': datetime.now().isoformat()
            }
            
            return results
            
        except Exception as e:
            print(f"Error in extract_text_from_image: {e}")
            return {
                'error': str(e),
                'statistics': {
                    'total_regions': 0,
                    'average_confidence': 0,
                    'processed_timestamp': datetime.now().isoformat()
                }
            }
            
    def extract_text(self, image_path: str) -> str:
        """Estrae il testo da un'immagine"""
        try:
            # Leggi l'immagine
            image = cv2.imread(image_path)
            if image is None:
                raise FileNotFoundError(f"Impossibile leggere l'immagine: {image_path}")
                
            # Estrai il testo usando il metodo esistente
            results = self.extract_text_from_image(image)
            
            # Combina tutto il testo trovato
            all_text = []
            
            # Aggiungi il testo normale
            for text_item in results.get('text', []):
                all_text.append(text_item['text'])
                
            # Aggiungi numeri
            for num_item in results.get('numbers', []):
                all_text.append(num_item['value'])
                
            # Aggiungi date
            for date_item in results.get('dates', []):
                all_text.append(date_item['date'])
                
            # Aggiungi email
            for email_item in results.get('emails', []):
                all_text.append(email_item['email'])
                
            # Aggiungi URL
            for url_item in results.get('urls', []):
                all_text.append(url_item['url'])
                
            # Unisci tutto il testo con spazi
            return ' '.join(all_text)
            
        except Exception as e:
            print(f"Error in extract_text: {e}")
            return ""
            
    def highlight_text_regions(self, image: np.ndarray, regions: List[TextRegion]) -> np.ndarray:
        """Evidenzia le regioni di testo nell'immagine"""
        # Crea una copia dell'immagine
        highlighted = image.copy()
        
        # Colori per i diversi tipi di testo
        colors = {
            'text': (0, 255, 0),    # Verde per testo normale
            'number': (255, 0, 0),   # Rosso per numeri
            'date': (0, 0, 255),     # Blu per date
            'email': (255, 255, 0),  # Giallo per email
            'url': (255, 0, 255)     # Magenta per URL
        }
        
        for region in regions:
            x, y, w, h = region.box
            color = colors.get(region.type, (0, 255, 0))
            
            # Disegna un rettangolo intorno al testo
            cv2.rectangle(highlighted, (x, y), (x + w, y + h), color, 2)
            
            # Aggiungi un'etichetta con il tipo e la confidenza
            label = f"{region.type} ({region.confidence:.2f})"
            cv2.putText(highlighted, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                       
        return highlighted

    def process_image(self, image_path: str) -> Dict[str, Any]:
        """Processa un'immagine ed estrae testo e altri dati"""
        try:
            # Carica l'immagine
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Impossibile caricare l'immagine")
                
            # Converti in scala di grigi
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Applica soglia per migliorare il contrasto
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Esegui OCR
            text = pytesseract.image_to_string(binary)
            
            # Estrai dati strutturati
            data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT)
            
            # Analizza il testo per estrarre informazioni specifiche
            result = {
                'text': text.split('\n'),
                'numbers': self._extract_numbers(text),
                'dates': self._extract_dates(text),
                'emails': self._extract_emails(text),
                'urls': self._extract_urls(text),
                'statistics': {
                    'total_regions': len(data['text']),
                    'average_confidence': sum(data['conf']) / len(data['conf']) if data['conf'] else 0,
                    'processed_timestamp': datetime.now().isoformat()
                }
            }
            
            return result
            
        except Exception as e:
            print(f"Error in process_image: {e}")
            return {
                'error': str(e),
                'text': [],
                'numbers': [],
                'dates': [],
                'emails': [],
                'urls': [],
                'statistics': {}
            }
