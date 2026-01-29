import os
import httpx
import math
from typing import List, Dict, Any, Protocol, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- Provider Interfaces ---

class LLMProvider(Protocol):
    def generate(self, prompt: str, total_issues: int) -> str:
        """Generates a text response for the given prompt."""
        ...

    def get_chunk_size(self) -> int:
        """Returns the recommended number of issues per chunk."""
        ...

class MockLLM:
    def get_chunk_size(self) -> int:
        return 20

    def generate(self, prompt: str, total_issues: int) -> str:
        """Returns a static mock response for testing/default behavior."""
        limit = 100
        limit = limit if len(prompt) > limit else len(prompt)
        return (
            "**MOCK ANALYSIS RESULT**\n\n"
            "This is a simulated response because no valid API key was found.\n"
            "The system successfully processed the logic without external calls.\n\n"
            f"Prompt Preview for {total_issues} issues: {prompt[:limit]}...\n\n"
            "**Key Insights (Simulated):**\n"
            "1. Issue velocity is stable.\n"
            "2. Top labels include 'bug' and 'feature-request'.\n"
            "3. No critical blockers identified in this mock run."
        )

def _is_retryable_error(e: BaseException) -> bool:
    return (
        isinstance(e, httpx.HTTPStatusError) and 
        (e.response.status_code == 429 or e.response.status_code >= 500)
    )

class OpenAILLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.openai.com/v1/responses"
        self.model = "gpt-4o-mini"
        self.client = httpx.Client(timeout=30.0)

    def get_chunk_size(self) -> int:
        # Keep this conservative for TPM safety
        return 5

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True
    )
    def _call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "input": prompt
        }

        try:
            response = self.client.post(
                self.url,
                headers=headers,
                json=data
            )
            response.raise_for_status()

            result = response.json()

            # Responses API convenience field
            return result["output_text"]

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            print(f"HTTP error {status}")

            if status == 429:
                print("⚠️ Rate limited")
                print("Retry-After:",
                      e.response.headers.get("retry-after"))

            # Re-raise so tenacity can retry
            raise

    def generate(self, prompt: str, total_issues: int) -> str:
        try:
            print("Generating response...")
            return self._call_api(prompt)
        except Exception as e:
            return f"Error calling OpenAI: {str(e)}"

    def close(self):
        self.client.close()


class AnthropicLLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-haiku-20240307" # Fast, cost-effective model

    def get_chunk_size(self) -> int:
        return 100  # Anthropic models have large context windows

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True
    )
    def _call_api(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    def generate(self, prompt: str, total_issues: int) -> str:
        try:
            result = self._call_api(prompt)
            return result["content"][0]["text"]
        except Exception as e:
            return f"Error calling Anthropic: {str(e)}"

class GeminiLLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # using gemini-1.5-flash which is fast and free-tier eligible
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def get_chunk_size(self) -> int:
        return 200  # Gemini 1.5 has a very large context window

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True
    )
    def _call_api(self, prompt: str) -> Dict[str, Any]:
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.url, params=params, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    def generate(self, prompt: str, total_issues: int) -> str:
        try:
            result = self._call_api(prompt)
            # Parse safety settings or empty responses safely
            if "candidates" not in result or not result["candidates"]:
                return "Error: No candidates returned from Gemini (possible safety block)."
            
            content = result["candidates"][0].get("content")
            if not content:
                    return "Error: Empty content from Gemini."
                    
            return content["parts"][0]["text"]
        except Exception as e:
            return f"Error calling Gemini: {str(e)}"

class OllamaLLM:
    def __init__(self, base_url: str, model: str):
        self.base_url = f"{base_url.rstrip('/')}/chat/completions"
        self.model = model
        self.api_key = "ollama"  # Required header structure but ignored by Ollama

    def get_chunk_size(self) -> int:
        return 50  # Conservative default for local models

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True
    )
    def _call_api(self, prompt: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()

    def generate(self, prompt: str, total_issues: int) -> str:
        try:
            print(f"prompt: {prompt}\n")
            result = self._call_api(prompt)
            print(f"result: {result}\n")
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error calling Ollama: {str(e)}"

# --- Factory / Selection Logic ---

def get_llm_client() -> LLMProvider:
    """Selects the LLM provider based on environment variables."""
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    ollama_url = os.getenv("OLLAMA_BASE_URL")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

    if openai_key:
        return OpenAILLM(openai_key)
    elif anthropic_key:
        return AnthropicLLM(anthropic_key)
    elif gemini_key:
        return GeminiLLM(gemini_key)
    elif ollama_url:
        return OllamaLLM(ollama_url, ollama_model)
    else:
        return MockLLM()

# --- Logic & Orchestration ---



def format_issue(issue: Dict[str, Any]) -> str:
    """Formats a single issue for the prompt."""
    return f"- #{issue.get('id')} {issue.get('title')} (Created: {issue.get('created_at')})\n  Body: {issue.get('body') or 'No description'}...\n"

def generate_analysis(prompt: str, issues: List[Dict[str, Any]]) -> str:
    """
    Orchestrates the analysis:
    1. Checks if chunking is needed.
    2. Runs map-reduce if issues > CHUNK_SIZE.
    3. Calls the selected LLM provider.
    """
    client = get_llm_client()
    chunk_size = client.get_chunk_size()
    
    # Safety fallback for empty list
    if not issues:
        return "No issues provided for analysis."

    total_issues = len(issues)
    
    # Direct pass if small enough
    if total_issues <= chunk_size:
        context = "\n".join([format_issue(i) for i in issues])
        full_prompt = (
            "System: You are a senior software triage assistant."
            "Synthesize issue summaries into a coherent, prioritized analysis.\n"
            f"User Prompt: {prompt}\n"
            f"Issues Context:{context}\n"
            "Provide a clear, actionable final analysis."
        )
        return client.generate(full_prompt, total_issues)

    # Map-Reduce for large sets
    # 1. Map: Analyze chunks
    chunk_summaries = []
    num_chunks = math.ceil(total_issues / chunk_size)
    
    for i in range(num_chunks):
        chunk = issues[i * chunk_size : (i + 1) * chunk_size]
        chunk_context = "\n".join([format_issue(iss) for iss in chunk])
        if (i > 0):
            chunk_prompt = (
                f"Summarize these GitHub issues relevant to this request: '{prompt}'.\n"
                f"Focus on themes, bugs, and feature requests.\n"
                f"Issues:{chunk_context}\n"
            )
        else:
            chunk_prompt = (
                "System: You are a senior software triage assistant."
                "Synthesize issue summaries into a coherent, prioritized analysis.\n"
                f"User Prompt: '{prompt}'"
                f"Focus on themes, bugs, and feature requests."
                f"Issues:\n{chunk_context}"
            )
        
        # We process chunks sequentially here (could be parallelized with async, but keeping it simple/safe)
        summary = client.generate(chunk_prompt, total_issues)
        chunk_summaries.append(f"Chunk {i+1}/{num_chunks} Summary:\n{summary}")

    # 2. Reduce: Final synthesis
    combined_summaries = "\n\n".join(chunk_summaries)
    final_prompt = (
        f"You are providing a final analysis of GitHub issues based on summaries of issue batches.\n"
        f"User Prompt: {prompt}\n"
        f"Intermediate Summaries:\n{combined_summaries}\n"
        f"Synthesize these summaries into a cohesive answer addressing the user prompt."
    )    
    return client.generate(final_prompt, total_issues)
