"""Service layer for Flashcard and Deck operations.

Provides CRUD for decks and flashcards, and retrieval methods.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import FlashcardDeck, Flashcard, Topic
from app.schemas.flashcard import FlashcardCreate, FlashcardDeckCreate

class FlashcardService:
    def __init__(self, db: Session):
        self.db = db

    # Deck operations
    def create_deck(self, subject_id: int, obj_in: FlashcardDeckCreate) -> FlashcardDeck:
        deck = FlashcardDeck(
            subject_id=subject_id,
            name=obj_in.name,
        )
        self.db.add(deck)
        self.db.commit()
        self.db.refresh(deck)
        return deck

    def get_deck(self, deck_id: int) -> Optional[FlashcardDeck]:
        return self.db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()

    def get_decks_by_subject(self, subject_id: int, skip: int = 0, limit: int = 100) -> List[FlashcardDeck]:
        return (
            self.db.query(FlashcardDeck)
            .filter(FlashcardDeck.subject_id == subject_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    # Flashcard operations
    def create_flashcard(self, deck_id: int, topic_id: Optional[int], obj_in: FlashcardCreate) -> Flashcard:
        flashcard = Flashcard(
            deck_id=deck_id,
            topic_id=topic_id,
            question=obj_in.question,
            answer=obj_in.answer,
            difficulty=obj_in.difficulty,
        )
        self.db.add(flashcard)
        self.db.commit()
        self.db.refresh(flashcard)
        return flashcard

    def get_flashcards_by_deck(self, deck_id: int, skip: int = 0, limit: int = 100) -> List[Flashcard]:
        return (
            self.db.query(Flashcard)
            .filter(Flashcard.deck_id == deck_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_flashcards_by_topic(self, topic_id: int, skip: int = 0, limit: int = 100) -> List[Flashcard]:
        return (
            self.db.query(Flashcard)
            .filter(Flashcard.topic_id == topic_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_flashcard(self, flashcard_id: int) -> None:
        obj = self.db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if obj:
            self.db.delete(obj)
            self.db.commit()
