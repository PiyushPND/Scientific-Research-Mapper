import json
from collections import defaultdict
from app.database import get_connection
from app.topics.extractor import extract_lda_topics
from app.topics.labeller import generate_topic_label


def initialize_topic_tables():
    connection = get_connection()
    connection.executescript("""CREATE TABLE IF NOT EXISTS topics(topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                  run_id TEXT NOT NULL,
                                                                  cluster_id INTEGER NOT NULL,
                                                                  topic_label TEXT NOT NULL,
                                                                  keywords TEXT NOT NULL,
                                                                  paper_count INTEGER NOT NULL,
                                                                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                                                  UNIQUE(run_id,cluster_id),
                                                                  FOREIGN KEY(run_id)
                                                                      REFERENCES clustering_runs(run_id));
                                CREATE TABLE IF NOT EXISTS topic_representatives(topic_id INTEGER NOT NULL,
                                                                                 paper_id TEXT NOT NULL,
                                                                                 membership_probability REAL NOT NULL,
                                                                                 PRIMARY KEY(topic_id,paper_id),
                                                                                 FOREIGN KEY(topic_id)
                                                                                     REFERENCES topics(topic_id),
                                                                                 FOREIGN KEY(paper_id)
                                                                                     REFERENCES processed_papers(paper_id));""")
    connection.commit()
    connection.close()


def generate_topics(
    run_id: str | None = None, top_n: int = 10, representative_count: int = 5
):
    if top_n < 1 or representative_count < 1:
        raise ValueError("Keyword and representative counts must be positive.")
    connection = get_connection()
    try:
        if run_id is None:
            run = connection.execute("""SELECT run_id FROM clustering_runs 
                                      WHERE status='completed' 
                                      ORDER BY started_at 
                                      DESC LIMIT 1""").fetchone()
            if run is None:
                raise ValueError("No completed clustering run found.")
            run_id = run["run_id"]
        run = connection.execute(
            """SELECT run_id,status FROM clustering_runs WHERE run_id=?""", (run_id,)
        ).fetchone()
        if run is None or run["status"] != "completed":
            raise ValueError("The requested clustering run is not completed.")
        rows = connection.execute(
            """SELECT pc.cluster_id,pc.paper_id,pc.membership_probability,p.cleaned_title,p.cleaned_abstract
                                   FROM paper_clusters pc
                                   JOIN processed_papers p
                                       ON p.paper_id=pc.paper_id
                                   WHERE pc.run_id=?
                                   AND pc.cluster_id!=-1
                                   ORDER BY pc.cluster_id,pc.membership_probability DESC""",
            (run_id,),
        ).fetchall()
        grouped = defaultdict(list)
        for row in rows:
            grouped[row["cluster_id"]].append(row)
        if not grouped:
            raise ValueError("No non-noise clusters exist in this run.")
        connection.execute("BEGIN")
        connection.execute(
            """DELETE FROM topic_representatives
                              WHERE topic_id IN (
                                  SELECT topic_id FROM topics WHERE run_id=?
                              )""",
            (run_id,),
        )
        connection.execute("DELETE FROM topics WHERE run_id=?", (run_id,))
        created_topics = []
        for cluster_id, papers in grouped.items():
            documents = [
                f"{paper['cleaned_title']} {paper['cleaned_abstract']}"
                for paper in papers
            ]
            lda_topics, document_topic_distribution = extract_lda_topics(
                documents,
                top_n=top_n,
                n_topics=min(5, len(documents)),
            )
            if not lda_topics:
                continue
            dominant_topic = int(document_topic_distribution.mean(axis=0).argmax())
            keywords = lda_topics[dominant_topic]
            label = generate_topic_label(keywords)
            cursor = connection.execute(
                """INSERT INTO topics(run_id,cluster_id,topic_label,keywords,paper_count) VALUES(?,?,?,?,?)""",
                (run_id, cluster_id, label, json.dumps(keywords), len(papers)),
            )
            topic_id = cursor.lastrowid
            representatives = sorted(
                papers, key=lambda paper: paper["membership_probability"], reverse=True
            )[:representative_count]
            for paper in representatives:
                connection.execute(
                    """INSERT INTO topic_representatives(topic_id,paper_id,membership_probability) VALUES(?,?,?)""",
                    (topic_id, paper["paper_id"], paper["membership_probability"]),
                )
            created_topics.append(
                {
                    "topic_id": topic_id,
                    "cluster_id": cluster_id,
                    "label": label,
                    "paper_count": len(papers),
                    "keywords": keywords,
                    "representative_count": len(representatives),
                }
            )
        connection.commit()
        return {
            "run_id": run_id,
            "number_of_topics": len(created_topics),
            "topics": created_topics,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_topics(run_id: str | None = None):
    connection = get_connection()
    try:
        if run_id is None:
            run = connection.execute("""SELECT run_id FROM clustering_runs 
                                      WHERE status='completed' 
                                      ORDER BY started_at 
                                      DESC LIMIT 1""").fetchone()
            if run is None:
                return []
            run_id = run["run_id"]
        rows = connection.execute(
            """SELECT topic_id,cluster_id,topic_label,keywords,paper_count FROM topics 
                                   WHERE run_id=? ORDER BY cluster_id""",
            (run_id,),
        ).fetchall()
        return [
            {
                "topic_id": row["topic_id"],
                "cluster_id": row["cluster_id"],
                "label": row["topic_label"],
                "keywords": json.loads(row["keywords"]),
                "paper_count": row["paper_count"],
            }
            for row in rows
        ]
    finally:
        connection.close()


def get_topic_details(topic_id: int):
    connection = get_connection()
    try:
        topic = connection.execute(
            """SELECT * FROM topics WHERE topic_id=?""", (topic_id,)
        ).fetchone()
        if topic is None:
            return None
        representatives = connection.execute(
            """SELECT tr.paper_id,tr.membership_probability,p.cleaned_title,p.cleaned_abstract 
                                              FROM topic_representatives tr
                                              JOIN processed_papers p
                                                  ON p.paper_id=tr.paper_id
                                              WHERE tr.topic_id=?
                                              ORDER BY tr.membership_probability DESC""",
            (topic_id,),
        ).fetchall()
        return {
            "topic_id": topic["topic_id"],
            "run_id": topic["run_id"],
            "cluster_id": topic["cluster_id"],
            "label": topic["topic_label"],
            "keywords": json.loads(topic["keywords"]),
            "paper_count": topic["paper_count"],
            "representative_papers": [
                {
                    "paper_id": row["paper_id"],
                    "title": row["cleaned_title"],
                    "abstract": row["cleaned_abstract"],
                    "membership_probability": row["membership_probability"],
                }
                for row in representatives
            ],
        }
    finally:
        connection.close()
