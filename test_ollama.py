import os
import httpx
from dotenv import load_dotenv

# Load env but force Ollama for this test (or check if set)
load_dotenv()

# Simulate what the user would do to test this
os.environ["OLLAMA_BASE_URL"] = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
os.environ["OLLAMA_MODEL"] = os.environ.get("OLLAMA_MODEL", "llama3")

from llm_client import get_llm_client, OllamaLLM

def test_ollama_connection():
    print("Testing Ollama Connection...")
    client = get_llm_client()
    
    if not isinstance(client, OllamaLLM):
        print(f"FAILED: Expected OllamaLLM, got {type(client).__name__}")
        print("Ensure OPENAI_API_KEY, ANTHROPIC_API_KEY, and GEMINI_API_KEY are NOT set, or OLLAMA is prioritized (it is not currently prioritized in factory if others are present).")
        # For this test, we might want to unset others to verify Ollama specifically
        return

    print(f"Client: {type(client).__name__}")
    print(f"Base URL: {client.base_url}")
    print(f"Model: {client.model}")

    try:
        response = client.generate("Say 'Hello from Ollama' and nothing else.", 1)
        print(f"Response: {response}")
        if "Hello from Ollama" in response or "Hello" in response:
             print("SUCCESS: Ollama responded correctly.")
        else:
             print("WARNING: Unexpected response content.")
    except Exception as e:
        print(f"FAILED: Error during generation: {e}")

if __name__ == "__main__":
    # Temporarily unset other keys to force Ollama for checking
    if "OPENAI_API_KEY" in os.environ: del os.environ["OPENAI_API_KEY"]
    if "ANTHROPIC_API_KEY" in os.environ: del os.environ["ANTHROPIC_API_KEY"]
    if "GEMINI_API_KEY" in os.environ: del os.environ["GEMINI_API_KEY"]
    
    test_ollama_connection()
