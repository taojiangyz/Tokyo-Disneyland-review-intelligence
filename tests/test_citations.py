from app.citations import inspect_evidence_citations


def test_accepts_single_and_grouped_returned_ids() -> None:
    cited, unknown = inspect_evidence_citations(
        "Finding [181518036, b948413830da6471434689bb5b2b2fbf]",
        {"181518036", "b948413830da6471434689bb5b2b2fbf"},
    )
    assert cited == {"181518036", "b948413830da6471434689bb5b2b2fbf"}
    assert unknown == set()


def test_ignores_non_citation_bracketed_prose() -> None:
    cited, unknown = inspect_evidence_citations(
        "Low ratings [1-3 stars] are discussed without a source.",
        {"181518036"},
    )
    assert cited == set()
    assert unknown == set()


def test_reports_plausible_unknown_review_id() -> None:
    cited, unknown = inspect_evidence_citations(
        "Supported [181518036], but fabricated [999999999].",
        {"181518036"},
    )
    assert cited == {"181518036"}
    assert unknown == {"999999999"}
