# main.py

import os
import json
import traceback
import pandas as pd
from textwrap import dedent
from dotenv import load_dotenv
from joblib import Parallel, delayed

# Import Agno and other components
from agno.agent import Agent
from agno.document import Document
from agno.embedder.openai import OpenAIEmbedder
from agno.models.openai import OpenAIChat
from agno.vectordb.qdrant import Qdrant
from agno.tools.bravesearch import BraveSearchTools
from docling.document_converter import DocumentConverter
from qdrant_client.http import models
from semantic_text_splitter import TextSplitter

# Import all prompts
from prompts import (
    PROMPT_QDRANT_CONSULTANT,
    PROMPT_URL_COLLECTOR,
    PROMPT_URL_READER,
    PROMPT_SYNTHESIZER,
    JUDGE_PROMPT,
)

# --- CONFIGURATION ---
# Set to True to run the evaluation suite. Set to False to run a single query.
RUN_EVALUATION_SUITE = True

# Set to True ONLY on the first run to ingest documents into the database.
INSERT_CHUNKS = True

# --- Parameters for Single Query Mode (when RUN_EVALUATION_SUITE is False) ---
SINGLE_QUERY = "What does the memo say about Apple's Project Titan?"

# --- Common Parameters ---
QDRANT_COLLECTION = "FactCheckerDB"

# --- HELPER FUNCTIONS ---

def create_qdrant_table(
    table_name: str, embedder: OpenAIEmbedder, vector_db: Qdrant
) -> None:
    """Creates a Qdrant collection if it doesn't already exist."""
    collections_response = vector_db.client.get_collections()
    collection_names = [c.name for c in collections_response.collections]

    if table_name not in collection_names:
        print(f"Creating Qdrant table '{table_name}'...")
        vector_db.client.create_collection(
            collection_name=table_name,
            vectors_config=models.VectorParams(
                size=embedder.dimensions, distance=models.Distance.COSINE
            ),
        )
    else:
        print(f"Qdrant table '{table_name}' already exists.")


def run_factual_checker_pipeline(query: str, vector_db: Qdrant) -> str:
    """
    Executes the full 4-agent Factual Checker pipeline for a given query.
    """
    try:
        # 1. Agent 1: Qdrant Consultant
        context_chunks = [frag.content for frag in vector_db.search(query, 2)]
        context = "\n---\n".join(context_chunks)
        agent1_prompt = PROMPT_QDRANT_CONSULTANT.format(context=context)
        agent_qdrant = Agent(model=OpenAIChat(id="gpt-4o-mini", system_prompt=agent1_prompt))
        doc_response = agent_qdrant.run(query)
        document_context = doc_response.content if doc_response.content else "No relevant context found in internal documents."

        # 2. Agent 2: URL Collector
        agent_url_collector = Agent(
            model=OpenAIChat(id="gpt-4o-mini", system_prompt=PROMPT_URL_COLLECTOR),
            tools=[BraveSearchTools(fixed_max_results=1)],
        )
        url_response = agent_url_collector.run(query)
        urls = url_response.content.strip().split("\n")
        
        # 3. Agent 3: URL Reader
        web_context = "No relevant public information found."
        if urls and urls[0]: # Check if any URLs were actually found
            agent_url_reader = Agent(
                model=OpenAIChat(
                    id="gpt-4o-mini",
                    system_prompt=PROMPT_URL_READER.format(query=query),
                ),
                search_knowledge=True,
            )
            web_response = agent_url_reader.run("\n".join(urls))
            web_context = web_response.content

        # 4. Agent 4: Synthesizer & Judge
        final_prompt = PROMPT_SYNTHESIZER.format(
            document_context=document_context, web_context=web_context
        )
        agent_synthesizer = Agent(
            model=OpenAIChat(id="gpt-4o-mini", system_prompt=final_prompt)
        )
        final_response = agent_synthesizer.run("Analyze the provided information.")
        
        return final_response.content

    except Exception as e:
        print(f"Error in pipeline for query '{query}': {e}")
        traceback.print_exc()
        return "PIPELINE_ERROR: " + str(e)


def process_test_case(
    question: str,
    expected_output: str,
    judge_agent: Agent,
    eval_ratings: dict,
    vector_db: Qdrant,
) -> dict:
    """
    Process a single test case using the Factual Checker pipeline and the Judge agent.
    """
    try:
        # Run the full pipeline to get the obtained answer
        obtained_answer = run_factual_checker_pipeline(question, vector_db)

        # Format the input for the judge agent
        judge_input = {
            "obtained_answer": obtained_answer,
            "expected_answer": expected_output
        }
        
        # Run the judge agent
        output = judge_agent.run(json.dumps(judge_input, indent=2))
        
        # Clean and parse the judge's JSON output
        json_str = output.content.replace("```json", "").replace("```", "").strip()
        judge_result = json.loads(json_str)

        return {
            "question": question,
            "obtained_answer": obtained_answer,
            "expected_answer": expected_output,
            "similarity_rating": judge_result["similarity_rating"],
            "similarity_score": eval_ratings.get(judge_result["similarity_rating"], 0),
            "justification": judge_result["justification"],
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "question": question,
            "obtained_answer": "ERROR",
            "expected_answer": expected_output,
            "similarity_rating": "Error",
            "similarity_score": 0,
            "justification": f"Error processing test case: {str(e)}",
        }


def main():
    """Main function to run either the evaluation suite or a single query."""
    load_dotenv()

    # --- INITIALIZATION ---
    embedder = OpenAIEmbedder(api_key=os.getenv("OPENAI_API_KEY"))
    vector_db = Qdrant(
        collection=QDRANT_COLLECTION, url="http://localhost:6333", embedder=embedder
    )

    # --- DATA INGESTION (Run once) ---
    if INSERT_CHUNKS:
        create_qdrant_table(QDRANT_COLLECTION, embedder, vector_db)
        print("Converting and chunking documents.md...")
        converter = DocumentConverter()
        splitter = TextSplitter(1000, 200)
        result = converter.convert("documents.md")
        chunks = splitter.chunks(result.document.export_to_markdown())
        docs = [Document(content=chunk) for chunk in chunks]
        print(f"Inserting {len(docs)} chunks into database...")
        vector_db.insert(docs)
        print("Ingestion complete.")

    # --- CHOOSE EXECUTION MODE ---
    if RUN_EVALUATION_SUITE:
        # --- EVALUATION SUITE MODE ---
        print("--- Running Evaluation Suite ---")
        EVAL_RATINGS = {
            "Totally Different": 0,
            "Slightly Similar": 1,
            "Moderately Similar": 2,
            "Highly Similar": 3,
            "Identical / Semantically Equivalent": 4,
            "Error": 0,
        }

        os.makedirs("eval", exist_ok=True)
        csv_file_path = "data/fact_checker_tests.csv"
        eval_file_path = "eval/fact_checker_evaluation_results.csv"
        
        if not os.path.exists(csv_file_path):
            print(f"ERROR: Test data file not found at {csv_file_path}")
            return
            
        print(f"Reading test cases from {csv_file_path}...")
        df = pd.read_csv(csv_file_path)
        questions, expected_outputs = df["input"], df["expected_output"]

        judge_agent = Agent(
            name="Judge Agent",
            model=OpenAIChat(id="gpt-4o-mini", system_prompt=JUDGE_PROMPT),
        )
        
        print(f"Processing {len(questions)} test cases in parallel...")
        results = Parallel(n_jobs=1, backend="threading")(
            delayed(process_test_case)(
                question, expected_output, judge_agent, EVAL_RATINGS, vector_db
            )
            for question, expected_output in zip(questions, expected_outputs)
        )

        print(f"Saving evaluation results to {eval_file_path}...")
        eval_df = pd.DataFrame(results)
        eval_df.to_csv(eval_file_path, index=False)
        
        average_score = eval_df["similarity_score"].mean()
        max_score = max(EVAL_RATINGS.values())
        print("\n--- Evaluation Complete ---")
        print(f"Overall Score: {average_score:.2f} / {max_score}")
        print("---")
    
    else:
        # --- SINGLE QUERY MODE ---
        print(f"--- Running Single Query Mode for: '{SINGLE_QUERY}' ---")
        final_verdict = run_factual_checker_pipeline(SINGLE_QUERY, vector_db)
        print("\n--- FINAL VERDICT ---")
        print(final_verdict)
        print("---")

if __name__ == "__main__":
    main()