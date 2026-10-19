from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.messages import MessageResponse


class AIChatRequest(BaseModel):
    conversation_id: UUID
    message: str = Field(min_length=1)
    message_id: UUID | None = None
    provider: str = Field(default="ollama", pattern="^(openai|gemini|ollama|custom)$")
    model: str | None = Field(default=None, max_length=100)
    custom_api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    custom_api_key: str | None = Field(default=None, min_length=1, max_length=500)
    openai_api_key: str | None = Field(default=None, min_length=1, max_length=500)
    gemini_api_key: str | None = Field(default=None, min_length=1, max_length=500)


class CustomAPIModelsRequest(BaseModel):
    custom_api_base_url: str = Field(min_length=1, max_length=500)
    custom_api_key: str | None = Field(default=None, min_length=1, max_length=500)


class AIChatResponse(BaseModel):
    conversation_id: UUID
    provider: str
    model: str
    user_message: MessageResponse
    assistant_message: MessageResponse


class MeetingSummaryRequest(BaseModel):
    transcript: str = Field(min_length=10)
    provider: str = Field(default="ollama", pattern="^(openai|gemini|ollama|custom)$")
    model: str | None = Field(default=None, max_length=100)
    custom_api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    custom_api_key: str | None = Field(default=None, min_length=1, max_length=500)


class MeetingSummaryResponse(BaseModel):
    summary: str
    provider: str
    model: str
