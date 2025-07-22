# Corporate Chatbot with RAG

This project is a fully functional web application that implements a Retrieval-Augmented Generation (RAG) system. It allows users to upload their own documents (`.pdf`, `.txt`, `.md`) and then ask questions about the content. The application uses a vector database (Qdrant) to store document embeddings and leverages OpenAI's language models to provide accurate, context-aware answers with source citations.

## Features

* **Document Upload**: Simple interface to upload `.pdf`, `.txt`, and `.md` files.
* **Automatic Indexing**: Uploaded documents are automatically processed, chunked, embedded, and indexed into a Qdrant vector database.
* **RAG-Powered Chat**: An interactive chat interface to ask questions about the uploaded content.
* **Source Citation**: The chatbot's answers include references to the original source documents used to generate the response.
* **Separated Frontend/Backend**: A robust architecture with a Gradio-based frontend and a FastAPI backend.
* **Easy Setup**: Utilizes Docker for the vector database and standard Python libraries for the application logic.

## Project Structure

The project is organized into distinct components for clarity and maintainability:

```
corporate-chatbot/
├── backend/
│   ├── uploads/          # Temporarily stores uploaded files
│   ├── main.py           # FastAPI backend logic
│   └── prompts.py        # Prompts for the LLM agent
├── frontend/
│   └── app.py            # Gradio frontend UI and logic
├── qdrant/
│   └── docker-compose.yml # Docker configuration for Qdrant
├── .env                  # Environment variables (API keys, URLs)
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Prerequisites

Before you begin, ensure you have the following installed on your system:

* **Python 3.8+**
* **Docker** and **Docker Compose**
* An **OpenAI API Key**

## Setup and Installation

Follow these steps to get the application up and running.

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone <your-repository-url>
cd corporate-chatbot
```

### 2. Run the Qdrant Vector Database

The Qdrant vector database runs in a Docker container. To start it, navigate to the `qdrant` directory and use Docker Compose.

```bash
# Navigate to the qdrant folder
cd qdrant

# Build and run the container in detached mode
docker compose up --build -d
```

This command will download the Qdrant image and start the database service in the background. You can verify it's running by visiting `http://localhost:6333` in your browser.

### 3. Configure Environment Variables

Create a `.env` file in the root directory of the project. Copy the contents of `.env.example` (if provided) or create it from scratch.

```
# .env

# Backend Configuration
BACKEND_URL="[http://127.0.0.1:8000](http://127.0.0.1:8000)"

# OpenAI API Key
OPENAI_API_KEY="sk-..."

# Qdrant Configuration
QDRANT_URL="http://localhost:6333"
```

**Important**: Replace `"sk-..."` with your actual OpenAI API key.

### 4. Install Python Dependencies

Install all the required Python libraries using the `requirements.txt` file. It's highly recommended to do this within a virtual environment.

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install dependencies from the root directory
pip install -r requirements.txt
```

## How to Run the Application

The application requires two separate terminal sessions: one for the backend and one for the frontend.

### Terminal 1: Start the Backend

Navigate to the `backend` directory and start the FastAPI server using Uvicorn.

```bash
cd backend
uvicorn main:app --reload
```

The `--reload` flag automatically restarts the server when you make changes to the code.

### Terminal 2: Start the Frontend

Navigate to the `frontend` directory and run the Gradio application.

```bash
cd frontend
python app.py
```

After running this command, your terminal will display a local URL (usually `http://127.0.0.1:7860`). Open this URL in your web browser to use the application.

## How to Use the Application

1.  **Upload Documents**: Open the application in your browser and navigate to the **⬆️ Upload Documents** tab. Select a `.pdf`, `.txt`, or `.md` file and click "Upload File". You will see a status message confirming the upload and indexing.
2.  **Chat with Your Documents**: Switch to the **💬 Chat** tab. Type your question into the input box and press Enter. The chatbot will generate an answer based on the content of the documents you uploaded and will cite its sources.

## Technologies Used

* **Backend**: FastAPI, Uvicorn
* **Frontend**: Gradio
* **Vector Database**: Qdrant
* **LLM & Embeddings**: OpenAI (GPT-4o-mini, text-embedding-3-small)
* **Document Processing**: PyMuPDF, semantic-text-splitter
