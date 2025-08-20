# src/pd2/tools/feedback.py
import json
from datetime import datetime
from .config import FEEDBACK_LOG, logger
from .kb_manager import kb_manager

def log_feedback(query: str, response: str, correct: bool, corrected_solution: str = "") -> None:
    data = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": response,
        "correct": correct,
        "corrected_solution": corrected_solution,
    }
    try:
        with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to log feedback: {e}")

    if not correct and corrected_solution:
        kb_manager.update(query, corrected_solution)
