import os
from app import app
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")

if __name__ == "__main__":
    if not openai.api_key:
        print("WARNING: OpenAI API key not found. AI health analysis features will not work properly.")
        print("Please set the OPENAI_API_KEY environment variable.")
    app.run(host="0.0.0.0", port=5000, debug=True)
