import json
import uuid
import numpy as np
from app.database import get_connection
from app.config import EMBEDDING_MODEL, EMBEDDING_VERSION, EMBEDDING_DIMENSION
from app.clustering.reducer import reduce_dimensions, generate_visualization_coordinates
from app.clustering.clusterer import perform_clustering

DEFAULT_MIN_CLUSTER_SIZE = 15
DEFAULT_MIN_SAMPLES = 5


def get_clustering_stats(run_id=None):
    connection = get_connection()
    try:
        if run_id is None:
            run = connection.execute(
                """SELECT * FROM clustering_runs ORDER BY started_at DESC LIMIT 1"""
            ).fetchone()
        else:
            run = connection.execute(
                """SELECT * FROM clustering_runs WHERE run_id=?""", (run_id,)
            ).fetchone()
        if run is None:
            return None
        result = dict(run)
        result["parameters"] = json.loads(result["parameters"])
        if result["status"] == "completed":
            clusters = connection.execute(
                """SELECT cluster_id,COUNT(*) AS paper_count,ROUND(AVG(membership_probability),4) AS average_probability FROM paper_clusters
                                           WHERE run_id=? GROUP BY cluster_id ORDER BY cluster_id""",
                (run["run_id"],),
            ).fetchall()
            result["clusters"] = [dict(cluster) for cluster in clusters]
        return result
    finally:
        connection.close()


def get_research_map(run_id=None):
    connection = get_connection()
    try:
        if run_id is None:
            run = connection.execute("""SELECT run_id FROM clustering_runs
                                      WHERE status='completed'
                                      ORDER BY started_at DESC LIMIT 1""").fetchone()
            if run is None:
                return {"run_id": None, "map_stale": False, "nodes": []}
            run_id = run["run_id"]
        rows = connection.execute(
            """SELECT pc.paper_id,pc.cluster_id,pc.membership_probability,pc.x,pc.y,
                                          p.title,p.abstract,p.authors,p.year,
                                          t.topic_id,t.topic_label
                                   FROM paper_clusters pc
                                   JOIN papers p ON p.paper_id=pc.paper_id
                                   LEFT JOIN topics t
                                       ON t.run_id=pc.run_id AND t.cluster_id=pc.cluster_id
                                   WHERE pc.run_id=?
                                   ORDER BY pc.cluster_id,pc.paper_id""",
            (run_id,),
        ).fetchall()
        nodes = [
            {
                "paper_id": row["paper_id"],
                "cluster_id": row["cluster_id"],
                "membership_probability": row["membership_probability"],
                "x": row["x"],
                "y": row["y"],
                "title": row["title"],
                "abstract": row["abstract"],
                "authors": row["authors"],
                "year": row["year"],
                "topic_id": row["topic_id"],
                "topic_label": row["topic_label"],
            }
            for row in rows
        ]
        total_papers = connection.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        return {
            "run_id": run_id,
            "map_stale": len(nodes) != total_papers,
            "nodes": nodes,
        }
    finally:
        connection.close()


def run_clustering(
    min_cluster_size=DEFAULT_MIN_CLUSTER_SIZE, min_samples=DEFAULT_MIN_SAMPLES
):
    if not isinstance(min_cluster_size, int) or isinstance(min_cluster_size, bool):
        raise ValueError("min_cluster_size must be an integer.")
    if not isinstance(min_samples, int) or isinstance(min_samples, bool):
        raise ValueError("min_samples must be an integer.")
    if min_cluster_size < 2:
        raise ValueError("min_cluster_size must be at least 2.")
    if min_samples < 1:
        raise ValueError("min_samples must be positive.")
    run_id = str(uuid.uuid4())
    parameters = {
        "reduction": "UMAP",
        "clustering": "HDBSCAN",
        "reduced_dimensions": 10,
        "visualization_dimensions": 2,
        "n_neighbors": 15,
        "min_dist": 0,
        "metric": "cosine",
        "min_cluster_size": min_cluster_size,
        "min_samples": min_samples,
        "cluster_selection_method": "eom",
        "random_state": 42,
    }
    connection = get_connection()
    try:
        total_papers = connection.execute(
            """SELECT COUNT(*)FROM processed_papers"""
        ).fetchone()[0]
        valid_count = connection.execute(
            """SELECT COUNT(*)FROM processed_papers p
                                          INNER JOIN embeddings e
                                              ON p.paper_id=e.paper_id
                                          WHERE e.model_name=?
                                          AND e.embedding_version=?
                                          AND e.source_hash=p.source_hash
                                          AND e.dimension=?""",
            (EMBEDDING_MODEL, EMBEDDING_VERSION, EMBEDDING_DIMENSION),
        ).fetchone()[0]
        if total_papers == 0:
            raise ValueError("No preprocessed papers are available.")
        if valid_count != total_papers:
            raise ValueError(
                f"Embedding integrity failure:"
                f"{valid_count} valid embeddings for "
                f"{total_papers} processed papers."
            )
        if total_papers < min_cluster_size:
            raise ValueError(
                f"Not enough papers for the selected minimum cluster size."
            )
        connection.execute(
            """INSERT INTO clustering_runs(run_id,status,model_name,embedding_version,total_papers,parameters)
                              VALUES(?,?,?,?,?,?)""",
            (
                run_id,
                "running",
                EMBEDDING_MODEL,
                EMBEDDING_VERSION,
                total_papers,
                json.dumps(parameters),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    try:
        connection = get_connection()
        try:
            rows = connection.execute(
                """SELECT p.paper_id,e.embedding FROM processed_papers p
                                       INNER JOIN embeddings e
                                           ON p.paper_id=e.paper_id
                                       WHERE e.model_name=?
                                       AND e.embedding_version=?
                                       AND e.source_hash=p.source_hash
                                       AND e.dimension=?
                                       ORDER BY p.paper_id""",
                (EMBEDDING_MODEL, EMBEDDING_VERSION, EMBEDDING_DIMENSION),
            ).fetchall()
        finally:
            connection.close()
        paper_ids = [row["paper_id"] for row in rows]
        embedding_list = []
        for row in rows:
            vector = np.frombuffer(row["embedding"], dtype="<f4")
            if vector.shape != (EMBEDDING_DIMENSION,):
                raise ValueError("Invalid stored embedding size.")
            if not np.isfinite(vector).all():
                raise ValueError("Invalid stored embedding values.")
            if not np.isclose(np.linalg.norm(vector), 1, atol=1e-3):
                raise ValueError("Stored embedding is not normalized.")
            embedding_list.append(vector)
        embeddings = np.stack(embedding_list).astype(np.float32, copy=False)
        reduced = reduce_dimensions(
            embeddings, n_components=10, n_neighbors=15, min_dist=0, random_state=42
        )
        labels, probabilities = perform_clustering(
            reduced, min_cluster_size=min_cluster_size, min_samples=min_samples
        )
        coordinates = generate_visualization_coordinates(reduced, random_state=42)
        if not (
            len(paper_ids) == len(labels) == len(probabilities) == len(coordinates)
        ):
            raise RuntimeError("Paper assignment count mismatch.")
        number_of_clusters = len(set(labels.tolist()) - {-1})
        noise_papers = int(np.sum(labels == -1))
        records = [
            (
                run_id,
                paper_id,
                int(label),
                float(probability),
                float(coordinate[0]),
                float(coordinate[1]),
            )
            for paper_id, label, probability, coordinate in zip(
                paper_ids, labels, probabilities, coordinates
            )
        ]
        connection = get_connection()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                """INSERT INTO paper_clusters(run_id,paper_id,cluster_id,membership_probability,x,y) VALUES (?,?,?,?,?,?)""",
                records,
            )
            connection.execute(
                """UPDATE clustering_runs
                                  SET
                                      status='completed',
                                      clustered_papers=?,
                                      noise_papers=?,
                                      number_of_clusters=?,
                                      completed_at=CURRENT_TIMESTAMP
                                  WHERE run_id=?""",
                (len(records), noise_papers, number_of_clusters, run_id),
            )
            connection.commit()
        finally:
            connection.close()
        return get_clustering_stats(run_id)
    except Exception as error:
        connection = get_connection()
        try:
            connection.execute(
                """UPDATE clustering_runs
                                  SET
                                      status='failed',
                                      error_message=?
                                  WHERE run_id=?""",
                (str(error)[:1000], run_id),
            )
            connection.commit()
        finally:
            connection.close()
        raise
