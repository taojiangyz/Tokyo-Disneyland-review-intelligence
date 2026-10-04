"""Offline telemetry summary. No model calls; unknown usage is never a zero-cost claim."""
import argparse
import json
import math
from collections import Counter
from pathlib import Path


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo), 2)


def summarize(events):
    calls = [e for e in events if 'call_id' in e]
    interactions = [e for e in events if e.get('event_type') == 'ui_interaction']
    tokens = {}
    for key in ('prompt_token_count', 'candidates_token_count', 'thoughts_token_count',
                'cached_content_token_count', 'total_token_count'):
        values = [e['usage'].get(key) for e in calls]
        tokens[key] = {'known_sum': sum(v for v in values if v is not None),
                       'unknown_calls': sum(v is None for v in values)}
    costs = [e['cost']['estimated_paid_usd'] for e in calls]
    durations = [e['duration_ms'] for e in calls]
    operations = {e['operation'] for e in calls}
    return {
        'calls': len(calls), 'completed_calls': sum(e['status'] == 'completed' for e in calls),
        'failed_calls': sum(e['status'] != 'completed' for e in calls),
        'fallback_attempts': sum(e['attempt'] > 1 for e in calls),
        'requests': len({e['request_id'] for e in calls}),
        'by_model': dict(Counter(e['model'] for e in calls)),
        'by_operation': {op: sum(e['operation'] == op for e in calls) for op in sorted(operations)},
        'tokens': tokens,
        'estimated_paid_usd_known_subtotal': round(sum(c for c in costs if c is not None), 10),
        'cost_unknown_calls': sum(c is None for c in costs),
        'estimated_paid_usd_total': round(sum(costs), 10) if costs and all(c is not None for c in costs) else None,
        'actual_billed_usd': None,
        'price_versions': sorted({e['cost']['price_version'] for e in calls if e['cost']['price_version']}),
        'sdk_attempt_latency_ms': {'samples': len(durations), 'p50': percentile(durations, .5),
                                   'p95': percentile(durations, .95)},
        'ui_interaction_latency_ms': {'samples': len(interactions),
            'p50': percentile([e['duration_ms'] for e in interactions], .5),
            'p95': percentile([e['duration_ms'] for e in interactions], .95)},
        'note': 'Token subtotals cover reported fields only. Latency pools successes and failures; inspect per-call records. UI timing includes API and translation, not browser rendering. Small samples are not capacity benchmarks.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('evals/results/llm_calls'))
    parser.add_argument('--output', type=Path, default=Path('evals/results/llm_summary.json'))
    parser.add_argument('--request-id')
    args = parser.parse_args()
    events, malformed, seen = [], 0, set()
    for path in sorted(args.input.glob('*.jsonl')):
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if args.request_id and event.get('request_id') != args.request_id:
                continue
            if event.get('call_id') in seen:
                continue
            if event.get('call_id'):
                seen.add(event['call_id'])
            events.append(event)
    report = summarize(events)
    report['malformed_lines'] = malformed
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
