import os
import shutil
import uuid
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

# --- Import our new prompt ---
from prompts import FINAL_ANSWER_PROMPT

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
UPLOAD_DIRECTORY = "uploads"
QDRANT_URL = os.getenv("QDRANT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_COLLECTION_NAME = "rag_collection_v1"
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

# --- Pydantic Models for API ---
class UploadResponse(BaseModel):
    filename: str
    message: str
    chunks_inserted: int

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Application Backend",
    description="API for handling document uploads and chat for a RAG system.",
    version="1.0.0",
)

# --- Existing Helper Functions (upload and processing) are here... ---
# (No changes needed to the upload/processing code from the previous step)
def extract_text_from_file(filepath: str) -> str:
    # ... (same as before)
    file_extension = os.path.splitext(filepath)[1].lower()
    if file_extension == ".pdf":
        try:
            doc = fitz.open(filepath)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            return text
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing PDF file: {e}")
    elif file_extension in [".txt", ".md"]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading text file: {e}")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

async def process_and_embed_document(filepath: str, filename: str) -> int:
    # ... (same as before)
    text = extract_text_from_file(filepath)
    if not text or not text.strip():
        return 0
    chunks = text_splitter.chunks(text)
    embeddings_response = openai_client.embeddings.create(input=chunks, model=EMBEDDING_MODEL)
    embeddings = [item.embedding for item in embeddings_response.data]
    points_to_upsert = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embeddings[i],
            payload={"text": chunks[i], "source": filename}
        ) for i in range(len(chunks))
    ]
    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=points_to_upsert,
        wait=True
    )
    return len(chunks)

# --- Existing /upload Endpoint ---
@app.post("/upload", response_model=UploadResponse)
async def upload_and_process_file(file: UploadFile = File(...)):
    # ... (same as before)
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        num_chunks = await process_and_embed_document(file_path, file.filename)
        return {
            "filename": file.filename,
            "message": f"File '{file.filename}' uploaded and indexed successfully.",
            "chunks_inserted": num_chunks
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# --- NEW /chat Endpoint ---
@app.post("/chat", response_model=ChatResponse)
async def handle_chat_request(request: ChatRequest):
    """Handles a chat query by retrieving context and generating an answer."""
    query = request.query
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # 1. Retrieve relevant context from Qdrant
    print(f"🔎 Searching for context for query: '{query}'")
    query_embedding = openai_client.embeddings.create(
        input=[query],
        model=EMBEDDING_MODEL
    ).data[0].embedding

    search_results: List[ScoredPoint] = qdrant_client.search(
        collection_name=QDRANT_COLLECTION_NAME,
        query_vector=query_embedding,
        limit=5,  # Retrieve top 5 most relevant chunks
        with_payload=True
    )

    if not search_results:
        return ChatResponse(answer="I could not find any relevant information in the uploaded documents.", sources=[])

    # 2. Prepare the context for the synthesis agent
    context_chunks = [result.payload['text'] for result in search_results]
    source_documents = list(set([result.payload['source'] for result in search_results]))
    
    formatted_context = "\n\n---\n\n".join(context_chunks)

    # 3. Synthesize the final answer
    print("🤖 Synthesizing final answer...")
    formatted_prompt = FINAL_ANSWER_PROMPT.format(context=formatted_context, query=query)
    
    try:
        response = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": formatted_prompt}],
            temperature=0.1,
        )
        final_answer = response.choices[0].message.content

        return ChatResponse(answer=final_answer, sources=source_documents)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response from LLM: {e}")

# --- Application Startup Event (same as before) ---
@app.on_event("startup")
async def startup_event():
    # ... (same as before)
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)