"""Phase 14 – Flashcards routes.

Endpoints:
  POST /flashcards/generate
  GET  /flashcards/decks
  GET  /flashcards/decks/{deck_id}
  GET  /flashcards/topic/{topic_id}
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.flashcard_service import FlashcardService
from app.services.flashcard_generation_service import FlashcardGenerationService
from app.schemas.flashcard import (
    Flashcard,
    FlashcardDeck,
    FlashcardDeckCreate,
)
from pydantic import BaseModel, Field

router = APIRouter(tags=["Flashcards"])


class FlashcardGenerateRequest(BaseModel):
    subject_id: int = Field(..., ge=1)
    deck_name: str = Field(..., max_length=255)
    topics: List[str] = Field(..., min_items=1, description="List of topic names to generate flashcards for")
    cards_per_topic: int = Field(default=5, ge=1, le=20)


class FlashcardGenerateResponse(BaseModel):
    deck: FlashcardDeck
    flashcards: List[Flashcard]


@router.post("/flashcards/generate", response_model=FlashcardGenerateResponse)
def generate_flashcards(
    payload: FlashcardGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate flashcards for the supplied topics and store them in a new deck."""
    fc_svc = FlashcardService(db)
    deck = fc_svc.create_deck(
        subject_id=payload.subject_id,
        obj_in=FlashcardDeckCreate(name=payload.deck_name),
    )
    gen_svc = FlashcardGenerationService(db)
    cards = gen_svc.generate_and_store(
        deck_id=deck.id,
        topics=payload.topics,
        cards_per_topic=payload.cards_per_topic,
    )
    return FlashcardGenerateResponse(deck=deck, flashcards=cards)


@router.get("/flashcards/decks", response_model=List[FlashcardDeck])
def list_decks(
    subject_id: int = Query(..., ge=1, description="Filter decks by subject"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return all flashcard decks for a given subject."""
    return FlashcardService(db).get_decks_by_subject(
        subject_id=subject_id, skip=skip, limit=limit
    )


@router.get("/flashcards/decks/{deck_id}", response_model=FlashcardDeck)
def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
):
    """Return a single flashcard deck by ID."""
    deck = FlashcardService(db).get_deck(deck_id)
    if deck is None:
        raise HTTPException(status_code=404, detail="Flashcard deck not found")
    return deck


@router.get("/flashcards/topic/{topic_id}", response_model=List[Flashcard])
def list_flashcards_for_topic(
    topic_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return all flashcards associated with a given topic."""
    return FlashcardService(db).get_flashcards_by_topic(
        topic_id=topic_id, skip=skip, limit=limit
    )
