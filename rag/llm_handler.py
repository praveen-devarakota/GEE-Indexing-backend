import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # best for reasoning
            messages=[
                {"role": "system", "content": "You must return ONLY valid JSON. No explanation, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        return response.choices[0].message.content

    except Exception as e:
        print("LLM Error:", e)
        return "Error generating response"