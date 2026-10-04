"""Deterministic presentation safeguards, not semantic answer validation."""
import re

OUTPUT_POLICY_VERSION = 'v1-localized-scope-ranking'
ZH_RANKING_NOTICE = '以下仅列出检索到的评论观点，不能据此确定全体游客的排名或出现频率。'
EN_RANKING_NOTICE = 'These are views from the retrieved reviews; they do not establish rankings or frequencies across all visitors.'


def asks_for_ranking(query: str) -> bool:
    return bool(re.search(
        r'最(?:常|多|少|受|满意|滿意|喜欢|喜歡|好|差|值得)|排名|排行|频率|頻率|占比'
        r'|\b(?:most|least|best|worst|top|rank(?:ing|ings)?|frequen(?:cy|cies|tly)|how often)\b',
        query, re.IGNORECASE,
    ))


def present_answer(query: str, answer: str) -> str:
    # Never create an apparent successful answer from an empty provider response.
    if not answer.strip():
        return answer
    chinese = any('\u4e00' <= c <= '\u9fff' for c in query)
    label = '证据范围说明：' if chinese else 'Evidence scope statement:'
    scope = ('本回答仅基于检索到的评论。' if chinese
             else 'This answer is based only on the retrieved reviews.')
    # Normalize only a standalone known label; preserve findings and citations.
    pattern = r'(?im)^(\s*(?:\*\*)?)(?:Evidence scope statement|证据范围声明|证据范围说明)\s*[:：]'
    result = re.sub(pattern, lambda m: m.group(1) + label, answer.strip())
    if not re.search(pattern, result):
        result += '\n\n' + label + scope
    if asks_for_ranking(query):
        notice = ZH_RANKING_NOTICE if chinese else EN_RANKING_NOTICE
        if notice not in result:
            result = notice + '\n\n' + result
    return result
