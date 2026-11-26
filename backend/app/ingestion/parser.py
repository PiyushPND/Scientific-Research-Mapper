import csv
import io
import json
import re
import zipfile
from pathlib import PurePosixPath

from docx import Document
from pypdf import PdfReader

ALIASES = {
    "paper_id": {"paper_id", "id", "document_id"},
    "title": {"title", "paper_title", "name"},
    "abstract": {"abstract", "summary", "description"},
    "authors": {"authors", "author", "researchers"},
    "year": {"year", "publication_year"},
    "doi": {"doi", "digital_object_identifier"},
    "source": {"source", "journal", "publisher"},
}


def normalize_column_name(name):
    return str(name).strip().lower().replace("-", "_").replace(" ", "_")


def normalize_records(records):
    if not records:
        raise ValueError("The uploaded dataset is empty.")
    normalized_records = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} must be a JSON object.")
        normalized = {}
        for column, val in record.items():
            key = normalize_column_name(column)
            target = None
            for field, aliases in ALIASES.items():
                if key in aliases:
                    target = field
                    break
            if target:
                if target in normalized:
                    raise ValueError(f"Multiple columns map to '{target}'.")
                normalized[target] = val
        normalized_records.append(normalized)
    return normalized_records


def parse_csv(content):
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV headers are missing.")
        headers = {normalize_column_name(name) for name in reader.fieldnames if name}
        missing = {"title", "abstract"} - headers
        if missing:
            raise ValueError("CSV must include 'title' and 'abstract' columns.")
        records = list(reader)
        return normalize_records(records)
    except UnicodeDecodeError:
        raise ValueError("CSV must use UTF-8 encoding.")


def parse_json(content):
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("Invalid JSON file.")
    if isinstance(data, dict):
        if "papers" in data:
            data = data["papers"]
        elif "data" in data:
            data = data["data"]
        else:
            data = [data]
    if not isinstance(data, list):
        raise ValueError("JSON must contain a list of research papers.")
    return normalize_records(data)


def parse_jsonl(content):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("JSONL must use UTF-8 encoding.")
    records = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON on line {line_number}.")
        records.append(record)
    return normalize_records(records)


def _extract_sections(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    cleaned = re.sub(r"\s+", " ", " ".join(lines)).strip()
    title = lines[0] if lines else ""
    abstract_match = re.search(
        r"\babstract\b\s*:?\s*(.*?)(?:\bintroduction\b|\bkeywords?\b|$)",
        cleaned,
        re.IGNORECASE,
    )
    abstract = abstract_match.group(1).strip(" -:\n\t") if abstract_match else cleaned
    return title[:2000], abstract[:100000]


def _parse_pdf(filename, content):
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    title, abstract = _extract_sections(text)
    return {
        "title": title or PurePosixPath(filename).stem,
        "abstract": abstract,
        "source": filename,
    }


def _parse_docx(filename, content):
    document = Document(io.BytesIO(content))
    text = "\n".join(
        paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()
    )
    title, abstract = _extract_sections(text)
    return {
        "title": title or PurePosixPath(filename).stem,
        "abstract": abstract,
        "source": filename,
    }


def parse_zip(content):
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise ValueError("The uploaded file is not a valid ZIP archive.")
    records = []
    with archive:
        members = [member for member in archive.infolist() if not member.is_dir()]
        if not members:
            raise ValueError("The ZIP archive contains no research papers.")
        for member in members:
            path = PurePosixPath(member.filename)
            extension = path.suffix.lower()
            if extension not in {".pdf", ".docx"}:
                raise ValueError(f"Unsupported file in ZIP archive: {member.filename}")
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe file path in ZIP archive: {member.filename}")
            data = archive.read(member)
            record = (
                _parse_pdf(member.filename, data)
                if extension == ".pdf"
                else _parse_docx(member.filename, data)
            )
            if not record["abstract"]:
                raise ValueError(f"No readable text found in: {member.filename}")
            records.append(record)
    return normalize_records(records)


def parse_file(filename, content):
    extension = "." + filename.rsplit(".", 1)[-1].lower()
    if extension == ".csv":
        return parse_csv(content)
    raise ValueError("Upload a CSV file with required 'title' and 'abstract' columns.")
