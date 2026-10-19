from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_messages(session: AsyncSession, conversation_id: UUID):
    result = await session.execute(
        text(
            """
            select id, conversation_id, role, content, created_at
            from public.messages
            where conversation_id = :conversation_id
            order by created_at asc, id asc
            """
        ),
        {"conversation_id": conversation_id},
    )
    return result.mappings().all()


async def create_message(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    role: str,
    content: str,
):
    result = await session.execute(
        text(
            """
            insert into public.messages (conversation_id, role, content)
            values (:conversation_id, :role, :content)
            returning id, conversation_id, role, content, created_at
            """
        ),
        {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        },
    )
    await session.commit()
    return result.mappings().one()


async def update_user_message_and_delete_following(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    message_id: UUID,
    content: str,
):
    result = await session.execute(
        text(
            """
            update public.messages
            set content = :content
            where id = :message_id
              and conversation_id = :conversation_id
              and role = 'user'
            returning id, conversation_id, role, content, created_at
            """
        ),
        {"content": content, "message_id": message_id, "conversation_id": conversation_id},
    )
    updated_message = result.mappings().first()
    if updated_message is None:
        return None

    await session.execute(
        text(
            """
            delete from public.messages
            where conversation_id = :conversation_id
              and (created_at, id) > (
                  select created_at, id
                  from public.messages
                  where id = :message_id and conversation_id = :conversation_id
              )
            """
        ),
        {"message_id": message_id, "conversation_id": conversation_id},
    )
    await session.commit()
    return updated_message


async def delete_messages_after(
    session: AsyncSession,
    *,
    conversation_id: UUID,
    message_id: UUID,
):
    result = await session.execute(
        text(
            """
            delete from public.messages
            where conversation_id = :conversation_id
              and (created_at, id) > (
                  select created_at, id
                  from public.messages
                  where id = :message_id and conversation_id = :conversation_id
              )
            """
        ),
        {"message_id": message_id, "conversation_id": conversation_id},
    )
    await session.commit()
    return result.rowcount

