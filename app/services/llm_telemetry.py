"""Content-free telemetry for each application-level Gemini attempt."""
import json
import logging
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

logger = logging.getLogger(__name__)
FIELDS = ('prompt_token_count', 'candidates_token_count', 'thoughts_token_count',
          'cached_content_token_count', 'total_token_count')


def usage_from(response):
    metadata = getattr(response, 'usage_metadata', None)
    raw = metadata.model_dump(mode='json', exclude_none=True) if hasattr(metadata, 'model_dump') else {
        k: getattr(metadata, k, None) for k in FIELDS
    }
    return {k: raw.get(k) if isinstance(raw.get(k), int) and raw[k] >= 0 else None for k in FIELDS}


def estimate_cost(usage, model, *, price_file=None, today=None):
    result = {'estimated_paid_usd': None, 'actual_billed_usd': None,
              'billing_tier_declared': os.getenv('LLM_BILLING_TIER', 'unknown'),
              'price_version': None, 'reason': 'price_unavailable'}
    try:
        path = Path(price_file or os.getenv('LLM_PRICE_FILE', 'config/llm_prices.json'))
        prices = json.loads(path.read_text())
        result['price_version'] = prices['version']
        day = today or datetime.now(timezone.utc).date().isoformat()
        if not prices['valid_from'] <= day <= prices['valid_through']:
            result['reason'] = 'price_outside_validity'
            return result
        rates = prices['models'].get(model)
        if not rates:
            return result
        prompt, output, thoughts, cached, total = (usage[k] for k in FIELDS)
        if prompt is None or output is None or total is None:
            result['reason'] = 'usage_incomplete'
            return result
        # Optional zero-valued fields may be omitted; verify the total before pricing.
        thoughts, cached = thoughts or 0, cached or 0
        if cached > prompt or total != prompt + output + thoughts:
            result['reason'] = 'usage_inconsistent_or_unsupported'
            return result
        cost = ((prompt - cached) * rates['input'] + cached * rates['cached_input']
                + (output + thoughts) * rates['output']) / 1_000_000
        result.update(estimated_paid_usd=round(cost, 10), reason='estimated_standard_text')
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return result


def write_event(event):
    """Separate file per process prevents API/UI writers interleaving JSON records."""
    try:
        directory = Path(os.getenv('LLM_TELEMETRY_DIR', 'evals/results/llm_calls'))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f'calls-{socket.gethostname()}-{os.getpid()}.jsonl'
        data = (json.dumps(event, ensure_ascii=False) + '\n').encode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            if os.write(fd, data) != len(data):
                raise OSError('Incomplete telemetry write')
        finally:
            os.close(fd)
        return True
    except OSError:
        logger.warning('LLM telemetry could not be persisted')
        return False


def generate_text(client, models, prompt, *, request_id=None, operation='answer',
                  prompt_version='v1', attempts=None, validator=None):
    """Return text; append request-local attempt evidence even when all models fail."""
    attempts = attempts if attempts is not None else []
    request_id = request_id or str(uuid4())
    last_error = None
    for index, model in enumerate(dict.fromkeys(models), 1):
        start = perf_counter()
        event = dict(schema_version=1, timestamp=datetime.now(timezone.utc).isoformat(),
                     request_id=request_id, call_id=str(uuid4()), operation=operation,
                     prompt_version=prompt_version, attempt=index, model=model,
                     status='failed', error_type=None, usage={k: None for k in FIELDS})
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            event['usage'] = usage_from(response)
            text = response.text or ''
            if not text.strip():
                raise ValueError('Empty model response')
            if validator:
                validator(text)
            event['status'] = 'completed'
            return text
        except Exception as exc:
            last_error = exc
            event['error_type'] = type(exc).__name__
        finally:
            event['duration_ms'] = round((perf_counter() - start) * 1000, 2)
            event['cost'] = estimate_cost(event['usage'], model)
            attempts.append(event)
            event['persisted'] = write_event(event)
    assert last_error is not None
    raise last_error
