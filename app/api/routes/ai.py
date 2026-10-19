from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIProviderError, generate_ai_response, list_custom_api_models
from app.auth.dependencies import get_current_user_id
from app.core.database import get_db_session
from app.core.config import get_settings
from app.repositories.conversations import get_conversation
from app.repositories.messages import (
    create_message,
    delete_messages_after,
    list_messages,
    update_user_message_and_delete_following,
)
from app.schemas.ai import AIChatRequest, AIChatResponse, CustomAPIModelsRequest
from app.schemas.blog import BlogGenerateRequest, BlogGenerateResponse
from app.schemas.content import (
    LearningPlanGenerateRequest,
    LearningPlanGenerateResponse,
    SocialPostGenerateRequest,
    SocialPostGenerateResponse,
)
from app.services.blog_service import generate_blog
from app.services.content_service import generate_learning_plan, generate_social_post

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/providers")
async def get_provider_status(_: UUID = Depends(get_current_user_id)):
    """Return safe provider configuration for the client; secrets are never exposed."""
    settings = get_settings()
    return {
        "providers": {
            "ollama": {"configured": bool(settings.ollama_host), "default_model": settings.ollama_model},
            "openai": {"configured": bool(settings.openai_api_key), "default_model": settings.openai_model},
            "gemini": {"configured": bool(settings.gemini_api_key), "default_model": settings.gemini_model},
            "custom": {
                "configured": bool(settings.custom_api_base_url and settings.custom_api_model),
                "default_model": settings.custom_api_model,
                "requires_api_key": not bool(settings.custom_api_key),
            },
        }
    }


@router.post("/custom-models")
async def get_custom_api_models(
    payload: CustomAPIModelsRequest,
    _: UUID = Depends(get_current_user_id),
):
    try:
        models = await list_custom_api_models(
            base_url=payload.custom_api_base_url,
            api_key=payload.custom_api_key,
        )
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return {"models": models}


async def ensure_conversation_access(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    user_id: UUID,
):
    conversation = await get_conversation(session, conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation was not found.",
        )


@router.post("/chat", response_model=AIChatResponse)
async def chat_with_ai(
    payload: AIChatRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    await ensure_conversation_access(
        session,
        conversation_id=payload.conversation_id,
        user_id=user_id,
    )

    previous_messages = await list_messages(session, payload.conversation_id)
    user_message = await create_message(
        session,
        conversation_id=payload.conversation_id,
        role="user",
        content=payload.message,
    )
    ai_messages = [
        {"role": message["role"], "content": message["content"]}
        for message in previous_messages
    ]
    ai_messages.append({"role": "user", "content": payload.message})

    try:
        assistant_content, model = await generate_ai_response(
            provider=payload.provider,
            messages=ai_messages,
            model=payload.model,
            custom_api_base_url=payload.custom_api_base_url,
            custom_api_key=payload.custom_api_key,
            openai_api_key=payload.openai_api_key,
            gemini_api_key=payload.gemini_api_key,
        )
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    assistant_message = await create_message(
        session,
        conversation_id=payload.conversation_id,
        role="assistant",
        content=assistant_content,
    )

    return AIChatResponse(
        conversation_id=payload.conversation_id,
        provider=payload.provider,
        model=model,
        user_message=user_message,
        assistant_message=assistant_message,
    )


@router.post("/chat/edit", response_model=AIChatResponse)
async def edit_chat_message(
    payload: AIChatRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    await ensure_conversation_access(session, conversation_id=payload.conversation_id, user_id=user_id)
    if payload.message_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A message ID is required.")

    previous_messages = await list_messages(session, payload.conversation_id)
    target_index = next(
        (index for index, message in enumerate(previous_messages) if message["id"] == payload.message_id),
        None,
    )
    if target_index is None or previous_messages[target_index]["role"] != "user":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User message was not found.")

    ai_messages = [
        {"role": item["role"], "content": item["content"]}
        for item in previous_messages[:target_index]
    ] + [{"role": "user", "content": payload.message}]
    assistant_content, model = await _generate_chat_content(payload, ai_messages)
    user_message = await update_user_message_and_delete_following(
        session,
        conversation_id=payload.conversation_id,
        message_id=payload.message_id,
        content=payload.message,
    )
    if user_message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User message was not found.")
    assistant_message = await create_message(
        session,
        conversation_id=payload.conversation_id,
        role="assistant",
        content=assistant_content,
    )
    return AIChatResponse(
        conversation_id=payload.conversation_id,
        provider=payload.provider,
        model=model,
        user_message=user_message,
        assistant_message=assistant_message,
    )


@router.post("/chat/retry", response_model=AIChatResponse)
async def retry_chat_reply(
    payload: AIChatRequest,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    await ensure_conversation_access(session, conversation_id=payload.conversation_id, user_id=user_id)
    if payload.message_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A message ID is required.")

    previous_messages = await list_messages(session, payload.conversation_id)
    target_index = next(
        (index for index, message in enumerate(previous_messages) if message["id"] == payload.message_id),
        None,
    )
    if target_index is None or previous_messages[target_index]["role"] != "user":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User message was not found.")

    user_message = previous_messages[target_index]
    ai_messages = [
        {"role": item["role"], "content": item["content"]}
        for item in previous_messages[:target_index + 1]
    ]
    assistant_content, model = await _generate_chat_content(payload, ai_messages)
    await delete_messages_after(
        session,
        conversation_id=payload.conversation_id,
        message_id=payload.message_id,
    )
    assistant_message = await create_message(
        session,
        conversation_id=payload.conversation_id,
        role="assistant",
        content=assistant_content,
    )
    return AIChatResponse(
        conversation_id=payload.conversation_id,
        provider=payload.provider,
        model=model,
        user_message=user_message,
        assistant_message=assistant_message,
    )


async def _generate_chat_content(
    payload: AIChatRequest,
    ai_messages: list[dict[str, str]],
) -> tuple[str, str]:
    try:
        assistant_content, model = await generate_ai_response(
            provider=payload.provider,
            messages=ai_messages,
            model=payload.model,
            custom_api_base_url=payload.custom_api_base_url,
            custom_api_key=payload.custom_api_key,
            openai_api_key=payload.openai_api_key,
            gemini_api_key=payload.gemini_api_key,
        )
    except AIProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return assistant_content, model


@router.post("/generate-blog", response_model=BlogGenerateResponse)
async def generate_blog_content(
    payload: BlogGenerateRequest,
    _: UUID = Depends(get_current_user_id),
):
    return await generate_blog(payload)


@router.post("/generate-post", response_model=SocialPostGenerateResponse)
async def generate_social_post_content(
    payload: SocialPostGenerateRequest,
    _: UUID = Depends(get_current_user_id),
):
    return await generate_social_post(payload)


@router.post("/learn", response_model=LearningPlanGenerateResponse)
async def generate_learning_assistant_content(
    payload: LearningPlanGenerateRequest,
    _: UUID = Depends(get_current_user_id),
):
    return await generate_learning_plan(payload)
