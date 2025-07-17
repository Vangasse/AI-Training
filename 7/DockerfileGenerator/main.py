from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools, MultiMCPTools
from dotenv import load_dotenv
from agno.agent import Agent
from textwrap import dedent
import asyncio
import json
import re
import os
import subprocess

from mcp_server import list_project_files, read_project_file

# Import prompts from the dedicated file
from prompts import ANALYSIS_PROMPT, DOCKERFILE_PROMPT, VERIFICATION_PROMPT

# Define project and app directories
PROJECT_DIR = "project"

def print_step(title):
    """Helper function to print formatted step headers."""
    print("\n" + "="*60)
    print(f"## {title}")
    print("="*60 + "\n")

def run_command(command, working_dir):
    """Executes a shell command, prints its output, and checks for errors."""
    print(f"▶️  Running command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_dir,
            check=True,
            encoding='utf-8' 
        )
        print(result.stdout)
        if result.stderr:
            print("--- Stderr ---")
            print(result.stderr)
        print(f"✅ Command successful: {command}\n")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing command: {command}")
        print(e.stdout)
        print(e.stderr)
        raise
    except FileNotFoundError:
        print(f"❌ Command not found: {command.split()[0]}. Is it installed and in your PATH?")
        raise

async def main():
    load_dotenv()

    model = OpenAIChat(id="gpt-4o-mini")

    # --- STEP 1: ANALYZE PROJECT ---
    print_step("STEP 1: ANALYZING PROJECT FILES")
    
    file_list_str = list_project_files()
    file_list = file_list_str.split('\n') if file_list_str else []
    
    if not any(file_list):
        print(f"The '{PROJECT_DIR}' directory is empty. Please add your project files and run again.")
        return

    print(f"Found files: {file_list}")
    
    file_contents = ""
    for filename in file_list:
        if filename:
            content = read_project_file(filename=filename)
            file_contents += f"--- File: {filename} ---\n{content}\n\n"

    analysis_prompt = ANALYSIS_PROMPT.format(file_contents=file_contents)

    async with MultiMCPTools(["python mcp_server.py"]) as mcp_tools:
        agent = Agent(model=model, tools=[mcp_tools])
        analysis_response = await agent.arun(
            analysis_prompt,
            markdown=True,
        )

        analysis_response_str = analysis_response.content

        try:
            # Use a regular expression to find content between ```json and ```
            match = re.search(r"```json\s*([\s\S]+?)\s*```", analysis_response_str)
            
            # If a match is found, parse the extracted group
            if match:
                json_str = match.group(1)
                analysis_json = json.loads(json_str)
            else:
                # Fallback for cases where the response is plain JSON without markdown
                analysis_json = json.loads(analysis_response_str)

            print("Project Analysis Complete:")
            print(json.dumps(analysis_json, indent=2))

        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from analysis response.\nResponse was:\n{analysis_response_str}")
            return

        dockerfile_prompt = DOCKERFILE_PROMPT.format(analysis_json=analysis_json)
        
        dockerfile_response = await agent.arun(
            dockerfile_prompt,
            markdown=True,
        )

        dockerfile_response_str = dockerfile_response.content

        try:
            # Use a regular expression to find content between ```json and ```
            match = re.search(r"```json\s*([\s\S]+?)\s*```", dockerfile_response_str)
            
            # If a match is found, parse the extracted group
            if match:
                json_str = match.group(1)
                dockerfile_json = json.loads(json_str)
            else:
                # Fallback for cases where the response is plain JSON without markdown
                dockerfile_json = json.loads(dockerfile_response_str)

            print("Project Analysis Complete:")
                    
            print(json.dumps(dockerfile_json, indent=2))
        
            # Get the content from the JSON
            dockerfile_content = dockerfile_json.get("dockerfile")
            docker_compose_content = dockerfile_json.get("docker_compose_yml")

            # Save the Dockerfile
            if dockerfile_content:
                with open(os.path.join(PROJECT_DIR, "Dockerfile"), "w") as f:
                    f.write(dockerfile_content)
                print(f"Successfully saved Dockerfile to {os.path.join(PROJECT_DIR, 'Dockerfile')}")

            # Save the docker-compose.yml
            if docker_compose_content:
                with open(os.path.join(PROJECT_DIR, "docker-compose.yml"), "w") as f:
                    f.write(docker_compose_content)
                print(f"Successfully saved docker-compose.yml to {os.path.join(PROJECT_DIR, 'docker-compose.yml')}")

        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from analysis response.\nResponse was:\n{analysis_response_str}")
            return

        try:

            # Hard-code the standard build and run commands
            run_command(f"docker-compose build", working_dir=PROJECT_DIR)
            run_command(f"docker-compose up", working_dir=PROJECT_DIR)

            verification_prompt = VERIFICATION_PROMPT.format(
                analysis_json=json.dumps(analysis_json, indent=2),
                docker_compose_yml=docker_compose_content
            )

            verification_response = await agent.arun(
                verification_prompt,
                markdown=True,
            )
            
            # The verification command is the direct content of the response
            verification_command = verification_response.content.strip()

            # Run the verification command provided by the LLM
            run_command(verification_command, working_dir=PROJECT_DIR)

            print("\n🎉 Verification successful! The container is running correctly.")
        except (subprocess.CalledProcessError, ValueError) as e:
            print(f"\n❌ A critical error occurred during deployment or verification.")
        finally:
            # This will run whether the try block succeeds or fails
            print_step("STEP 5: CLEANING UP")
            run_command(f"docker-compose down", working_dir=PROJECT_DIR)
        

if __name__ == "__main__":
    asyncio.run(main())