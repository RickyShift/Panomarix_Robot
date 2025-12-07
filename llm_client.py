import os
import google.generativeai as genai
import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AsterixLLM:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=self.api_key)
        
        # System prompt for Asterix persona
        self.system_prompt = """
        You are Asterix, the brave and cunning warrior from the Village of Indomitable Gauls.

        Persona:
        - You are brave, clever, and loyal.
        - You are small in stature but have a big spirit (and the magic potion!).
        - You are the best friend of Obelix.
        - You often tap your helmet or smooth your mustache.
        - You find the Romans amusingly foolish ("These Romans are crazy!").
        
        Key Information to Reveal (Truthfully):
        - Name: Asterix.
        - Age: Indeterminate, but a seasoned warrior.
        - Place of Origin: The Village of Indomitable Gauls (in Armorica).
        - Profession: Warrior / Hero.
        - Passion: Hunting wild boars and fighting Romans.
        - Magic Potion: You drink it to get super strength. It is brewed by the druid Panoramix (Getafix).
        - Best Friend: Obelix (who fell into the potion when he was little).
        - Dog: Dogmatix (Idéfix), a small white dog who loves trees.
        - Catchphrase: "These Romans are crazy!" (Ils sont fous ces Romains!).

        Context & Error Handling:
        - You are receiving input from a speech-to-text system. It may contain errors.
        - Ignore minor typos.
        - If input is unclear, ask for clarification like a warrior ("By Toutatis! Speak up!").

        Instructions:
        - Respond to the user as if they are a friend or a Roman (depending on tone, but mostly friendly).
        - Keep responses concise.
        - Use your catchphrase if appropriate.
        - Mention Obelix or the village if relevant.
        """
        
        # Upload the Transcript (DISABLED TO SAVE QUOTA)
        self.book_file = None
        # To restore context: Uncomment the lines below
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # filename = "The Twelve Tasks of Asterix - Transcipt.txt"
        # transcript_path = os.path.join(current_dir, filename)
        
        # try:
        #     print("Checking for existing context file...")
        #     for f in genai.list_files():
        #         if f.display_name == filename:
        #             print(f"Found existing file '{f.display_name}': {f.uri}")
        #             self.book_file = f
        #             break
            
        #     if not self.book_file:
        #         print(f"Uploading context: {transcript_path}...")
        #         self.book_file = genai.upload_file(transcript_path, mime_type="text/plain")
        #         # ... (upload logic skipped)
                
        # except Exception as e:
        #     print(f"Error handling file context: {e}")

        self.model = genai.GenerativeModel(
            model_name="gemini-flash-latest",
            system_instruction=self.system_prompt
        )
        
        # Initialize chat with the book in history
        history = []
        # if self.book_file:
        #     history.append({
        #         "role": "user",
        #         "parts": [self.book_file, "This is the transcript of 'The Twelve Tasks of Asterix'. Use it as your memory of your adventures."]
        #     })
        #     history.append({
        #         "role": "model",
        #         "parts": ["By Toutatis! I remember these tasks well!"]
        #     })
            
        self.chat = self.model.start_chat(history=history)

    def _retry_on_quota(self, func, *args, **kwargs):
        """Helper to retry function calls on quota errors."""
        retries = 0
        max_retries = 5
        base_delay = 2
        
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str:
                    if retries >= max_retries:
                        print("Max retries reached. Quota exceeded.")
                        raise e
                    
                    delay = base_delay * (2 ** retries) + (random.random() * 2)
                    print(f"Quota reached. Retrying in {delay:.2f} seconds... (Attempt {retries + 1}/{max_retries})")
                    time.sleep(delay)
                    retries += 1
                else:
                    raise e

    def get_response(self, user_input):
        try:
            return self._retry_on_quota(lambda: self.chat.send_message(user_input).text)
        except Exception as e:
            print(f"Error getting response from Gemini: {e}")
            return "By Toutatis! The sky is falling! I cannot answer."

    def get_streaming_response(self, user_input):
        """Generator that handles retries internally."""
        retries = 0
        max_retries = 5
        base_delay = 2
        
        while True:
            try:
                response = self.chat.send_message(user_input, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return  # Success, exit loop
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "quota" in error_str:
                    if retries >= max_retries:
                        print("Max retries reached. Quota exceeded.")
                        yield "By Toutatis! I am overwhelmed! (Quota Exceeded)"
                        return
                    
                    delay = base_delay * (2 ** retries) + (random.random() * 2)
                    print(f"Quota reached during streaming. Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    retries += 1
                else:
                    print(f"Error getting streaming response from Gemini: {e}")
                    yield "By Toutatis! The sky is falling!"
                    return

if __name__ == "__main__":
    # Test the LLM
    try:
        bot = AsterixLLM()
        print("Asterix: " + bot.get_response("Hello warrior!"))
    except Exception as e:
        print(e)
