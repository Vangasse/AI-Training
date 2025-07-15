from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools, MultiMCPTools
from dotenv import load_dotenv
from agno.agent import Agent
from textwrap import dedent
import asyncio
import json

from mcp_server import list_project_files, read_project_file

# Import prompts from the dedicated file
from prompts import ANALYSIS_PROMPT, DOCKERFILE_PROMPT, VERIFICATION_PROMPT

# Define project and app directories
PROJECT_DIR = "project"
APP_DIR = "app"

def print_step(title):
    """Helper function to print formatted step headers."""
    print("\n" + "="*60)
    print(f"## {title}")
    print("="*60 + "\n")

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
            if analysis_response_str.strip().startswith("```json"):
                analysis_response_str = analysis_response_str.strip()[7:-4]
            analysis_json = json.loads(analysis_response_str)
            print("Project Analysis Complete:")
            print(json.dumps(analysis_json, indent=2))
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from analysis response.\nResponse was:\n{analysis_response_str}")
            return
        
        exit()
        
        await agent.aprint_response(
            DOCKERFILE_PROMPT,
            stream=True,
            markdown=True,
        )

if __name__ == "__main__":
    asyncio.run(main())