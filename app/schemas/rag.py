from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.documents import DocumentChunkResponse
from app.schemas.messages import MessageResponse


class RAGChatRequest(BaseModel):
    file_id: UUID
    question: str = Field(min_length=1)
    conversation_id: UUID | None = None
    provider: str = Field(default="ollama", pattern="^(openai|gemini|ollama|custom)$")
    model: str | None = Field(default=None, max_length=100)
    top_k: int = Field(default=5, ge=1, le=10)
    custom_api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    custom_api_key: str | None = Field(default=None, min_length=1, max_length=500)


class RAGChatResponse(BaseModel):
    file_id: UUID
    question: str
    answer: str
    provider: str
    model: str
    sources: list[DocumentChunkResponse]
    user_message: MessageResponse | None = None
    assistant_message: MessageResponse | None = None
