# src/pd2/tools/kb_manager.py
import os
import json
import uuid
import re
from pathlib import Path
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document
from .config import DATASET_PATH, KB_FILE, CHROMA_DIR, EMBEDDING_MODEL_NAME, logger

# ------------------------------- Embedding & Chroma -------------------------------
try:
    embedding_model = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embedding_model,
        collection_name="math_kb"
    )
except Exception as e:
    logger.error(f"Failed to initialize embeddings or Chroma: {e}")
    raise


class KBManager:
    """Handles storing and retrieving Q/A pairs for math queries with similarity threshold."""

    SIMILARITY_THRESHOLD = 0.4

    def __init__(self, kb_file: Path, dataset_path: str):
        self.kb_file = kb_file
        self.dataset_path = dataset_path
        self.docs: list[dict] = []
        self.load_kb()

    def load_kb(self):
        """Load KB from file or dataset if missing/invalid."""
        if self.kb_file.exists():
            try:
                with open(self.kb_file, "r", encoding="utf-8") as f:
                    self.docs = json.load(f)
                if not self.docs:
                    self.build_from_dataset()
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load KB: {e}")
                self.build_from_dataset()
        else:
            self.build_from_dataset()

    def build_from_dataset(self):
        """Initialize KB from the training dataset (first 50 records)."""
        self.docs = []
        if os.path.exists(self.dataset_path):
            try:
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if i >= 50:
                            break
                        item = json.loads(line)
                        q, a = item.get("question", ""), item.get("answer", "")
                        if q:
                            formatted_a = self.format_answer(a)
                            self.docs.append({"id": str(uuid.uuid4()), "query": q, "answer": formatted_a})
                            vectorstore.add_documents([Document(page_content=formatted_a, metadata={"query": q})])
                logger.info(f"KB initialized with {len(self.docs)} records from dataset")
            except Exception as e:
                logger.error(f"Failed to build KB from dataset: {e}")
        else:
            logger.warning(f"No dataset found at {self.dataset_path}")

    def search(self, query: str) -> dict | None:
        """Search KB by embeddings + fallback string search."""
        try:
            hits_with_scores = vectorstore.similarity_search_with_score(query, k=1)
            if hits_with_scores:
                doc, score = hits_with_scores[0]
                logger.info(f"Similarity score for KB hit: {score}")

                if score >= self.SIMILARITY_THRESHOLD:
                    query_tokens = set(re.findall(r'\w+', query.lower()))
                    kb_tokens = set(re.findall(r'\w+', doc.metadata["query"].lower()))
                    if len(query_tokens.intersection(kb_tokens)) >= 2:
                        return {"query": doc.metadata["query"], "answer": self.format_answer(doc.page_content)}

            # fallback fuzzy match
            for doc in self.docs:
                if query.lower() in doc["query"].lower():
                    return {"query": doc["query"], "answer": self.format_answer(doc["answer"])}
        except Exception as e:
            logger.error(f"KB search failed: {e}")
        return None

    def update(self, query: str, answer: str):
        """Update KB with new Q/A or replace old answer."""
        try:
            formatted_answer = self.format_answer(answer)
            existing = self.search(query)
            if existing:
                existing["answer"] = formatted_answer
            else:
                self.docs.append({"id": str(uuid.uuid4()), "query": query, "answer": formatted_answer})
                vectorstore.add_documents([Document(page_content=formatted_answer, metadata={"query": query})])
            vectorstore.persist()
        except Exception as e:
            logger.error(f"Failed to update KB: {e}")

    @staticmethod
    def format_answer(raw_answer: str) -> str:
        """Format answer into clean markdown with LaTeX and boxed final answer."""
        if not raw_answer:
            return ""

        # Normalize inline LaTeX
        cleaned = re.sub(r'\$(.*?)\$', r'$$\1$$', raw_answer)
        cleaned = re.sub(r'Final Answer:.*', '', cleaned, flags=re.IGNORECASE)

        # Extract boxed/LaTeX final answer
        final_answer_pattern = r'\*\*Final Answer\*\*.*?\$\$([^$]+)\$\$|\\boxed{([^}]*)}'
        matches = re.findall(final_answer_pattern, cleaned, re.DOTALL)
        final_answers = [m[0] or m[1] for m in matches if m[0] or m[1]]
        final_answer = final_answers[-1] if final_answers else ""

        return f"**Solution Steps**:\n{cleaned.strip()}\n\n**Final Answer**:\n$$\\boxed{{{final_answer}}}$$".strip()


# Singleton
kb_manager = KBManager(KB_FILE, DATASET_PATH)
