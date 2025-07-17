# mcp_server.py

import os
import subprocess
import traceback
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server with a unique name
mcp = FastMCP("docker-agent-server-v1")

# Define project and app directories
PROJECT_DIR = "project"

@mcp.tool()
def list_project_files() -> str:
    """
    Lists all files in the './project' directory recursively.

    :return: A string containing a list of file paths, one per line.
    """
    try:
        if not os.path.isdir(PROJECT_DIR):
            return f"Error: Directory '{PROJECT_DIR}' not found."
        
        file_list = []
        for root, _, files in os.walk(PROJECT_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
        
        return "\n".join(file_list)
    except Exception as e:
        traceback.print_exc()
        return f"Error listing files: {str(e)}"

@mcp.tool()
def read_project_file(filename: str) -> str:
    """
    Reads the content of a specific file from the './project' directory.

    :param filename: The path to the file to read, relative to the script's location.
    :type filename: str
    :return: The content of the file as a string, or an error message.
    """
    try:
        # Security check to prevent path traversal attacks
        safe_path = os.path.abspath(filename)
        if not safe_path.startswith(os.path.abspath(PROJECT_DIR)):
            return f"Error: Access denied. Can only read files within the '{PROJECT_DIR}' directory."

        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return f"Error: File not found at '{filename}'."
    except Exception as e:
        traceback.print_exc()
        return f"Error reading file '{filename}': {str(e)}"

@mcp.tool()
def save_app_file(filename: str, content: str) -> str:
    """
    Saves content to a file inside the './app' directory.

    :param filename: The name of the file to be saved (e.g., 'Dockerfile').
    :type filename: str
    :param content: The content to write to the file.
    :type content: str
    :return: A confirmation message or an error message.
    """
    try:
        if not os.path.exists(PROJECT_DIR):
            os.makedirs(PROJECT_DIR)
        
        file_path = os.path.join(PROJECT_DIR, filename)
        
        # Security check
        safe_path = os.path.abspath(file_path)
        if not safe_path.startswith(os.path.abspath(PROJECT_DIR)):
             return f"Error: Access denied. Can only write files within the '{PROJECT_DIR}' directory."

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully saved file to '{file_path}'."
    except Exception as e:
        traceback.print_exc()
        return f"Error saving file '{filename}': {str(e)}"

@mcp.tool()
def run_shell_command(command: str) -> str:
    """
    Executes a shell command and returns its output.
    WARNING: This tool can execute any command and is a potential security risk.
    Use with caution in a controlled environment.

    :param command: The shell command to execute.
    :type command: str
    :return: The stdout and stderr from the command execution.
    """
    try:
        print(f"Executing command: {command}")
        # Using shell=True for simplicity, but it's a security risk.
        # In a real product, commands should be parsed and executed without shell=True.
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=False, # Don't raise exception on non-zero exit codes
            cwd=PROJECT_DIR # Run commands from the app directory
        )
        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
        print(output)
        return output
    except Exception as e:
        traceback.print_exc()
        return f"Error executing command '{command}': {str(e)}"

if __name__ == "__main__":
    # Ensure project directory exists for the user
    if not os.path.exists(PROJECT_DIR):
        os.makedirs(PROJECT_DIR)
        # Create a sample Python project for demonstration
        with open(os.path.join(PROJECT_DIR, "requirements.txt"), "w") as f:
            f.write("fastapi\nuvicorn")
        with open(os.path.join(PROJECT_DIR, "main.py"), "w") as f:
            f.write(
                "from fastapi import FastAPI\n\n"
                "app = FastAPI()\n\n"
                "@app.get('/')\n"
                "def read_root():\n"
                "    return {'message': 'Hello from Docker!'}\n"
            )
        print(f"Created a sample FastAPI project in '{PROJECT_DIR}' for you to test.")
        
    mcp.run(transport="stdio")
