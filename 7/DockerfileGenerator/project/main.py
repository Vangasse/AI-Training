from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools, MultiMCPTools
from dotenv import load_dotenv
from agno.agent import Agent
from textwrap import dedent
import asyncio


async def main():
    load_dotenv()

    QUERY = dedent(
        """
    Some o espaço disponível de todos os discos e me retorne o resultado em GB, garanta que a soma está correta.
    Além disso, quais os processos que estão consumindo mais RAM?
    Use as funções disponíveis.
    """
    )
    model = OpenAIChat(id="gpt-4o-mini")

    async with MultiMCPTools(["python mcp_server.py"]) as mcp_tools:
        agent = Agent(model=model, tools=[mcp_tools])
        await agent.aprint_response(
            QUERY,
            stream=True,
            markdown=True,
        )
        pass


if __name__ == "__main__":
    asyncio.run(main())