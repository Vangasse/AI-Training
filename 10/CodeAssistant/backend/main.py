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
import fitz  # PyMuPDF
from dotenv import load_dotenv
from typing import List

# --- Qdrant, OpenAI, and Text Splitting ---
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, ScoredPoint
from openai import OpenAI
from semantic_text_splitter import TextSplitter

# --- Import our prompts from the separate file ---
from prompts import FINAL_ANSWER_PROMPT, FILTER_CONTEXT_PROMPT

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".cpp", ".h", ".c", ".go", ".rs", ".rb",
    ".php", ".kt", ".swift", ".m", ".scala", ".pl", ".pm", ".lua", ".r",
    ".sh", ".bat", ".ps1", ".json", ".yaml", ".yml", ".xml", ".html", ".css",
    ".sql", ".dockerfile", "Dockerfile", ".gitignore", ".gitattributes"
}
UPLOAD_DIRECTORY = "temp_uploads"
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_COLLECTION_NAME = "code_assistant_v1"
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
text_splitter = TextSplitter(1000, 200)

# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)
    try:
        collections_response = qdrant_client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        if QDRANT_COLLECTION_NAME not in collection_names:
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
    if os.path.exists(UPLOAD_DIRECTORY):
        shutil.rmtree(UPLOAD_DIRECTORY)

# --- Pydantic Models for API ---
class IndexResponse(BaseModel):
    message: str
    total_files_processed: int
    total_chunks_inserted: int
    errors: List[str]

class ChatRequest(BaseModel):
    query: str

class Source(BaseModel):
    text: str
    filename: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]

app = FastAPI(
    title="Code Assistant Backend",
    description="API for indexing codebases and providing AI-powered suggestions.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Helper Functions ---
def extract_text_from_file(filepath: str) -> str:
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lower()
    if file_extension == ".pdf":
        try:
            with fitz.open(filepath) as doc:
                text = "".join(page.get_text() for page in doc)
            return text
        except Exception as e:
            print(f"Error processing PDF {filepath}: {e}")
            return ""
    elif file_extension in [".txt", ".md"] or file_extension in CODE_EXTENSIONS:
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text/code file {filepath}: {e}")
            return ""
    else:
        print(f"Unsupported file type: {file_extension}")
        return ""

def process_and_embed_document(filepath: str, filename: str) -> int:
    text = extract_text_from_file(filepath)
    if not text or not text.strip():
        return 0
    chunks = text_splitter.chunks(text)
    if not chunks:
        return 0
    try:
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
    total_chunks, files_processed, error_list = 0, 0, []
    for file in files:
        base_filename = os.path.basename(file.filename)
        file_path = os.path.join(UPLOAD_DIRECTORY, f"{uuid.uuid4()}-{base_filename}")
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            num_chunks = process_and_embed_document(file_path, file.filename)
            if num_chunks > 0:
                total_chunks += num_chunks
                files_processed += 1
        except Exception as e:
            error_msg = f"Failed to process file {file.filename}: {e}"
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

@app.post("/chat", response_model=ChatResponse)
async def handle_chat_request(request: ChatRequest):
    try:
        query = request.query
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty.")

        # 1. RETRIEVAL
        query_embedding = openai_client.embeddings.create(input=[query], model=EMBEDDING_MODEL).data[0].embedding
        
        search_results: List[ScoredPoint] = qdrant_client.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_embedding,
            limit=10,
            with_payload=True
        )

        if not search_results:
            return ChatResponse(answer="I could not find any relevant information in the codebase.", sources=[])

        # 2. FILTERING (Agent 1)
        context_for_filter = "\n\n".join(f"Chunk {i}: {result.payload['text']}" for i, result in enumerate(search_results))
        filtering_prompt = FILTER_CONTEXT_PROMPT.format(context=context_for_filter, query=query)
        
        essential_chunks = []
        try:
            filter_response = openai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[{"role": "system", "content": filtering_prompt}],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            response_data = json.loads(filter_response.choices[0].message.content)
            essential_indices = response_data.get("relevant_chunk_indices", [])
            essential_chunks = [search_results[i] for i in essential_indices if i < len(search_results)]
        except Exception as e:
            print(f"⚠️ Filtering agent failed: {e}. Defaulting to all search results.")
            essential_chunks = search_results

        # CORRECTED LOGIC: If the filter returns nothing, fall back to the original search results.
        # This makes our system more robust to general queries.
        if not essential_chunks and search_results:
            print("⚠️ Filter agent returned no chunks. Falling back to all retrieved chunks.")
            essential_chunks = search_results
        
        if not essential_chunks:
             return ChatResponse(answer="I found some potentially relevant documents, but none contained specific information to answer your question.", sources=[])

        # 3. SYNTHESIS (Agent 2)
        final_source_objects = [Source(text=chunk.payload['text'], filename=chunk.payload['source']) for chunk in essential_chunks]
        formatted_context = "\n\n---\n\n".join([chunk.payload['text'] for chunk in essential_chunks])
        synthesis_prompt = FINAL_ANSWER_PROMPT.format(context=formatted_context, query=query)

        synthesis_response = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": synthesis_prompt}],
            temperature=0.1,
        )
        final_answer = synthesis_response.choices[0].message.content
        return ChatResponse(answer=final_answer, sources=final_source_objects)

    except Exception as e:
        print(f"🔥🔥🔥 AN UNEXPECTED ERROR OCCURRED: {e} 🔥🔥🔥")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)