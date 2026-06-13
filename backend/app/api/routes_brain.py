"""`POST /brain/query` — ask a question, get an answer grounded in the org's data."""

from __future__ import annotations

from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_tenant_cursor
from app.rag.answer import ClaudeAnswerClient
from app.rag.embeddings import Embedder
from app.rag.query import answer_question
from app.rag.retriever import PostgresRetriever

router = APIRouter(prefix="/brain", tags=["brain"])


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)


class SourceOut(BaseModel):
    interaction_id: str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


@router.post("/query", response_model=QueryResponse)
async def query_brain(
    body: QueryRequest,
    cur: Annotated[psycopg.AsyncCursor, Depends(get_tenant_cursor)],
) -> QueryResponse:
    """Retrieve org-scoped context and return a sourced answer.

    The cursor is already scoped to the caller's org/user/role, so retrieval can
    only ever see this tenant's chunks (enforced by RLS).
    """
    result = await answer_question(
        body.question,
        Embedder(),
        PostgresRetriever(cur),
        ClaudeAnswerClient(),
        top_k=body.top_k,
    )
    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceOut(interaction_id=s.interaction_id, snippet=s.snippet) for s in result.sources
        ],
    )
