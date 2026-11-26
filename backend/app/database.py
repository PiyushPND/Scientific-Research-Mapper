import sqlite3
from app.config import DATABASE_PATH


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def initialize_database():
    connection = get_connection()
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS papers(paper_id TEXT PRIMARY KEY,
                                                                title TEXT NOT NULL,
                                                                abstract TEXT NOT NULL,
                                                                authors TEXT,
                                                                year INTEGER,
                                                                doi TEXT,
                                                                doi_norm TEXT,
                                                                title_key TEXT NOT NULL UNIQUE,
                                                                source TEXT,
                                                                created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        connection.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_doi_unique ON papers(doi_norm) WHERE doi_norm IS NOT NULL"""
        )
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)"""
        )
        connection.execute("""CREATE TABLE IF NOT EXISTS processed_papers(paper_id TEXT PRIMARY KEY,
                                                                          cleaned_title TEXT NOT NULL,
                                                                          cleaned_abstract TEXT NOT NULL,
                                                                          combined_text TEXT NOT NULL,
                                                                          source_hash TEXT NOT NULL,
                                                                          preprocessing_version TEXT NOT NULL,
                                                                          processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                                                          FOREIGN KEY(paper_id)
                                                                              REFERENCES papers(paper_id)
                                                                              ON DELETE CASCADE)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS embeddings(paper_id TEXT PRIMARY KEY,
                                                                    embedding BLOB NOT NULL,
                                                                    dimension INTEGER NOT NULL,
                                                                    model_name TEXT NOT NULL,
                                                                    embedding_version TEXT NOT NULL,
                                                                    source_hash TEXT NOT NULL,
                                                                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                                                    FOREIGN KEY(paper_id)
                                                                        REFERENCES processed_papers(paper_id)
                                                                        ON DELETE CASCADE)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS clustering_runs(run_id TEXT PRIMARY KEY,
                                                                         status TEXT NOT NULL,
                                                                         model_name TEXT NOT NULL,
                                                                         embedding_version TEXT NOT NULL,
                                                                         total_papers INTEGER NOT NULL,
                                                                         clustered_papers INTEGER DEFAULT 0,
                                                                         noise_papers INTEGER DEFAULT 0,
                                                                         number_of_clusters INTEGER DEFAULT 0,
                                                                          parameters TEXT NOT NULL,
                                                                         started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                                                                         completed_at TEXT,
                                                                         error_message TEXT)""")

        connection.execute("""CREATE TABLE IF NOT EXISTS paper_clusters(run_id TEXT NOT NULL,
                                                                        paper_id TEXT NOT NULL,
                                                                        cluster_id INTEGER NOT NULL,
                                                                        membership_probability REAL NOT NULL,
                                                                        x REAL NOT NULL,
                                                                        y REAL NOT NULL,
                                                                        PRIMARY KEY(run_id, paper_id),
                                                                        FOREIGN KEY(run_id)
                                                                            REFERENCES clustering_runs(run_id)
                                                                            ON DELETE CASCADE,
                                                                        FOREIGN KEY(paper_id)
                                                                            REFERENCES processed_papers(paper_id)
                                                                            ON DELETE CASCADE)""")
        connection.execute(
            """CREATE INDEX IF NOT EXISTS idx_paper_clusters_cluster ON paper_clusters(run_id, cluster_id)"""
        )
        connection.commit()
    finally:
        connection.close()
