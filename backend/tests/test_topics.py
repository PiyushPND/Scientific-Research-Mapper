import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from app.topics import service
from app.topics.extractor import extract_lda_topics


class LdaTopicExtractionTests(unittest.TestCase):
    def test_extracts_topics_and_document_distributions(self):
        documents = [
            "quantum particle photon electron energy quantum field",
            "particle physics photon electron quantum energy field",
            "quantum field particle photon physics electron",
            "neural network machine learning training model data",
            "machine learning neural model data network training",
            "training data neural network machine learning model",
        ]

        topics, distributions = extract_lda_topics(documents, top_n=5, n_topics=2)

        self.assertEqual(len(topics), 2)
        self.assertEqual(distributions.shape, (len(documents), 2))
        np.testing.assert_allclose(distributions.sum(axis=1), 1.0)
        self.assertTrue(all(topic for topic in topics))
        self.assertTrue(
            all(0 <= keyword["score"] <= 1 for topic in topics for keyword in topic)
        )

    def test_returns_no_topics_when_documents_have_no_usable_terms(self):
        topics, distributions = extract_lda_topics(["the and or", "to of in"])

        self.assertEqual(topics, [])
        self.assertEqual(distributions.shape, (2, 0))


class TopicServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "topics.sqlite"

        def connect():
            connection = sqlite3.connect(self.database_path)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            return connection

        self.connection_factory = connect
        self.connection = connect()
        self.connection.executescript(
            """
            CREATE TABLE clustering_runs (
                run_id TEXT PRIMARY KEY,
                status TEXT NOT NULL
            );
            CREATE TABLE processed_papers (
                paper_id TEXT PRIMARY KEY,
                cleaned_title TEXT NOT NULL,
                cleaned_abstract TEXT NOT NULL
            );
            CREATE TABLE paper_clusters (
                run_id TEXT NOT NULL,
                paper_id TEXT NOT NULL,
                cluster_id INTEGER NOT NULL,
                membership_probability REAL NOT NULL
            );
            CREATE TABLE topics (
                topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                cluster_id INTEGER NOT NULL,
                topic_label TEXT NOT NULL,
                keywords TEXT NOT NULL,
                paper_count INTEGER NOT NULL,
                UNIQUE(run_id, cluster_id)
            );
            CREATE TABLE topic_representatives (
                topic_id INTEGER NOT NULL,
                paper_id TEXT NOT NULL,
                membership_probability REAL NOT NULL
            );
            INSERT INTO clustering_runs VALUES ('test-run', 'completed');
            """
        )
        papers = [
            (
                f"physics-{index}",
                "quantum photon particle",
                "electron field quantum physics",
            )
            for index in range(6)
        ] + [
            (
                f"computing-{index}",
                "neural network machine",
                "learning model training data",
            )
            for index in range(6)
        ]
        self.connection.executemany(
            "INSERT INTO processed_papers VALUES (?, ?, ?)", papers
        )
        self.connection.executemany(
            "INSERT INTO paper_clusters VALUES ('test-run', ?, ?, ?)",
            [
                (paper_id, 0 if paper_id.startswith("physics") else 1, 0.9)
                for paper_id, _, _ in papers
            ],
        )
        self.connection.commit()
        self.connection.close()
        self.connection_patch = patch.object(
            service, "get_connection", side_effect=self.connection_factory
        )
        self.connection_patch.start()

    def tearDown(self):
        self.connection_patch.stop()
        self.temp_dir.cleanup()

    def test_generates_and_persists_lda_based_cluster_topics(self):
        result = service.generate_topics(run_id="test-run", top_n=5)

        self.assertEqual(result["number_of_topics"], 2)
        topics = service.get_topics("test-run")
        self.assertEqual(len(topics), 2)
        self.assertTrue(all(topic["keywords"] for topic in topics))
        self.assertEqual(sum(topic["paper_count"] for topic in topics), 12)
        self.assertTrue(
            all(topic["label"] != "Unclassified Research" for topic in topics)
        )


if __name__ == "__main__":
    unittest.main()
