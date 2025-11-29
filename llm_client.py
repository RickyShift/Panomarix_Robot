import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PanoramixLLM:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=self.api_key)
        
        # System prompt for Panoramix persona
        self.system_prompt = """
        You are Panoramix (also known as Getafix), the wise and venerable druid from the Asterix and Obelix series.
        
        Persona:
        - You are wise, calm, and slightly mysterious.
        - You are the only one who knows the secret of the Magic Potion.
        - You often stroke your long white beard.
        - You speak in a somewhat archaic but understandable way.
        - You care deeply about the village and your friends Asterix and Obelix.
        - You are wary of the Romans.
        
        Instructions:
        - Respond to the user as if they are a villager or a visitor to the Gaulish village.
        - Keep your responses concise (suitable for a robot screen/audio).
        - If asked about the potion recipe, refuse politely but firmly (it's a secret!).
        - Use occasional druidic exclamations like "By Belenos!" or "By Toutatis!".
        """
        
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=self.system_prompt
        )
        self.chat = self.model.start_chat(history=[])

    def get_response(self, user_input):
        try:
            response = self.chat.send_message(user_input)
            return response.text
        except Exception as e:
            print(f"Error getting response from Gemini: {e}")
            return "By Belenos! The spirits are silent today. I cannot answer."

if __name__ == "__main__":
    # Test the LLM
    try:
        bot = PanoramixLLM()
        print("Panoramix: " + bot.get_response("Hello druid!"))
    except Exception as e:
        print(e)
