from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.security import DemoUsageGuard
from app.services.gemini_service import GeminiService
from app.services.llm_service import OpenAICompatibleService
from app.services.llm_telemetry import CURRENT_REQUEST_ID


@pytest.mark.parametrize('provider', ['gemini', 'openai_compatible'])
def test_review_api_preserves_auth_provider_and_presentation(provider, monkeypatch, tmp_path):
    monkeypatch.setenv('ALADDIN_API_TOKEN', 'test-token')
    monkeypatch.setenv('LLM_TELEMETRY_DIR', str(tmp_path))
    payload = dict(review_id='123456789', region='KR', rating=5, review_date='2025-01-01', text='Friendly staff')
    rag = SimpleNamespace(retrieve_for_evaluation=lambda **kwargs: ([(SimpleNamespace(payload=payload, score=.9),.9)], {'timing_ms':{},'hybrid_candidate_count':1,'final_selected_count':1}))
    if provider == 'gemini':
        service = GeminiService.__new__(GeminiService)
        service.model_name = service.fallback_model_name = 'mock-model'
        service.client = SimpleNamespace(models=Mock())
        service.client.models.generate_content.return_value = SimpleNamespace(text='Staff are friendly [123456789].')
    else:
        response = Mock()
        response.json.return_value = {'model':'mock-model','choices':[{'message':{'content':'Staff are friendly [123456789].'}}],'usage':{'total_tokens':12}}
        session = Mock();session.post.return_value = response
        service = OpenAICompatibleService(model_name='mock-model',session=session)
    monkeypatch.setattr(app.state,'rag_service',rag,raising=False)
    monkeypatch.setattr(app.state,'llm_service',service,raising=False)
    monkeypatch.setattr(app.state,'demo_usage_guard',DemoUsageGuard(),raising=False)
    client = TestClient(app)
    assert client.post('/api/v1/analyze',json={'query':'What do visitors praise most?'}).status_code == 401
    response = client.post('/api/v1/analyze',json={'query':'What do visitors praise most?'},headers={'X-Aladdin-Token':'test-token','X-Request-ID':'merged-test'})
    assert response.status_code == 200
    data = response.json(); generation = data['trace']['generation']
    assert generation['status'] == 'completed'
    assert generation['provider'] == provider
    assert generation['prompt_id'] == 'review_answer'
    assert generation['prompt_version'] == '3.0.0'
    assert data['answer'].startswith('These are views from the retrieved reviews;')
    assert '[123456789]' in data['answer']
    if provider == 'gemini':
        assert generation['attempts'][0]['request_id'] == 'merged-test'
    assert CURRENT_REQUEST_ID.get() is None
