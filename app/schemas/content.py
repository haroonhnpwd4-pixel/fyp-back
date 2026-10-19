from pydantic import BaseModel, Field


class SocialPostGenerateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    platform: str = Field(default="linkedin", max_length=50)
    tone: str = Field(default="professional", max_length=100)
    provider: str = Field(default="ollama", pattern="^(openai|gemini|ollama|custom)$")
    model: str | None = Field(default=None, max_length=100)
    custom_api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    custom_api_key: str | None = Field(default=None, min_length=1, max_length=500)


class SocialPostGenerateResponse(BaseModel):
    provider: str
    model: str
    platform: str
    post: str
    hashtags: list[str]


class LearningPlanGenerateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    level: str = Field(default="beginner", max_length=50)
    duration: str = Field(default="2 weeks", max_length=50)
    provider: str = Field(default="ollama", pattern="^(openai|gemini|ollama|custom)$")
    model: str | None = Field(default=None, max_length=100)
    custom_api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    custom_api_key: str | None = Field(default=None, min_length=1, max_length=500)


class LearningPlanGenerateResponse(BaseModel):
    provider: str
    model: str
    topic: str
    roadmap: list[str]
    assignments: list[str]
    quiz_questions: list[str]
