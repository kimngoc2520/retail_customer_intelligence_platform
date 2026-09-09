import httpx
import pytest

from app.api_client import AnalyticsAPIError, ask_api


def test_api_client_posts_question(monkeypatch) -> None:
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, kwargs=kwargs)
        return httpx.Response(200, json={"success": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)
    assert ask_api("Show revenue by month.", base_url="http://api:8000") == {"success": True}
    assert captured["url"] == "http://api:8000/ask"
    assert captured["kwargs"]["json"] == {"question": "Show revenue by month."}


def test_api_client_wraps_http_errors(monkeypatch) -> None:
    def fake_post(url, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(AnalyticsAPIError):
        ask_api("Show revenue by month.")
