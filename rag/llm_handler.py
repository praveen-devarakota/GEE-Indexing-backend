import os

from groq import Groq

client = Groq(
    api_key=os.getenv(
        "GROQ_API_KEY"
    )
)


def generate_response(prompt):

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1
    )

    return response.choices[0].message.content