# Scientific Research Mapper

Scientific Research Mapper organizes research papers into an interactive topic map. It accepts CSV paper records, preprocesses title and abstract text, groups papers by semantic similarity, and describes each group using Latent Dirichlet Allocation (LDA).

Topic discovery uses scikit-learn LDA. The application does not use a generative LLM or an external LLM API. A sentence-transformer encoder is used to create embeddings for clustering and map layout.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm

## Run locally

Start the backend:

```powershell
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

In another terminal, start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:5173`. The API runs at `http://localhost:8000`; interactive API documentation is available at `http://localhost:8000/docs`.

## Input format

Uploads must be CSV files. Every file must include `title` and `abstract` columns, and every record must have a non-empty title and abstract. Header matching ignores letter case and surrounding whitespace. JSON, JSONL, ZIP, PDF, and DOCX uploads are not accepted.

Optional columns are `paper_id`, `authors`, `year`, `doi`, and `source`. Common aliases for optional fields include `id`, `author`, `publication_year`, `journal`, and `publisher`. The upload limit is 100 MB by default, and the database supports up to 40,000 unique papers. Duplicate records are detected during ingestion.

## Use the application

1. Select a CSV file and choose **Upload and build map**.
2. The application validates and stores new papers, preprocesses pending records, creates sentence-transformer embeddings, clusters the papers, and generates LDA topics for the clusters.
3. Explore the map by panning, zooming, filtering by topic, and selecting points to inspect papers. The map canvas and controls remain visible even before map data is available; topic labels appear below the map.
4. Search and filter stored papers by text and year. Select rows to reveal their Edit and Delete actions, or select multiple papers for bulk deletion.
5. Switch between light and dark themes using the moon/sun control beside the capacity indicator. The selected theme is saved in the browser.

Editing or deleting papers invalidates derived map data. Use **Rebuild map** to preprocess changed papers, refresh embeddings and clusters, and regenerate topics.

## Topic modelling

For each non-noise semantic cluster, the application fits scikit-learn's `LatentDirichletAllocation` model to that cluster's preprocessed titles and abstracts. Text is represented as a bag-of-words document-term matrix with English stop words and unigram/bigram features. The model discovers up to five topics per cluster, subject to the number of documents and available vocabulary. The cluster's most prevalent LDA topic supplies its keywords and display label.

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check API health |
| `GET` | `/api/papers/stats` | Read storage and capacity statistics |
| `POST` | `/api/ingestion/upload` | Validate and ingest a CSV file |
| `POST` | `/api/preprocessing/run` | Preprocess pending papers |
| `GET` | `/api/preprocessing/stats` | Read preprocessing status |
| `POST` | `/api/embeddings/run` | Generate pending embeddings |
| `GET` | `/api/embeddings/stats` | Read embedding status |
| `POST` | `/api/clustering/run` | Create a clustering run |
| `GET` | `/api/clustering/stats` | Read clustering statistics |
| `GET` | `/api/clustering/map` | Read map nodes and topic metadata |
| `POST` | `/api/topics/generate` | Generate and persist LDA topics |
| `GET` | `/api/topics` | List topics |
| `GET` | `/api/topics/{topic_id}` | Read a topic and its representative papers |
| `GET` | `/api/discovery/search` | Search and filter papers |
| `GET` | `/api/discovery/relationships` | Read topic relationships |
| `GET` | `/api/papers/{paper_id}` | Read a paper |
| `PATCH` | `/api/papers/{paper_id}` | Update a paper |
| `DELETE` | `/api/papers/{paper_id}` | Delete a paper |
| `POST` | `/api/papers/bulk-delete` | Delete selected papers |

## Architecture

The backend separates ingestion, preprocessing, embeddings, clustering, topic extraction, discovery, and paper management. SQLite stores papers and each processing stage. The React and TypeScript frontend uses the API to manage papers and display the map.

See [docs/architecture.md](docs/architecture.md) for the component responsibilities, data model, and processing flow.
