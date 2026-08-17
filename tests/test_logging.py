import json
import logging

from app.logging_config import JsonFormatter


def test_json_formatter_includes_request_context() -> None:
    record = logging.LogRecord(
        name="app.main",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.method = "POST"
    record.path = "/api/v1/analyze"
    record.status_code = 200
    record.duration_ms = 12.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "request_completed"
    assert payload["request_id"] == "request-123"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 12.5
