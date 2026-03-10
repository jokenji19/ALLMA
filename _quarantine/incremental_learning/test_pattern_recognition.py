"""
Test per il Sistema di Pattern Recognition
"""

import unittest
from datetime import datetime, timedelta
import numpy as np
from allma_model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem, Pattern, PatternMatch

class TestPatternRecognitionSystem(unittest.TestCase):
    def setUp(self):
        """Inizializza il sistema per ogni test"""
        self.system = PatternRecognitionSystem(
            confidence_threshold=0.7
        )
        
    def test_pattern_learning(self):
        """Verifica l'apprendimento di nuovi pattern"""
        features = [1.0, 0.0, 0.0]
        category = "test"
        
        print("\n=== Test Pattern Learning ===")
        print(f"Pattern iniziale: {features}")
        
        # Apprendi il primo pattern
        pattern1 = self.system.learn_pattern(features, category)
        print(f"\nDopo primo learn:")
        print(f"Numero pattern: {len(self.system.patterns)}")
        print(f"Pattern ID: {pattern1.id}")
        print(f"Features: {pattern1.features}")
        
        # Apprendi un pattern simile
        features2 = [0.9, 0.1, 0.0]
        print(f"\nPattern simile: {features2}")
        pattern2 = self.system.learn_pattern(features2, category)
        print(f"\nDopo secondo learn:")
        print(f"Numero pattern: {len(self.system.patterns)}")
        print(f"Pattern ID: {pattern2.id}")
        print(f"Features: {pattern2.features}")
        
        self.assertEqual(len(self.system.patterns), 1)
        
    def test_pattern_recognition(self):
        """Verifica il riconoscimento di pattern"""
        # Crea alcuni pattern
        self.system.learn_pattern([1.0, 0.0, 0.0], "category_a")
        self.system.learn_pattern([0.0, 1.0, 0.0], "category_b")
        
        # Riconosce un pattern simile
        matches = self.system.recognize_pattern([0.9, 0.1, 0.0])
        
        self.assertEqual(len(matches), 1)
        self.assertGreater(matches[0].similarity, 0.8)
        
    def test_category_search(self):
        """Verifica la ricerca per categoria"""
        print("\n=== Test Category Search ===")
        
        # Crea pattern in diverse categorie
        p1 = self.system.learn_pattern([1.0, 0.0, 0.0], "cat_1")
        print(f"Pattern 1 (cat_1): {p1.features}")
        
        p2 = self.system.learn_pattern([0.0, 1.0, 0.0], "cat_2")
        print(f"Pattern 2 (cat_2): {p2.features}")
        
        p3 = self.system.learn_pattern([0.997, 0.003, 0.0], "cat_1")
        print(f"Pattern 3 (cat_1): {p3.features}")
        
        # Verifica similarità
        sim = self.system._calculate_similarity(p1.features, p3.features)
        print(f"\nSimilarità tra p1 e p3: {sim}")
        
        # Cerca pattern per categoria
        cat_1_patterns = self.system.find_patterns_by_category("cat_1")
        print(f"\nPattern trovati in cat_1: {len(cat_1_patterns)}")
        for p in cat_1_patterns:
            print(f"- {p.id}: {p.features}")
            
        cat_2_patterns = self.system.find_patterns_by_category("cat_2")
        print(f"\nPattern trovati in cat_2: {len(cat_2_patterns)}")
        for p in cat_2_patterns:
            print(f"- {p.id}: {p.features}")
            
        # Verifica categorie
        print(f"\nCategorie nel sistema:")
        for cat, patterns in self.system.pattern_categories.items():
            print(f"- {cat}: {patterns}")
            
        self.assertEqual(len(cat_1_patterns), 2)
        self.assertEqual(len(cat_2_patterns), 1)
        
    def test_pattern_clustering(self):
        """Verifica il clustering dei pattern"""
        print("\n=== Test Pattern Clustering ===")
        
        # Crea due cluster di pattern
        cluster1 = []
        print("\nCluster 1:")
        for i in range(3):  # Primo cluster
            p = self.system.learn_pattern([-50.0 + i*0.1, -50.0 + i*0.1, 0.0], "cluster_test")
            print(f"- Pattern {i}: {p.features}")
            cluster1.append(p)
            
        cluster2 = []
        print("\nCluster 2:")
        for i in range(3):  # Secondo cluster
            p = self.system.learn_pattern([50.0 + i*0.1, 50.0 + i*0.1, 0.0], "cluster_test")
            print(f"- Pattern {i}: {p.features}")
            cluster2.append(p)
            
        # Stampa alcune similarità
        print("\nSimilarità intra-cluster:")
        print(f"Cluster 1: {self.system._calculate_similarity(cluster1[0].features, cluster1[1].features)}")
        print(f"Cluster 2: {self.system._calculate_similarity(cluster2[0].features, cluster2[1].features)}")
        print("\nSimilarità inter-cluster:")
        print(f"Tra cluster: {self.system._calculate_similarity(cluster1[0].features, cluster2[0].features)}")
        
        clusters = self.system.discover_pattern_clusters(min_samples=2, eps=100.0)
        
        print(f"\nCluster trovati: {len(clusters)}")
        for i, c in clusters.items():
            print(f"\nCluster {i}:")
            for p in c:
                print(f"- {p.features}")
        
        # Dovrebbe trovare due cluster
        self.assertEqual(len(clusters), 2)
        
        # Verifica che i pattern siano nei cluster corretti
        cluster_sets = [{p.id for p in c} for c in clusters.values()]
        cluster1_ids = {p.id for p in cluster1}
        cluster2_ids = {p.id for p in cluster2}
        
        print("\nVerifica dei cluster:")
        print(f"Cluster 1 IDs: {cluster1_ids}")
        print(f"Cluster 2 IDs: {cluster2_ids}")
        print(f"Cluster trovati IDs: {cluster_sets}")
        
        self.assertTrue(any(cluster1_ids.issubset(c) for c in cluster_sets))
        self.assertTrue(any(cluster2_ids.issubset(c) for c in cluster_sets))
        
    def test_related_patterns(self):
        """Verifica la ricerca di pattern correlati"""
        print("\n=== Test Related Patterns ===")
        
        # Crea tre pattern con similarità diverse
        p1 = self.system.learn_pattern([1.0, 0.0, 0.0], "test")
        print(f"Pattern 1: {p1.features}")
        p2 = self.system.learn_pattern([0.9, 0.1, 0.0], "test")  # Molto simile a p1
        print(f"Pattern 2: {p2.features}")
        p3 = self.system.learn_pattern([0.7, 0.3, 0.0], "test")  # Meno simile a p1
        print(f"Pattern 3: {p3.features}")
        
        # Stampa le similarità
        print(f"\nSimilarità tra p1 e p2: {self.system._calculate_similarity(p1.features, p2.features)}")
        print(f"Similarità tra p1 e p3: {self.system._calculate_similarity(p1.features, p3.features)}")
        
        # Cerca pattern correlati
        related = self.system.find_related_patterns(p1.id, min_similarity=0.5)
        
        print(f"\nPattern correlati trovati: {len(related)}")
        for pid in related:
            pattern = self.system.patterns[pid]
            print(f"- {pattern.id}: {pattern.features}")
        
        # Verifica che solo p2 sia correlato
        self.assertEqual(len(related), 1, "Dovrebbe trovare solo un pattern correlato")
        
    def test_pattern_merging(self):
        """Verifica la fusione di pattern"""
        # Crea pattern da unire
        p1 = self.system.learn_pattern([1.0, 0.0, 0.0], "merge_test")
        p2 = self.system.learn_pattern([0.8, 0.2, 0.0], "merge_test")
        
        merged = self.system.merge_patterns([p1.id, p2.id])
        
        self.assertIsNotNone(merged)
        self.assertEqual(len(self.system.patterns), 1)  # Solo il pattern unito
        self.assertEqual(merged.category, "merge_test")
        
    def test_pattern_quality(self):
        """Verifica la valutazione della qualità dei pattern"""
        # Crea un pattern e lo valuta
        pattern = self.system.learn_pattern([1.0, 0.0, 0.0], "quality_test")
        quality = self.system.evaluate_pattern_quality(pattern.id)
        
        self.assertIn('confidence', quality)
        self.assertIn('occurrences', quality)
        self.assertIn('age_days', quality)
        self.assertIn('stability', quality)
        self.assertIn('generalization', quality)
        
    def test_similarity_computation(self):
        """Verifica il calcolo della similarità"""
        features1 = np.array([1.0, 0.0, 0.0])
        features2 = np.array([0.0, 1.0, 0.0])
        features3 = np.array([0.9, 0.1, 0.0])
        
        # Calcola similarità
        sim1_2 = self.system._calculate_similarity(features1, features2)
        sim1_3 = self.system._calculate_similarity(features1, features3)
        
        self.assertLess(sim1_2, sim1_3)  # features3 è più simile a features1
        
    def test_stability_score(self):
        """Verifica il calcolo del punteggio di stabilità"""
        # Crea un pattern
        features = [1.0, 0.0, 0.0]
        pattern = self.system.learn_pattern(features, "stability_test")
        
        # Verifica che un pattern nuovo abbia stabilità massima
        self.assertEqual(pattern.stability_score, 1.0)
        
        # Aggiorna il pattern più volte
        for i in range(5):
            pattern = self.system.learn_pattern([1.0 - 0.1*i, 0.1*i, 0.0], "stability_test")
            
        # Verifica che la stabilità sia diminuita ma ancora positiva
        self.assertLess(pattern.stability_score, 1.0)
        self.assertGreater(pattern.stability_score, 0.0)
        
    def test_generalization_score(self):
        """Verifica il calcolo del punteggio di generalizzazione"""
        # Crea un gruppo di pattern simili
        base_features = np.array([1.0, 0.0, 0.0])
        pattern1 = self.system.learn_pattern(base_features, "gen_test")
        
        # Aggiungi variazioni moderate per buona generalizzazione
        variations = [
            np.array([0.9, 0.1, 0.0]),
            np.array([0.95, 0.05, 0.0]),
            np.array([0.85, 0.15, 0.0])
        ]
        
        for features in variations:
            self.system.learn_pattern(features, "gen_test")
            
        # Simula l'apprendimento ripetuto per aumentare le occorrenze
        for _ in range(3):
            self.system.learn_pattern(base_features, "gen_test")
            
        # Calcola il punteggio di generalizzazione
        gen_score = self.system._calculate_generalization_score(pattern1)
        
        # Il punteggio dovrebbe essere buono per variazioni moderate
        self.assertGreater(gen_score, 0.6,
                          "Il punteggio di generalizzazione dovrebbe essere buono")
        
    def test_validation_score(self):
        """Verifica il calcolo del punteggio di validazione"""
        # Crea un pattern stabile
        features = np.array([1.0, 0.0, 0.0])
        pattern = self.system.learn_pattern(features, "val_test")
        
        # Simula un pattern stabile con buona generalizzazione
        pattern.stability_score = 0.9
        pattern.generalization_score = 0.8
        
        # Calcola il punteggio di validazione per un match simile
        similar_features = np.array([0.9, 0.1, 0.0])
        validation_score = self.system._calculate_validation_score(
            pattern,
            similar_features
        )
        
        # Il punteggio dovrebbe essere alto per un buon match
        self.assertGreater(validation_score, 0.7,
                          "Il punteggio di validazione dovrebbe essere alto")
        
        # Verifica la cache di validazione
        cached_score = self.system._calculate_validation_score(
            pattern,
            similar_features
        )
        self.assertEqual(validation_score, cached_score,
                        "Il punteggio dovrebbe essere recuperato dalla cache")
        
    def test_outlier_detection(self):
        """Verifica il rilevamento degli outlier"""
        # Crea un gruppo di pattern normali
        normal_patterns = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.95, 0.05, 0.0],
            [0.85, 0.15, 0.0]
        ]
        
        for features in normal_patterns:
            self.system.learn_pattern(np.array(features), "outlier_test")
            
        # Prova ad aggiungere un outlier
        outlier_features = np.array([0.0, 0.0, 1.0])
        outlier_pattern = self.system.learn_pattern(outlier_features, "outlier_test")
        
        # L'outlier dovrebbe avere una confidenza più bassa
        self.assertLess(outlier_pattern.confidence, 0.7,
                       "L'outlier dovrebbe avere una confidenza più bassa")
        
    def test_robust_scaling(self):
        """Verifica lo scaling robusto delle caratteristiche"""
        # Crea un sistema con scaling robusto
        robust_system = PatternRecognitionSystem(use_robust_scaling=True)
        
        # Crea pattern con outlier
        features = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [100.0, 0.0, 0.0]  # Outlier
        ]
        
        for f in features:
            robust_system.learn_pattern(np.array(f), "scaling_test")
            
        # Verifica che il sistema possa ancora riconoscere pattern normali
        test_features = np.array([0.95, 0.05, 0.0])
        matches = robust_system.recognize_pattern(test_features)
        
        self.assertGreater(len(matches), 0,
                          "Dovrebbe riconoscere pattern nonostante gli outlier")
        
    def test_pattern_evolution(self):
        """Verifica l'evoluzione dei pattern nel tempo"""
        # Crea un pattern iniziale
        features = np.array([1.0, 0.0, 0.0])
        pattern = self.system.learn_pattern(features, "evolution_test")
        print("\nPattern iniziale:", pattern.features)
        
        # Simula l'evoluzione graduale del pattern
        variations = [
            np.array([0.9, 0.1, 0.0]),
            np.array([0.8, 0.2, 0.0]),
            np.array([0.7, 0.3, 0.0])
        ]
        
        for features in variations:
            print("\nNuove features:", features)
            # Salva le features precedenti
            old_features = pattern.features.copy()
            
            # Ripeti l'apprendimento per forzare l'evoluzione
            for i in range(3):
                pattern = self.system.learn_pattern(features, "evolution_test")
                print(f"Dopo update {i+1}:", pattern.features)
            
            # Verifica che il pattern si sia adattato
            print("Confronto:", old_features, "vs", pattern.features)
            self.assertFalse(np.array_equal(old_features, pattern.features),
                           "Il pattern dovrebbe evolversi")
            
            # Verifica che la stabilità sia mantenuta
            self.assertGreater(pattern.stability_score, 0.5,
                             "Il pattern dovrebbe mantenere una buona stabilità")
            
    if __name__ == '__main__':
        unittest.main()
