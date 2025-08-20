# src/pd2/tools/guardrails.py
import re
from .config import logger

def math_guardrails_ok(query: str) -> bool:
    query_lower = query.lower()
    banned_keywords = ["politics", "hello", "celebrity", "gossip", "nsfw", "crypto pump"]
    if any(k in query_lower for k in banned_keywords):
        logger.info("Guardrails → blocked due to banned keywords")
        return False

    math_keywords = ["solve","area","evaluate","simplify","integrate","differentiate",
                     "derivative","integral","limit","algebra","geometry","probability",
                     "combinatorics","matrix","vector","equation","root","sum","product","percent"]

    math_expr_pattern = r"(\d+\s*[\+\-\*\/=])|(\\frac|\\sqrt|\\begin\{.*?\}|\\end\{.*?\}|\$.*?\$)"
    numeric_patterns = r"(\d+|half-life|percent|times more|sum|difference|product|ratio|average|mean|median|probability)"
    math_action_verbs = r"(calculate|find|determine|required|after|minimum|maximum|how many|time|left|remaining|total)"

    mathy = (
        any(k in query_lower for k in math_keywords)
        or bool(re.search(math_expr_pattern, query, re.IGNORECASE | re.DOTALL))
        or (
            bool(re.search(numeric_patterns, query_lower, re.IGNORECASE)) and
            bool(re.search(math_action_verbs, query_lower, re.IGNORECASE))
        )
    )
    logger.info(f"Guardrails check → mathy={mathy}")
    return mathy

def output_guardrails_ok(answer: str) -> bool:
    banned_keywords = ["politics","celebrity","nsfw","crypto","gossip","adult","violence"]
    return not any(k in answer.lower() for k in banned_keywords)
