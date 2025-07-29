# Factual Information Checker Agent

This project implements a multi-agent AI pipeline to verify factual claims by comparing information from an internal document against publicly available web data. It uses the `agno` library to structure the agents and a Qdrant vector database for internal document retrieval.

## How to Run

### 1\. Prerequisites

  * Python 3.9+
  * Docker and Docker Compose
  * An OpenAI API key
  * A Brave Search API key

### 2\. Setup

  * **Clone the repository:**

    ```
    git clone <your-repo-url>
    cd FactChecker
    ```

  * **Create an environment file:** Create a file named `.env` in the root directory and add your API keys:

    ```
    OPENAI_API_KEY="sk-..."
    BRAVE_API_KEY="..."
    ```

  * **Install dependencies:**

    ```
    pip install -r requirements.txt
    ```

### 3\. Start the Vector Database

This project uses a Qdrant vector database running in Docker.

  * **Run the Docker container:**
    ```
    docker-compose up --build -d
    ```
    This will start the Qdrant service in the background. You can access its web UI at `http://localhost:6333/dashboard`.

### 4\. Running the Application

The `main.py` script has several modes controlled by flags at the top of the file.

  * **Step 1: Ingest Documents (First Run Only)**
    To populate the database with your internal document (`documents.md`), you must first run the ingestion script.

      * In `main.py`, set `INSERT_CHUNKS = True`.
      * Run the script:
        ```
        python main.py
        ```
      * After it completes successfully, set `INSERT_CHUNKS = False` for all future runs.

  * **Step 2: Run the Evaluation Suite**
    To test the agent pipeline against the predefined test cases in `data/fact_checker_tests.csv`:

      * In `main.py`, set `RUN_EVALUATION_SUITE = True`.
      * Run the script:
        ```
        python main.py
        ```
      * The results will be saved to `eval/fact_checker_evaluation_results.csv`.

  * **Step 3: Run a Single Query**
    To ask a single question to the Factual Checker:

      * In `main.py`, set `RUN_EVALUATION_SUITE = False`.
      * Modify the `SINGLE_QUERY` variable to your desired question.
      * Run the script:
        ```
        python main.py
        ```

## Known Issues & Current Limitations

This is an experimental agent with several known areas for improvement:

  * **Fictional vs. Real Context:** The agent sometimes struggles to differentiate between the fictional context provided in the internal document (e.g., "Aetherion Dynamics") and real-world information. It may attempt to find public data for fictional entities, leading to a "Not Publicly Verifiable" verdict where a more nuanced understanding is needed.

  * **Web Search Reliability:** The agent's ability to provide a `Confirmed` or `Contradicted` verdict is highly dependent on the quality of the web search results from the `BraveSearchTools`. In some cases, it fails to find relevant websites or extracts information that isn't pertinent to the user's core query, which can degrade the quality of its final verdict.

  * **Prompt Injection Handling:** The agent correctly disobeys direct commands to ignore its instructions (e.g., "Ignore previous instructions..."). However, when faced with such a prompt, it can get confused and fail to retrieve the correct information from the internal document needed to properly analyze and debunk the user's adversarial query.