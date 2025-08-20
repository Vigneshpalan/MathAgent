# src/pd2/tools/config.py
import logging
from pathlib import Path

# ------------------------
# Logging setup
# ------------------------
logger = logging.getLogger("pd2")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


# ------------------------
# Paths & configuration
# ------------------------
DATASET_PATH = Path(r"C:\Users\Vignesh\Downloads\train.jsonl")  # training dataset
KB_FILE = Path("autogen_kb.json")                              # knowledge base file
FEEDBACK_LOG = Path("feedback_log.jsonl")                      # feedback storage
CHROMA_DIR = Path("chroma_db")                                 # vector database dir

# ------------------------
# Models
# ------------------------
OLLAMA_MODEL = "mistral"
USE_INTERNAL_GUARDRAILS = True                            # LLM for reasoning
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"                      # embedding model
