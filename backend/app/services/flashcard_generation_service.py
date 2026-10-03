"""Service for generating flashcards using LLM (Groq).

Workflow:
1. Accept a list of topics (or a subject ID) and optional number of cards per topic.
2. Build a prompt that asks the LLM to produce flashcards for each topic.
3. Parse the LLM output (expects JSON list of cards).
4. Persist generated flashcards via FlashcardService.
"""

from typing import List, Dict
from typing import TYPE_CHECKING

from app.services.flashcard_service import FlashcardService
from app.schemas.flashcard import FlashcardCreate
from app.core.config import settings
import httpx
import json

if TYPE_CHECKING:
    from app.models import Flashcard

class FlashcardGenerationService:
    def __init__(self, db_session):
        self.db = db_session
        self.flashcard_service = FlashcardService(db_session)

    def _call_groq(self, topics: List[str], cards_per_topic: int = 5) -> List[Dict]:
        """Call Groq LLM to generate flashcards.
        Returns a list of dicts with keys: question, answer, difficulty (optional).
        """
        prompt = (
            "You are an educational assistant. Generate *{n}* flashcards for each of the following topics. "
            "Return a JSON array where each element has the fields: `question`, `answer`, and optional `difficulty` (easy|medium|hard).\n"
            "Do NOT include any extra text.\n"
            "Topics:\n"
            + "\n".join([f"- {t}" for t in topics])
            + "\n"
        ).format(n=cards_per_topic)
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
        payload = {"model": "llama3-70b-8192", "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
        response = httpx.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        try:
            cards = json.loads(data["choices"][0]["message"]["content"].strip())
            if isinstance(cards, list):
                return cards
        except Exception:
            # Fallback – split lines assuming one JSON object per line
            raw = data["choices"][0]["message"]["content"].strip()
            return [json.loads(line) for line in raw.split('\n') if line.strip()]
        return []

    def generate_and_store(self, deck_id: int, topics: List[str], cards_per_topic: int = 5) -> List["Flashcard"]:
        """Generate flashcards for the given topics and store them in the deck.
        Returns the list of created Flashcard ORM objects.
        """
        raw_cards = self._call_groq(topics, cards_per_topic)
        created = []
        for card in raw_cards:
            fc_in = FlashcardCreate(
                question=card.get("question", ""),
                answer=card.get("answer", ""),
                difficulty=card.get("difficulty", "medium"),
                topic_id=None,
            )
            created_fc = self.flashcard_service.create_flashcard(deck_id, None, fc_in)
            created.append(created_fc)
        return created
