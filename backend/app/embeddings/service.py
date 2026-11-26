import numpy as np
from app.config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    EMBEDDING_VERSION,
    MAX_EMBEDDING_BATCH,
)
from app.database import get_connection
from app.embeddings.model import generate_embeddings


def get_embedding_stats():
    connection = get_connection()
    try:
        total = connection.execute("SELECT COUNT(*)FROM processed_papers").fetchone()[0]
        completed = connection.execute(
            """SELECT COUNT(*)FROM processed_papers p
                                        INNER JOIN embeddings e
                                            ON p.paper_id=e.paper_id
                                        WHERE e.model_name=?
                                        AND e.embedding_version=?
                                        AND e.source_hash=p.source_hash""",
            (EMBEDDING_MODEL, EMBEDDING_VERSION),
        ).fetchone()[0]
        return {
            "total_processed_papers": total,
            "embedded_papers": completed,
            "pending_papers": total - completed,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "model": EMBEDDING_MODEL,
            "completion_percentage": (
                round(completed / total * 100, 2) if total else 0
            ),
        }
    finally:
        connection.close()


def process_embedding_batch(batch_size=128):
    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or batch_size < 1
        or batch_size > MAX_EMBEDDING_BATCH
    ):
        raise ValueError(f"Batch size must be between 1 and {MAX_EMBEDDING_BATCH}.")
    connection = get_connection()
    try:
        rows = connection.execute(
            """SELECT p.paper_id,p.combined_text,p.source_hash FROM processed_papers p
                                   LEFT JOIN embeddings e
                                       ON p.paper_id=e.paper_id
                                       AND e.model_name=?
                                       AND e.embedding_version=?
                                       AND e.source_hash=p.source_hash
                                   WHERE e.paper_id IS NULL
                                   ORDER BY p.paper_id
                                   LIMIT ?""",
            (EMBEDDING_MODEL, EMBEDDING_VERSION, batch_size),
        ).fetchall()
        if not rows:
            return {"status": "completed", "batch_embedded": 0, **get_embedding_stats()}
        texts = [row["combined_text"] for row in rows]
        vectors = generate_embeddings(texts)
        connection.execute("BEGIN IMMEDIATE")
        embedded_count = 0
        for row, vector in zip(rows, vectors):
            vector = np.asarray(vector, dtype="<f4")
            if vector.shape != (EMBEDDING_DIMENSION,):
                raise ValueError("Invalid embedding vector dimensions.")
            if not np.isfinite(vector).all():
                raise ValueError("Embedding contains non-finite values.")
            vector_blob = vector.tobytes()
            connection.execute(
                """INSERT INTO embeddings(paper_id,embedding,dimension,model_name,embedding_version,source_hash) VALUES(?,?,?,?,?,?)
                                  ON CONFLICT(paper_id)DO UPDATE SET
                                    embedding=excluded.embedding,
                                    dimension=excluded.dimension,
                                    model_name=excluded.model_name,
                                    embedding_version=excluded.embedding_version,
                                    source_hash=excluded.source_hash,
                                    created_at=CURRENT_TIMESTAMP""",
                (
                    row["paper_id"],
                    vector_blob,
                    EMBEDDING_DIMENSION,
                    EMBEDDING_MODEL,
                    EMBEDDING_VERSION,
                    row["source_hash"],
                ),
            )
            embedded_count += 1
        connection.commit()
        stats = get_embedding_stats()
        return {
            "status": ("completed" if stats["pending_papers"] == 0 else "in_progress"),
            "batch_embedded": embedded_count,
            **stats,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
