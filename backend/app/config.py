import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
MAX_PAPERS = int(os.getenv("MAX_PAPERS", "40000"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/research_mapper.db")
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".csv"}
if MAX_PAPERS < 1:
    raise ValueError("MAX_PAPERS must be positive.")
if MAX_UPLOAD_MB < 1:
    raise ValueError("MAX_UPLOAD_MB must be positive.")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
EMBEDDING_BATCH_SIZE = 32
MAX_EMBEDDING_BATCH = 128
EMBEDDING_VERSION = "1.0"
