# AI Guardrail Service

This project demonstrates a simple but effective AI-powered guardrail service designed to inspect and sanitize text in real-time. It identifies and redacts Personally Identifiable Information (PII) and offensive content from user inputs and LLM outputs, making AI applications safer and more compliant.

The service is built with a decoupled client-server architecture, making it scalable and easy to integrate into existing systems.

## Key Features

* **PII Redaction**: Detects and masks names, emails, phone numbers, addresses, and more.
* **Offensive Content Filtering**: Identifies and redacts hate speech, threats, and other inappropriate language.
* **Structured JSON Output**: Returns a predictable JSON object with a boolean flag (`issues_found`) and the sanitized text.
* **Scalable Architecture**: Built as a FastAPI backend service, ready to be deployed and consumed by multiple applications.
* **Customizable**: Easily adapt the detection rules by modifying the core system prompt.

## How It Works

The service leverages a large language model (LLM) as its core inspection engine.

1.  The client sends raw text to the `/inspect` API endpoint.
2.  The backend service wraps the text inside a detailed **System Prompt**. This prompt instructs the LLM to act as a guardrail, defining exactly what to look for and how to format the response.
3.  The request is sent to the OpenAI API, which processes the text according to the prompt's rules.
4.  The LLM returns a clean, structured JSON object containing its analysis.
5.  The backend service forwards this JSON response directly to the client.

## Architecture

The application is split into two main components:

1.  **Backend Service (`guardrail_service/`)**: A high-performance API built with **FastAPI**. It exposes a single endpoint (`/inspect`) that receives text, uses an OpenAI model to perform the analysis, and returns a structured JSON response.
2.  **Client Application (`main.py`)**: A simple Python script that simulates an application consuming the guardrail service. It sends sample text to the backend API and prints the results.

## How to Run the Demonstration

Follow these steps to set up and run the project on your local machine.

### 1. Prerequisites

* Python 3.8+ (which includes `pip` for package management).
* An OpenAI API Key.

### 2. Setup

**a. Create a Project Structure**

Organize your files as follows. You will also create the `requirements.txt` file in a later step.

```
.
├── guardrail_service/
│   ├── backend.py
│   └── prompts.py
├── main.py
├── requirements.txt
└── .env
```

**b. Create the Environment File**

Create a file named `.env` in the root directory. This file will securely store your OpenAI API key.

```
OPENAI_API_KEY="sk-..."
```

Replace `sk-...` with your actual OpenAI API key.

**c. Set Up a Virtual Environment**

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python -m venv venv
# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

**d. Install Dependencies**

First, create a requirements.txt file in the project's root directory with the following content:

```plaintext

# requirements.txt
fastapi
uvicorn
python-dotenv
openai
requests
```

Now, install these dependencies using the file.
```bash
pip install -r requirements.txt
```

### 3. Running the Application
You will need to run the backend service and the client application in two separate terminal windows.

**a. Terminal 1: Start the Backend Service**

In your first terminal (with the virtual environment active), run the FastAPI application using Uvicorn.

```bash

# Make sure your virtual environment is active
uvicorn guardrail_service.backend:app --reload
```

You should see output indicating that the server is running on http://127.0.0.1:8000.

**b. Terminal 2: Run the Client Application**

In a second terminal (with the virtual environment also activated), run the main.py client script.


```bash
# Make sure your virtual environment is active
python main.py
```

## Expected Results
The client script will call the backend service twice. The output in your second terminal should look exactly like this:

```
--- Calling Guardrail Service for Content ---
'Hello, my name is Jane Doe and I live at 123 AI Lane, Techville. My email is jane.doe@email.com, and my phone is (555) 123-9876. Please help me with my issue.'

--- User Query Inspection Result ---
{
  "issues_found": true,
  "redacted_text": "Hello, my name is [REDACTED] and I live at [REDACTED]. My email is [REDACTED], and my phone is [REDACTED]. Please help me with my issue."
}

==================================================

--- Calling Guardrail Service for Content ---
'You are being unhelpful and I am getting very angry. This is a final warning.'

--- LLM Output Inspection Result ---
{
  "issues_found": true,
  "redacted_text": "You are being unhelpful and I am getting very angry. [REDACTED]"
}
```

## Customization
The easiest way to customize the guardrail is by editing the PROMPT_GUARDRAIL variable in guardrail_service/prompts.py.

To detect new types of information: Add a new item to the list under the <Task> tag. For example, to detect financial account numbers, you could add "3. Financial Information: Bank account numbers, routing numbers, etc."

To change the redaction placeholder: Modify the guideline in the prompt that specifies [REDACTED]. You could change it to [CENSORED] or any other placeholder.