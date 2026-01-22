import os
import httpx
import math
from typing import List, Dict, Any, Protocol, Optional

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

class OpenAILLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-3.5-turbo" # Defaulting to a cost-effective model

    def get_chunk_size(self) -> int:
        return 50  # GPT-3.5 can handle more context

    def generate(self, prompt: str, total_issues: int) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error calling OpenAI: {str(e)}"

class AnthropicLLM:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-haiku-20240307" # Fast, cost-effective model

    def get_chunk_size(self) -> int:
        return 100  # Anthropic models have large context windows

    def generate(self, prompt: str, total_issues: int) -> str:
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
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
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

    def generate(self, prompt: str, total_issues: int) -> str:
        params = {"key": self.api_key}
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(self.url, params=params, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                # Parse safety settings or empty responses safely
                if "candidates" not in result or not result["candidates"]:
                    return "Error: No candidates returned from Gemini (possible safety block)."
                
                content = result["candidates"][0].get("content")
                if not content:
                     return "Error: Empty content from Gemini."
                     
                return content["parts"][0]["text"]
        except Exception as e:
            return f"Error calling Gemini: {str(e)}"

# --- Factory / Selection Logic ---

def get_llm_client() -> LLMProvider:
    """Selects the LLM provider based on environment variables."""
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    if openai_key:
        return OpenAILLM(openai_key)
    elif anthropic_key:
        return AnthropicLLM(anthropic_key)
    elif gemini_key:
        return GeminiLLM(gemini_key)
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
            f"You are analyzing GitHub issues. \n"
            f"User Prompt: {prompt}\n\n"
            f"Issues Context:\n{context}\n\n"
            f"Please provide the analysis."
        )
        return client.generate(full_prompt, total_issues)

    # Map-Reduce for large sets
    # 1. Map: Analyze chunks
    chunk_summaries = []
    num_chunks = math.ceil(total_issues / chunk_size)
    
    for i in range(num_chunks):
        chunk = issues[i * chunk_size : (i + 1) * chunk_size]
        chunk_context = "\n".join([format_issue(iss) for iss in chunk])
        
        chunk_prompt = (
            f"Summarize these GitHub issues relevant to this request: '{prompt}'.\n"
            f"Focus on themes, bugs, and feature requests.\n\n"
            f"Issues:\n{chunk_context}"
        )
        
        # We process chunks sequentially here (could be parallelized with async, but keeping it simple/safe)
        summary = client.generate(chunk_prompt, total_issues)
        chunk_summaries.append(f"Chunk {i+1}/{num_chunks} Summary:\n{summary}")

    # 2. Reduce: Final synthesis
    combined_summaries = "\n\n".join(chunk_summaries)
    final_prompt = (
        f"You are providing a final analysis of GitHub issues based on summaries of issue batches.\n"
        f"User Prompt: {prompt}\n\n"
        f"Intermediate Summaries:\n{combined_summaries}\n\n"
        f"Synthesize these summaries into a cohesive answer addressing the user prompt."
    )    
    return client.generate(final_prompt, total_issues)
