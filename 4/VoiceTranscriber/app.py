from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from a .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Define the folder for temporary file uploads
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Initialize the OpenAI client with the API key from environment variables
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in .env file or environment variables.")
    client = OpenAI(api_key=api_key)
    print("OpenAI client initialized successfully.")
except ValueError as e:
    print(f"Error: {e}")
    client = None

@app.route('/')
def index():
    """
    Renders the main page of the application from the template.
    """
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Receives an audio file, sends it to the OpenAI Whisper API for transcription,
    and returns the transcription text. This is the official and recommended method.
    """
    if not client:
        return jsonify({'error': 'OpenAI client is not initialized. Please check your API key setup.'}), 500

    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file found in the request'}), 400

    file = request.files['audio_file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filepath = "" # Define filepath to ensure it's available in the finally block
    if file:
        try:
            # Save the file temporarily
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            print(f"File saved temporarily to {filepath}")

            # Open the saved file and send it to the Whisper API
            with open(filepath, "rb") as audio_file:
                print("Sending audio to OpenAI Whisper API for transcription...")
                # The correct, official model for audio transcription is "whisper-1"
                transcription = client.audio.transcriptions.create(
                  model="gpt-4o-mini-transcribe", 
                  file=audio_file
                )
                print("Transcription received.")

            # Return the transcription text
            return jsonify({'transcription': transcription.text})

        except Exception as e:
            print(f"An error occurred: {e}")
            return jsonify({'error': str(e)}), 500
        
        finally:
            # Clean up the temporary file if it exists
            if filepath and os.path.exists(filepath):
                # os.remove(filepath)
                print(f"Temporary file {filepath} removed.")


    return jsonify({'error': 'An unknown error occurred'}), 500


if __name__ == '__main__':
    # Run the app in debug mode for development
    app.run(debug=True)
