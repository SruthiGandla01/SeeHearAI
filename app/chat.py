# app/chat.py

from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function to ask GPT with conversation history
def ask_gpt(conversation_history):
    response = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-3.5-turbo" if needed
        messages=conversation_history
    )
    return response.choices[0].message.content
