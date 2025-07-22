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
from qdrant_client.http.models import PointStruct
from openai import OpenAI
from semantic_text_splitter import TextSplitter

# --- Load Environment Variables ---
load_dotenv()

# --- Configuration ---
UPLOAD_DIRECTORY = "uploads"
QDRANT_URL = os.getenv("QDRANT_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_COLLECTION_NAME = "rag_collection_v1"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536  # Dimension for text-embedding-3-small

# --- Validate Environment Configuration ---
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is not set in the environment variables.")
if not QDRANT_URL:
    raise ValueError("❌ QDRANT_URL is not set in the environment variables.")

# --- Initialize Global Clients ---
openai_client = OpenAI(api_key=OPENAI_API_KEY)
qdrant_client = QdrantClient(url=QDRANT_URL)
# Using a simple character-based splitter, similar to the example
text_splitter = TextSplitter(1000, 200)

# Pydantic model for the response
class UploadResponse(BaseModel):
    filename: str
    message: str
    chunks_inserted: int

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Application Backend",
    description="API for handling document uploads and processing for a RAG system.",
    version="1.0.0",
)

# --- Core Helper Functions ---

def extract_text_from_file(filepath: str) -> str:
    """Extracts text content from a file (.pdf, .txt, .md)"""
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
    """Main pipeline: Extracts text, chunks, creates embeddings, and upserts to Qdrant."""
    
    # 1. Extract text from the document
    print(f"📄 Extracting text from {filename}...")
    text = extract_text_from_file(filepath)
    if not text or not text.strip():
        print(f"⚠️ No text extracted from {filename}.")
        return 0

    # 2. Split the text into manageable chunks
    print(f"🔪 Splitting text into chunks...")
    chunks = text_splitter.chunks(text)
    print(f"   Created {len(chunks)} chunks.")

    # 3. Generate embeddings for each chunk
    print(f"🧠 Generating embeddings for {len(chunks)} chunks...")
    embeddings_response = openai_client.embeddings.create(input=chunks, model=EMBEDDING_MODEL)
    embeddings = [item.embedding for item in embeddings_response.data]

    # 4. Prepare and upsert points into Qdrant
    print(f"💾 Upserting {len(chunks)} vectors into Qdrant...")
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
        wait=True  # Wait for the operation to complete
    )
    print("✅ Upsert complete.")
    return len(chunks)

# --- API Endpoint ---

@app.post("/upload", response_model=UploadResponse)
async def upload_and_process_file(file: UploadFile = File(...)):
    """Receives a file, saves it, processes it, and cleans up."""
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    
    try:
        # Save the file temporarily
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run the processing pipeline
        num_chunks = await process_and_embed_document(file_path, file.filename)
        
        return {
            "filename": file.filename,
            "message": f"File '{file.filename}' uploaded and indexed successfully.",
            "chunks_inserted": num_chunks
        }
    except HTTPException as e:
        # Re-raise HTTPExceptions to be sent to the client
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        # Clean up the saved file after processing
        if os.path.exists(file_path):
            os.remove(file_path)

# --- Application Startup Event ---

@app.on_event("startup")
async def startup_event():
    """On startup, ensure the Qdrant collection exists."""
    try:
        collections_response = qdrant_client.get_collections()
        collection_names = [c.name for c in collections_response.collections]
        
        if QDRANT_COLLECTION_NAME not in collection_names:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' not found. Creating it...")
            qdrant_client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSION,
                    distance=models.Distance.COSINE
                ),
            )
        else:
            print(f"Collection '{QDRANT_COLLECTION_NAME}' already exists.")
            
    except Exception as e:
        print(f"🔥 Could not connect to Qdrant or create collection: {e}")
        # Depending on the desired behavior, you might want to exit the application
        # raise SystemExit(f"Could not initialize Qdrant collection: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)