import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer


def extract_lda_topics(
    documents: list[str],
    top_n: int = 10,
    n_topics: int = 10,
) -> tuple[list[list[dict[str, float | str]]], np.ndarray]:
    if top_n < 1 or n_topics < 1:
        raise ValueError("Keyword and topic counts must be positive.")
    if not documents:
        return [], np.empty((0, 0), dtype=np.float64)

    vectorizer = CountVectorizer(
        ngram_range=(1, 2),
        stop_words="english",
        max_features=30000,
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9]+\b",
    )
    try:
        document_term_matrix = vectorizer.fit_transform(documents)
    except ValueError as error:
        if "empty vocabulary" in str(error).lower():
            return [], np.empty((len(documents), 0), dtype=np.float64)
        raise

    topic_count = min(n_topics, len(documents), document_term_matrix.shape[1])
    model = LatentDirichletAllocation(
        n_components=topic_count,
        learning_method="batch",
        max_iter=10,
        random_state=42,
        n_jobs=1,
    )
    document_topic_distribution = model.fit_transform(document_term_matrix)
    feature_names = vectorizer.get_feature_names_out()

    topics = []
    for topic_weights in model.components_:
        total_weight = topic_weights.sum()
        normalized_weights = topic_weights / total_weight
        top_indices = np.argsort(normalized_weights)[::-1][:top_n]
        topics.append(
            [
                {
                    "keyword": str(feature_names[index]),
                    "score": float(normalized_weights[index]),
                }
                for index in top_indices
            ]
        )
    return topics, document_topic_distribution
