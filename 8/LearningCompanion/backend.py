import os
import json
import openai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
from prompt import MATERIAL_PROMPT, QUIZ_PROMPT

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

# --- Pydantic Models for API requests and responses ---

class MaterialRequest(BaseModel):
    topic: str

class MaterialResponse(BaseModel):
    learning_material: str

class QuizRequest(BaseModel):
    learning_material: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

# --- FastAPI Application ---
app = FastAPI(
    title="AI Learning Assistant API",
    description="API for generating learning materials and quizzes.",
    version="1.0.0",
)

@app.post("/generate-material", response_model=MaterialResponse)
async def generate_material_endpoint(request: MaterialRequest):
    """
    Generates learning material for a given topic.
    """
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized.")
    
    try:
        formatted_prompt = MATERIAL_PROMPT.format(topic=request.topic)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": formatted_prompt}],
            temperature=0.5,
        )
        material = response.choices[0].message.content
        return MaterialResponse(learning_material=material)

    except Exception as e:
        print(f"An error occurred while generating material: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz_endpoint(request: QuizRequest):
    """
    Generates a quiz based on the provided learning material.
    """
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized.")

    try:
        formatted_prompt = QUIZ_PROMPT.format(learning_material=request.learning_material)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": formatted_prompt}],
            response_format={"type": "json_object"}, # Enforce JSON output
            temperature=0.3,
        )
        
        quiz_data = json.loads(response.choices[0].message.content)
        # Pydantic will automatically validate the structure of quiz_data['questions']
        return QuizResponse(questions=quiz_data['questions'])

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse quiz data from model.")
    except Exception as e:
        print(f"An error occurred while generating quiz: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
