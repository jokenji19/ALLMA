import math
from collections import Counter
import numpy as np

class SimpleTfidf:
    def __init__(self, max_features=None, stop_words=None):
        self.vocab = {}
        self.doc_count = 0
        self.idf = {}
        self.max_features = max_features
        self.stop_words = stop_words or []
        
    def fit_transform(self, documents):
        self.doc_count = len(documents)
        word_counts = []
        all_words = set()
        
        for doc in documents:
            if not isinstance(doc, str):
                continue
            words = doc.lower().split()
            # Basic stop word filtering if list provided
            if self.stop_words == 'english':
                # Minimal placeholder list for english
                pass 
                
            counts = Counter(words)
            word_counts.append(counts)
            all_words.update(words)
            
        self.vocab = sorted(list(all_words))
        
        # Implement max_features limitation if requested
        if self.max_features and len(self.vocab) > self.max_features:
            # Sort by frequency across all docs
            total_counts = Counter()
            for wc in word_counts:
                total_counts.update(wc)
            most_common = total_counts.most_common(self.max_features)
            self.vocab = sorted([word for word, count in most_common])

        self.idf = {}
        
        for word in self.vocab:
            doc_freq = sum(1 for counts in word_counts if word in counts)
            self.idf[word] = math.log(self.doc_count / (1 + doc_freq))
            
        vectors = []
        for counts in word_counts:
            vector = [counts[word] * self.idf.get(word, 0) for word in self.vocab]
            vectors.append(vector)
            
        return np.array(vectors)

    def get_feature_names_out(self):
        return self.vocab
        
    def transform(self, documents):
        vectors = []
        for doc in documents:
            if not isinstance(doc, str):
                vectors.append([0] * len(self.vocab))
                continue
            words = doc.lower().split()
            counts = Counter(words)
            vector = [counts[word] * self.idf.get(word, 0) for word in self.vocab]
            vectors.append(vector)
        return np.array(vectors)

def cosine_similarity(v1, v2):
    # Ensure inputs are numpy arrays
    v1 = np.array(v1)
    v2 = np.array(v2)
    
    # Handle 2D arrays (matrices) vs 1D arrays
    if v1.ndim == 1:
        v1 = v1.reshape(1, -1)
    if v2.ndim == 1:
        v2 = v2.reshape(1, -1)
        
    # Calculate norms
    norm1 = np.linalg.norm(v1, axis=1)
    norm2 = np.linalg.norm(v2, axis=1)
    
    # Avoid division by zero
    norm1[norm1 == 0] = 1e-10
    norm2[norm2 == 0] = 1e-10
    
    # Calculate dot product
    dot_product = np.dot(v1, v2.T)
    
    # Calculate similarity
    similarity = dot_product / (norm1[:, None] * norm2)
    
    return similarity
