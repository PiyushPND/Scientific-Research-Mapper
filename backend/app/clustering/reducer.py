import numpy as np
import umap


def reduce_dimensions(
    embeddings, n_components=10, n_neighbors=15, min_dist=0, random_state=42
):
    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim != 2:
        raise ValueError("Embeddings must be a 2D matrix.")
    if not np.isfinite(embeddings).all():
        raise ValueError("Embeddings contain invalid values.")
    sample_count = len(embeddings)
    if sample_count < 3:
        raise ValueError("At least 3 papers are required for UMAP.")
    if not 2 <= n_components < sample_count:
        raise ValueError("Invalid UMAP output dimensions.")
    if not 2 <= n_neighbors < sample_count:
        raise ValueError("Invalid UMAP neighbor count.")
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric="cosine",
        random_state=random_state,
        n_jobs=1,
        low_memory=True,
    )
    reduced = reducer.fit_transform(embeddings)
    reduced = np.asarray(reduced, dtype=np.float32)
    if reduced.shape != (sample_count, n_components):
        raise RuntimeError("Unexpected UMAP output dimensions.")
    if not np.isfinite(reduced).all():
        raise RuntimeError("UMAP generated invalid coordinates.")
    return reduced


def generate_visualization_coordinates(reduced_embeddings, random_state=42):
    reduced_embeddings = np.asarray(reduced_embeddings, dtype=np.float32)
    if len(reduced_embeddings) < 3:
        raise ValueError("At least 3 papers are required.")
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=min(15, len(reduced_embeddings) - 1),
        min_dist=0.1,
        metric="euclidean",
        random_state=random_state,
        n_jobs=1,
        low_memory=True,
    )
    coordinates = reducer.fit_transform(reduced_embeddings)
    if not np.isfinite(coordinates).all():
        raise RuntimeError("Invalid visualization coordinates.")
    return coordinates.astype(np.float32)
