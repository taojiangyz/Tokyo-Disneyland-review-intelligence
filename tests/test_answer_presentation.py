import pytest
from app.services.answer_presentation import present_answer, asks_for_ranking, ZH_RANKING_NOTICE, EN_RANKING_NOTICE


@pytest.mark.parametrize('query', ['What receives the most praise?', '高评分游客最满意哪些方面？', '香港游客最常提到什么？'])
def test_ranking_notice_precedes_claims_and_is_idempotent(query):
    source = 'Finding [review-42].'
    result = present_answer(query, source)
    assert result.startswith(ZH_RANKING_NOTICE if '游客' in query else EN_RANKING_NOTICE)
    assert source in result
    assert present_answer(query, result) == result


def test_chinese_footer_label_preserves_citations():
    source = '餐饮有不同评价 [abc, def]。\n\nEvidence scope statement: 本回答仅基于检索到的评论。'
    result = present_answer('餐饮贵吗？', source)
    assert 'Evidence scope statement' not in result
    assert '[abc, def]' in result
    assert result.count('证据范围说明：') == 1
    assert ZH_RANKING_NOTICE not in result


@pytest.mark.parametrize('query', ['What about payment methods?', '最新的评论说了什么？', 'The atmosphere was mostly pleasant?', '天气如何？'])
def test_nonranking_questions_do_not_get_ranking_notice(query):
    assert not asks_for_ranking(query)


def test_empty_output_stays_empty():
    assert present_answer('最常见？', '') == ''


def test_japanese_question_retains_japanese_presentation():
    from app.services.answer_presentation import answer_language
    query = '一番多い不満は何ですか？'
    assert answer_language(query) == 'Japanese'
    answer = present_answer(query, '待ち時間です [123456789]。')
    assert answer.startswith('以下は検索されたレビュー')
    assert '根拠の範囲：' in answer
    assert present_answer(query, answer) == answer
