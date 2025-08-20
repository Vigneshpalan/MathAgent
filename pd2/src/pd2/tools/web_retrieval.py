import re
from ddgs import DDGS
from .config import logger

def clean_extracted_text(text: str) -> str:
    irrelevant_patterns = r"(class|lecture|syllabus|year|new zealand|india|plus)"
    lines = [line for line in text.split("\n") if not re.search(irrelevant_patterns, line, re.I)]
    return "\n".join(lines).strip()

async def retrieve_via_web(query: str) -> str:
    try:
        with DDGS() as ddgs:  # ✅ use sync context manager
            results = ddgs.text(query, max_results=3)  # ✅ this is a generator
            combined = "\n".join([r.get("body", "") for r in results if r.get("body")])
            if combined.strip():
                cleaned = clean_extracted_text(combined)
                return re.sub(r"[^0-9a-zA-Z\s\+\-\*\/\=\^\(\)\[\]\.\:]", "", cleaned)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
    return ""

