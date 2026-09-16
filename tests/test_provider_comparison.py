import json

import pytest

from scripts.compare_agent_reports import compare_reports


def write_report(path, provider, model, passed=2):
    path.write_text(
        json.dumps(
            {
                "mode": "live",
                "total": 2,
                "passed": passed,
                "results": [
                    {
                        "id": "a",
                        "live": {
                            "provider": provider,
                            "model": model,
                            "total_ms": 100,
                            "usage": {"total_tokens": 10},
                        },
                    },
                    {
                        "id": "b",
                        "live": {
                            "provider": provider,
                            "model": model,
                            "total_ms": 300,
                            "usage": {"total_tokens": 20},
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_compare_provider_reports(tmp_path) -> None:
    gemini = tmp_path / "gemini.json"
    local = tmp_path / "local.json"
    write_report(gemini, "gemini", "gemini-test")
    write_report(local, "openai_compatible", "qwen-test", passed=1)
    comparison = compare_reports([gemini, local], ["Gemini", "Qwen"])
    assert comparison["case_count"] == 2
    assert comparison["providers"][0]["p50_latency_ms"] == 200
    assert comparison["providers"][0]["total_tokens"] == 30
    assert comparison["providers"][1]["pass_rate"] == 0.5


def test_compare_rejects_mismatched_cases(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_report(first, "gemini", "g")
    write_report(second, "openai_compatible", "q")
    body = json.loads(second.read_text())
    body["results"][1]["id"] = "different"
    second.write_text(json.dumps(body), encoding="utf-8")
    with pytest.raises(ValueError, match="same evaluation case IDs"):
        compare_reports([first, second], ["A", "B"])
