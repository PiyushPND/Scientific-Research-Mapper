from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import MAX_PAPERS, MAX_UPLOAD_MB, ALLOWED_EXTENSIONS
from app.database import initialize_database, get_connection
from app.ingestion.service import ingest_dataset
from app.preprocessing.service import process_batch, get_preprocessing_stats
from app.embeddings.service import process_embedding_batch, get_embedding_stats
from app.clustering.service import (
    run_clustering,
    get_clustering_stats,
    get_research_map,
)
from app.topics.service import (
    initialize_topic_tables,
    generate_topics,
    get_topics,
    get_topic_details,
)
from app.discovery.service import search_papers, get_topic_relationships
from app.papers import get_paper, update_paper, delete_papers
from app.schemas import PaperUpdate, BulkPaperDelete


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    initialize_topic_tables()
    yield


app = FastAPI(
    title="Scientific Research Mapper API",
    description="Research paper ingestion and data validation",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "application": "Scientific Research Mapper",
        "status": "running",
        "maximum_papers": MAX_PAPERS,
    }


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.post("/api/ingestion/upload")
async def upload_dataset(file: UploadFile = File(...)):
    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Upload a CSV file with required 'title' and 'abstract' columns.",
        )
    content = await file.read(MAX_UPLOAD_MB * 1048577)
    if len(content) > MAX_UPLOAD_MB * 1048576:
        raise HTTPException(
            status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_MB}MB."
        )
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        return ingest_dataset(filename, content)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(
            status_code=500, detail="Internal error during dataset ingestion."
        )


@app.get("/api/papers/stats")
def paper_statistics():
    connection = get_connection()
    try:
        total = connection.execute("SELECT COUNT(*)FROM papers").fetchone()[0]
        return {
            "total_papers": total,
            "maximum_capacity": MAX_PAPERS,
            "remaining_capacity": MAX_PAPERS - total,
        }
    finally:
        connection.close()


@app.post("/api/preprocessing/run")
def run_preprocessing(batch_size: int = 500):
    try:
        return process_batch(batch_size)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(
            status_code=500, detail="An error occurred during preprocessing."
        )


@app.get("/api/preprocessing/stats")
def preprocessing_statistics():
    return get_preprocessing_stats()


@app.post("/api/embeddings/run")
def run_embedding_generation(batch_size: int = 128):
    try:
        return process_embedding_batch(batch_size)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(status_code=500, detail="Embedding generation failed.")


@app.get("/api/embeddings/stats")
def embedding_statistics():
    return get_embedding_stats()


@app.post("/api/clustering/run")
def execute_clustering(min_cluster_size: int = 15, min_samples: int = 5):
    try:
        return run_clustering(
            min_cluster_size=min_cluster_size, min_samples=min_samples
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except Exception:
        raise HTTPException(status_code=500, detail="Clustering execution failed.")


@app.get("/api/clustering/stats")
def clustering_statistics(run_id: str = None):
    result = get_clustering_stats(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No clustering run found.")
    return result


@app.get("/api/clustering/map")
def research_map(run_id: str | None = None):
    return get_research_map(run_id)


@app.post("/api/topics/generate")
def create_topics(
    run_id: str | None = None, top_n: int = 10, representative_count: int = 5
):
    try:
        return generate_topics(
            run_id=run_id, top_n=top_n, representative_count=representative_count
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/topics")
def list_topics(run_id: str | None = None):
    return get_topics(run_id)


@app.get("/api/topics/{topic_id}")
def topic_details(topic_id: int):
    result = get_topic_details(topic_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result


@app.get("/api/discovery/search")
def discover_papers(
    query: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    topic_id: int | None = None,
    source: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    try:
        return search_papers(
            query=query,
            year_from=year_from,
            year_to=year_to,
            topic_id=topic_id,
            source=source,
            limit=limit,
            offset=offset,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/api/papers/{paper_id}")
def paper_details(paper_id: str):
    result = get_paper(paper_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return result


@app.patch("/api/papers/{paper_id}")
def edit_paper(paper_id: str, update: PaperUpdate):
    return update_paper(paper_id, update.model_dump(exclude_unset=True))


@app.delete("/api/papers/{paper_id}")
def remove_paper(paper_id: str):
    deleted = delete_papers([paper_id])
    if not deleted:
        raise HTTPException(status_code=404, detail="Paper not found.")
    return {"deleted_count": deleted, "map_stale": True}


@app.post("/api/papers/bulk-delete")
def remove_papers(request: BulkPaperDelete):
    deleted = delete_papers(request.paper_ids)
    return {"deleted_count": deleted, "map_stale": bool(deleted)}


@app.get("/api/discovery/relationships")
def discover_topic_relationships(run_id: str | None = None):
    return get_topic_relationships(run_id)
