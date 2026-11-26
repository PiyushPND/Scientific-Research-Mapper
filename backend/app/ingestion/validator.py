import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime


def is_missing(val):
    if val is None:
        return True
    if isinstance(val, float):
        return math.isnan(val)
    return False


def normalize_text(val):
    val = unicodedata.normalize("NFKC", str(val))
    val = val.lower()
    val = re.sub(r"[^\w\s]", " ", val)
    val = re.sub(r"\s+", " ", val)
    return val.strip()


def normalize_doi(val):
    if is_missing(val):
        return None
    doi = str(val).strip().lower()
    if not doi:
        return None
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    if not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
        raise ValueError("Invalid DOI format.")
    return doi


def prepare_record(row):
    raw_title = row.get("title")
    raw_abstract = row.get("abstract")
    title = "" if is_missing(raw_title) else str(raw_title).strip()
    abstract = "" if is_missing(raw_abstract) else str(raw_abstract).strip()
    if not title:
        raise ValueError("Missing paper title.")
    if not abstract:
        raise ValueError("Missing paper abstract.")
    if len(title) > 2000:
        raise ValueError("Title exceeds 2000 characters.")
    if len(abstract) > 100000:
        raise ValueError("Abstract exceeds 100000 characters.")
    year_val = row.get("year")
    year = None
    if not is_missing(year_val) and str(year_val).strip():
        try:
            numeric_year = float(str(year_val).strip())
            if not math.isfinite(numeric_year):
                raise ValueError
            if not numeric_year.is_integer():
                raise ValueError
            year = int(numeric_year)
        except (ValueError, TypeError):
            raise ValueError("Invalid publication year.")
        if year < 1500 or year > datetime.now().year + 1:
            raise ValueError("Publication year is out of range.")
    doi = normalize_doi(row.get("doi"))
    authors_val = row.get("authors")
    if is_missing(authors_val):
        authors = None
    elif isinstance(authors_val, (list, dict)):
        authors = json.dumps(authors_val, ensure_ascii=False)
    else:
        authors = str(authors_val).strip() or None
    source_val = row.get("source")
    source = None if is_missing(source_val) else str(source_val).strip() or None
    normalized_title = normalize_text(title)
    if not normalized_title:
        raise ValueError("Title contains no usable characters.")
    title_key = hashlib.sha256(
        f"{normalized_title}|{year or ''}".encode("utf-8")
    ).hexdigest()
    identity = doi if doi else title_key
    paper_id_val = row.get("paper_id")
    paper_id = "" if is_missing(paper_id_val) else str(paper_id_val).strip()
    if not paper_id:
        paper_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    if len(paper_id) > 256:
        raise ValueError("Paper ID exceeds 256 characters.")
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "year": year,
        "doi": doi,
        "doi_norm": doi,
        "title_key": title_key,
        "source": source,
    }
