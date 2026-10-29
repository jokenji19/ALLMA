"""Raw sparse postings with exact current-corpus TF-IDF at query time."""
from array import array
import math
import numpy as np

from allma_model.utils.memory_concepts import concepts


class IncrementalVectorIndex:
    def __init__(self, tfidf_type):
        self.tfidf = tfidf_type()
        self.entries = []
        self.postings = {}
        self.owners = {}
        self.concepts = {}
        self._idf = None

    def append(self, rows):
        for identifier, owner, text in rows:
            self.tfidf.partial_fit(text)
            vector = self.tfidf.encode_counts(text)
            position = len(self.entries)
            self.entries.append((identifier, owner, vector))
            self.owners.setdefault(owner, []).append(position)
            for term, count in zip(vector.indices, vector.weights):
                positions, counts = self.postings.setdefault(int(term), {}).setdefault(
                    owner, (array('q'), array('f')))
                positions.append(position)
                counts.append(float(count))
            for concept in concepts(text):
                self.concepts.setdefault(concept, set()).add(identifier)
        self._idf = None

    def score(self, owner, variants):
        positions = self.owners.get(owner, [])
        identifiers = [self.entries[position][0] for position in positions]
        best = np.zeros(len(positions), dtype=np.float32)
        if not positions:
            return identifiers, best
        local = {position: index for index, position in enumerate(positions)}
        if self._idf is None:
            self._idf = np.empty(len(self.tfidf.vocab), dtype=np.float64)
            for word, term in self.tfidf.vocab.items():
                self._idf[term] = 1.0 + math.log((self.tfidf.n_docs + 1)/(self.tfidf.df[word] + 1))
        norms = {}
        for variant in variants:
            query = self.tfidf.encode_sparse(variant)
            score = np.zeros(len(positions), dtype=np.float32)
            for term, query_weight in zip(query.indices, query.weights):
                posting = self.postings.get(int(term), {}).get(owner)
                if posting is None:
                    continue
                global_positions, raw_counts = posting
                for position in global_positions:
                    if position not in norms:
                        vector = self.entries[position][2]
                        weighted = (vector.weights.astype(np.float64)*self._idf[vector.indices]).astype(np.float32)
                        norms[position] = np.linalg.norm(weighted)
                weights = (np.asarray(raw_counts,dtype=np.float64)*self._idf[int(term)]).astype(np.float32)
                weights /= np.fromiter((norms[p] for p in global_positions),dtype=np.float32)
                destination = np.fromiter((local[p] for p in global_positions),dtype=np.intp)
                score[destination] += weights*query_weight
            best = np.maximum(best, score)
        return identifiers, np.clip(best, 0., 1.)
