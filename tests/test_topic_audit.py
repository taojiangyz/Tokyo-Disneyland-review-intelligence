from scripts.export_topic_audit import select_audit_sample


def test_audit_sample_prioritizes_uncertain_and_covers_segments():
    rows = []
    for region in ["CN", "HK", "KR"]:
        for rating in [2, 5]:
            for number in range(10):
                rows.append(
                    {
                        "review_id": f"{region}-{rating}-{number}",
                        "region": region,
                        "rating": rating,
                        "sentiment": "negative" if rating == 2 else "positive",
                        "confidence": 0.7 if number == 0 else 0.9,
                    }
                )
    sample = select_audit_sample(rows, 24, seed=3)
    ids = {row["review_id"] for row in sample}
    assert len(sample) == len(ids) == 24
    assert all(f"{region}-{rating}-0" in ids for region in ["CN", "HK", "KR"] for rating in [2, 5])
    assert len({(row["region"], row["rating"]) for row in sample}) == 6
