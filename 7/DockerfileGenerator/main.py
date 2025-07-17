# main.py

from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from dotenv import load_dotenv
from agno.agent import Agent
import asyncio

from prompts import AUTONOMOUS_DOCKER_AGENT_PROMPT

async def main():
    """
    Initializes and runs the autonomous DevOps agent.
    """
    load_dotenv()

    print("\n" + "="*60)
    print("## AUTONOMOUS DOCKER AGENT INITIALIZED")
    print("="*60 + "\n")

    user_query = "Please containerize the application in the './project' directory. Follow your plan."
    model = OpenAIChat(id="gpt-4o-mini")

    async with MCPTools(command="python mcp_server.py") as mcp_tools:
        # <<< REVERTED: Removing the incorrect mcp_options argument
        agent = Agent(
            model=model,
            tools=[mcp_tools]
        )

        await agent.aprint_response(
            user_query,
            system_prompt=AUTONOMOUS_DOCKER_AGENT_PROMPT,
            stream=True,
            markdown=True,
        )

    print("\n" + "="*60)
    print("## AGENT MISSION COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())