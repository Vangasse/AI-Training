# guardrail_service/backend.py

import os
import json
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import uvicorn

# Import the prompt from our local prompts file
from prompts import PROMPT_GUARDRAIL

# --- Configuration ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = "gpt-4o-mini"

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is not set in the environment.")

# --- Pydantic Models for API Data Validation ---
class InspectRequest(BaseModel):
    """The request model for content to be inspected."""
    content: str

class InspectResponse(BaseModel):
    """The response model for the inspection result."""
    issues_found: bool
    redacted_text: str

# --- FastAPI Application Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and shutdown events."""
    print("🚀 Guardrail Service starting up...")
    app.state.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    yield
    print("🛑 Guardrail Service shutting down.")

app = FastAPI(
    title="Guardrail Inspection Service",
    description="An API to detect and redact PII and offensive content.",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/inspect", response_model=InspectResponse)
async def inspect_content(request: InspectRequest):
    """
    API endpoint to inspect text for sensitive content.
    """
    try:
        # Get the OpenAI client from the application state
        client = app.state.openai_client

        # Format the prompt with the user's content
        formatted_prompt = PROMPT_GUARDRAIL.format(text_input=request.content)

        # Send the request to the OpenAI API for analysis
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "system", "content": formatted_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        # Parse the JSON string from the response
        result = json.loads(response.choices[0].message.content)
        return InspectResponse(**result)

    except Exception as e:
        print(f"🔥🔥🔥 UNEXPECTED ERROR: {e} 🔥🔥🔥")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected server error occurred: {str(e)}"
        )

if __name__ == "__main__":
    # This makes the backend runnable as a standalone script
    uvicorn.run(app, host="0.0.0.0", port=8000)