import os
import google.generativeai as genai
import time
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
        
        # Upload the PDF book
        pdf_path = r"C:\Users\shueb\OneDrive\Documentos\GitHub\Panomarix_Robot\The Twelve Tasks of Asterix - PDF Room.pdf"
        print(f"Uploading context: {pdf_path}...")
        try:
            self.book_file = genai.upload_file(pdf_path, mime_type="application/pdf")
            print(f"Uploaded file '{self.book_file.display_name}' as: {self.book_file.uri}")
            
            # Wait for processing
            while self.book_file.state.name == "PROCESSING":
                print("Processing file...")
                time.sleep(2)
                self.book_file = genai.get_file(self.book_file.name)
                
            if self.book_file.state.name == "FAILED":
                raise ValueError(f"File processing failed: {self.book_file.state.name}")
                
            print("File processed successfully.")
        except Exception as e:
            print(f"Error uploading file: {e}")
            self.book_file = None

        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=self.system_prompt
        )
        
        # Initialize chat with the book in history
        history = []
        if self.book_file:
            history.append({
                "role": "user",
                "parts": [self.book_file, "This is the book 'The Twelve Tasks of Asterix'. Use it as your memory of your adventures."]
            })
            history.append({
                "role": "model",
                "parts": ["By Toutatis! I remember these tasks well!"]
            })
            
        self.chat = self.model.start_chat(history=history)

    def get_response(self, user_input):
        try:
            response = self.chat.send_message(user_input)
            return response.text
        except Exception as e:
            print(f"Error getting response from Gemini: {e}")
            return "By Toutatis! The sky is falling! I cannot answer."

    def get_streaming_response(self, user_input):
        try:
            response = self.chat.send_message(user_input, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"Error getting streaming response from Gemini: {e}")
            yield "By Toutatis! The sky is falling!"

if __name__ == "__main__":
    # Test the LLM
    try:
        bot = AsterixLLM()
        print("Asterix: " + bot.get_response("Hello warrior!"))
    except Exception as e:
        print(e)
