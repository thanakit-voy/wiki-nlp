from pymongo.collection import Collection
from pymongo import InsertOne
from typing import List, Optional, Any


def insert_embeddings(col: Collection, corpus_id: Any, section: str, embeddings: List[List[float]], indices: List[int]) -> List[Any]:
    """
    Insert embeddings into the embeddings collection and return their ObjectIds.
    section: 'sentences' or 'sentence_heads'
    indices: index in the section array
    """
    ops = []
    for vec, idx in zip(embeddings, indices):
        doc = {
            "corpus_id": corpus_id,
            "section": section,
            "index": idx,
            "embedding": vec
        }
        ops.append(InsertOne(doc))
    if not ops:
        return []
    res = col.bulk_write(ops, ordered=False)
    # Fetch inserted ids in order
    return [op.inserted_id for op in res.inserted_ops]
