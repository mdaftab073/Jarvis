from groq import Groq

from app.core.config import settings


client = Groq(
    api_key=settings.GROQ_API_KEY
)


def generate_answer(
    question: str,
    context: str,
):
    prompt = f"""
You are Jarvis, an academic assistant.

Answer ONLY using the provided context.

If the answer is not present in the context, respond exactly:

I could not find this information in the uploaded study materials.

Context:
{context}

Question:
{question}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,
    )
    print(f"Question: {question}")
    print(f"Context length: {len(context)}")
    
    return response.choices[0].message.content