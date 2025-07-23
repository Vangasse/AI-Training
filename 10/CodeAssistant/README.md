# 🤖 AI Code Review Assistant

This project is an AI-powered code assistant that helps developers improve their codebase. Users can index an entire code repository into a vector database and then ask for specific improvements, such as refactoring for clarity, checking for performance issues, or identifying potential bugs.

The application uses a two-agent AI system built on top of a RAG (Retrieval-Augmented Generation) pipeline:

1.  **Filter Agent**: Retrieves the most relevant code chunks from the database based on the user's request.
2.  **Code Improvement Agent**: Analyzes the filtered code and generates a structured list of concrete suggestions, including the file to modify, an explanation of the change, and the new code to implement.

## ✨ Features

-   **Directory Indexing**: Process an entire folder of code, supporting a wide range of programming languages.
-   **Vector-Based Retrieval**: Uses Qdrant as a vector database to find the most relevant code snippets for any given query.
-   **AI-Powered Suggestions**: Leverages Large Language Models (like GPT-4o mini) to provide intelligent and context-aware code improvements.
-   **Structured Output**: Presents suggestions in a clear, organized report, grouped by file.
-   **Interactive UI**: A simple and intuitive web interface built with Gradio for easy interaction.

## 📂 Project Structure

The project is divided into two main components:

```
/
├── backend/
│   ├── main.py         # FastAPI server, API endpoints, and RAG logic
│   ├── prompts.py      # System prompts for the AI agents
│   └── requirements.txt  # Python dependencies for the backend
│
├── frontend/
│   ├── app.py          # Gradio user interface
│   └── requirements.txt  # Python dependencies for the frontend
│
├── qdrant/
│   └── docker-compose.yml # Docker configuration for Qdrant
│
└── .env                # Environment variables (you will create this)
└── README.md           # This file
```

## ✅ Prerequisites

Before you begin, ensure you have the following installed:

-   **Docker** and **Docker Compose**: To run the Qdrant vector database.
-   **Python 3.9+**: For running the backend and frontend applications.
-   **OpenAI API Key**: You need an API key from OpenAI to use their language models.

## 🚀 Setup and Running the Application

Follow these steps to get the application running locally.

### 1. Start the Qdrant Database

The vector database runs in a Docker container.

```bash
# Navigate to the qdrant directory
cd qdrant

# Start the container in detached mode
docker compose up --build -d
```

This will download the Qdrant image and start the service. It will be accessible at `http://localhost:6333`.

### 2. Set Up the Python Environment

It is highly recommended to use a virtual environment for each component.

```bash
# From the project root, set up the backend environment
python -m venv backend/venv
source backend/venv/bin/activate  # On Windows, use `backend\venv\Scripts\activate`
pip install -r backend/requirements.txt

# Set up the frontend environment in a separate terminal
python -m venv frontend/venv
source frontend/venv/bin/activate # On Windows, use `frontend\venv\Scripts\activate`
pip install -r frontend/requirements.txt
```

### 3. Configure Environment Variables

Create a file named `.env` in the root of the project directory. Add your OpenAI API key to this file.

```ini
# .env
OPENAI_API_KEY="sk-YourSecretOpenAI_ApiKeyHere"
```

The application is configured to automatically load this variable.

### 4. Run the Backend Server

In your first terminal (with the backend environment activated), start the FastAPI server.

```bash
# Navigate to the backend directory
cd backend

# Run the uvicorn server
python main.py
```

The backend API will now be running at `http://localhost:8000`.

### 5. Run the Frontend Application

In your second terminal (with the frontend environment activated), start the Gradio UI.

```bash
# Navigate to the frontend directory
cd frontend

# Run the Gradio app
python app.py
```

The user interface will be accessible at `http://localhost:7860` (or another port if 7860 is busy).

## 🛠️ How to Use

1.  **Open the UI**: Navigate to the Gradio URL provided in your terminal (e.g., `http://localhost:7860`).
2.  **Index Your Code**:
    -   Go to the **"❶ Index Directory"** tab.
    -   Click the upload area and select the folder containing the code you want to analyze.
    -   Click the **"Index Directory"** button and wait for the confirmation message.
3.  **Get Suggestions**:
    -   Go to the **"❷ Get Suggestions"** tab.
    -   In the text box, type your request for code improvement. Be specific for better results.
    -   Press Enter or click Submit.
    -   The assistant will analyze the relevant files and generate a report with its suggestions.

### Example Requests

-   "Review the API endpoints in `backend/main.py` for potential bugs or performance issues."
-   "Can you refactor the `handle_chat` function in `frontend/app.py` to make it more readable?"
-   "Check for any style violations or suggest improvements for the helper functions."
