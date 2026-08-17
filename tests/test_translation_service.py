from app.services.translation_service import contains_korean, load_cache, save_cache


def test_contains_korean_detects_hangul_only() -> None:
    assert contains_korean("대기 시간이 길어요")
    assert not contains_korean("排队时间很长")
    assert not contains_korean("The queue is long")


def test_translation_cache_round_trip(tmp_path) -> None:
    cache_path = tmp_path / "translations.json"
    expected = {"review-1": "等待时间很长。"}

    save_cache(expected, cache_path)

    assert load_cache(cache_path) == expected
    assert not cache_path.with_suffix(".json.tmp").exists()
