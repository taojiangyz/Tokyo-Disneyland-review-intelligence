import re

from app.agent.state import AgentTask


COMPARISON_TERMS = (
    "compare",
    "comparison",
    "versus",
    " vs ",
    "difference",
    "比较",
    "对比",
    "差异",
    "比較",
    "違い",
)
IMPROVEMENT_TERMS = (
    "prioritize",
    "priority",
    "recommend",
    "improve",
    "improvement",
    "improvements",
    "action",
    "改善",
    "行动",
    "行動",
    "対策",
    "优先",
    "優先",
    "建议",
    "提案",
)
ROOT_CAUSE_TERMS = (
    "root cause",
    "cause",
    "causes",
    "complaint",
    "complaints",
    "dissatisfaction",
    "negative review",
    "low-rated",
    "low rated",
    "low rating",
    "problem",
    "issue",
    "不满",
    "投诉",
    "根因",
    "原因",
    "差评",
    "低评分",
    "問題",
    "不満",
    "苦情",
    "低評価",
)

MARKET_ALIASES = {
    "CN": ("china", "chinese", "mainland", "中国", "中国大陆", "中国本土"),
    "HK": ("hong kong", "香港"),
    "KR": ("south korea", "korea", "korean", "韩国", "韓国"),
}


def has_root_cause_intent(query: str) -> bool:
    normalized = query.casefold()
    return any(_contains_term(normalized, term) for term in ROOT_CAUSE_TERMS)


def _contains_term(normalized_query: str, term: str) -> bool:
    candidate = term.casefold().strip()
    if candidate.isascii():
        return bool(
            re.search(
                rf"(?<![a-z]){re.escape(candidate)}(?![a-z])",
                normalized_query,
            )
        )
    return candidate in normalized_query


def infer_markets(query: str) -> list[str]:
    normalized = f" {query.casefold()} "
    return [
        market
        for market, aliases in MARKET_ALIASES.items()
        if any(alias in normalized for alias in aliases)
    ]


def route_task(query: str) -> AgentTask:
    normalized = query.casefold()
    if any(_contains_term(normalized, term) for term in COMPARISON_TERMS):
        return "market_comparison"
    if any(_contains_term(normalized, term) for term in IMPROVEMENT_TERMS):
        return "improvement_planning"
    if has_root_cause_intent(query):
        return "root_cause_analysis"
    return "evidence_qa"
