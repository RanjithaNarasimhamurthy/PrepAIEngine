"""
FAISS-based vector index for semantic interview retrieval.

Embeddings are produced by sentence-transformers (all-MiniLM-L6-v2, 384-dim).
The index is persisted to disk so it survives restarts.

Metadata file maps FAISS integer IDs → PostgreSQL interview IDs.
"""
import json
import logging
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH    = os.getenv("FAISS_INDEX_PATH",    "./data/faiss_index.bin")
FAISS_METADATA_PATH = os.getenv("FAISS_METADATA_PATH", "./data/faiss_metadata.json")
EMBEDDING_MODEL     = "all-MiniLM-L6-v2"
EMBEDDING_DIM       = 384

# Lazy-loaded singletons
_model  = None
_index  = None
_id_map: List[int] = []   # FAISS position → PostgreSQL interview id


# ─── Model ────────────────────────────────────────────────────────────────────

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


# ─── FAISS helpers ────────────────────────────────────────────────────────────

def _get_index():
    global _index
    if _index is None:
        import faiss
        _index = faiss.IndexFlatIP(EMBEDDING_DIM)   # cosine-friendly with L2-normed vecs
    return _index


def _load_from_disk() -> bool:
    global _index, _id_map
    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(FAISS_METADATA_PATH):
        return False
    try:
        import faiss
        _index = faiss.read_index(FAISS_INDEX_PATH)
        with open(FAISS_METADATA_PATH, "r") as fh:
            _id_map = json.load(fh)
        logger.info("FAISS index loaded: %d vectors", _index.ntotal)
        return True
    except Exception as exc:
        logger.error("Failed to load FAISS index: %s", exc)
        return False


def _save_to_disk() -> None:
    import faiss
    os.makedirs(os.path.dirname(FAISS_INDEX_PATH) or ".", exist_ok=True)
    faiss.write_index(_get_index(), FAISS_INDEX_PATH)
    with open(FAISS_METADATA_PATH, "w") as fh:
        json.dump(_id_map, fh)
    logger.info("FAISS index saved: %d vectors", _get_index().ntotal)


# ─── Embedding ────────────────────────────────────────────────────────────────

def embed_texts(texts: List[str]) -> np.ndarray:
    """Return L2-normalised float32 embeddings, shape (N, EMBEDDING_DIM)."""
    model = _get_model()
    vecs  = model.encode(texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
    vecs  = vecs.astype(np.float32)
    # L2-normalise so IndexFlatIP == cosine similarity
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return vecs / norms


# ─── Public API ───────────────────────────────────────────────────────────────

def init_index(force_rebuild: bool = False) -> None:
    """
    Load an existing FAISS index from disk, or start fresh.
    Call build_index() to actually populate it.
    """
    if force_rebuild:
        global _index, _id_map
        import faiss
        _index  = faiss.IndexFlatIP(EMBEDDING_DIM)
        _id_map = []
        logger.info("FAISS index reset (force_rebuild=True)")
        return
    if not _load_from_disk():
        _get_index()   # initialise an empty in-memory index
        logger.info("Started with empty FAISS index")


def build_index(records: List[Dict]) -> None:
    """
    (Re)build the FAISS index from a list of dicts:
      {"id": <postgres_int>, "combined_text": <str>}
    Persists to disk when done.
    """
    global _id_map
    if not records:
        logger.warning("build_index called with empty records list")
        return

    import faiss

    logger.info("Building FAISS index for %d records …", len(records))

    texts   = [r["combined_text"] for r in records]
    pg_ids  = [r["id"] for r in records]
    vecs    = embed_texts(texts)

    new_index = faiss.IndexFlatIP(EMBEDDING_DIM)
    new_index.add(vecs)

    global _index
    _index  = new_index
    _id_map = pg_ids

    _save_to_disk()
    logger.info("FAISS index built: %d vectors", _index.ntotal)


def add_to_index(pg_id: int, text: str) -> None:
    """Add a single document to the live index and persist."""
    global _id_map
    init_index()
    vec     = embed_texts([text])
    _get_index().add(vec)
    _id_map.append(pg_id)
    _save_to_disk()


def search(query: str, top_k: int = 5) -> List[Tuple[int, float]]:
    """
    Semantic search for *query*.
    Returns a list of (postgres_interview_id, similarity_score) pairs,
    most similar first.
    """
    init_index()
    index = _get_index()

    if index.ntotal == 0:
        logger.warning("FAISS index is empty — no results returned")
        return []

    qvec          = embed_texts([query])
    k             = min(top_k, index.ntotal)
    scores, idxs  = index.search(qvec, k)

    results = []
    for score, faiss_pos in zip(scores[0], idxs[0]):
        if faiss_pos < 0 or faiss_pos >= len(_id_map):
            continue
        results.append((_id_map[faiss_pos], float(score)))

    return results


def index_size() -> int:
    init_index()
    return _get_index().ntotal
