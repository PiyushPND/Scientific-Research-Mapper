from app.config import MAX_PAPERS
from app.database import get_connection
from app.ingestion.parser import parse_file
from app.ingestion.validator import prepare_record


def ingest_dataset(filename, content):
    records = parse_file(filename, content)
    total_received = len(records)
    if total_received > MAX_PAPERS:
        raise ValueError(f"An upload cannot exceed {MAX_PAPERS} records.")
    required_fields = {"title", "abstract"}
    for field in required_fields:
        if not any(record.get(field) is not None for record in records):
            raise ValueError(f"Required column '{field}' is missing.")
    validated = []
    errors = []
    for index, record in enumerate(records, start=1):
        try:
            validated.append(prepare_record(record))
        except ValueError as error:
            errors.append(f"Record {index}:\t{error}")
    if errors:
        error_message = "Dataset validation failed:"
        error_message += " | ".join(errors[:20])
        if len(errors) > 20:
            error_message += f" | {len(errors) - 20} additional errors."
        raise ValueError(error_message)
    connection = get_connection()
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing_count = connection.execute("SELECT COUNT(*)FROM papers").fetchone()[0]
        existing = connection.execute(
            """SELECT paper_id,doi_norm,title_key FROM papers"""
        ).fetchall()
        existing_ids = {row["paper_id"] for row in existing}
        existing_dois = {
            row["doi_norm"] for row in existing if row["doi_norm"] is not None
        }
        existing_titles = {row["title_key"] for row in existing}
        seen_ids = set()
        seen_dois = set()
        seen_titles = set()
        new_records = []
        duplicates = 0
        for record in validated:
            paper_id = record["paper_id"]
            doi = record["doi_norm"]
            title_key = record["title_key"]
            duplicate = (
                paper_id in existing_ids
                or paper_id in seen_ids
                or title_key in existing_titles
                or title_key in seen_titles
                or (doi is not None and (doi in existing_dois or doi in seen_dois))
            )
            if duplicate:
                duplicates += 1
                continue
            new_records.append(record)
            seen_ids.add(paper_id)
            seen_titles.add(title_key)
            if doi:
                seen_dois.add(doi)
        if existing_count + len(new_records) > MAX_PAPERS:
            raise ValueError(
                f"Capacity exceeded. Existing:\t{existing_count},"
                f"new:\t{len(new_records)},maximum:\t{MAX_PAPERS}."
            )
        connection.executemany(
            """INSERT INTO papers(paper_id,title,abstract,authors,year,doi,doi_norm,title_key,source)
                                  VALUES(:paper_id,:title,:abstract,:authors,:year,:doi,:doi_norm,:title_key,:source)""",
            new_records,
        )
        total_in_database = existing_count + len(new_records)
        connection.commit()
        return {
            "status": "success",
            "total_received": total_received,
            "inserted": len(new_records),
            "duplicates": duplicates,
            "total_in_database": total_in_database,
            "message": "Dataset validated and stored successfully.",
        }
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
