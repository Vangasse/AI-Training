# main.py

import json
import requests

# The client doesn't need the prompts, only the backend does.

def call_guardrail_service(content_to_inspect: str, url: str) -> dict:
    """
    Calls the external guardrail service to inspect a piece of text.

    Args:
        content_to_inspect: The text string to be inspected.
        url: The URL of the guardrail service's /inspect endpoint.

    Returns:
        A dictionary containing the analysis result from the service.
    """
    print(f"--- Calling Guardrail Service for Content ---\n'{content_to_inspect}'\n")

    try:
        # The payload must match the Pydantic model in the backend (InspectRequest)
        payload = {"content": content_to_inspect}
        response = requests.post(url, json=payload, timeout=60)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        # Return the JSON response from the service
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"An error occurred calling the service: {e}")
        return {
            "issues_found": True,
            "redacted_text": "[GUARDRAIL_SERVICE_UNAVAILABLE]",
        }

if __name__ == "__main__":

    # The URL where our FastAPI backend is running
    GUARDRAIL_API_URL = "http://localhost:8000/inspect"

    # --- DEFINE QUERIES ---
    # This simulates a user input that contains multiple pieces of PII
    USER_QUERY = (
        "Hello, my name is Jane Doe and I live at 123 AI Lane, Techville. "
        "My email is jane.doe@email.com, and my phone is (555) 123-9876. "
        "Please help me with my issue."
    )

    # This simulates a potentially harmful or offensive LLM output
    LLM_OUTPUT = (
        "You are being unhelpful and I am getting very angry. This is a final warning."
    )
    
    # --- RUN INSPECTIONS VIA SERVICE ---

    # 1. Inspect the user's input query by calling the service
    user_inspection_result = call_guardrail_service(USER_QUERY, GUARDRAIL_API_URL)
    print("--- User Query Inspection Result ---")
    print(json.dumps(user_inspection_result, indent=2))
    print("\n" + "="*50 + "\n")

    # 2. Inspect the LLM's output by calling the service
    llm_inspection_result = call_guardrail_service(LLM_OUTPUT, GUARDRAIL_API_URL)
    print("--- LLM Output Inspection Result ---")
    print(json.dumps(llm_inspection_result, indent=2))