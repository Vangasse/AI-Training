# prompts.py

# Prompt for the first agent: Analyze the project files.
# It asks the LLM to act as an expert and return a structured JSON output,
# which is crucial for reliably passing information to the next agent.
# prompts.py

# ... (keep other prompts the same)

ANALYSIS_PROMPT = """
You are an expert software developer specializing in dependency analysis and project containerization.
Your task is to analyze the following project files to identify the programming language, web framework, 
application port, dependencies, and the exact command needed to run the application.

Please analyze the content of the files provided below:
---
{file_contents}
---

To determine the `run_command`, follow these steps carefully:
1.  **Identify the Entry Point File**: Look for the main application file. Prioritize files in this order: `main.py`, `app.py`, `server.py`, `index.js`.
2.  **Find the Application Instance**: Within the most likely entry point file, locate the application instantiation (e.g., `app = FastAPI()`, `app = Flask(__name__)`).
3.  **Locate the Run Logic**: Find the code that runs the application, such as a call to `uvicorn.run()`, `app.run()`, or code within an `if __name__ == "__main__":` block.
4.  **Construct the Command**: Create the shell command needed to execute that specific file and run logic. For example, if the entry point is `main.py` and it contains a FastAPI app instance named `app`, the command should be `uvicorn main:app --host 0.0.0.0 --port 8000`.

Based on your analysis, provide the output in a structured JSON format. The JSON object must have the following keys:
- "language": The primary programming language (e.g., "python", "nodejs").
- "framework": The web framework used, if any (e.g., "FastAPI", "Express").
- "port": The port the application is expected to run on. Default to 8000 if not specified.
- "dependencies": A list of package managers or dependency files found (e.g., ["requirements.txt", "package.json"]).
- "run_command": The precise, executable shell command required to start the application.

Example response:
{{
  "language": "python",
  "framework": "FastAPI",
  "port": 8000,
  "dependencies": ["requirements.txt"],
  "run_command": "uvicorn main:app --host 0.0.0.0 --port 8000"
}}
"""

# Prompt for the second agent: Generate Docker files.
# It takes the structured JSON from the first agent as input.
DOCKERFILE_PROMPT = """
You are a DevOps expert specializing in creating optimized and secure Dockerfiles and docker-compose configurations.
Based on the following project analysis, generate a `Dockerfile` and a `docker-compose.yml` file. 
Use the available functions of the MCP (Multi-Container Platform) to ensure the Dockerfile and docker-compose.yml are executable.

Project Analysis:
---
{analysis_json}
---

Follow these best practices:
1.  Use a specific, official base image (e.g., `python:3.11-slim`).
2.  Use a multi-stage build in the Dockerfile if it helps to reduce the final image size.
3.  Copy only necessary files into the container.
4.  The `docker-compose.yml` should build from the local Dockerfile and map the application port correctly.
5.  Ensure the `run_command` from the analysis is used in the `CMD` instruction of the Dockerfile.

Provide the output as a single JSON object with two keys: "dockerfile" and "docker_compose_yml".

Example response:
{{
  "dockerfile": "FROM python:3.11-slim\\nWORKDIR /app\\nCOPY requirements.txt .\\nRUN pip install --no-cache-dir -r requirements.txt\\nCOPY . .\\nEXPOSE 8000\\nCMD [\\"uvicorn\\", \\"main:app\\", \\"--host\\", \\"0.0.0.0\\", \\"--port\\", \\"8000\\"]",
  "docker_compose_yml": "version: '3.8'\\nservices:\\n  app:\\n    build: .\\n    ports:\\n      - '8000:8000'\\n    volumes:\\n      - ./project:/app"
}}
"""

# Prompt for the third agent: Plan the verification step.
# It asks for a single, executable command to verify the running container.
VERIFICATION_PROMPT = """
You are a Quality Assurance engineer responsible for verifying application deployments.
An application has been started inside a Docker container using the provided `docker-compose.yml`.

Based on the project analysis and the Docker configuration below, what is the single best shell command to verify that the application is running correctly?

Project Analysis:
---
{analysis_json}
---

Docker Compose content:
---
{docker_compose_yml}
---

For a web service, this should typically be a `curl` command to the exposed port.
For other applications, it might be a `docker logs` command.
Respond ONLY with the single, executable shell command and nothing else.

Example response:
curl http://localhost:8000
"""
