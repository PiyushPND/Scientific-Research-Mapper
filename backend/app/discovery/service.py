from collections import defaultdict
from app.config import MAX_PAPERS
from app.database import get_connection
from app.discovery.search import rank_papers


def search_papers(
    query: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    topic_id: int | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    if limit < 1 or limit > MAX_PAPERS:
        raise ValueError(f"Limit must be between 1 and {MAX_PAPERS}.")
    if offset < 0:
        raise ValueError("Offset cannot be negative.")
    if year_from is not None and year_to is not None:
        if year_from > year_to:
            raise ValueError("year_from cannot exceed year_to.")
    connection = get_connection()
    try:
        parameters = []
        conditions = []
        if year_from is not None:
            conditions.append("p.year>=?")
            parameters.append(year_from)
        if year_to is not None:
            conditions.append("p.year<=?")
            parameters.append(year_to)
        if source and source.strip():
            conditions.append("LOWER(p.source)=LOWER(?)")
            parameters.append(source.strip())
        topic_run_id = None
        if topic_id is not None:
            topic = connection.execute(
                """SELECT topic_id,run_id,cluster_id FROM topics WHERE topic_id=?""",
                (topic_id,),
            ).fetchone()
            if topic is None:
                raise ValueError("Topic not found.")
            topic_run_id = topic["run_id"]
            conditions.append("""EXISTS(SELECT 1 FROM paper_clusters pc 
                                 WHERE pc.paper_id=p.paper_id AND pc.run_id=? AND pc.cluster_id=?)""")
            parameters.extend([topic_run_id, topic["cluster_id"]])
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = connection.execute(
            f"""SELECT p.paper_id,p.title,p.abstract,p.authors,p.year,p.doi,p.source,pp.cleaned_title,pp.cleaned_abstract
                                    FROM papers p JOIN processed_papers pp ON pp.paper_id=p.paper_id 
                                    {where_clause}""",
            parameters,
        ).fetchall()
        papers = [dict(row) for row in rows]
        if query.strip():
            results = rank_papers(query, papers)
        else:
            results = papers
        total = len(results)
        return {
            "query": query,
            "total": total,
            "limit": limit,
            "offset": offset,
            "results": results[offset : offset + limit],
        }
    finally:
        connection.close()


def get_topic_relationships(run_id: str | None = None):
    connection = get_connection()
    try:
        if run_id is None:
            run = connection.execute(
                """SELECT run_id FROM clustering_runs WHERE status='completed' ORDER BY started_at DESC LIMIT 1"""
            ).fetchone()
            if run is None:
                return []
            run_id = run["run_id"]
        rows = connection.execute(
            """SELECT t1.topic_id AS source_topic_id,t2.topic_id AS target_topic_id,t1.topic_label AS source_label,
                                          t2.topic_label AS target_label,COUNT(DISTINCT lower(trim(p1.authors)))AS shared_authors
                                    FROM topics t1 JOIN topics t2 ON t1.run_id=t2.run_id AND t1.topic_id<t2.topic_id
                                    JOIN paper_clusters pc1 ON pc1.run_id=t1.run_id AND pc1.cluster_id=t1.cluster_id
                                    JOIN paper_clusters pc2 ON pc2.run_id=t2.run_id AND pc2.cluster_id=t2.cluster_id
                                    JOIN papers p1 ON p1.paper_id=pc1.paper_id JOIN papers p2 ON p2.paper_id=pc2.paper_id
                                    WHERE t1.run_id=? AND trim(p1.authors)!='' AND lower(trim(p1.authors))=lower(trim(p2.authors))
                                    GROUP BY t1.topic_id, t2.topic_id HAVING shared_authors>0 ORDER BY shared_authors 
                                    DESC""",
            (run_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
