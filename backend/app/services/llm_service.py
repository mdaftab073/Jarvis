import logging

from groq import Groq

from app.core.config import settings

logger = logging.getLogger(__name__)


client = Groq(
    api_key=settings.GROQ_API_KEY
)


def generate_answer(
    question: str,
    context: str,
):
    if context and context.strip():
        prompt = f"""You are Jarvis, an academic assistant and study tutor.

Answer the question clearly and accurately using the provided context from the student's study materials. Cite key details from the materials when appropriate.

Context:
{context}

Question:
{question}
"""
    else:
        prompt = f"""You are Jarvis, an expert academic tutor and university study assistant.
The student asked an academic or conceptual question, but has not uploaded course notes for this specific topic yet.

Answer the student's question thoroughly, accurately, and pedagogically as an expert tutor. Break down complex ideas with clear explanations and examples.

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
    logger.info(
        "Generated answer for question; context size=%d characters",
        len(context),
    )
    
    return response.choices[0].message.content