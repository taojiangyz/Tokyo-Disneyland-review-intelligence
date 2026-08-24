from scripts.evaluate_topic_labels import evaluate


def test_topic_evaluation_computes_multilabel_metrics():
    rows = [
        {"status": "verified", "ai_topics": ["a", "b"], "human_topics": ["a", "b"], "ai_sentiment": "positive", "human_sentiment": "positive"},
        {"status": "verified", "ai_topics": ["a", "c"], "human_topics": ["a"], "ai_sentiment": "positive", "human_sentiment": "negative"},
        {"status": "skipped", "ai_topics": ["x"], "human_topics": [], "ai_sentiment": "neutral", "human_sentiment": ""},
    ]
    result = evaluate(rows)
    assert result["reviewed"] == 3
    assert result["verified"] == 2
    assert result["topic_exact_match"] == 0.5
    assert result["topic_micro_precision"] == 0.75
    assert result["topic_micro_recall"] == 1.0
    assert result["topic_micro_f1"] == 0.8571
    assert result["sentiment_accuracy"] == 0.5
