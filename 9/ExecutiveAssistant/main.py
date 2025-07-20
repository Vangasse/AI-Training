from textwrap import dedent
from docling.document_converter import DocumentConverter
from semantic_text_splitter import TextSplitter
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.vectordb.qdrant import Qdrant
from qdrant_client.http import models
from agno.document import Document
from dotenv import load_dotenv
from agno.agent import Agent
import os

# Import both prompts from your prompts file
from prompts import SYSTEM_PROMPT_EXTRACTION, SYSTEM_PROMPT_FACT_CHECKING


def create_qdrant_table(
    table_name: str, embedder: OpenAIEmbedder, vector_db: Qdrant
) -> None:
    """
    Creates a Qdrant collection named 'ExecutiveAssistant' if it doesn't already exist.

    :param table_name: The name of the table to create.
    :type table_name: str
    :param embedder: The embedder instance used to get vector dimensions.
    :type embedder: OpenAIEmbedder
    :param vector_db: The Qdrant vector database instance.
    :type vector_db: Qdrant
    """
    collections_response = vector_db.client.get_collections()
    collection_names = [c.name for c in collections_response.collections]

    if table_name not in collection_names:
        vector_db.client.create_collection(
            collection_name=table_name,
            vectors_config=models.VectorParams(
                size=embedder.dimensions, distance=models.Distance.COSINE
            ),
        )


if __name__ == "__main__":
    load_dotenv()

    INSERT_CHUNKS = True
    WITH_CONTEXT = True

    # We will test with a query that mixes internal data with a public fact.
    QUERY = "What was decided about Project Chimera and what was the competitive threat mentioned by Marcus Thorne?"

    embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    vector_db = Qdrant(
        collection="ExecutiveAssistant", url="http://localhost:6333", embedder=embedder
    )

    converter = DocumentConverter()
    splitter = TextSplitter(1000, 200)

    if INSERT_CHUNKS:
        create_qdrant_table("ExecutiveAssistant", embedder, vector_db)

        result = converter.convert("minute.md")
        chunks = splitter.chunks(result.document.export_to_markdown())
        docs = [Document(content=chunk) for chunk in chunks]
        vector_db.insert(docs)

    # --- Step 1: Minute Extraction Agent ---
    if WITH_CONTEXT:
        # FIX 1: Increased the number of retrieved chunks from 3 to 5.
        # This provides a wider context to the agent, making it more likely
        # to find information for both parts of a complex query.
        context_chunks = [frag.content for frag in vector_db.search(QUERY, 5)]
        context = " - " + "\n - ".join(context_chunks)
    else:
        context = ""

    # Prepare the prompt for the first agent
    final_extraction_prompt = SYSTEM_PROMPT_EXTRACTION.format(context=context)

    agent_minute_extraction = Agent(
        show_tool_calls=True,
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=final_extraction_prompt),
        search_knowledge=False,
    )

    print("--- 1. Minute Extraction Result ---")
    extraction_response = agent_minute_extraction.run(QUERY)
    # Ensure we print the string content for clarity
    print(extraction_response.content)
    print("\n" + "="*40 + "\n")


    # --- Step 2: Fact-Checking Agent ---
    print("--- 2. Fact-Checking Result ---")

    agent_fact_checking = Agent(
        show_tool_calls=True,
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=SYSTEM_PROMPT_FACT_CHECKING),
        search_knowledge=True,
    )

    # FIX 2: Pass the .content attribute of the response object, not the object itself.
    # The agent's input query must be a string.
    agent_fact_checking.print_response(extraction_response.content, markdown=True)