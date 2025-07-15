import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import openai
from prompt import SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()

# Configure OpenAI client
try:
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file.")
    client = openai.OpenAI()
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    client = None

# --- Pydantic Models for Request and Response ---
class TranslationRequest(BaseModel):
    """
    Defines the shape of the incoming request body.
    """
    source_code: str
    target_language: str

class TranslationResponse(BaseModel):
    """
    Defines the shape of the outgoing response body.
    """
    translated_code: str

# --- FastAPI Application ---
app = FastAPI(
    title="Code Translation API",
    description="A simple API to translate code snippets into different languages.",
    version="1.0.0",
)

@app.post("/translate", response_model=TranslationResponse)
async def translate_code_endpoint(request: TranslationRequest):
    """
    Receives code and a target language, translates it using the OpenAI API,
    and returns the result.
    """
    if not client:
        raise HTTPException(
            status_code=500, detail="OpenAI client is not initialized. Check API key."
        )

    try:
        # Format the system prompt with the target language and source code
        context = f"Translate the following code to {request.target_language}:\n\n```\n{request.source_code}\n```"
        formatted_prompt = SYSTEM_PROMPT.format(
            target_language=request.target_language,
            context=context
        )

        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": request.source_code} # Sending the code again as user message
            ],
            temperature=0.2,
        )

        translated_code = response.choices[0].message.content
        return TranslationResponse(translated_code=translated_code)

    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        raise HTTPException(status_code=502, detail=f"An error occurred with the OpenAI API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
