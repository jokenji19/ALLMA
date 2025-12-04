"""
Test delle strutture cognitive fondamentali.
"""

import unittest
from .cognitive_foundations import (
    ConceptType, 
    Concept, 
    SemanticNetwork,
    CognitiveStructures,
    EnhancedCognitiveProcessor,
    CausalStructure
)

class TestCognitiveFoundations(unittest.TestCase):
    def setUp(self):
        """Inizializza il processore cognitivo per i test"""
        self.processor = EnhancedCognitiveProcessor()
        
    def test_basic_concepts(self):
        """Testa il riconoscimento di concetti base"""
        text = "Il libro è sopra il tavolo"
        result = self.processor.process_input(text)
        
        # Verifica che il concetto spaziale "sopra" sia riconosciuto
        concepts = result["concepts"]
        self.assertTrue(any(name == "sopra" for name, type_, _ in concepts))
        self.assertTrue(any(type_ == "spatial" for name, type_, _ in concepts))
        
    def test_multiple_concepts(self):
        """Testa il riconoscimento di concetti multipli e loro relazioni"""
        text = "Prima di mettere il libro sopra il tavolo, devo spostare la lampada"
        result = self.processor.process_input(text)
        
        # Verifica concetti temporali e spaziali
        concepts = result["concepts"]
        self.assertTrue(any(name == "prima" for name, type_, _ in concepts))
        self.assertTrue(any(name == "sopra" for name, type_, _ in concepts))
        
        # Verifica relazioni
        relations = result["relations"]
        self.assertTrue(len(relations) > 0)
        
    def test_causal_understanding(self):
        """Testa la comprensione di relazioni causali"""
        text = "Se piove, quindi prendo l'ombrello"
        result = self.processor.process_input(text)
        
        # Verifica relazione di implicazione
        relations = result["relations"]
        self.assertTrue(any(rel_type == "implicazione" for _, _, rel_type, _ in relations))
        
        # Verifica che l'antecedente e il conseguente siano corretti
        causal_rel = [r for r in relations if r[2] == "implicazione"][0]
        self.assertEqual(causal_rel[0], "piove")
        self.assertEqual(causal_rel[1], "prendo l'ombrello")
        
    def test_concept_examples(self):
        """Testa il riconoscimento attraverso esempi"""
        text = "Il contenuto è all'interno del contenitore"
        result = self.processor.process_input(text)
        
        # Verifica che "all'interno" sia riconosciuto come esempio di "dentro"
        concepts = result["concepts"]
        self.assertTrue(any(name == "dentro" for name, type_, _ in concepts))
        
    def test_relation_strength(self):
        """Testa la forza delle relazioni tra concetti"""
        text = "Prima viene la teoria, dopo la pratica"
        result = self.processor.process_input(text)
        
        # Verifica relazione forte tra "prima" e "dopo"
        relations = result["relations"]
        prima_dopo = [(s, t, r, v) for s, t, r, v in relations 
                     if (s == "prima" and t == "dopo") or (s == "dopo" and t == "prima")]
        
        self.assertTrue(len(prima_dopo) > 0)
        self.assertEqual(prima_dopo[0][3], 1.0)  # Forza massima
        
    def test_complex_causal_patterns(self):
        """Testa pattern causali più complessi"""
        test_cases = [
            (
                "Quando piove, succede che la strada si bagna",
                "temporale_causale",
                0.7
            ),
            (
                "Perché ho studiato, quindi ho superato l'esame",
                "conseguenza",
                1.0
            ),
            (
                "Nel caso in cui nevichi, allora resterò a casa",
                "implicazione",
                0.9
            )
        ]
        
        for text, expected_type, expected_strength in test_cases:
            result = self.processor.process_input(text)
            relations = result["relations"]
            
            # Verifica che il tipo di relazione sia corretto
            self.assertTrue(any(rel_type == expected_type for _, _, rel_type, _ in relations),
                          f"Non trovata relazione di tipo {expected_type} in: {text}")
            
            # Verifica la forza della relazione
            matching_relations = [r for r in relations if r[2] == expected_type]
            self.assertEqual(matching_relations[0][3], expected_strength,
                           f"Forza della relazione errata per: {text}")
        
if __name__ == '__main__':
    unittest.main()
