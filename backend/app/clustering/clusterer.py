import numpy as np
from sklearn.cluster import HDBSCAN


def perform_clustering(reduced_embeddings, min_cluster_size=15, min_samples=5):
    reduced_embeddings = np.asarray(reduced_embeddings, dtype=np.float32)
    if reduced_embeddings.ndim != 2:
        raise ValueError("Input must be a 2D matrix.")
    sample_count = len(reduced_embeddings)
    if sample_count < min_cluster_size:
        raise ValueError("Number of papers must be at least min_cluster_size.")
    if min_cluster_size < 2:
        raise ValueError("Minimum cluster size must be at least 2.")
    if min_samples < 1:
        raise ValueError("Minimum samples must be positive.")
    clusterer = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
        allow_single_cluster=False,
        n_jobs=-1,
    )
    labels = clusterer.fit_predict(reduced_embeddings)
    probabilities = clusterer.probabilities_
    labels = np.asarray(labels, dtype=np.int32)
    probabilities = np.asarray(probabilities, dtype=np.float32)
    if len(labels) != sample_count:
        raise RuntimeError("Cluster count mismatch.")
    if len(probabilities) != sample_count:
        raise RuntimeError("Probability count mismatch.")
    if not np.isfinite(probabilities).all():
        raise RuntimeError("Invalid cluster probabilities.")
    return labels, probabilities
