from app.services.llm_service import generate_answer


answer = generate_answer(
    question="What is Python?",
    context="Python is a programming language."
)

print(answer)