import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get the backend URL from environment variables, with a default value
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def upload_document(file):
    """
    Sends the selected file to the backend's /upload endpoint.
    """
    if file is None:
        return "⚠️ Please select a file first."

    # The 'files' parameter for requests needs a dictionary where the key ('file')
    # matches the expected field name on the backend.
    try:
        files = {'file': open(file.name, 'rb')}
        response = requests.post(f"{BACKEND_URL}/upload", files=files)
        
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status() 

        # Display the success message from the backend's JSON response
        return response.json().get("message", "✅ File uploaded successfully!")

    except requests.exceptions.RequestException as e:
        return f"🔥 Error connecting to the backend: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# --- Gradio Interface ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Step 1: Document Upload")
    gr.Markdown("Upload a document (.txt, .md, .pdf) to add it to the knowledge base.")

    with gr.Column():
        file_input = gr.File(
            label="Upload Your Document",
            file_types=[".txt", ".md", ".pdf"]
        )
        upload_button = gr.Button("Upload File", variant="primary")
    
    status_output = gr.Textbox(
        label="Upload Status",
        interactive=False,
        show_copy_button=True
    )

    # --- Event Handling: Link the button click to the upload function ---
    upload_button.click(
        fn=upload_document,
        inputs=[file_input],
        outputs=[status_output]
    )

if __name__ == "__main__":
    demo.launch()