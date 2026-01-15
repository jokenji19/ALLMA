"""
Modulo per l'estrazione di informazioni da vari tipi di input.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
import os
from .nlp_processor import NLPProcessor
from .ocr_processor import OCRProcessor
from .visual_memory import VisualMemorySystem

class InformationExtractor:
    """Classe per l'estrazione di informazioni da vari tipi di input"""
    
    def __init__(self):
        """Inizializza il sistema di estrazione"""
        self.nlp_processor = NLPProcessor()
        self.ocr_processor = OCRProcessor()
        self.visual_memory = VisualMemorySystem()
        
        # Espressioni regolari per pattern comuni
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'url': r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*',
            'date': r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
            'time': r'\b\d{1,2}:\d{2}\b',
            'number': r'\b\d+(?:\.\d+)?(?![-\d:/])',  # Numero non seguito da altri numeri o separatori
            'codice_fiscale': r'[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]',
            'partita_iva': r'IT\d{11}',
            'iban': r'IT\d{2}[A-Z]\d{22}',
            'gps': r'\b\d+(?:\.\d+)?°\s*[NS],\s*\d+(?:\.\d+)?°\s*[EW]\b'
        }
        
        # Categorie di entità
        self.entity_categories = {
            'person': ['nome', 'cognome', 'età', 'professione'],
            'location': ['città', 'indirizzo', 'paese', 'coordinate'],
            'organization': ['azienda', 'dipartimento', 'ruolo'],
            'temporal': ['data', 'ora', 'durata', 'frequenza'],
            'quantity': ['numero', 'percentuale', 'importo']
        }
        
    def extract_from_text(self, text: str, context: Dict[str, Any] = None, language: str = 'it') -> Dict[str, Any]:
        """Estrae informazioni da testo"""
        extracted = {
            'patterns': self._extract_patterns(text),
            'entities': self._extract_entities(text, context=context),
            'keywords': self._extract_keywords(text),
            'sentiment': self._analyze_sentiment(text),
            'relationships': self.extract_relationships(text),
            'domain_specific': self._extract_domain_specific(text, context) if context and 'domain' in context else {},
            'timestamp': datetime.now()
        }
        return extracted
        
    def extract_from_image(self, image_path: str) -> Dict[str, Any]:
        """Estrae informazioni da un'immagine"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"File non trovato: {image_path}")
            
        # Estrae testo dall'immagine usando OCR
        ocr_text = self.ocr_processor.extract_text(image_path)
        
        # Analizza l'immagine con il sistema di memoria visiva
        visual_analysis = self.visual_memory.analyze_image(image_path)
        
        # Combina i risultati
        extracted = {
            'ocr_text': ocr_text,
            'visual_objects': visual_analysis.get('objects', []),
            'scene_description': visual_analysis.get('description', ''),
            'text_in_image': self._extract_patterns(ocr_text),
            'timestamp': datetime.now()
        }
        return extracted
        
    def extract_from_document(self, document_path: str) -> Dict[str, Any]:
        """Estrae informazioni da un documento"""
        # TODO: Implementare l'estrazione da documenti
        raise NotImplementedError("L'estrazione da documenti non è ancora implementata")
        
    def _extract_patterns(self, text: str) -> Dict[str, List[str]]:
        """Estrae pattern comuni dal testo usando regex"""
        # Estrai i pattern nell'ordine corretto per evitare sovrapposizioni
        extracted_patterns = {}
        
        # Prima estrai i pattern più specifici
        for pattern_name in ['email', 'phone', 'url', 'date', 'time', 'codice_fiscale', 'partita_iva', 'iban', 'gps']:
            matches = re.findall(self.patterns[pattern_name], text)
            if matches:
                extracted_patterns[pattern_name] = matches
                # Rimuovi i match dal testo per evitare che vengano rilevati come numeri
                for match in matches:
                    text = text.replace(match, ' ' * len(match))
                    
        # Poi estrai i numeri dal testo rimanente
        matches = re.findall(self.patterns['number'], text)
        if matches:
            extracted_patterns['number'] = matches
            
        return extracted_patterns
        
    def _extract_entities(self, text: str, context: Dict[str, Any] = None) -> Dict[str, List[str]]:
        """Estrae entità dal testo"""
        entities = self.nlp_processor.extract_entities(text, context=context)
        extracted_entities = {}
        
        for category, items in entities.items():
            extracted_items = []
            for item in items:
                if item.lower() not in [x.lower() for x in extracted_items]:
                    extracted_items.append(item)
            extracted_entities[category] = extracted_items
            
        return extracted_entities
        
    def _extract_keywords(self, text: str) -> List[str]:
        """Estrae parole chiave dal testo"""
        return self.nlp_processor.extract_keywords(text)
        
    def _analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analizza il sentiment del testo"""
        return self.nlp_processor.analyze_sentiment(text)
        
    def extract_relationships(self, text: str) -> List[Tuple[str, str, str]]:
        """Estrae relazioni tra entità dal testo"""
        # Estrae prima le entità
        entities = self._extract_entities(text)
        relationships = []
        
        # Cerca relazioni tra entità della stessa categoria
        for category, items in entities.items():
            if len(items) > 1:
                # Analizza il contesto tra ogni coppia di entità
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        # Trova il testo tra le due entità
                        start = text.find(items[i])
                        end = text.find(items[j])
                        if start != -1 and end != -1:
                            context = text[start:end]
                            # Cerca verbi o preposizioni che indicano una relazione
                            relation = self._identify_relationship(context)
                            if relation:
                                relationships.append((items[i], relation, items[j]))
                                
        return relationships
        
    def _identify_relationship(self, context: str) -> Optional[str]:
        """Identifica il tipo di relazione dal contesto"""
        # Verbi comuni che indicano relazioni
        relation_verbs = {
            'è': 'is',
            'ha': 'has',
            'lavora': 'works_for',
            'vive': 'lives_in',
            'conosce': 'knows',
            'appartiene': 'belongs_to'
        }
        
        # Cerca i verbi nel contesto
        for verb, relation in relation_verbs.items():
            if verb in context.lower():
                return relation
                
        return None
        
    def _extract_domain_specific(self, text: str, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """Estrae informazioni specifiche per il dominio"""
        domain = context.get('domain', '')
        domain_info = {}
        
        if domain == 'tech':
            # Estrai termini tecnici
            tech_terms = {
                'software': ['app', 'software', 'programma', 'applicazione', 'sistema'],
                'hardware': ['dispositivo', 'device', 'hardware', 'server', 'computer'],
                'action': ['rilasciato', 'sviluppato', 'implementato', 'ottimizzato']
            }
            
            for category, terms in tech_terms.items():
                matches = []
                for term in terms:
                    if term.lower() in text.lower():
                        matches.append(term)
                if matches:
                    domain_info[category] = matches
                    
        return domain_info
