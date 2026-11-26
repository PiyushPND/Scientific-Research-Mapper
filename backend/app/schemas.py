from pydantic import BaseModel
from typing import Any


class IngestionResponse(BaseModel):
    status: str
    total_received: int
    inserted: int
    duplicates: int
    total_in_database: int
    message: str


class DatasetStats(BaseModel):
    total_papers: int
    maximum_capacity: int
    remaining_capacity: int


class PaperUpdate(BaseModel):
    title: str | None = None
    abstract: str | None = None
    authors: str | list[str] | None = None
    year: int | None = None
    doi: str | None = None
    source: str | None = None


class BulkPaperDelete(BaseModel):
    paper_ids: list[str]
