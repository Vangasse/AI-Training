import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# --- Upload Logic (from previous step, no changes) ---
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

# --- CORRECTED Chat Logic ---
def handle_chat(message: str, history: list):
    """
    Handles chat interaction. It updates the history with the user's message first,
    then gets the bot's response and updates the history again.
    """
    # Append the user's message to the history with a placeholder for the bot
    history.append([message, None])
    # Yield the updated history to show the user's message immediately
    yield history

    # Call the backend to get the bot's response
    try:
        response = requests.post(f"{BACKEND_URL}/chat", json={"query": message})
        response.raise_for_status()
        data = response.json()
        
        answer = data.get("answer", "Sorry, I encountered an error.")
        sources = data.get("sources", [])

        # Format sources for display
        if sources:
            sources_text = "\n\n---\n\n**Sources Used:**\n" + "\n".join(f"- `{s}`" for s in sources)
            answer += sources_text
        
        # Update the last entry in history with the bot's actual response
        history[-1][1] = answer

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
            chatbot = gr.Chatbot(label="Chat History", height=500)
            msg_input = gr.Textbox(label="Your Question", placeholder="e.g., What are the main findings of the report?")
            clear_button = gr.ClearButton([msg_input, chatbot])

            # The .submit() event now correctly points to the updated handle_chat function
            msg_input.submit(
                fn=handle_chat,
                inputs=[msg_input, chatbot],
                outputs=[chatbot]
            )

if __name__ == "__main__":
    demo.launch()