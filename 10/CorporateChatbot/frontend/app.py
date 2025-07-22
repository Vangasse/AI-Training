import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# --- Upload Logic (no changes) ---
def upload_document(file):
    if file is None:
        return "⚠️ Please select a file first."
    try:
        files = {'file': open(file.name, 'rb')}
        response = requests.post(f"{BACKEND_URL}/upload", files=files)
        response.raise_for_status()
        return response.json().get("message", "✅ File uploaded successfully!")
    except requests.exceptions.RequestException as e:
        return f"🔥 Error connecting to the backend: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

# --- UPDATED Chat Logic ---
def handle_chat(message: str, history: list):
    """
    Handles chat interaction. It updates the history with the user's message,
    gets the bot's response, formats it with source chunks, and updates the history again.
    """
    history.append([message, None])
    yield history

    try:
        response = requests.post(f"{BACKEND_URL}/chat", json={"query": message})
        response.raise_for_status()
        data = response.json()
        
        answer = data.get("answer", "Sorry, I encountered an error.")
        sources = data.get("sources", []) # This is now a list of source objects

        # Start building the final response string with the main answer
        final_response = answer

        # If sources are available, format them into a collapsible section
        if sources:
            # Use HTML <details> and <summary> tags for a collapsible accordion
            sources_details = "\n\n---\n\n<details><summary><strong>Click to see sources</strong></summary>\n\n"
            for i, source in enumerate(sources):
                # Add the filename for each source chunk
                sources_details += f"**Source {i+1}: `{source['filename']}`**\n"
                # Format the text chunk as a blockquote
                sources_details += f"> {source['text'].replace('\n', '\n> ')}\n\n"
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
    gr.Markdown("# Corporate Chatbot with RAG")
    gr.Markdown("Upload documents and ask questions about their content.")

    with gr.Tabs():
        # --- Upload Tab ---
        with gr.TabItem("⬆️ Upload Documents"):
            with gr.Column():
                file_input = gr.File(label="Upload Your Document", file_types=[".txt", ".md", ".pdf"])
                upload_button = gr.Button("Upload File", variant="primary")
                upload_status = gr.Textbox(label="Upload Status", interactive=False)
            
            upload_button.click(
                fn=upload_document,
                inputs=[file_input],
                outputs=[upload_status]
            )

        # --- Chat Tab ---
        with gr.TabItem("💬 Chat"):
            chatbot = gr.Chatbot(label="Chat History", height=500, render_markdown=True)
            msg_input = gr.Textbox(label="Your Question", placeholder="e.g., What are the main findings of the report?")
            clear_button = gr.ClearButton([msg_input, chatbot])

            msg_input.submit(
                fn=handle_chat,
                inputs=[msg_input, chatbot],
                outputs=[chatbot]
            )

if __name__ == "__main__":
    demo.launch()
