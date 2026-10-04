"""Deterministic presentation safeguards, not semantic answer validation."""
import re

OUTPUT_POLICY_VERSION = 'v2-localized-scope-ranking-ja'
ZH_RANKING_NOTICE = '以下仅列出检索到的评论观点，不能据此确定全体游客的排名或出现频率。'
EN_RANKING_NOTICE = 'These are views from the retrieved reviews; they do not establish rankings or frequencies across all visitors.'


def answer_language(query: str) -> str:
    if any('\u3040' <= c <= '\u30ff' for c in query):
        return 'Japanese'
    return 'Simplified Chinese' if any('\u4e00' <= c <= '\u9fff' for c in query) else 'English'


def asks_for_ranking(query: str) -> bool:
    return bool(re.search(
        r'最(?:常|多|少|受|满意|滿意|喜欢|喜歡|好|差|值得|も)|排名|排行|频率|頻率|占比|一番|ランキング|頻度'
        r'|\b(?:most|least|best|worst|top|rank(?:ing|ings)?|frequen(?:cy|cies|tly)|how often)\b',
        query, re.IGNORECASE,
    ))


def present_answer(query: str, answer: str) -> str:
    # Never create an apparent successful answer from an empty provider response.
    if not answer.strip():
        return answer
    language = answer_language(query)
    chinese = language == 'Simplified Chinese'
    label = '证据范围说明：' if chinese else 'Evidence scope statement:'
    scope = ('本回答仅基于检索到的评论。' if chinese
             else 'This answer is based only on the retrieved reviews.')
    if language == 'Japanese':
        label, scope = '根拠の範囲：', 'この回答は検索されたレビューのみに基づきます。'
    # Normalize only a standalone known label; preserve findings and citations.
    pattern = r'(?im)^(\s*(?:\*\*)?)(?:Evidence scope statement|证据范围声明|证据范围说明|根拠の範囲)\s*[:：]'
    result = re.sub(pattern, lambda m: m.group(1) + label, answer.strip())
    if not re.search(pattern, result):
        result += '\n\n' + label + scope
    if asks_for_ranking(query):
        notice = ZH_RANKING_NOTICE if chinese else EN_RANKING_NOTICE
        if language == 'Japanese':
            notice = '以下は検索されたレビューの意見であり、訪問者全体の順位や頻度を示すものではありません。'
        if notice not in result:
            result = notice + '\n\n' + result
    return result
