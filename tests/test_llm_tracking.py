from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from app.services.llm_tracking import RequestTracking


def test_shared_provider_tracking_is_request_local():
    service = RequestTracking()
    service.model_name = 'default'
    service.reset_tracking()
    barrier = Barrier(2)

    def request(prompt):
        service.reset_tracking()
        service.last_prompt_id = prompt
        service.last_model_name = prompt + '-model'
        service.last_usage = {'total_tokens': len(prompt)}
        barrier.wait()
        return service.last_prompt_id, service.last_model_name, service.last_usage

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(request, ['review', 'agent']))
    assert results == [('review', 'review-model', {'total_tokens':6}), ('agent', 'agent-model', {'total_tokens':5})]
    assert service.last_prompt_id is None
    assert service.last_model_name == 'default'
