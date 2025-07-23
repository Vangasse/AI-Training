# frontend/app.py

import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# --- NEW: Logic to handle directory indexing ---
def index_directory(files):
    """
    Sends the list of files (from a directory upload) to the backend's
    /index-directory endpoint for processing.
    """
    if not files:
        return "⚠️ Please select a directory first."
    
    try:
        # The 'files' parameter for requests expects a list of tuples.
        # Each tuple is ('files', (filename, file_object, content_type)).
        # Gradio provides temp files with a .name attribute holding the path.
        file_tuples = [("files", (os.path.basename(f.name), open(f.name, 'rb'))) for f in files]
        
        response = requests.post(f"{BACKEND_URL}/index-directory", files=file_tuples)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        # Nicely format the JSON response for display
        data = response.json()
        message = data.get("message", "Processing complete.")
        processed = data.get("total_files_processed", 0)
        chunks = data.get("total_chunks_inserted", 0)
        errors = data.get("errors", [])

        status_report = (
            f"✅ **{message}**\n\n"
            f"- **Files Processed**: {processed}\n"
            f"- **Chunks Created**: {chunks}"
        )
        if errors:
            status_report += f"\n- **Errors Encountered**: {len(errors)}"

        return status_report

    except requests.exceptions.RequestException as e:
        return f"🔥 Error connecting to the backend: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        # The file objects in file_tuples are automatically closed by requests
        pass

# --- Chat Logic (placeholder for next step) ---
def handle_chat(message: str, history: list):
    """
    This will be implemented in the next step. For now, it just gives a placeholder response.
    """
    # This is a placeholder until the chat backend is ready.
    yield [[message, "Chat functionality is not yet implemented."]]


# --- Gradio Interface ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Code Assistant")
    gr.Markdown("Index an entire code repository and then ask questions about it.")

    with gr.Tabs():
        # --- MODIFIED: Tab for indexing a directory ---
        with gr.TabItem("❶ Index Directory"):
            with gr.Column():
                gr.Markdown("## Select Your Codebase Directory")
                gr.Markdown("Click the button below to upload a folder. All supported code files within the folder will be processed and indexed into the vector database.")
                # MODIFIED: Use file_count="directory" for folder upload
                file_input = gr.File(
                    label="Upload Your Directory",
                    file_count="directory"
                )
                index_button = gr.Button("Index Directory", variant="primary")
                index_status = gr.Markdown(label="Indexing Status")
            
            index_button.click(
                fn=index_directory,
                inputs=[file_input],
                outputs=[index_status]
            )

        # --- Chat Tab (for next step) ---
        with gr.TabItem("❷ Chat with Your Code"):
            chatbot = gr.Chatbot(label="Chat History", height=500, render_markdown=True)
            msg_input = gr.Textbox(label="Your Question", placeholder="e.g., Explain the 'index_directory' function in app.py")
            clear_button = gr.ClearButton([msg_input, chatbot])

            msg_input.submit(
                fn=handle_chat,
                inputs=[msg_input, chatbot],
                outputs=[chatbot]
            )

if __name__ == "__main__":
    demo.launch()