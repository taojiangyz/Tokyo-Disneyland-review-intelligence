from datetime import date, timedelta

from app.security import DemoUsageGuard
from scripts.configure_interview_demo import read_values, update_lines


def test_rate_limit_is_per_client_and_recovers_after_window() -> None:
    guard = DemoUsageGuard(requests_per_minute=2)
    assert guard.check_request("client-a", now=100).allowed
    assert guard.check_request("client-a", now=101).allowed
    blocked = guard.check_request("client-a", now=102)
    assert not blocked.allowed
    assert blocked.reason == "rate_limit"
    assert guard.check_request("client-b", now=102).allowed
    assert guard.check_request("client-a", now=161).allowed


def test_daily_generation_budget_resets_on_new_day() -> None:
    today = date(2026, 8, 25)
    guard = DemoUsageGuard(generations_per_day=2)
    assert guard.reserve_generation(today).allowed
    assert guard.reserve_generation(today).allowed
    assert not guard.reserve_generation(today).allowed
    assert guard.reserve_generation(today + timedelta(days=1)).allowed


def test_zero_limits_disable_demo_guard() -> None:
    guard = DemoUsageGuard()
    for _ in range(100):
        assert guard.check_request("same-client", now=1).allowed
        assert guard.reserve_generation(date(2026, 8, 25)).allowed


def test_demo_env_update_preserves_existing_secrets_and_adds_limits() -> None:
    lines = ["GEMINI_API_KEY=private-value\n", "ALADDIN_API_TOKEN=old\n"]
    updated = update_lines(
        lines,
        {
            "ALADDIN_API_TOKEN": "new-hidden-token",
            "ALADDIN_RATE_LIMIT_PER_MINUTE": "20",
        },
    )
    values = read_values(updated)
    assert values["GEMINI_API_KEY"] == "private-value"
    assert values["ALADDIN_API_TOKEN"] == "new-hidden-token"
    assert values["ALADDIN_RATE_LIMIT_PER_MINUTE"] == "20"
