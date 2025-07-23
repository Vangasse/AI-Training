# backend/main.py

import os
import shutil
import uuid
import json
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
import fitz
from dotenv import load_dotenv
from typing import List

from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, ScoredPoint
from openai import OpenAI
from semantic_text_splitter import TextSplitter

# MODIFIED: Import the new prompt
from prompts import CODE_IMPROVEMENT_PROMPT, FILTER_CONTEXT_PROMPT

load_dotenv()

# --- Configuration (remains the same) ---
CODE_EXTENSIONS = {".py",".js",".ts",".java",".cs",".cpp",".h",".c",".go",".rs",".rb",".php",".kt",".swift",".m",".scala",".pl",".pm",".lua",".r",".sh",".bat",".ps1",".json",".yaml",".yml",".xml",".html",".css",".sql",".dockerfile","Dockerfile",".gitignore",".gitattributes"}
UPLOAD_DIRECTORY = "temp_uploads"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_COLLECTION_NAME = "code_assistant_v1"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
CHAT_MODEL = "gpt-4o-mini"

if not OPENAI_API_KEY: raise ValueError("❌ OPENAI_API_KEY is not set")
if not QDRANT_URL: raise ValueError("❌ QDRANT_URL is not set")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)
text_splitter = TextSplitter(1000, 200)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    try:
        collections_response = qdrant_client.get_collections()
        if QDRANT_COLLECTION_NAME not in [c.name for c in collections_response.collections]:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' not found. Creating it...")
            qdrant_client.recreate_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(size=EMBEDDING_DIMENSION, distance=models.Distance.COSINE),
            )
        else:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' already exists.")
    except Exception as e:
        print(f"🔥 Could not connect to Qdrant or create collection: {e}")
    yield
    print("🧹 Shutting down and cleaning up...")
    if os.path.exists(UPLOAD_DIRECTORY): shutil.rmtree(UPLOAD_DIRECTORY)

# MODIFIED: Pydantic models are now for suggestions, not Q&A.
class IndexResponse(BaseModel):
    message: str
    total_files_processed: int
    total_chunks_inserted: int
    errors: List[str]

class ChatRequest(BaseModel):
    query: str

class Suggestion(BaseModel):
    file_name: str
    explanation: str
    suggested_code: str

class ChatResponse(BaseModel):
    suggestions: List[Suggestion]

app = FastAPI(
    title="Code Assistant Backend",
    description="API for providing code improvement suggestions.",
    version="2.0.0",
    lifespan=lifespan
)

# Helper functions (extract_text_from_file, process_and_embed_document) remain the same
def extract_text_from_file(filepath: str) -> str:
    _, file_extension = os.path.splitext(filepath)
    if file_extension.lower() == ".pdf":
        try:
            with fitz.open(filepath) as doc: return "".join(page.get_text() for page in doc)
        except Exception as e: print(f"Error processing PDF {filepath}: {e}"); return ""
    elif file_extension.lower() in [".txt", ".md"] or file_extension.lower() in CODE_EXTENSIONS:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f: return f.read()
        except Exception as e: print(f"Error reading file {filepath}: {e}"); return ""
    else: return ""

def process_and_embed_document(filepath: str, filename: str) -> int:
    text = extract_text_from_file(filepath)
    if not text or not text.strip(): return 0
    chunks = text_splitter.chunks(text)
    if not chunks: return 0
    try:
        embeddings = [item.embedding for item in openai_client.embeddings.create(input=chunks, model=EMBEDDING_MODEL).data]
        points = [PointStruct(id=str(uuid.uuid4()), vector=emb, payload={"text": ch, "source": filename}) for emb, ch in zip(embeddings, chunks)]
        qdrant_client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points, wait=True)
        return len(points)
    except Exception as e: print(f"Error embedding chunks for {filename}: {e}"); return 0

@app.post("/index-directory", response_model=IndexResponse)
async def index_directory(files: List[UploadFile] = File(...)):
    # This endpoint remains the same
    total_chunks, files_processed, error_list = 0, 0, []
    for file in files:
        file_path = os.path.join(UPLOAD_DIRECTORY, f"{uuid.uuid4()}-{os.path.basename(file.filename)}")
        try:
            with open(file_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
            num_chunks = process_and_embed_document(file_path, file.filename)
            if num_chunks > 0: total_chunks += num_chunks; files_processed += 1
        except Exception as e: error_list.append(f"Failed to process {file.filename}: {e}")
        finally:
            if os.path.exists(file_path): os.remove(file_path)
            await file.close()
    return IndexResponse(message="Indexing complete.", total_files_processed=files_processed, total_chunks_inserted=total_chunks, errors=error_list)

# MODIFIED: The chat endpoint now generates and returns structured suggestions.
@app.post("/chat", response_model=ChatResponse)
async def handle_chat_request(request: ChatRequest):
    try:
        query = request.query
        if not query: raise HTTPException(status_code=400, detail="Query cannot be empty.")

        query_embedding = openai_client.embeddings.create(input=[query], model=EMBEDDING_MODEL).data[0].embedding
        search_results = qdrant_client.search(collection_name=QDRANT_COLLECTION_NAME, query_vector=query_embedding, limit=10, with_payload=True)
        if not search_results: return ChatResponse(suggestions=[])

        context_for_filter = "\n\n".join(f"Chunk {i}: {result.payload['text']}" for i, result in enumerate(search_results))
        filtering_prompt = FILTER_CONTEXT_PROMPT.format(context=context_for_filter, query=query)
        
        essential_chunks = []
        try:
            filter_response = openai_client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "system", "content": filtering_prompt}], response_format={"type": "json_object"}, temperature=0.0)
            essential_indices = json.loads(filter_response.choices[0].message.content).get("relevant_chunk_indices", [])
            essential_chunks = [search_results[i] for i in essential_indices if i < len(search_results)]
        except Exception as e: print(f"⚠️ Filtering agent failed: {e}. Defaulting to all search results."); essential_chunks = search_results

        if not essential_chunks and search_results: essential_chunks = search_results
        if not essential_chunks: return ChatResponse(suggestions=[])

        formatted_context = "\n\n---\n\n".join(f"**File: {chunk.payload['source']}**\n\n```\n{chunk.payload['text']}\n```" for chunk in essential_chunks)
        synthesis_prompt = CODE_IMPROVEMENT_PROMPT.format(context=formatted_context, query=query)

        synthesis_response = openai_client.chat.completions.create(model=CHAT_MODEL, messages=[{"role": "system", "content": synthesis_prompt}], response_format={"type": "json_object"}, temperature=0.2)
        suggestion_data = json.loads(synthesis_response.choices[0].message.content)
        
        return ChatResponse(suggestions=suggestion_data.get("suggestions", []))

    except Exception as e:
        print(f"🔥🔥🔥 AN UNEXPECTED ERROR OCCURRED: {e} 🔥🔥🔥"); traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)