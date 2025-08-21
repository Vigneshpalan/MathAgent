import re
import asyncio
import unicodedata
from .config import logger, OLLAMA_MODEL, USE_INTERNAL_GUARDRAILS
from .kb_manager import kb_manager
from .web_retrieval import retrieve_via_web
from .ollama_helper import query_ollama
from .guardrails import math_guardrails_ok, output_guardrails_ok

class MathAgentTool:
    """Math problem-solving agent with KB → Web → Direct LLM fallback pipeline.

    Returns a dict with:
        { "reasoning": "<plain text steps>", "answer": "<plain text final answer>", "source": "KB|Web|LLM|Error" }
    """

    def __init__(self):
        self.llm = query_ollama

    def _normalize_query(self, query: str) -> str:
        """Normalize Unicode characters in the query to ASCII where possible."""
        try:
            # Normalize Unicode (e.g., convert ∫ to 'integral' or keep as is if necessary)
            normalized = unicodedata.normalize('NFKD', query)
            # Replace integral symbol (∫) with 'integral' for compatibility
            normalized = normalized.replace('\u222b', 'integral ')
            return normalized.encode('utf-8', errors='ignore').decode('utf-8')
        except Exception as e:
            logger.error(f"Query normalization failed: {e}")
            return query

    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with UTF-8 encoding."""
        try:
            # Ensure prompt is UTF-8 encoded
            prompt = prompt.encode('utf-8', errors='ignore').decode('utf-8')
            res = self.llm(prompt)
            if asyncio.iscoroutine(res):
                res = await res
            # Ensure response is UTF-8 decoded
            return res.encode('utf-8', errors='ignore').decode('utf-8') if isinstance(res, str) else res
        except TypeError:
            try:
                res2 = self.llm(prompt, OLLAMA_MODEL)
                if asyncio.iscoroutine(res2):
                    res2 = await res2
                return res2.encode('utf-8', errors='ignore').decode('utf-8') if isinstance(res2, str) else res2
            except Exception as e:
                logger.error(f"LLM helper call failed: {e}")
                raise
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    async def solve(self, query: str) -> dict:
        # Normalize query to handle Unicode characters
        query = self._normalize_query(query)

        # Guardrail: Check if query is math-related using guardrails.py
        if not math_guardrails_ok(query):
            return {
                "reasoning": "This query is not math-related. Please provide a math problem to solve, such as an equation, geometry problem, or statistical question.",
                "answer": "",
                "source": "Error"
            }

        # ---------------- Step 1: KB ----------------
        kb_result = kb_manager.search(query)
        if kb_result:
            logger.info("Answer retrieved from KB ✅")
            steps, final_answer = self._extract_steps_and_final(kb_result.get("answer", ""))
            # Apply output guardrails
            if not output_guardrails_ok(steps + " " + final_answer):
                logger.info("Guardrails → blocked due to inappropriate output content")
                return {
                    "reasoning": "The response contains inappropriate content and cannot be displayed.",
                    "answer": "",
                    "source": "Error"
                }
            return {"reasoning": steps, "answer": final_answer, "source": "KB"}

        # ---------------- Step 2: Web ----------------
        try:
            web_context = await retrieve_via_web(query)
            if web_context:
                # Ensure web context is UTF-8 encoded
                web_context = web_context.encode('utf-8', errors='ignore').decode('utf-8')
                prompt_with_web = self._build_prompt(query) + "\n\nRelevant context:\n" + web_context
                response = await self._call_llm(prompt_with_web)
                steps, final_answer = self._extract_steps_and_final(response)
                # Apply output guardrails
                if not output_guardrails_ok(steps + " " + final_answer):
                    logger.info("Guardrails → blocked due to inappropriate output content")
                    return {
                        "reasoning": "The response contains inappropriate content and cannot be displayed.",
                        "answer": "",
                        "source": "Error"
                    }
                if steps or final_answer:
                    return {"reasoning": steps, "answer": final_answer, "source": "Web+LLM"}
        except Exception as e:
            logger.error(f"Web fallback failed: {e}")

        # ---------------- Step 3: Direct LLM ----------------
        try:
            prompt = self._build_prompt(query)
            response = await self._call_llm(prompt)
            steps, final_answer = self._extract_steps_and_final(response)
            # Apply output guardrails
            if not output_guardrails_ok(steps + " " + final_answer):
                logger.info("Guardrails → blocked due to inappropriate output content")
                return {
                    "reasoning": "The response contains inappropriate content and cannot be displayed.",
                    "answer": "",
                    "source": "Error"
                }

            if steps or final_answer:
                combined = (steps + "\n\nFinal Answer:\n" + final_answer) if final_answer else steps
                kb_manager.update(query, combined)

            return {"reasoning": steps, "answer": final_answer, "source": "LLM"}
        except Exception as e:
            logger.error(f"LLM solving failed: {e}")

        # ---------------- Error fallback ----------------
        return {"reasoning": "⚠️ Could not solve problem.", "answer": "", "source": "Error"}

    def _build_prompt(self, query: str) -> str:
        if USE_INTERNAL_GUARDRAILS:
            return (
                "You are a strict math solver. Follow these rules:\n"
                "- Provide numbered step-by-step reasoning (plain text, no markdown).\n"
                "- Use the simplest and most direct method to solve the problem.\n"
                "- Provide exactly one final answer only, on a separate line.\n"
                "- Do NOT duplicate the final answer inside steps.\n"
                "- Avoid unnecessary steps or complex methods for simple arithmetic.\n\n"
                f"Solve this math problem:\n{query}\n\n"
                "Example output:\n1. Step ...\n2. Step ...\nFinal Answer: 42\n"
            )
        else:
            return (
                "Solve step-by-step (plain text) using the simplest method and provide a single final answer.\n"
                f"Problem: {query}"
            )

    def _extract_steps_and_final(self, text: str):
        """Extract steps and a single clean final answer (plain text) from text."""
        # Ensure text is UTF-8 encoded
        text = text.encode('utf-8', errors='ignore').decode('utf-8') if isinstance(text, str) else text

        # Remove all << ... >> placeholders
        cleaned_text = re.sub(r"<<.*?>>", "", text).strip()

        # Split into lines and separate steps vs final answer
        lines = [line.strip() for line in cleaned_text.split("\n") if line.strip()]
        steps = []
        final_line = ""

        for line in lines:
            if re.search(r"(Final Answer|✅ Final Answer|Answer:)", line, re.IGNORECASE):
                final_line = line
            else:
                steps.append(line)

        # Extract plain final answer from final line
        final_answer = ""
        if final_line:
            # Remove marker words and trailing punctuation
            final_answer = re.sub(r"(Final Answer|✅ Final Answer|Answer:)", "", final_line, flags=re.IGNORECASE).strip()
            final_answer = re.sub(r"[:\s]+$", "", final_answer)

        # Fallback: pick last sensible token from steps if final is empty
        if not final_answer and steps:
            tokens = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?|[A-Za-z][A-Za-z0-9_]*', "\n".join(steps))
            if tokens:
                final_answer = tokens[-1]

        return ("\n".join(steps), final_answer)