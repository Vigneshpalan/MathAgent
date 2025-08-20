# main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.pd2.crew import Pd2
from src.pd2.tools.math_agent import MathAgentTool as MathAgent
from src.pd2.tools.feedback import log_feedback
from src.pd2.tools.kb_manager import kb_manager

# ---------------- Logging ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stdin.reconfigure(encoding='utf-8')

# ---------------- Crew Instance ----------------
try:
    crew_instance = Pd2().crew()
    logger.info("✅ Crew initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize crew: {str(e)}")
    crew_instance = None

# ---------------- FastAPI ----------------
app = FastAPI(title="Pd2 Math Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Models ----------------
class QueryPayload(BaseModel):
    query: str

class FeedbackPayload(BaseModel):
    query: str
    response: str
    correct: bool
    corrected_solution: str

# ---------------- MathAgent ----------------
math_agent = MathAgent()

# ---------------- Endpoints ----------------
@app.post("/ask")
async def ask(payload: QueryPayload):
    if not crew_instance:
        return {"error": "Crew not initialized", "source": "Error"}
    try:
        # Route through MathAgent (crew orchestration can be added later)
        result = await math_agent.solve(payload.query)
        return {
            "reasoning": result.get("reasoning", ""),
            "answer": result.get("answer", ""),
            "source": result.get("source", "MathAgent")
        }
    except Exception as e:
        logger.error(f"Error in MathAgent: {str(e)}")
        return {"error": str(e), "source": "Error"}


@app.post("/feedback")
async def submit_feedback(payload: FeedbackPayload):
    try:
        log_feedback(
            query=payload.query,
            response=payload.response,
            correct=payload.correct,
            corrected_solution=payload.corrected_solution
        )
        if payload.correct and payload.corrected_solution:
            kb_manager.update(payload.query, payload.corrected_solution)
        return {"message": "Feedback received"}
    except Exception as e:
        logger.error(f"Error in feedback submission: {str(e)}")
        return {"error": str(e)}
