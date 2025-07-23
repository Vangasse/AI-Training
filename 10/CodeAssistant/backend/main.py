# backend/main.py

import os
import shutil
import uuid
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
import fitz  # PyMuPDF
from dotenv import load_dotenv
from typing import List

# --- Qdrant, OpenAI, and Text Splitting ---
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, ScoredPoint
from openai import OpenAI
from semantic_text_splitter import TextSplitter

# --- Import our updated prompts ---
# from prompts import FINAL_ANSWER_PROMPT, FILTER_CONTEXT_PROMPT # We will use these in the next step

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
# NEW: Define supported code extensions
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".cpp", ".h", ".c", ".go", ".rs", ".rb",
    ".php", ".kt", ".swift", ".m", ".scala", ".pl", ".pm", ".lua", ".r",
    ".sh", ".bat", ".ps1", ".json", ".yaml", ".yml", ".xml", ".html", ".css",
    ".sql", ".dockerfile", "Dockerfile", ".gitignore", ".gitattributes"
}
UPLOAD_DIRECTORY = "temp_uploads" # Create a temporary directory for processing
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_COLLECTION_NAME = "code_assistant_v1" # New collection name for our app
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
CHAT_MODEL = "gpt-4o-mini"

# --- Validate Environment Configuration ---
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is not set in the environment variables.")
if not QDRANT_URL:
    raise ValueError("❌ QDRANT_URL is not set in the environment variables.")

# --- Initialize Global Clients ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)
# Using a larger chunk size suitable for code
text_splitter = TextSplitter(2000, 200)

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, ensure the Qdrant collection exists and create the temp upload dir.
    print("🚀 Starting up...")
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    try:
        collections_response = qdrant_client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        if QDRANT_COLLECTION_NAME not in collection_names:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' not found. Creating it...")
            qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(size=EMBEDDING_DIMENSION, distance=models.Distance.COSINE),
            )
        else:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' already exists.")
    except Exception as e:
        print(f"🔥 Could not connect to Qdrant or create collection: {e}")
    yield
    # On shutdown, clean up the temporary upload directory.
    print("🧹 Shutting down and cleaning up...")
    shutil.rmtree(UPLOAD_DIRECTORY)

# --- Pydantic Models for API ---
# NEW: Response model for the directory indexing endpoint
class IndexResponse(BaseModel):
    message: str
    total_files_processed: int
    total_chunks_inserted: int
    errors: List[str]

# Models for the chat functionality (will be fully used in the next step)
class ChatRequest(BaseModel):
    query: str

class Source(BaseModel):
    text: str
    filename: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]

# Initialize the FastAPI app with the lifespan handler
app = FastAPI(
    title="Code Assistant Backend",
    description="API for indexing codebases and providing AI-powered suggestions.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Helper Functions ---
# MODIFIED: Expanded to handle code files
def extract_text_from_file(filepath: str) -> str:
    """Extracts text from various file types, including code files."""
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lower()

    if file_extension == ".pdf":
        try:
            doc = fitz.open(filepath)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception as e:
            print(f"Error processing PDF {filepath}: {e}")
            return "" # Return empty string on error
    # Handle text-based and code files
    elif file_extension in [".txt", ".md"] or file_extension in CODE_EXTENSIONS:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text/code file {filepath}: {e}")
            return "" # Return empty string on error
    else:
        print(f"Unsupported file type: {file_extension}")
        return "" # Return empty string for unsupported types

def process_and_embed_document(filepath: str, filename: str) -> int:
    """Processes a single file, splits it into chunks, and embeds them into Qdrant."""
    text = extract_text_from_file(filepath)
    if not text or not text.strip():
        return 0 # Skip empty or unsupported files

    chunks = text_splitter.chunks(text)
    if not chunks:
        return 0

    try:
        # CORRECTED: Removed 'await' from this line
        embeddings_response = openai_client.embeddings.create(input=chunks, model=EMBEDDING_MODEL)
        embeddings = [item.embedding for item in embeddings_response.data]

        points_to_upsert = [
            PointStruct(id=str(uuid.uuid4()), vector=embeddings[i], payload={"text": chunks[i], "source": filename})
            for i in range(len(chunks))
        ]

        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points_to_upsert, wait=True)
        return len(chunks)
    except Exception as e:
        print(f"Error embedding or upserting chunks for {filename}: {e}")
        return 0

# --- API Endpoints ---
@app.post("/index-directory", response_model=IndexResponse)
async def index_directory(files: List[UploadFile] = File(...)):
    """Receives a list of files from a directory upload, processes and embeds them."""
    total_chunks = 0
    files_processed = 0
    error_list = []

    for file in files:
        base_filename = os.path.basename(file.filename)
        file_path = os.path.join(UPLOAD_DIRECTORY, f"{uuid.uuid4()}-{base_filename}")
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # CORRECTED: Removed 'await' from the function call
            num_chunks = process_and_embed_document(file_path, file.filename)
            if num_chunks > 0:
                total_chunks += num_chunks
                files_processed += 1
            else:
                print(f"No chunks generated for file: {file.filename}")

        except Exception as e:
            error_msg = f"Failed to process file {file.filename}: {e}"
            print(error_msg)
            error_list.append(error_msg)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
            await file.close()

    return IndexResponse(
        message=f"Indexing complete. Processed {files_processed}/{len(files)} files.",
        total_files_processed=files_processed,
        total_chunks_inserted=total_chunks,
        errors=error_list
    )


# The /chat endpoint remains for the next step. We are not using it yet.
# @app.post("/chat", response_model=ChatResponse)
# async def handle_chat_request(request: ChatRequest):
#     # Logic for Retrieval, Filtering, and Synthesis will go here in the next step
#     pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)