import subprocess
import json

import subprocess

def query_ollama(prompt: str, model: str = "mistral") -> str:
    """Query Ollama locally with a given model (default = mistral)."""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            text=True,
            encoding='utf-8',      # decode output as UTF-8
            errors='ignore',       # ignore undecodable bytes
            capture_output=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        # decode stderr safely or fallback to raw byte string if needed
        err_msg = ""
        if e.stderr:
            try:
                err_msg = e.stderr
            except Exception:
                err_msg = "Error reading stderr"
        return f"Error querying Ollama: {err_msg}"

