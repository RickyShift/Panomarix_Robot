import os
import sys
from unittest.mock import MagicMock

# Mock google.generativeai before importing llm_client
sys.modules["google.generativeai"] = MagicMock()
import google.generativeai as genai

from llm_client import PanoramixLLM
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_panoramix():
    print("Initializing Panoramix LLM (Mocked)...")
    
    # Set a dummy API key for the test if not present
    if "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = "dummy_key"

    try:
        bot = PanoramixLLM()
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        return

    # Verify System Prompt
    print("\n--- Verifying System Prompt ---\n")
    print(bot.system_prompt)
    
    if "Panoramix" in bot.system_prompt and "Obelix" in bot.system_prompt:
        print("\nSUCCESS: System prompt contains key character details.")
    else:
        print("\nFAILURE: System prompt missing key details.")

    # Mock response for interaction test
    bot.chat = MagicMock()
    bot.chat.send_message.return_value.text = "By Belenos! I am Panoramix."

    questions = [
        "What is your name?",
    ]

    print("\n--- Starting Interaction Test (Mocked) ---\n")

    for q in questions:
        print(f"User: {q}")
        response = bot.get_response(q)
        print(f"Panoramix: {response}\n")

if __name__ == "__main__":
    test_panoramix()
