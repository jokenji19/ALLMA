import unittest
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from allma_model.core.ocr_processor import OCRProcessor

class TestOCRProcessor(unittest.TestCase):
    def setUp(self):
        """Setup per i test"""
        self.ocr = OCRProcessor()
        self.test_dir = "test_ocr"
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        """Pulizia dopo i test"""
        if os.path.exists(self.test_dir):
            for file in os.listdir(self.test_dir):
                os.remove(os.path.join(self.test_dir, file))
            os.rmdir(self.test_dir)
            
    def create_test_image(self, text: str, filename: str) -> str:
        """Crea un'immagine di test con il testo specificato"""
        # Crea un'immagine bianca grande
        width = 1000
        height = 300
        image = np.full((height, width, 3), 255, dtype=np.uint8)
        
        # Usa OpenCV per aggiungere il testo
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2.0
        thickness = 3
        color = (0, 0, 0)  # Nero
        
        # Calcola la dimensione del testo
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Calcola la posizione per centrare il testo
        x = (width - text_width) // 2
        y = (height + text_height) // 2
        
        # Aggiungi il testo
        cv2.putText(image, text, (x, y), font, font_scale, color, thickness)
        
        # Salva l'immagine
        image_path = os.path.join(self.test_dir, filename)
        cv2.imwrite(image_path, image)
        
        return image_path
        
    def test_text_detection(self):
        """Test rilevamento testo base"""
        # Crea un'immagine con testo semplice
        test_text = "HELLO ALLMA"
        image_path = self.create_test_image(test_text, "hello.jpg")
        
        # Carica l'immagine
        image = cv2.imread(image_path)
        
        # Rileva il testo
        regions = self.ocr.detect_text_regions(image)
        
        # Verifica che almeno una regione sia stata trovata
        self.assertTrue(len(regions) > 0)
        
        # Verifica che il testo sia stato rilevato correttamente
        found_text = False
        detected_text = ""
        for region in regions:
            detected_text += region.text + " "
            if "ALLMA" in region.text:
                found_text = True
                break
        print(f"Detected text: {detected_text}")  # Per debug
        self.assertTrue(found_text)
        
    def test_text_classification(self):
        """Test classificazione tipi di testo"""
        # Test date
        self.assertEqual(self.ocr._classify_text_type("12/03/2024"), "date")
        self.assertEqual(self.ocr._classify_text_type("2024-01-21"), "date")
        
        # Test numeri
        self.assertEqual(self.ocr._classify_text_type("12345"), "number")
        self.assertEqual(self.ocr._classify_text_type("123.45"), "number")
        
        # Test email
        self.assertEqual(self.ocr._classify_text_type("test@example.com"), "email")
        
        # Test URL
        self.assertEqual(self.ocr._classify_text_type("https://www.example.com"), "url")
        
        # Test testo normale
        self.assertEqual(self.ocr._classify_text_type("Normal text"), "text")
        
    def test_text_extraction(self):
        """Test estrazione completa del testo"""
        # Crea un'immagine con diversi tipi di testo
        test_text = "TEST@EMAIL.COM 12345 2024-01-21"
        image_path = self.create_test_image(test_text, "complex.jpg")
        
        # Analizza l'immagine
        image = cv2.imread(image_path)
        results = self.ocr.extract_text_from_image(image)
        
        # Verifica che abbiamo risultati per ogni categoria
        self.assertTrue('text' in results)
        self.assertTrue('numbers' in results)
        self.assertTrue('dates' in results)
        self.assertTrue('emails' in results)
        self.assertTrue('urls' in results)
        
        # Verifica le statistiche
        self.assertTrue('statistics' in results)
        self.assertTrue(results['statistics']['total_regions'] > 0)
        
    def test_highlighting(self):
        """Test evidenziazione delle regioni di testo"""
        # Crea un'immagine di test
        test_text = "TEST 123"
        image_path = self.create_test_image(test_text, "highlight.jpg")
        
        # Carica l'immagine
        image = cv2.imread(image_path)
        
        # Rileva le regioni
        regions = self.ocr.detect_text_regions(image)
        
        # Evidenzia le regioni
        highlighted = self.ocr.highlight_text_regions(image, regions)
        
        # Verifica che l'immagine evidenziata sia diversa dall'originale
        self.assertFalse(np.array_equal(image, highlighted))
        
        # Salva l'immagine evidenziata per ispezione visiva
        highlighted_path = os.path.join(self.test_dir, "highlighted.jpg")
        cv2.imwrite(highlighted_path, highlighted)
        
if __name__ == '__main__':
    unittest.main()
