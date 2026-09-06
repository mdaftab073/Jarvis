from app.services.vector_service import (
    search_similar_chunks,
)

from app.services.llm_service import (
    generate_answer,
)


def build_context(
    question: str,
    top_k: int = 5,
    subject_id: int | None = None,
):
    results = search_similar_chunks(
        query=question,
        n_results=top_k,
        subject_id=subject_id,
    )

    context = "\n\n".join(
        item["document"]
        for item in results
    )

    return context, results


def ask_question(
    question: str,
    subject_id: int | None = None,
):
    context, results = build_context(
        question=question,
        subject_id=subject_id,
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