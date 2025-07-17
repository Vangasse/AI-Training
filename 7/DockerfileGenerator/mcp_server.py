# mcp_server.py

import os
import subprocess
import asyncio # <<< Import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docker-agent-server-v1")
PROJECT_DIR = "project"

# ... (other tools like list_project_files, read_project_file, create_docker_artifacts remain the same) ...
@mcp.tool()
def list_project_files() -> str:
    """Lists all files in the './project' directory recursively."""
    try:
        if not os.path.isdir(PROJECT_DIR): return f"Error: Directory '{PROJECT_DIR}' not found."
        file_list = [os.path.join(root, file) for root, _, files in os.walk(PROJECT_DIR) for file in files]
        return "\n".join(file_list) if file_list else "No files found in the project directory."
    except Exception as e: return f"Error listing files: {str(e)}"

def _get_safe_project_path(filename: str) -> str:
    """Ensures the file path is safely within the PROJECT_DIR."""
    clean_filename = os.path.basename(filename)
    return os.path.join(PROJECT_DIR, clean_filename)

@mcp.tool()
def read_project_file(filename: str) -> str:
    """Reads a file from the './project' directory. Handles path automatically."""
    try:
        safe_path = _get_safe_project_path(filename)
        with open(safe_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except FileNotFoundError: return f"Error: File not found at '{filename}'."
    except Exception as e: return f"Error reading file '{filename}': {str(e)}"

@mcp.tool()
def create_docker_artifacts(dockerfile_content: str, compose_content: str) -> str:
    """Saves both the Dockerfile and docker-compose.yml files to the project directory in a single, atomic step."""
    try:
        dockerfile_path = _get_safe_project_path("Dockerfile")
        with open(dockerfile_path, 'w', encoding='utf-8') as f: f.write(dockerfile_content)
        compose_path = _get_safe_project_path("docker-compose.yml")
        with open(compose_path, 'w', encoding='utf-8') as f: f.write(compose_content)
        return "Successfully created both Dockerfile and docker-compose.yml."
    except Exception as e: return f"Error creating artifacts: {str(e)}"


# <<< THE DEFINITIVE FIX: Making the tool asynchronous >>>
@mcp.tool()
async def run_shell_command(command: str) -> str:
    """Executes a shell command asynchronously inside the './project' directory."""
    try:
        # Use asyncio's non-blocking way to run a shell command
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_DIR
        )

        # Wait for the command to finish and get the output
        stdout, stderr = await proc.communicate()

        return f"STDOUT:\n{stdout.decode()}\n\nSTDERR:\n{stderr.decode()}"
    except Exception as e:
        return f"Error executing command '{command}': {str(e)}"


if __name__ == "__main__":
    if not os.path.exists(PROJECT_DIR):
        os.makedirs(PROJECT_DIR)
        with open(os.path.join(PROJECT_DIR, "requirements.txt"), "w") as f: f.write("fastapi\nuvicorn")
        with open(os.path.join(PROJECT_DIR, "main.py"), "w") as f:
            f.write(
                "from fastapi import FastAPI\n\napp = FastAPI()\n\n"
                "@app.get('/')\ndef read_root():\n    return {'message': 'Hello from Docker!'}\n"
            )
        print(f"Created a sample FastAPI project in '{PROJECT_DIR}' for you to test.")
    mcp.run()