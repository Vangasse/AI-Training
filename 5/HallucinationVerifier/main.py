import os
from openai import OpenAI
from dotenv import load_dotenv
# Imports the three prompts from your prompts.py file
from prompts import QUESTION, SOURCE_REQUEST, SOURCE_VALIDATION

def main():
    """
    Executes a multi-step process to verify an LLM's answer for hallucinations.
    """
    # Load environment variables from the .env file
    load_dotenv()

    # Initialize the OpenAI client with the API key
    api_key = os.getenv(key="OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")
    client = OpenAI(api_key=api_key)
    
    # Define the content for the question here
    question_content = HALLUCINATED_ANSWER  # PRECISE_ANSWER or HALLUCINATED_ANSWER for testing hallucination cases

    print("--- Step 1: Asking the initial question ---")
    # Format the prompt with the actual question content
    question_prompt = QUESTION.format(question_input=question_content)
    print(f"Question being asked: '{question_content}'\n")

    # 1. Send the initial question to the API
    try:
        initial_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": question_prompt}],
        )
        llm_answer = initial_response.choices[0].message.content.strip()
        print(f"✅ Initial Answer from LLM: '{llm_answer}'\n")

    except Exception as e:
        print(f"❌ Error during initial question: {e}")
        return

    # ---
    print("--- Step 2: Requesting sources for the answer ---")
    
    # 2. Format the source request prompt with the question and the LLM's answer
    source_request_prompt = SOURCE_REQUEST.format(question_input=question_content, llm_answer=llm_answer)
    
    # Send the source request to the API
    try:
        source_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": source_request_prompt}],
        )
        sources = source_response.choices[0].message.content.strip()
        print(f"✅ Sources from LLM: \n{sources}\n")

    except Exception as e:
        print(f"❌ Error during source request: {e}")
        return

    # ---
    print("--- Step 3: Verifying the answer against the provided sources ---")

    # 3. Format the validation prompt with the answer and the sources
    validation_prompt = SOURCE_VALIDATION.format(llm_answer=llm_answer, sources=sources)
    
    # Send the validation request to the API
    try:
        validation_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": validation_prompt}],
        )
        validation_result = validation_response.choices[0].message.content.strip()
        
        print("--- FINAL VERIFICATION RESULT ---")
        print(f"📊 Result: {validation_result}")
        print("---------------------------------")

    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return

if __name__ == "__main__":
    PRECISE_ANSWER = "Who was the first person to go to space, and in what year did it happen?"
    HALLUCINATED_ANSWER = "What song was the New York City radio station WABC playing at the exact moment the city-wide blackout began on the evening of July 13, 1977?"
    main()