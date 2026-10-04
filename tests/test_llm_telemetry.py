import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.llm_telemetry import FIELDS, estimate_cost, generate_text
from scripts.summarize_llm_usage import summarize
from scripts.run_regression import evaluate_response


def response(text='answer'):
    return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(
        prompt_token_count=100, candidates_token_count=20, thoughts_token_count=10,
        cached_content_token_count=40, total_token_count=130))


def test_usage_cost_and_no_sensitive_log(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(tmp_path))
    client = SimpleNamespace(models=Mock())
    client.models.generate_content.return_value = response()
    attempts = []
    assert generate_text(client, ['gemini-3.5-flash-lite'], 'SECRET PROMPT',
                         attempts=attempts, request_id='r') == 'answer'
    cost = estimate_cost(attempts[0]['usage'], 'gemini-3.5-flash-lite', today='2026-10-04')
    assert cost['estimated_paid_usd'] == pytest.approx((60*.3+40*.03+30*2.5)/1e6)
    assert cost['actual_billed_usd'] is None
    contents = next(tmp_path.glob('*.jsonl')).read_text()
    assert 'SECRET' not in contents and 'answer' not in json.loads(contents).get('response', '')
    assert json.loads(contents)['usage']['total_token_count'] == 130


def test_unknown_and_expired_price_are_not_zero():
    usage = {k: None for k in FIELDS}
    assert estimate_cost(usage, 'unknown')['estimated_paid_usd'] is None
    assert estimate_cost(usage, 'gemini-3.5-flash-lite', today='2027-01-01')['reason'] == 'price_outside_validity'
    assert estimate_cost(usage, 'gemini-3.5-flash-lite', today='2026-10-04')['estimated_paid_usd'] is None


def test_failed_and_empty_calls_retain_unknown_or_used_tokens(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(tmp_path))
    client = SimpleNamespace(models=Mock())
    client.models.generate_content.side_effect = [RuntimeError('SECRET'), response('')]
    attempts = []
    with pytest.raises(ValueError):
        generate_text(client, ['one', 'two'], 'private', attempts=attempts)
    assert len(attempts) == 2
    assert attempts[0]['usage']['total_token_count'] is None
    assert attempts[1]['usage']['total_token_count'] == 130
    report = summarize(attempts)
    assert report['failed_calls'] == 2
    assert report['tokens']['total_token_count']['unknown_calls'] == 1
    assert report['estimated_paid_usd_total'] is None
    assert 'SECRET' not in next(tmp_path.glob('*.jsonl')).read_text()


def test_concurrent_requests_are_separate(tmp_path, monkeypatch):
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(tmp_path))
    client = SimpleNamespace(models=Mock())
    client.models.generate_content.return_value = response()
    def run(i):
        attempts = []
        generate_text(client, [f'model-{i}'], 'x', request_id=str(i), attempts=attempts)
        return attempts[0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        events = list(pool.map(run, range(8)))
    assert all(e['model'] == 'model-'+e['request_id'] for e in events)
    assert len([json.loads(l) for l in next(tmp_path.glob('*.jsonl')).read_text().splitlines()]) == 8


def test_degraded_answer_does_not_pass_normal_case():
    case = {'expect': {'min_evidence': 1}}
    data = {'evidence': [{'review_id': 'r'}], 'trace': {'generation': {'status': 'degraded'}}}
    assert evaluate_response(case, data)
    case = {'expect': {'max_evidence': 0, 'generation_status': 'skipped_no_evidence'}}
    assert not evaluate_response(case, {'evidence': [], 'trace': {'generation': {'status': 'skipped_no_evidence'}}})


def test_logging_failure_does_not_repeat_generation(tmp_path, monkeypatch):
    path = tmp_path/'not-a-directory'; path.write_text('x')
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(path))
    client = SimpleNamespace(models=Mock())
    client.models.generate_content.return_value = response()
    attempts = []
    assert generate_text(client, ['one', 'two'], 'x', attempts=attempts) == 'answer'
    assert not attempts[0]['persisted']
    assert client.models.generate_content.call_count == 1


def test_bad_translation_records_usage_and_tries_fallback(tmp_path, monkeypatch):
    from app.services.translation_parsing import parse_translation
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(tmp_path))
    client = SimpleNamespace(models=Mock())
    client.models.generate_content.side_effect = [response('[42]'), response('["translated"]')]
    attempts = []
    text = generate_text(client, ['one', 'two'], 'x', attempts=attempts,
                         validator=lambda text: parse_translation(text, count=1))
    assert parse_translation(text, count=1) == ['translated']
    assert attempts[0]['status'] == 'failed'
    assert attempts[0]['usage']['total_token_count'] == 130
    assert attempts[1]['status'] == 'completed'


def test_request_trace_is_local_and_no_evidence_skips_llm(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    rag = SimpleNamespace(retrieve_for_evaluation=lambda **kwargs: (
        [], {'hybrid_candidate_count': 0, 'final_selected_count': 0, 'timing_ms': {}}))
    gemini = Mock()
    monkeypatch.setattr(app.state, 'rag_service', rag, raising=False)
    monkeypatch.setattr(app.state, 'gemini_service', gemini, raising=False)
    client = TestClient(app)  # No lifespan: no model loads, no external requests.
    result = client.post('/api/v1/analyze', json={'query': 'nothing here'}, headers={'X-Request-ID': 'isolated'})
    assert result.status_code == 200
    trace = result.json()['trace']
    assert trace['request_id'] == result.headers['X-Request-ID'] == 'isolated'
    assert trace['generation']['model'] is None
    assert trace['generation']['attempts'] == []
    assert trace['generation']['status'] == 'skipped_no_evidence'
    gemini.generate_answer.assert_not_called()


def test_grouped_citations_accept_valid_ids_and_reject_unknown_ids():
    case = {'expect': {'min_evidence': 1}}
    data = {'evidence': [{'review_id': 'a'}, {'review_id': 'b'}],
            'answer': 'Finding [a, b].', 'trace': {'generation': {'status': 'completed'}}}
    assert not evaluate_response(case, data)
    data['answer'] = 'Finding [a, fabricated].'
    assert 'answer cites review IDs outside retrieved evidence' in evaluate_response(case, data)
