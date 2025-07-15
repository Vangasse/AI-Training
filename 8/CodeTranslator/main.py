import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the backend URL from environment variables, with a default value
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def translate_code(code: str, target_language: str) -> str:
    """
    Calls the backend API to translate a code snippet.

    Args:
        code: The source code to translate.
        target_language: The language to translate the code into.

    Returns:
        The translated code as a string, or an error message.
    """
    if not code:
        return "Error: Please enter some code to translate."
    if not target_language:
        return "Error: Please select a target language."

    # The endpoint in our backend.py
    translate_url = f"{BACKEND_URL}/translate"

    # The payload matches the TranslationRequest Pydantic model in the backend
    payload = {
        "source_code": code,
        "target_language": target_language,
    }
    
    try:
        # Make the POST request to the backend
        response = requests.post(translate_url, json=payload)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Extract the result from the JSON response
        response_data = response.json()
        return response_data.get("translated_code", "Error: No result found in backend response.")

    except requests.exceptions.RequestException as e:
        print(f"Error calling backend: {e}")
        return (
            "Error: Could not connect to the backend service.\n"
            f"Please ensure the FastAPI server is running at {BACKEND_URL}."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"An unexpected error occurred: {e}"

# Define the Gradio Interface
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        """
        # AI Code Translator
        Paste your code in the box below, select the target language, and click "Translate" to get the equivalent code.
        """
    )
    with gr.Row():
        with gr.Column(scale=1):
            language_input = gr.Code(label="Source Code", language=None, lines=15)
            language_dropdown = gr.Dropdown(
                label="Target Language",
                choices=["Python", "JavaScript", "Go", "Rust", "Java", "C++"],
                value="Python"
            )
            translate_button = gr.Button("Translate", variant="primary")
        with gr.Column(scale=1):
            language_output = gr.Code(label="Translated Code", language=None, lines=15, interactive=False)

    translate_button.click(
        fn=translate_code,
        inputs=[language_input, language_dropdown],
        outputs=[language_output]
    )

if __name__ == "__main__":
    demo.launch()
