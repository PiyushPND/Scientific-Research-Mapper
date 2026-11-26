import numpy as np
from sentence_transformers import SentenceTransformer
from app.config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    EMBEDDING_BATCH_SIZE,
    MAX_EMBEDDING_BATCH,
)

_model = None
CHUNK_SIZE = 224
CHUNK_OVERLAP = 32


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
        dimension = _model.get_sentence_embedding_dimension()
        if dimension != EMBEDDING_DIMENSION:
            raise RuntimeError("Embedding dimension mismatch.")
    return _model


def split_into_chunks(text, tokenizer):
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    if not token_ids:
        return [], []
    chunks = []
    weights = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    for start in range(0, len(token_ids), step):
        chunk_ids = token_ids[start : start + CHUNK_SIZE]
        if not chunk_ids:
            break
        chunk_text = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        chunks.append(chunk_text)
        weights.append(len(chunk_ids))
        if start + CHUNK_SIZE >= len(token_ids):
            break
    return chunks, weights


def generate_embeddings(texts):
    if not texts:
        return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
    model = get_model()
    tokenizer = model.tokenizer
    all_chunks = []
    paper_weights = []
    for text in texts:
        chunks, weights = split_into_chunks(text, tokenizer)
        if not chunks:
            raise ValueError("Cannot embed an empty document.")
        start = len(all_chunks)
        all_chunks.extend(chunks)
        paper_weights.append((start, len(all_chunks), weights))
    batch_size = (
        MAX_EMBEDDING_BATCH if model.device.type == "cuda" else EMBEDDING_BATCH_SIZE
    )
    chunk_embeddings = model.encode(
        all_chunks,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    results = []
    for start, end, weights in paper_weights:
        vectors = chunk_embeddings[start:end]
        weights_array = np.asarray(weights, dtype=np.float32)
        weighted_vector = np.average(vectors, axis=0, weights=weights_array)
        norm = np.linalg.norm(weighted_vector)
        if norm == 0 or not np.isfinite(norm):
            raise ValueError("Invalid aggregated embedding.")
        weighted_vector = weighted_vector / norm
        results.append(weighted_vector)
    embeddings = np.asarray(results, dtype=np.float32)
    if embeddings.shape != (len(texts), EMBEDDING_DIMENSION):
        raise RuntimeError("Unexpected embedding dimensions.")
    if not np.isfinite(embeddings).all():
        raise RuntimeError("Embeddings contain invalid numerical values.")
    return embeddings
