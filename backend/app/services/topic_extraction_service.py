"""Service for extracting topics from study material using Groq.

Workflow:
1. Retrieve material content (via StudyMaterialService).
2. Call Groq LLM to identify major concepts.
3. De‑duplicate topics.
4. Persist topics with TopicService.
"""

from typing import List

from app.services.topic_service import TopicService
from app.services.study_material_service import StudyMaterialService  # existing service
from app.schemas.topic import TopicCreate
from app.core.config import settings
import httpx
import json

class TopicExtractionService:
    def __init__(self, db_session):
        self.db = db_session
        self.topic_service = TopicService(db_session)
        self.material_service = StudyMaterialService(db_session)

    def _call_groq(self, content: str) -> List[str]:
        """Call Groq to get a list of topic strings.
        The prompt asks Groq to return a JSON array of distinct topic names.
        """
        prompt = (
            "Extract the main educational topics from the following text. "
            "Return a JSON array of short topic names (no duplicates).\n\n"
            f"Text:\n{content}\n"
        )
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
        }
        response = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        try:
            topics = json.loads(data["choices"][0]["message"]["content"].strip())
            if isinstance(topics, list):
                return topics
        except Exception:
            raw = data["choices"][0]["message"]["content"].strip()
            return [t.strip() for t in raw.split('\n') if t.strip()]
        return []

    def extract_and_store(self, material_id: int, subject_id: int) -> List["Topic"]:
        """Extract topics from a study material and store them.
        Returns the list of created Topic objects.
        """
        material = self.material_service.get_material(material_id)
        if not material:
            raise ValueError(f"Material {material_id} not found")
        content = getattr(material, "content", None)
        if not content:
            file_path = getattr(material, "file_path", None)
            if file_path:
                import os
                if os.path.exists(file_path):
                    from app.services.pdf_service import extract_text_from_pdf
                    try:
                        content = extract_text_from_pdf(file_path)
                    except Exception:
                        content = getattr(material, "title", "")
                else:
                    content = getattr(material, "title", "")
            else:
                content = getattr(material, "title", "")
        raw_topics = self._call_groq(content)
        seen = set()
        unique_topics = []
        for t in raw_topics:
            norm = t.lower()
            if norm not in seen:
                seen.add(norm)
                unique_topics.append(t)
        created = []
        for name in unique_topics:
            topic_in = TopicCreate(name=name, description=None)
            created_topic = self.topic_service.create_topic(subject_id, topic_in)
            created.append(created_topic)
        return created
