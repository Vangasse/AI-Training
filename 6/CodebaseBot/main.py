from docling.document_converter import DocumentConverter
from semantic_text_splitter import TextSplitter
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.vectordb.qdrant import Qdrant
from qdrant_client.http import models
from agno.document import Document
from dotenv import load_dotenv
from agno.agent import Agent
import requests
import os
import re

# Import the system prompt from your new file
from prompt import SYSTEM_PROMPT

def create_qdrant_table(
    table_name: str, embedder: OpenAIEmbedder, vector_db: Qdrant
) -> None:
    """
    Creates a Qdrant collection if it doesn't already exist.

    :param table_name: The name of the table to create.
    :param embedder: The embedder instance for vector dimensions.
    :param vector_db: The Qdrant vector database instance.
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

def get_all_repo_files(repo_url: str) -> list[str]:
    """
    Gets all files with specified extensions from a GitHub repository folder
    using the GitHub API.

    :param repo_url: The URL of the GitHub repository folder.
    :return: A list of download URLs for the files in the repository.
    """
    match = re.search(r"github\.com/([^/]+)/([^/]+)/tree/[^/]+/(.*)", repo_url)
    if not match:
        print(f"Error: Could not parse the provided GitHub folder URL: {repo_url}")
        return []
        
    owner, repo, path = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    try:
        response = requests.get(api_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from GitHub API: {e}")
        return []

    files_data = response.json()
    file_urls = []
    
    for item in files_data:
        if item.get('type') == 'file' and item.get('download_url'):
            file_name = item.get('name', '')
            if file_name.endswith((".py", ".js", ".md")):
                file_urls.append(item['download_url'])
                
    return file_urls

if __name__ == "__main__":
    load_dotenv()

    # --- Configuration ---
    INSERT_CHUNKS = True
    WITH_CONTEXT = True  # The WITH_CONTEXT flag is back
    QUERY = "What does the example of lecture 2 do?"
    REPO_URL = "https://github.com/tfvieira/tic43/tree/main/Lecture2"
    COLLECTION_NAME = "tic43_lectures"

    # --- Initializations ---
    embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    vector_db = Qdrant(
        collection=COLLECTION_NAME, url="http://localhost:6333", embedder=embedder
    )
    converter = DocumentConverter()
    # TextSplitter parameters are now positional
    splitter = TextSplitter(1000, 200)

    # --- Indexing Logic ---
    if INSERT_CHUNKS:
        print(f"Creating Qdrant table '{COLLECTION_NAME}' if it doesn't exist...")
        create_qdrant_table(COLLECTION_NAME, embedder, vector_db)
        
        print(f"Fetching files from repository: {REPO_URL}")
        repo_files = get_all_repo_files(REPO_URL)

        if not repo_files:
            print("No files found to index. Exiting.")
        else:
            print(f"Found {len(repo_files)} files to index.")
            for file_url in repo_files:
                file_name = file_url.split('/')[-1]
                print(f"  - Processing {file_name}...")
                
                document_text = ""
                try:
                    if file_url.endswith((".py", ".js")):
                        response = requests.get(file_url)
                        response.raise_for_status()
                        document_text = response.text
                    elif file_url.endswith(".md"):
                        result = converter.convert(file_url)
                        document_text = result.document.export_to_markdown()
                    else:
                        print(f"    - Skipping unsupported file type: {file_name}")
                        continue

                    if document_text:
                        chunks = splitter.chunks(document_text)
                        docs = [Document(content=chunk) for chunk in chunks]
                        vector_db.insert(docs)

                except Exception as e:
                    print(f"    - Failed to process {file_name}: {e}")
                    continue

            print("Finished indexing all files.")

    # --- Querying Logic ---
    if WITH_CONTEXT:
        print("\nSearching for context related to the query...")
        context_fragments = vector_db.search(QUERY, 5)
        context = " - " + "\n - ".join([frag.content for frag in context_fragments])
    else:
        context = ""

    formatted_prompt = SYSTEM_PROMPT.format(context=context)

    print("Generating response...")
    agent = Agent(
        show_tool_calls=True,
        model=OpenAIChat(id="gpt-4o-mini", system_prompt=formatted_prompt),
    )

    agent.print_response(QUERY, markdown=True)