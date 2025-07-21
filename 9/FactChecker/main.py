import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.document import Document
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.vectordb.qdrant import Qdrant
from docling.document_converter import DocumentConverter
from qdrant_client.http import models
from semantic_text_splitter import TextSplitter
from agno.tools.bravesearch import BraveSearchTools

# Import all the prompts from our prompts file
from prompts import (
    PROMPT_QDRANT_CONSULTANT,
    PROMPT_URL_COLLECTOR,
    PROMPT_URL_READER,
    PROMPT_SYNTHESIZER,
)


def create_qdrant_table(
    table_name: str, embedder: OpenAIEmbedder, vector_db: Qdrant
) -> None:
    """Creates a Qdrant collection if it doesn't already exist."""
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

    # --- CONFIGURATION ---
    # Set to True on the first run to ingest the document.
    INSERT_CHUNKS = False
    QDRANT_COLLECTION = "FactCheckerDB"
    QUERY = "What does the memo say about Apple's Project Titan?"

    # --- INITIALIZATION ---
    embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    vector_db = Qdrant(
        collection=QDRANT_COLLECTION, url="http://localhost:6333", embedder=embedder
    )
    converter = DocumentConverter()
    splitter = TextSplitter(1000, 200)

    # --- DATA INGESTION (Run once) ---
    if INSERT_CHUNKS:
        print(f"Creating Qdrant table '{QDRANT_COLLECTION}'...")
        create_qdrant_table(QDRANT_COLLECTION, embedder, vector_db)

        print("Converting and chunking documents.md...")
        result = converter.convert("documents.md")
        chunks = splitter.chunks(result.document.export_to_markdown())
        docs = [Document(content=chunk) for chunk in chunks]

        print(f"Inserting {len(docs)} chunks into database...")
        vector_db.insert(docs)
        print("Ingestion complete.")

    # --- AGENT PIPELINE ---

    # 1. AGENT 1: Qdrant Consultant
    print("\n--- Running Agent 1: Qdrant Consultant ---")
    context_chunks = [frag.content for frag in vector_db.search(QUERY, 2)]
    context = "\n---\n".join(context_chunks)
    agent1_prompt = PROMPT_QDRANT_CONSULTANT.format(context=context)
    agent_qdrant = Agent(model=OpenAIChat(id="gpt-4o-mini", system_prompt=agent1_prompt))
    doc_response = agent_qdrant.run(QUERY)
    document_context = doc_response.content
    print(f"Retrieved Document Context:\n{document_context}")

    # 2. AGENT 2: URL Collector
    print("\n--- Running Agent 2: URL Collector ---")
    agent_url_collector = Agent(
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=PROMPT_URL_COLLECTOR),
        tools=[BraveSearchTools(fixed_max_results=1)],
    )
    url_response = agent_url_collector.run(QUERY)
    urls = url_response.content.strip().split("\n")
    print(f"Found URLs:\n" + "\n".join(urls))

    # 3. AGENT 3: URL Reader
    print("\n--- Running Agent 3: URL Reader ---")
    agent_url_reader = Agent(
        model=OpenAIChat(
            id="gpt-4o-mini",
            system_prompt=PROMPT_URL_READER.format(query=QUERY),
        ),
        search_knowledge=True, # This agent needs web access
    )
    # The "query" to this agent is the list of URLs to read
    web_response = agent_url_reader.run("\n".join(urls))
    web_context = web_response.content
    print(f"Extracted Web Context:\n{web_context}")

    # 4. AGENT 4: Synthesizer & Judge
    print("\n--- Running Agent 4: Synthesizer & Judge ---")
    final_prompt = PROMPT_SYNTHESIZER.format(
        document_context=document_context, web_context=web_context
    )
    agent_synthesizer = Agent(
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=final_prompt)
    )
    # The final agent doesn't need a query, as the prompt contains all info
    agent_synthesizer.print_response("Analyze the provided information.", markdown=True)