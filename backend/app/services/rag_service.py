from app.services.vector_service import (
    search_similar_chunks,
)

from app.services.llm_service import (
    generate_answer,
)


def build_context(
    question: str,
    top_k: int = 5,
):
    results = search_similar_chunks(
        query=question,
        n_results=top_k,
    )

    context = "\n\n".join(
        item["document"]
        for item in results
    )

    return context, results


def ask_question(
    question: str,
):
    context, results = build_context(
        question=question
    )
    
    print("\n========== CONTEXT ==========")
    print(context[:3000])
    print("\n=============================\n")

    answer = generate_answer(
        question=question,
        context=context,
    )

    print(f"Retrieved chunks: {len(results)}")
    
    return {
        "answer": answer,
        "results": results,
    }