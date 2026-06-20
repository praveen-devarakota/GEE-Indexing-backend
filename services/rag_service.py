import json
import os

from groq import Groq

from rag.pipeline import (
    run_analysis_pipeline,
    run_chat_pipeline
)

from rag.prompt_builder import (
    build_chat_prompt
)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def analyze_with_rag(data):

    try:

        result = run_analysis_pipeline(data)

        return {
            "success": True,
            "analysis": result
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def chat_with_rag(context, question):

    try:

        context = run_chat_pipeline(
            context,
            question
        )

        prompt = build_chat_prompt(
            context,
            question
        )
        print("\n========== PROMPT ==========")
        print(prompt[:5000])
        print("========== END PROMPT ==========\n")

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            response_format={
                "type": "json_object"
            }
        )

        raw = response.choices[0].message.content

        try:
            parsed = json.loads(raw)

            return {
                "success": True,
                "answer": parsed.get(
                    "answer",
                    raw
                )
            }

        except Exception:

            return {
                "success": True,
                "answer": raw
            }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }