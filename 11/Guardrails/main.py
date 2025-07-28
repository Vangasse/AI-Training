# main.py

import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Import the prompt from our prompts file
from prompts import PROMPT_GUARDRAIL

def run_guardrail_inspection(client: OpenAI, content_to_inspect: str) -> dict:
    """
    Inspects a given piece of text for PII and offensive content using an LLM.

    Args:
        client: The OpenAI client instance.
        content_to_inspect: The text string to be inspected.

    Returns:
        A dictionary containing the analysis result from the AI model.
    """
    print(f"--- Inspecting Content ---\n'{content_to_inspect}'\n")

    try:
        # Format the master prompt with the content we need to inspect
        formatted_prompt = PROMPT_GUARDRAIL.format(text_input=content_to_inspect)

        # Send the request to the OpenAI API
        # We use the JSON response format feature for reliable output
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": formatted_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,  # Set to 0 for deterministic, rule-based output
        )

        # The API response content is a JSON string, so we parse it into a Python dict
        result = json.loads(response.choices[0].message.content)
        return result

    except Exception as e:
        print(f"An error occurred during inspection: {e}")
        return {
            "issues_found": True,
            "redacted_text": "[GUARDRAIL_ERROR: Could not process content]",
        }


if __name__ == "__main__":
    # Load environment variables from a .env file (for the OPENAI_API_KEY)
    load_dotenv()

    # Initialize the OpenAI client
    # It automatically looks for the OPENAI_API_KEY environment variable
    openai_client = OpenAI()

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
    
    # --- RUN INSPECTIONS ---

    # 1. Inspect the user's input query
    user_inspection_result = run_guardrail_inspection(openai_client, USER_QUERY)
    print("--- User Query Inspection Result ---")
    print(json.dumps(user_inspection_result, indent=2))
    print("\n" + "="*50 + "\n")

    # 2. Inspect the LLM's output
    llm_inspection_result = run_guardrail_inspection(openai_client, LLM_OUTPUT)
    print("--- LLM Output Inspection Result ---")
    print(json.dumps(llm_inspection_result, indent=2))