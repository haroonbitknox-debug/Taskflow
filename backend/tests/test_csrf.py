from http.cookies import SimpleCookie
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, Response
from fastapi.testclient import TestClient

from app.api.dependencies import require_csrf
from app.api.routes.auth import (
    _clear_auth_cookies,
    _set_auth_cookies,
    router as auth_router,
)
from app.core.config import settings


def create_csrf_probe() -> FastAPI:
    probe = FastAPI()
    probe.include_router(auth_router, prefix="/api")

    @probe.post("/protected", dependencies=[Depends(require_csrf)])
    def protected() -> dict[str, bool]:
        return {"ok": True}

    return probe


def test_production_csrf_cookie_is_cross_site_compatible_and_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    with TestClient(create_csrf_probe(), base_url="https://testserver") as client:
        csrf_response = client.get("/api/auth/csrf")

        assert csrf_response.status_code == 200
        token = csrf_response.json()["csrf_token"]
        csrf_cookie = SimpleCookie()
        csrf_cookie.load(csrf_response.headers["set-cookie"])
        csrf_morsel = csrf_cookie[settings.csrf_cookie_name]
        assert csrf_morsel.value == token
        assert csrf_morsel["path"] == "/"
        assert csrf_morsel["max-age"] == str(settings.access_token_expire_minutes * 60)
        assert csrf_morsel["samesite"].casefold() == "none"
        assert csrf_morsel["secure"]
        assert not csrf_morsel["httponly"]
        assert client.cookies.get(settings.csrf_cookie_name) == token

        accepted = client.post(
            "/protected",
            headers={"X-CSRF-Token": token},
        )
        assert accepted.status_code == 200

        missing_header = client.post("/protected")
        assert missing_header.status_code == 403

        mismatched_header = client.post(
            "/protected",
            headers={"X-CSRF-Token": "not-the-cookie-token"},
        )
        assert mismatched_header.status_code == 403


def test_production_auth_cookies_are_cross_site_compatible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    response = Response()

    _set_auth_cookies(response, SimpleNamespace(id=1), "test-csrf-token")

    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)

    auth_cookie = cookies[settings.auth_cookie_name]
    assert auth_cookie["path"] == "/"
    assert auth_cookie["max-age"] == str(settings.access_token_expire_minutes * 60)
    assert auth_cookie["samesite"].casefold() == "none"
    assert auth_cookie["secure"]
    assert auth_cookie["httponly"]

    csrf_cookie = cookies[settings.csrf_cookie_name]
    assert csrf_cookie.value == "test-csrf-token"
    assert csrf_cookie["path"] == "/"
    assert csrf_cookie["max-age"] == str(settings.access_token_expire_minutes * 60)
    assert csrf_cookie["samesite"].casefold() == "none"
    assert csrf_cookie["secure"]
    assert not csrf_cookie["httponly"]


def test_auth_cookie_deletion_preserves_production_attributes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    response = Response()

    _clear_auth_cookies(response)

    cookies = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        cookies.load(header)

    for cookie_name in (settings.auth_cookie_name, settings.csrf_cookie_name):
        cookie = cookies[cookie_name]
        assert cookie["path"] == "/"
        assert cookie["max-age"] == "0"
        assert cookie["samesite"].casefold() == "none"
        assert cookie["secure"]

    assert cookies[settings.auth_cookie_name]["httponly"]
    assert not cookies[settings.csrf_cookie_name]["httponly"]


def test_development_csrf_cookie_keeps_lax_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "development")
    with TestClient(create_csrf_probe(), base_url="http://testserver") as client:
        csrf_response = client.get("/api/auth/csrf")

    cookie = SimpleCookie()
    cookie.load(csrf_response.headers["set-cookie"])
    csrf_morsel = cookie[settings.csrf_cookie_name]
    assert csrf_morsel["samesite"].casefold() == "lax"
    assert not csrf_morsel["secure"]
