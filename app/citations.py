from __future__ import annotations

import re
from collections.abc import Iterable


BRACKET_GROUP = re.compile(r"\[([^\]]+)\]")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{5,}")


def inspect_evidence_citations(
    answer: str,
    evidence_ids: Iterable[str],
) -> tuple[set[str], set[str]]:
    """Return cited evidence IDs and plausible unknown review IDs.

    Gemini sometimes groups citations as ``[id1, id2]``. Treating the whole
    bracket body as one ID creates false failures, so matching is performed
    against each returned ID. Unknown tokens are reported only when they have
    the same broad numeric/hex shape as IDs in the evidence set; ordinary
    bracketed prose or ranges are ignored.
    """
    expected = {str(item) for item in evidence_ids if item}
    groups = BRACKET_GROUP.findall(answer or "")
    cited: set[str] = set()
    for review_id in expected:
        pattern = re.compile(
            rf"(?<![A-Za-z0-9_-]){re.escape(review_id)}(?![A-Za-z0-9_-])"
        )
        if any(pattern.search(group) for group in groups):
            cited.add(review_id)

    has_numeric_ids = any(item.isdigit() and len(item) >= 6 for item in expected)
    has_hex_ids = any(
        len(item) >= 16 and re.fullmatch(r"[0-9a-fA-F]+", item)
        for item in expected
    )
    unknown: set[str] = set()
    for group in groups:
        for token in TOKEN.findall(group):
            if token in expected:
                continue
            plausible_numeric = has_numeric_ids and token.isdigit()
            plausible_hex = (
                has_hex_ids
                and len(token) >= 16
                and bool(re.fullmatch(r"[0-9a-fA-F]+", token))
            )
            if plausible_numeric or plausible_hex:
                unknown.add(token)
    return cited, unknown
