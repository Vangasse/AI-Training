# frontend/app.py

import os
import gradio as gr
import requests
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def index_directory(files):
    # This function remains the same
    if not files: return "⚠️ Please select a directory first."
    try:
        file_tuples = [("files", (os.path.basename(f.name), open(f.name, 'rb'))) for f in files]
        response = requests.post(f"{BACKEND_URL}/index-directory", files=file_tuples)
        response.raise_for_status()
        data = response.json()
        status_report = (f"✅ **{data.get('message')}**\n- **Files Processed**: {data.get('total_files_processed')}\n- **Chunks Created**: {data.get('total_chunks_inserted')}")
        if errors := data.get("errors"): status_report += f"\n- **Errors**: {len(errors)}"
        return status_report
    except requests.exceptions.RequestException as e: return f"🔥 Error connecting to backend: {e}"
    except Exception as e: return f"An unexpected error occurred: {e}"

def handle_chat(message: str, history: list):
    history.append([message, None])
    yield history

    try:
        response = requests.post(f"{BACKEND_URL}/chat", json={"query": message})
        response.raise_for_status()
        data = response.json()
        
        suggestions = data.get("suggestions", [])

        if not suggestions:
            final_response = "✅ No specific improvements were suggested. The code seems to be in good shape regarding your request!"
        else:
            # Group suggestions by file
            suggestions_by_file = defaultdict(list)
            for s in suggestions:
                suggestions_by_file[s['file_name']].append(s)

            # Format the response as a markdown report
            final_response = "Here are the suggested improvements for your codebase:\n\n---\n"
            # CORRECTED: Removed the stray hyphen from "-sug_list"
            for file_name, sug_list in suggestions_by_file.items():
                final_response += f"\n\n### 📄 Suggestions for `{file_name}`\n\n"
                for i, sug in enumerate(sug_list, 1):
                    final_response += f"**Suggestion {i}:**\n"
                    final_response += f"{sug['explanation']}\n\n"
                    final_response += f"**Suggested Code:**\n"
                    final_response += f"```python\n{sug['suggested_code']}\n```\n\n"
                final_response += "---\n"

        history[-1][1] = final_response

    except requests.RequestException as e:
        history[-1][1] = f"🔥 Error connecting to the backend: {e}"
    except Exception as e:
        history[-1][1] = f"An unexpected error occurred: {e}"

    yield history

# The Gradio Interface layout remains the same
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 AI Code Review Assistant")
    gr.Markdown("Index a code repository and ask for refactoring or improvement suggestions.")

    with gr.Tabs():
        with gr.TabItem("❶ Index Directory"):
            with gr.Column():
                file_input = gr.File(label="Upload Your Code Directory", file_count="directory")
                index_button = gr.Button("Index Directory", variant="primary")
                index_status = gr.Markdown(label="Indexing Status")
            index_button.click(fn=index_directory, inputs=[file_input], outputs=[index_status])

        with gr.TabItem("❷ Get Suggestions"):
            chatbot = gr.Chatbot(label="Suggestion Report", height=600, render_markdown=True, bubble_full_width=False)
            msg_input = gr.Textbox(label="Your Request", placeholder="e.g., 'Refactor the database logic for clarity' or 'Are there any performance issues in the API endpoints?'")
            clear_button = gr.ClearButton([msg_input, chatbot])
            msg_input.submit(fn=handle_chat, inputs=[msg_input, chatbot], outputs=[chatbot])

if __name__ == "__main__":
    demo.launch()