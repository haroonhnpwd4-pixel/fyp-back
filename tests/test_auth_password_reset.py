import asyncio

import app.services.auth_service as auth_service


def test_request_password_reset_returns_temporary_password_for_registered_user(monkeypatch):
    async def fake_get_user_by_email(session, email):
        return {"id": "00000000-0000-0000-0000-000000000001", "email": email}

    async def fake_update_user_password_hash(session, user_id, password_hash):
        assert password_hash
        assert user_id == "00000000-0000-0000-0000-000000000001"

    monkeypatch.setattr(auth_service, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_service, "update_user_password_hash", fake_update_user_password_hash)

    async def run_flow():
        return await auth_service.request_password_reset(None, "user@example.com")

    result = asyncio.run(run_flow())

    assert "temporary password" in result["message"].lower()


def test_request_password_reset_returns_generic_message_for_unknown_email(monkeypatch):
    async def fake_get_user_by_email(session, email):
        return None

    monkeypatch.setattr(auth_service, "get_user_by_email", fake_get_user_by_email)

    async def run_flow():
        return await auth_service.request_password_reset(None, "missing@example.com")

    result = asyncio.run(run_flow())

    assert "registered" in result["message"].lower()
