
import pytest
from unittest.mock import MagicMock, patch
from llm_client import get_llm_client, generate_analysis, MockLLM, OpenAILLM, AnthropicLLM, GeminiLLM
import httpx
import os

# --- Provider Selection Tests ---

def test_get_llm_client_default_mock():
    # Ensure no env vars set for this test
    with patch.dict(os.environ, {}, clear=True):
        client = get_llm_client()
        assert isinstance(client, MockLLM)

def test_get_llm_client_openai():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-exist"}, clear=True):
        client = get_llm_client()
        assert isinstance(client, OpenAILLM)

def test_get_llm_client_anthropic():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant"}, clear=True):
        client = get_llm_client()
        assert isinstance(client, AnthropicLLM)

def test_get_llm_client_gemini():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "AIza"}, clear=True):
        client = get_llm_client()
        assert isinstance(client, GeminiLLM)


# --- Generation Logic Tests ---

def test_generate_analysis_empty_issues():
    result = generate_analysis("prompt", [])
    assert "No issues provided" in result

@patch("llm_client.get_llm_client")
def test_generate_analysis_direct_pass(mock_get_client):
    # Setup mock client
    mock_llm = MagicMock()
    mock_llm.get_chunk_size.return_value = 10
    mock_llm.generate.return_value = "Analysis Result"
    mock_get_client.return_value = mock_llm

    # 5 issues (<= chunk size 10)
    issues = [{"id": i, "title": f"T{i}", "body": "B", "created_at": "D"} for i in range(5)]
    
    result = generate_analysis("Do analysis", issues)
    
    assert result == "Analysis Result"
    mock_llm.generate.assert_called_once()
    # Check prompt contains issue info
    args, _ = mock_llm.generate.call_args
    assert "User Prompt: Do analysis" in args[0]
    assert "T0" in args[0]

@patch("llm_client.get_llm_client")
def test_generate_analysis_map_reduce(mock_get_client):
    # Setup mock client
    mock_llm = MagicMock()
    mock_llm.get_chunk_size.return_value = 2 # Small chunk size to force split
    mock_llm.generate.side_effect = [
        "Summary Chunk 1", # Map 1
        "Summary Chunk 2", # Map 2
        "Final Analysis"   # Reduce
    ]
    mock_get_client.return_value = mock_llm

    # 3 issues ( > chunk size 2)
    issues = [{"id": i, "title": f"T{i}", "body": "B", "created_at": "D"} for i in range(3)]
    
    result = generate_analysis("Do analysis", issues)
    
    assert result == "Final Analysis"
    assert mock_llm.generate.call_count == 3
    
    # Check intermediate calls
    calls = mock_llm.generate.call_args_list
    # First chunk
    assert "T0" in calls[0][0][0]
    # Second chunk
    assert "T2" in calls[1][0][0]
    # Reduce step
    assert "Summary Chunk 1" in calls[2][0][0]
    assert "Summary Chunk 2" in calls[2][0][0]


# --- Provider Specific Tests (Mocking HTTP) ---

def test_openai_generate_success():
    client = OpenAILLM("key")
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "GPT Response"}}]
        }
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
        
        resp = client.generate("test", 1)
        assert resp == "GPT Response"

def test_openai_generate_error():
    client = OpenAILLM("key")
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("Net Error")
        
        resp = client.generate("test", 1)
        # After retries, it should still return the error message string
        assert "Error calling OpenAI" in resp

def test_openai_generate_retry_success():
    client = OpenAILLM("key")
    # We need to mock the underlying _call_api's network call, BUT tenacity decorates _call_api.
    # So if we mock _call_api, we bypass tenacity. We must mock httpx.Client.
    
    with patch("httpx.Client") as mock_client_cls:
        mock_post = mock_client_cls.return_value.__enter__.return_value.post
        
        # Create a 429 response
        error_response = MagicMock()
        error_response.status_code = 429
        error_429 = httpx.HTTPStatusError("Too Many Requests", request=MagicMock(), response=error_response)
        
        # Create a 200 response
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"choices": [{"message": {"content": "Retry Success"}}]}
        
        # Fail twice with 429, then succeed
        mock_post.side_effect = [error_429, error_429, success_response]
        
        resp = client.generate("test", 1)
        assert resp == "Retry Success"
        # minimal wait in tests ideally, but tenacity defaults might slow this down unless we override.
        # However, verifying logic is more important. 
        # For unit tests, we might want to patch sleep or use a custom retry config, 
        # but let's see if 1s+2s wait is acceptable. It might be 3+ seconds test. 
        # Actually proper unit testing of tenacity usually involves overriding the wait strategy to wait_none() 
        # during tests, but let's try this first.
        
        assert mock_post.call_count == 3

def test_anthropic_generate_success():
    client = AnthropicLLM("key")
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"text": "Claude Response"}]
        }
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
        
        resp = client.generate("test", 1)
        assert resp == "Claude Response"

def test_gemini_generate_success():
    client = GeminiLLM("key")
    with patch("httpx.Client") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Gemini Response"}]}}]
        }
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
        
        resp = client.generate("test", 1)
        assert resp == "Gemini Response"

def test_gemini_generate_error_handling():
    client = GeminiLLM("key")
    with patch("httpx.Client") as mock_client_cls:
        mock_post = mock_client_cls.return_value.__enter__.return_value.post
        
        # Test 1: Exception during call
        mock_post.side_effect = Exception("Net Error")
        assert "Error calling Gemini" in client.generate("test", 1)
        
        # Reset
        mock_post.side_effect = None
        
        # Test 2: No candidates (safety block)
        mock_post.return_value.json.return_value = {}
        assert "No candidates" in client.generate("test", 1)
        
        # Test 3: Empty content
        mock_post.return_value.json.return_value = {"candidates": [{}]}
        assert "Empty content" in client.generate("test", 1)

def test_chunk_sizes():
    assert OpenAILLM("k").get_chunk_size() == 50
    assert AnthropicLLM("k").get_chunk_size() == 100
    assert GeminiLLM("k").get_chunk_size() == 200
    assert MockLLM().get_chunk_size() == 20

def test_anthropic_error():
    client = AnthropicLLM("k")
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("Boom")
        assert "Error calling Anthropic" in client.generate("t", 1)

def test_mock_llm_generate():
    # Execute the actual MockLLM.generate method
    llm = MockLLM()
    res = llm.generate("prompt", 10)
    assert "MOCK ANALYSIS RESULT" in res

