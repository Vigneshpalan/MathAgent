import subprocess
import json

def query_ollama(prompt: str, model: str = "mistral") -> str:
    """Query Ollama locally with a given model (default = mistral)."""
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error querying Ollama: {e.stderr}"
