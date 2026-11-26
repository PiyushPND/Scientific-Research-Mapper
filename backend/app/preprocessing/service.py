from app.database import get_connection
from app.config import MAX_PAPERS
from app.preprocessing.cleaner import preprocess_paper

DEFAULT_BATCH_SIZE = 500


def get_preprocessing_stats():
    connection = get_connection()
    try:
        total = connection.execute("SELECT COUNT(*)FROM papers").fetchone()[0]
        processed = connection.execute(
            "SELECT COUNT(*)FROM processed_papers"
        ).fetchone()[0]
        return {
            "total_papers": total,
            "processed_papers": processed,
            "pending_papers": total - processed,
            "maximum_capacity": MAX_PAPERS,
            "completion_percentage": (
                round(processed / total * 100, 2) if total else 0
            ),
        }
    finally:
        connection.close()


def process_batch(batch_size=DEFAULT_BATCH_SIZE):
    if not isinstance(batch_size, int) or isinstance(batch_size, bool):
        raise ValueError("Batch size must be an integer.")
    if batch_size < 1 or batch_size > 500:
        raise ValueError("Batch size must be between 1 and 500.")
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        papers = connection.execute(
            """SELECT p.paper_id,p.title,p.abstract FROM papers p
                                     LEFT JOIN processed_papers pp
                                         ON p.paper_id=pp.paper_id
                                     WHERE pp.paper_id IS NULL
                                     ORDER BY p.paper_id
                                     LIMIT ?""",
            (batch_size,),
        ).fetchall()
        processed_count = 0
        for paper in papers:
            result = preprocess_paper(paper)
            connection.execute(
                """INSERT INTO processed_papers(paper_id,cleaned_title,cleaned_abstract,combined_text,source_hash,preprocessing_version)
                                  VALUES(:paper_id,:cleaned_title,:cleaned_abstract,:combined_text,:source_hash,:preprocessing_version)""",
                result,
            )
            processed_count += 1
        connection.commit()
        stats = get_preprocessing_stats()
        return {
            "status": "completed" if stats["pending_papers"] == 0 else "in_progress",
            "batch_processed": processed_count,
            **stats,
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
