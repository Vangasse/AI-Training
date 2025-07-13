import os
import json
from openai import OpenAI
from dotenv import load_dotenv
# Assumes the prompt is saved in a file named prompt.py
from prompt import INVOICE_PARSING_PROMPT

def main():
    """
    Executes the invoice parsing process using the designed prompt.
    """
    # Load environment variables from the .env file
    load_dotenv()

    # Initialize the OpenAI client with the API key
    api_key = os.getenv(key="OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")
    client = OpenAI(api_key=api_key)

    # --- A new unstructured text example with a conversational style ---
    unstructured_text = """
    INVOICE # INV-987XYZ --- Ship To: 123 Construction Way, Job Site B

    Item: Titanium Hammer (SKU: TH-001), 3 units.
    Also included: a dozen Safety Cones.
    Industrial Shelving Unit, 2 units, $500.00 per unit.
    Notes: Please deliver to the rear entrance.
    GRAND TOTAL: $2,150.50
    MegaCorp Hardware & Industrial Supply
    Box of Nails (5lbs), we sent 10 of these.
    Price for the hammers was @ 75.00 ea.
    Contractor Grade Wheelbarrow, 1x, Price: $180.00
    VAT (18%): $328.00
    Terms: NET 60
    SKU for the shelving unit is ISU-HEAVY-DUTY.
    Extension Cords (50ft) came to $320.00 total for 4 units.
    Total for nails: $150.00.
    The SKU for the orange cones is SC-ORANGE and the total for them was $240.00.
    Date of issue: July 21st, 2025 --- Call 555-1234 for questions.
    """

    print("--- 1. Input: Unstructured Invoice Text ---")
    print(unstructured_text)

    # Format the final prompt with the invoice text
    final_prompt = INVOICE_PARSING_PROMPT.format(unstructured_invoice_text=unstructured_text)

    print("\n--- 2. Sending Request to LLM ---")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": final_prompt}],
            # Enforce JSON output for higher reliability
            response_format={"type": "json_object"},
        )
        
        json_response_str = response.choices[0].message.content
        print("✅ Raw JSON response received from LLM.")

    except Exception as e:
        print(f"❌ Error during API call: {e}")
        return

    print("\n--- 3. Parsing and Displaying Structured Data ---")
    try:
        # The response should already be a valid JSON string
        parsed_json = json.loads(json_response_str)
        
        # Pretty-print the parsed JSON data
        print(json.dumps(parsed_json, indent=2))
        print("\n✅ Successfully parsed invoice data.")

    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON response: {e}")
        print("Raw response from API was:")
        print(json_response_str)

if __name__ == "__main__":
    main()
