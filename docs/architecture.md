# Architecture

Scientific Research Mapper is a React and TypeScript frontend backed by a FastAPI service, a scientific text-processing pipeline, and SQLite persistence.

## System overview

```text
CSV upload
   |
   v
FastAPI -> ingestion and validation -> SQLite source papers
                                           |
                                           v
                                preprocessing and cleaning
                                           |
                                           v
                              sentence-transformer embeddings
                                           |
                                           v
                              UMAP reduction and HDBSCAN
                                           |
                                           v
                     cluster-specific scikit-learn LDA models
                                           |
                                           v
                          map, topics, and discovery APIs
                                           |
                                           v
                              React interactive dashboard
```

The frontend calls the API at `http://localhost:8000`; the development frontend runs at `http://localhost:5173`.

## Backend components

- **Ingestion** (`backend/app/ingestion/`): accepts CSV only, checks the required `title` and `abstract` headers, normalizes supported column names, validates each paper, detects duplicates, and stores accepted records. Optional columns include paper ID, authors, year, DOI, and source.
- **Preprocessing** (`backend/app/preprocessing/`): removes markup, URLs, and unwanted control characters, normalizes Unicode and whitespace, and creates a combined title/abstract text with a source hash.
- **Embeddings** (`backend/app/embeddings/`): creates normalized vectors with `sentence-transformers/all-MiniLM-L6-v2`. Long texts are split into overlapping chunks, embedded, and aggregated per paper.
- **Clustering** (`backend/app/clustering/`): reduces embeddings with UMAP, groups papers with HDBSCAN, and creates two-dimensional map coordinates.
- **Topics** (`backend/app/topics/`): vectorizes the cleaned titles and abstracts within each non-noise cluster, fits scikit-learn LDA with up to five components, and chooses the cluster's dominant topic from the mean document-topic distribution. The topic's highest-weight terms form its keywords and display label. Representative papers are selected by clustering membership probability.
- **Discovery** (`backend/app/discovery/`): searches and filters papers and returns topic relationships.
- **Paper management** (`backend/app/papers.py`): retrieves, edits, and deletes papers. Changes clear or invalidate derived map data so it can be rebuilt.
- **API application** (`backend/app/main.py`): initializes the database and topic tables at startup and exposes processing, map, topic, search, and paper-management routes.

No generative LLM or external LLM API is used. Sentence-transformer embeddings support semantic clustering; LDA performs topic modelling.

## Processing flow

1. A CSV file must contain `title` and `abstract` columns, with non-empty values for every paper. Header matching ignores case and surrounding whitespace. JSON, JSONL, ZIP, PDF, and DOCX uploads are not supported.
2. Ingestion validates records and avoids duplicates using paper IDs, normalized title/year keys, and normalized DOIs.
3. Preprocessing cleans titles and abstracts and stores source hashes so changed papers can be identified.
4. Embedding generation stores model name, dimension, version, and source hash with each vector. Clustering rejects stale or invalid embeddings.
5. UMAP and HDBSCAN assign clusters and map coordinates. Noise points use cluster ID `-1` and do not receive topic labels.
6. For each non-noise cluster, LDA fits up to five topics over that cluster's bag-of-words matrix. A cluster-level mean of the document-topic distributions determines which topic supplies the displayed keywords.
7. Topic labels and representative papers are persisted and returned with map data.

Processing operations are API routes. The frontend runs preprocessing and embeddings in batches after upload, then runs clustering and topic generation for the resulting clustering run. A rebuild refreshes the derived pipeline after paper changes.

## Data model

SQLite stores source records and derived results:

- `papers`: paper identifier, original title and abstract, authors, year, DOI, source, and normalized keys for duplicate prevention.
- `processed_papers`: cleaned title and abstract, combined text, source hash, and preprocessing version.
- `embeddings`: vector data, dimension, model name, embedding version, and source hash.
- `clustering_runs`: run status, model/version information, parameters, counts, timestamps, and error details.
- `paper_clusters`: cluster assignment, membership probability, and two-dimensional map coordinates for each paper in a run.
- `topics`: one displayed topic descriptor per cluster, including its label, keyword scores, and paper count.
- `topic_representatives`: representative paper IDs and their clustering membership probabilities.

Foreign keys link derived records to their source papers and clustering runs. Paper deletion cascades to derived paper records. Indexes and uniqueness constraints support duplicate prevention and map lookups.

## Frontend behavior

The dashboard provides CSV upload, storage statistics, an interactive paper map, topic labels, and a searchable paper-management list. The map canvas, zoom controls, and topic section remain rendered regardless of map data; paper points appear when a completed clustering run is available. Map interactions include panning, zooming, topic filtering, and paper inspection.

The paper list supports text and year filtering, row selection, edit and delete actions for selected rows, and bulk deletion. The list scrolls inside the manage panel. A theme toggle switches between light and dark themes and saves the preference in browser storage.

## Capacity and runtime configuration

The database supports up to 40,000 unique papers by default. Uploads are limited to 100 MB by default. `MAX_PAPERS`, `MAX_UPLOAD_MB`, and `DATABASE_PATH` can be set in the backend environment. The embedding model and vector dimension are configured in `backend/app/config.py`.
