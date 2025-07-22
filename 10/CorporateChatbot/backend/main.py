import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn

# Create the directory for storing uploaded documents if it doesn't exist
UPLOAD_DIRECTORY = "uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Pydantic model for the response
class UploadResponse(BaseModel):
    """Response model for a successful file upload."""
    filename: str
    message: str

# Initialize the FastAPI app
app = FastAPI(
    title="RAG Application Backend",
    description="API for handling document uploads for the RAG system.",
    version="1.0.0",
)

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Accepts a file upload and saves it to the server's 'uploads' directory.
    
    The `UploadFile` type from FastAPI handles the incoming file stream efficiently.
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file was sent.")

    # Define the full path where the file will be saved
    file_path = os.path.join(UPLOAD_DIRECTORY, file.filename)
    
    try:
        # Use shutil.copyfileobj to save the file in chunks, which is memory-efficient
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "filename": file.filename,
            "message": f"File '{file.filename}' was uploaded successfully."
        }
    except Exception as e:
        # Handle potential errors during file saving
        raise HTTPException(status_code=500, detail=f"Could not save the file: {e}")

if __name__ == "__main__":
    # Run the server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)