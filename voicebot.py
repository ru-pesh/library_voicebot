import sounddevice as sd
import wavio
import speech_recognition as sr
import google.generativeai as genai
import csv
import re 
import os
from elevenlabs.client import ElevenLabs 
from elevenlabs.play import play
from dotenv import load_dotenv

load_dotenv()

#API Key for Gemini and ElevenLabs
genai.configure(api_key= os.getenv("gemini"))
ELEVENLABS_API_KEY = os.getenv("eleven") 

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

r = sr.Recognizer()

# Load book catalog from CSV
def load_books_from_csv(filename="books.csv"):

    """Loads the book catalog from a CSV file."""
    books = []
    try:
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                books.append(row)
        print(f"✅ Successfully loaded {len(books)} books from {filename}.")
        return books
    except FileNotFoundError:
        print(f"⚠️ Error: The file {filename} was not found. The bot will have no book data.")
        return []
    except Exception as e:
        print(f"⚠️ Error loading {filename}: {e}")
        return []

# Record audio from microphone
def record_audio(filename="input.wav", duration=5, samplerate=44100):

    print(f"🎤 Speak now (recording for {duration} seconds)...")
    try:
        audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        wavio.write(filename, audio, samplerate, sampwidth=2)
        print("✅ Recording complete.")
        return filename
    except Exception as e:
        print(f"⚠️ Error during recording: {e}")
        return None

# Convert speech to text
def listen():

    try:
        filename = record_audio()
        if filename is None: 
            return ""
            
        with sr.AudioFile(filename) as source:
            audio = r.record(source)
        text = r.recognize_google(audio)
        print(f"🗣️ You said: {text}")
        return text
    except sr.UnknownValueError:
        print("⚠️ Google Speech Recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        print(f"⚠️ Could not request results from Google Speech Recognition service; {e}")
        return ""
    except Exception as e:
        print(f"⚠️ Speech recognition failed: {e}")
        return input("🧍 Type your query instead: ")


# Send user query to Gemini and get response
def ask_gemini(prompt, books_data):
    """
    Sends user query to Gemini and returns the FULL response.
    """
    catalog_string_parts = []
    for book in books_data:
        title = book.get('Title', 'N/A')
        author = book.get('Author', 'N/A')
        status = book.get('Status', 'N/A')
        section = book.get('Section', 'Unknown')
        shelf = book.get('Shelf', 'Unknown')
        
        catalog_string_parts.append(
            f"- Title: {title}, Author: {author}, Status: {status}, Section: {section}, Shelf: {shelf}"
        )
    catalog_string = "\n".join(catalog_string_parts)

    if not catalog_string:
        catalog_string = "No books are available in the catalog."

    system_prompt = f"""
You are a helpful AI library assistant. Your
job is to answer user questions *only* based on the book catalog provided below.
When a user asks for a book, tell them if it is available and *its exact location (Section and Shelf)*.
Do not make up information or answer questions about books not in this list.
If a book is not in the list, politely say you don't have it in the catalog.
If a user asks for a recommendation, use the genres from the list.

--- LIBRARY CATALOG (Title, Author, Status, Section, Shelf) ---
{catalog_string}
-----------------------

User: {prompt}
Assistant:
"""
# Call Gemini API
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        response = model.generate_content(system_prompt)
        
        full_text = response.text
        clean_full_text = re.sub(r'[\*#]', '', full_text)
        
        return clean_full_text    
    except Exception as e:
        print(f"⚠️ Error calling Gemini: {e}")
        return "I'm sorry, I'm having trouble connecting to my brain right now."

# Speak the initial greeting using ElevenLabs
def speak_initial_greeting(text):
    try:
        
        print(f"\n📚 LibraryBot: {text}")
        
        
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb", 
            model_id="eleven_multilingual_v2",
        )
        play(audio)
        
    except Exception as e:
        print(f"\n🔇 Could not play streaming audio ({e}).")
    print() 

# Speak the response using ElevenLabs
def speak(text: str):
    """
    Takes full text, converts it to audio using ElevenLabs, and plays it.
    This is a non-streaming (blocking) function.
    """
    
    try:
        print(f"\n📚 LibraryBot: {text}")
    
        audio = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id="JBFqnCBsd6RMkjVDRZzb", 
            model_id="eleven_multilingual_v2",
        )
        play(audio)
        
    except Exception as e:
        print(f"\n🔇 Could not play streaming audio ({e}).")
    print() 

# Main interaction loop
def main():
    books = load_books_from_csv("books.csv")    
    speak_initial_greeting(f"Hello! I am your library assistant. I have {len(books)} books in my catalog. How can I help you today?")
    
    while True:
        query = listen()
        if not query:
            continue
        if any(word in query.lower() for word in ["exit", "quit", "goodbye", "stop"]):
            
            speak_initial_greeting("Goodbye! Have a nice day!")
            break
        answer_text = ask_gemini(query, books)
        
        speak(answer_text)

if __name__ == "__main__":
    main()


