from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user_id
from app.core.database import get_db_session
from app.schemas.ai import MeetingSummaryRequest, MeetingSummaryResponse
from app.services.meeting_service import generate_meeting_summary

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("/summaries")
async def list_meeting_summaries(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
):
    result = await session.execute(
        text(
            """
            select id, meeting_id, summary, transcript, created_at
            from public.meeting_summaries
            where user_id = :user_id
            order by created_at desc
            """
        ),
        {"user_id": user_id},
    )
    return result.mappings().all()


@router.post("/summarize", response_model=MeetingSummaryResponse)
async def summarize_meeting(
    request: MeetingSummaryRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Generate a summary from a meeting transcript."""
    summary, selected_model = await generate_meeting_summary(
        transcript=request.transcript,
        provider=request.provider,
        model=request.model,
        custom_api_base_url=request.custom_api_base_url,
        custom_api_key=request.custom_api_key,
    )
    return MeetingSummaryResponse(
        summary=summary,
        provider=request.provider,
        model=selected_model,
    )
