"""Validate translation structure before a model attempt is marked successful."""
import json


def parse_translation(text, *, count=None, ids=None):
    text = text.strip()
    if text.startswith('```'):
        text = text.removeprefix('```json').removeprefix('```').removesuffix('```').strip()
    value = json.loads(text)
    if ids is not None:
        if not isinstance(value, dict) or set(value) != set(ids) or not all(isinstance(v, str) and v.strip() for v in value.values()):
            raise ValueError('Translation IDs or values do not match')
    elif not isinstance(value, list) or len(value) != count or not all(isinstance(v, str) and v.strip() for v in value):
        raise ValueError('Translation count or values do not match')
    return value
