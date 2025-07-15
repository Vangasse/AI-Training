import os
import gradio as gr
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the backend URL from environment variables, with a default value
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def get_learning_material(topic):
    """Calls backend to get learning material."""
    if not topic:
        return gr.update(visible=False), "Please enter a topic.", gr.update(visible=False)
    
    try:
        response = requests.post(f"{BACKEND_URL}/generate-material", json={"topic": topic})
        response.raise_for_status()
        material = response.json()["learning_material"]
        
        return gr.update(value=material, visible=True), material, gr.update(visible=True)
    
    except requests.RequestException as e:
        error_md = f"### Error\nCould not connect to backend: {e}"
        return gr.update(value=error_md, visible=True), "", gr.update(visible=False)

def get_quiz(material):
    """Calls backend to get a quiz and stores it in the state."""
    if not material:
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), None
    
    try:
        response = requests.post(f"{BACKEND_URL}/generate-quiz", json={"learning_material": material})
        response.raise_for_status()
        quiz_questions = response.json()["questions"]
        
        # Create UI updates for each question
        q1_update, q2_update, q3_update = [gr.update(visible=False)] * 3
        
        if len(quiz_questions) > 0:
            q1_update = gr.update(label=quiz_questions[0]['question'], choices=quiz_questions[0]['options'], visible=True, value=None)
        if len(quiz_questions) > 1:
            q2_update = gr.update(label=quiz_questions[1]['question'], choices=quiz_questions[1]['options'], visible=True, value=None)
        if len(quiz_questions) > 2:
            q3_update = gr.update(label=quiz_questions[2]['question'], choices=quiz_questions[2]['options'], visible=True, value=None)

        submit_button_update = gr.update(visible=True)
        score_output_update = gr.update(value="", visible=False) # Hide and clear score

        # Return UI updates AND the quiz data to be stored in the state
        return q1_update, q2_update, q3_update, submit_button_update, score_output_update, quiz_questions
    
    except requests.RequestException as e:
        print(f"Error generating quiz: {e}")
        error_update = gr.update(value="Error generating quiz.", visible=True)
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), error_update, None


def submit_quiz(quiz_questions, ans1, ans2, ans3):
    """Submits answers and validates them against the stored quiz data from the state."""
    # --- FIX ---
    # No new API call. We use the quiz_questions passed from the gr.State.
    if not quiz_questions:
        return gr.update(value="Error: Quiz data not found. Please generate a new quiz.", visible=True)

    try:
        score = 0
        user_answers = [ans1, ans2, ans3]
        
        for i, question_data in enumerate(quiz_questions):
            if i < len(user_answers) and user_answers[i] == question_data['correct_answer']:
                score += 1
        
        total = len(quiz_questions)
        return gr.update(value=f"Your score: {score} out of {total}", visible=True)
        
    except Exception as e:
        print(f"An error occurred during submission: {e}")
        return gr.update(value=f"An error occurred during submission: {e}", visible=True)


# --- Gradio Interface ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# AI Learning Assistant")
    gr.Markdown("Enter a topic you want to learn about. I will provide the material and then quiz you on it.")

    # State variables to store data between interactions
    material_state = gr.State("")
    quiz_state = gr.State() # New state for storing the quiz questions and answers

    # --- Step 1: Get Topic and Material ---
    with gr.Row():
        topic_input = gr.Textbox(label="Topic", placeholder="e.g., 'Photosynthesis' or 'Python decorators'")
    material_button = gr.Button("Get Learning Material")
    
    # --- Step 2: Display Material and Offer Quiz ---
    material_output = gr.Markdown(visible=False)
    quiz_button = gr.Button("Generate Quiz", variant="primary", visible=False)

    # --- Step 3: Display Quiz ---
    with gr.Column() as quiz_container:
        q1 = gr.Radio(label="Question 1", visible=False)
        q2 = gr.Radio(label="Question 2", visible=False)
        q3 = gr.Radio(label="Question 3", visible=False)
        submit_button = gr.Button("Submit Answers", visible=False)

    # --- Step 4: Display Score ---
    score_output = gr.Label(label="Result", visible=False)

    # --- Event Handling ---
    material_button.click(
        fn=get_learning_material,
        inputs=[topic_input],
        outputs=[material_output, material_state, quiz_button]
    )
    
    quiz_button.click(
        fn=get_quiz,
        inputs=[material_state],
        outputs=[q1, q2, q3, submit_button, score_output, quiz_state] # Add quiz_state to outputs
    )

    submit_button.click(
        fn=submit_quiz,
        inputs=[quiz_state, q1, q2, q3], # Use quiz_state as input
        outputs=[score_output]
    )


if __name__ == "__main__":
    demo.launch()
