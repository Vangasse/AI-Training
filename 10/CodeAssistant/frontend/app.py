# frontend/app.py

import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# ... (index_directory function remains the same) ...
def index_directory(files):
    if not files:
        return "⚠️ Please select a directory first."
    try:
        file_tuples = [("files", (os.path.basename(f.name), open(f.name, 'rb'))) for f in files]
        response = requests.post(f"{BACKEND_URL}/index-directory", files=file_tuples)
        response.raise_for_status()
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


# MODIFIED: Implemented chat logic
def handle_chat(message: str, history: list):
    """
    Handles chat interaction. It sends the user's message to the backend,
    gets the bot's response, formats it with sources, and yields the result.
    """
    # Append the user's message to the history for immediate display
    history.append([message, None])
    yield history

    try:
        # Call the backend's /chat endpoint
        response = requests.post(f"{BACKEND_URL}/chat", json={"query": message})
        response.raise_for_status()
        data = response.json()
        
        answer = data.get("answer", "Sorry, I encountered an error.")
        sources = data.get("sources", [])

        # Start building the final response string with the main answer
        final_response = answer

        # If sources are available, format them into a collapsible HTML section
        if sources:
            sources_details = "\n\n---\n\n<details><summary><strong>Click to see sources</strong></summary>\n\n"
            for i, source in enumerate(sources):
                # Add the filename for each source chunk
                sources_details += f"**Source {i+1}: `{source['filename']}`**\n"
                # Format the text chunk as a blockquote, escaping for markdown
                formatted_text = source['text'].replace('\n', '\n> ')
                sources_details += f"> {formatted_text}\n\n"
            sources_details += "</details>"
            
            # Append the formatted sources to the final answer
            final_response += sources_details

        # Update the last entry in history with the bot's full response
        history[-1][1] = final_response

    except requests.RequestException as e:
        history[-1][1] = f"🔥 Error connecting to the backend: {e}"
    except Exception as e:
        history[-1][1] = f"An unexpected error occurred: {e}"

    # Yield the final history to the chatbot
    yield history


# --- Gradio Interface (no changes to the layout) ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Code Assistant")
    gr.Markdown("Index an entire code repository and then ask questions about it.")

    with gr.Tabs():
        with gr.TabItem("❶ Index Directory"):
            with gr.Column():
                gr.Markdown("## Select Your Codebase Directory")
                gr.Markdown("Click the button below to upload a folder. All supported code files within the folder will be processed and indexed into the vector database.")
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

        with gr.TabItem("❷ Chat with Your Code"):
            chatbot = gr.Chatbot(label="Chat History", height=500, render_markdown=True, bubble_full_width=False)
            msg_input = gr.Textbox(label="Your Question", placeholder="e.g., Explain the 'index_directory' function in app.py", scale=7)
            clear_button = gr.ClearButton([msg_input, chatbot])

            msg_input.submit(
                fn=handle_chat,
                inputs=[msg_input, chatbot],
                outputs=[chatbot]
            )

if __name__ == "__main__":
    demo.launch()