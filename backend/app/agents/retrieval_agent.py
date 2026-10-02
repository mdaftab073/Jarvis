from app.agents.base import BaseAgent
from app.agents.base import execute_agent_tool


def ask_question(*, question, db, subject_id=None):
    return execute_agent_tool("rag_search", {"question": question, "db": db, "subject_id": subject_id})


class RetrievalAgent(BaseAgent):
    name = "retrieval"

    def execute(self, context: dict) -> dict:
        question = context.get("retrieval_question") or context.get("goal", "")
        if not question.strip():
            return self.response("No retrieval question was supplied.")
        result = ask_question(
            question=question,
            db=context["db"],
            subject_id=context.get("subject_id"),
        )
        sources = [
            {
                "material_id": item["metadata"].get("material_id"),
                "title": item["metadata"].get("title"),
            }
            for item in result["results"]
        ]
        return self.response(
            result["answer"],
            data={"answer": result["answer"], "sources": sources, "stats": result["stats"]},
        )