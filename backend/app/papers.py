import json
from typing import Any

from fastapi import HTTPException

from app.database import get_connection
from app.ingestion.validator import prepare_record


def _clear_derived_data(connection):
    connection.execute("DELETE FROM topic_representatives")
    connection.execute("DELETE FROM topics")
    connection.execute("DELETE FROM paper_clusters")
    connection.execute("DELETE FROM clustering_runs")


def get_paper(paper_id: str) -> dict[str, Any] | None:
    connection = get_connection()
    try:
        paper = connection.execute(
            """SELECT paper_id,title,abstract,authors,year,doi,source
               FROM papers WHERE paper_id=?""",
            (paper_id,),
        ).fetchone()
        return dict(paper) if paper else None
    finally:
        connection.close()


def update_paper(paper_id: str, values: dict[str, Any]) -> dict[str, Any]:
    existing = get_paper(paper_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    record = {**existing, **values, "paper_id": paper_id}
    prepared = prepare_record(record)
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        _clear_derived_data(connection)
        connection.execute(
            """UPDATE papers SET title=?,abstract=?,authors=?,year=?,doi=?,doi_norm=?,
                               title_key=?,source=? WHERE paper_id=?""",
            (
                prepared["title"],
                prepared["abstract"],
                prepared["authors"],
                prepared["year"],
                prepared["doi"],
                prepared["doi_norm"],
                prepared["title_key"],
                prepared["source"],
                paper_id,
            ),
        )
        connection.execute("DELETE FROM processed_papers WHERE paper_id=?", (paper_id,))
        connection.commit()
        return get_paper(paper_id) or {}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def delete_papers(paper_ids: list[str]) -> int:
    if not paper_ids:
        raise HTTPException(
            status_code=400, detail="At least one paper ID is required."
        )
    paper_ids = list(dict.fromkeys(paper_ids))
    chunk_size = 900
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        chunks = [
            paper_ids[index : index + chunk_size]
            for index in range(0, len(paper_ids), chunk_size)
        ]
        existing = 0
        for chunk in chunks:
            placeholders = ",".join("?" for _ in chunk)
            existing += connection.execute(
                f"SELECT COUNT(*) FROM papers WHERE paper_id IN ({placeholders})", chunk
            ).fetchone()[0]
        if not existing:
            connection.commit()
            return 0
        _clear_derived_data(connection)
        deleted = 0
        for chunk in chunks:
            placeholders = ",".join("?" for _ in chunk)
            cursor = connection.execute(
                f"DELETE FROM papers WHERE paper_id IN ({placeholders})", chunk
            )
            deleted += cursor.rowcount
        connection.commit()
        return deleted
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
