from collections import defaultdict

from asyncpg.exceptions import PostgresError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import DatabaseConfigurationError


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.exception_handler(DatabaseConfigurationError)
    async def database_configuration_error_handler(_, exc: DatabaseConfigurationError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": str(exc),
                "hint": "Check DEVNEXUS_DATABASE_URL in your .env file.",
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error_handler(_, __: SQLAlchemyError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database connection failed.",
                "hint": "Check your Supabase database host, password, and connection string.",
            },
        )

    @app.exception_handler(PostgresError)
    async def postgres_error_handler(_, __: PostgresError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database connection failed.",
                "hint": (
                    "Copy a fresh Session pooler connection string from Supabase "
                    "and set it as DEVNEXUS_DATABASE_URL."
                ),
            },
        )

    @app.exception_handler(OSError)
    async def network_error_handler(_, __: OSError):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database network connection failed.",
                "hint": "Check whether your Supabase direct database host resolves, or use the Session pooler connection string.",
            },
        )

    return app


app = create_app()

# In-memory WebRTC signaling. Media flows directly between participants; the API only
# relays offer, answer, and ICE messages for the room.
meeting_connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)


@app.websocket("/webrtc/ws/{room_id}/{client_id}")
async def meeting_signaling(websocket: WebSocket, room_id: str, client_id: str):
    await websocket.accept()
    room = meeting_connections[room_id]
    existing_clients = list(room.items())
    room[client_id] = websocket
    for existing_id, existing_socket in existing_clients:
        await existing_socket.send_json({"type": "user-joined", "client_id": client_id})

    try:
        while True:
            message = await websocket.receive_json()
            target = message.get("target")
            target_socket = room.get(target)
            if target_socket:
                message["sender"] = client_id
                await target_socket.send_json(message)
    except WebSocketDisconnect:
        pass
    finally:
        room.pop(client_id, None)
        for client_socket in room.values():
            await client_socket.send_json({"type": "user-left", "client_id": client_id})
        if not room:
            meeting_connections.pop(room_id, None)
