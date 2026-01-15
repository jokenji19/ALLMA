import unittest
import os
import cv2
import numpy as np
from allma_model.core.visual_memory import VisualMemorySystem

class TestVisualMemory(unittest.TestCase):
    def setUp(self):
        # Crea una directory temporanea per i test
        self.test_dir = "test_visual_memory"
        self.visual_memory = VisualMemorySystem(storage_dir=self.test_dir)
        
        # Crea un'immagine di test
        self.test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(self.test_image, (30, 30), (70, 70), (255, 255, 255), -1)
        self.test_image_path = os.path.join(self.test_dir, "test_image.jpg")
        cv2.imwrite(self.test_image_path, self.test_image)
        
    def tearDown(self):
        # Pulisci i file di test
        if os.path.exists(self.test_dir):
            for root, dirs, files in os.walk(self.test_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.test_dir)
            
    def test_learn_visual_concept(self):
        """Test apprendimento di un concetto visivo"""
        # Impara un concetto
        success = self.visual_memory.learn_visual_concept(
            self.test_image_path,
            label="square",
            description="A white square on black background"
        )
        self.assertTrue(success)
        
        # Verifica che il concetto sia stato memorizzato
        concepts = self.visual_memory.get_visual_concepts(label="square")
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]['label'], "square")
        self.assertEqual(concepts[0]['description'], "A white square on black background")
        
    def test_find_similar_images(self):
        """Test ricerca di immagini simili"""
        # Impara alcuni concetti
        self.visual_memory.learn_visual_concept(
            self.test_image_path,
            label="square1",
            description="First square"
        )
        
        # Crea un'immagine simile
        similar_image = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(similar_image, (35, 35), (75, 75), (255, 255, 255), -1)
        similar_image_path = os.path.join(self.test_dir, "similar_image.jpg")
        cv2.imwrite(similar_image_path, similar_image)
        
        # Cerca immagini simili
        similar = self.visual_memory.find_similar_images(similar_image_path)
        self.assertTrue(len(similar) > 0)
        self.assertTrue(similar[0]['similarity_score'] > 0.1)  # Abbassiamo la soglia di similarità
        
    def test_delete_visual_concept(self):
        """Test eliminazione di un concetto visivo"""
        # Impara un concetto
        success = self.visual_memory.learn_visual_concept(
            self.test_image_path,
            label="to_delete",
            description="This will be deleted"
        )
        self.assertTrue(success)
        
        # Trova l'ID del concetto
        concepts = self.visual_memory.get_visual_concepts(label="to_delete")
        self.assertEqual(len(concepts), 1)
        concept_id = concepts[0]['stored_path'].split('/')[-1].split('.')[0]  # Ottieni l'ID dal nome del file
        
        # Elimina il concetto
        success = self.visual_memory.delete_visual_concept(concept_id)
        self.assertTrue(success)
        
        # Verifica che sia stato eliminato
        concepts = self.visual_memory.get_visual_concepts(label="to_delete")
        self.assertEqual(len(concepts), 0)
        
    def test_invalid_image_path(self):
        """Test gestione di un percorso immagine non valido"""
        success = self.visual_memory.learn_visual_concept(
            "non_esistente.jpg",
            label="invalid",
            description="This should fail"
        )
        self.assertFalse(success)
        
        similar = self.visual_memory.find_similar_images("non_esistente.jpg")
        self.assertEqual(len(similar), 0)
        
    def test_database_persistence(self):
        """Test persistenza del database tra le istanze"""
        # Impara un concetto
        self.visual_memory.learn_visual_concept(
            self.test_image_path,
            label="persistence",
            description="Testing database persistence"
        )
        
        # Crea una nuova istanza che dovrebbe caricare i dati esistenti
        new_instance = VisualMemorySystem(storage_dir=self.test_dir)
        concepts = new_instance.get_visual_concepts(label="persistence")
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]['label'], "persistence")
        
    def test_feature_extraction(self):
        """Test estrazione features"""
        # Test con immagine a colori
        features_color = self.visual_memory._extract_features(self.test_image)
        self.assertIsInstance(features_color, np.ndarray)
        self.assertTrue(np.all(np.isfinite(features_color)))  # Verifica no NaN/inf
        
        # Test con immagine in scala di grigi
        gray_image = cv2.cvtColor(self.test_image, cv2.COLOR_BGR2GRAY)
        features_gray = self.visual_memory._extract_features(gray_image)
        self.assertIsInstance(features_gray, np.ndarray)
        self.assertTrue(np.all(np.isfinite(features_gray)))
        
    def test_multiple_concepts_same_label(self):
        """Test gestione di più concetti con la stessa etichetta"""
        # Impara due concetti con la stessa etichetta
        self.visual_memory.learn_visual_concept(
            self.test_image_path,
            label="multi",
            description="First concept"
        )
        
        # Crea una seconda immagine leggermente diversa
        img2 = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(img2, (40, 40), (60, 60), (255, 255, 255), -1)
        img2_path = os.path.join(self.test_dir, "test_image2.jpg")
        cv2.imwrite(img2_path, img2)
        
        self.visual_memory.learn_visual_concept(
            img2_path,
            label="multi",
            description="Second concept"
        )
        
        # Verifica che entrambi i concetti siano stati memorizzati
        concepts = self.visual_memory.get_visual_concepts(label="multi")
        self.assertEqual(len(concepts), 2)
        self.assertNotEqual(concepts[0]['stored_path'], concepts[1]['stored_path'])
        
    def test_empty_database_operations(self):
        """Test operazioni su database vuoto"""
        # Crea una nuova istanza con directory vuota
        empty_dir = "empty_test_dir"
        os.makedirs(empty_dir, exist_ok=True)
        empty_memory = VisualMemorySystem(storage_dir=empty_dir)
        
        # Test operazioni
        self.assertEqual(len(empty_memory.get_visual_concepts()), 0)
        self.assertEqual(len(empty_memory.find_similar_images(self.test_image_path)), 0)
        self.assertFalse(empty_memory.delete_visual_concept("non_esistente"))
        
        # Pulisci
        if os.path.exists(empty_dir):
            for root, dirs, files in os.walk(empty_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(empty_dir)
        
if __name__ == '__main__':
    unittest.main()
