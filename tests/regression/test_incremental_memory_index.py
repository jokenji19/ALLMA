"""Incremental ingestion must keep exactly the current-corpus retrieval scores."""
import sqlite3
from unittest.mock import patch

import numpy as np
import pytest

from allma_model.core.vector_memory_engine import VectorMemoryEngine, _LightTfidf


def test_append_search_cycles_do_not_reencode_previous_memories(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    engine.add('u','Una stella sul mare.',metadata={'role':'user'})
    engine.search('u','mare')
    with patch.object(engine,'_rebuild_index',wraps=engine._rebuild_index) as rebuild:
        for i in range(8):
            text=f'Appunto {i} sul mare e le stelle.'
            engine.add('u',text,metadata={'role':'user'})
            assert engine.search('u','mare')
    assert rebuild.call_count==0


def test_growing_index_matches_fresh_dense_reference_at_every_step(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    texts=[]
    for text in ['Mare stelle mare.','Appunti sul libro e musica.',
                 'Mare mare mare stelle lontane.', 'Musica e stelle.',
                 'Galassia sconosciuta.', 'Stelle mare.', 'Libro libro stelle.']:
        texts.append(text)
        engine.add('u',text,metadata={'role':'user'})
        reference=_LightTfidf()
        for row in texts:reference.partial_fit(row)
        matrix=np.vstack([reference.encode(row) for row in texts])
        for query in ('mare stelle','libro musica','galassia','termineassente'):
            scores=matrix@reference.encode(query)
            expected=[(texts[i],float(np.clip(scores[i],0,1)))
                      for i in np.lexsort((-np.arange(1,len(texts)+1),-scores)) if scores[i]>0]
            actual=engine.search('u',query,top_k=20,use_expansion=False)
            assert [r['content'] for r in actual]==[r[0] for r in expected]
            assert [r['score'] for r in actual]==pytest.approx([r[1] for r in expected],abs=2e-7)


def test_external_content_update_with_unchanged_count_and_id_invalidates_index(tmp_path):
    engine=VectorMemoryEngine(str(tmp_path/'vectors.db'))
    identifier=engine.add('u','Ombrello in cucina.',metadata={'role':'user'})
    assert engine.search('u','ombrello')
    with sqlite3.connect(engine.db_path) as db:
        db.execute('UPDATE memories SET content=? WHERE id=?',('Forbici nel mobile.',identifier))
    assert not engine.search('u','ombrello')
    assert engine.search('u','tagliare carta')[0]['content']=='Forbici nel mobile.'
