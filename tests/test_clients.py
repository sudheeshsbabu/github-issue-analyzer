
import pytest
from unittest.mock import AsyncMock, patch
from clients import GitHubClient

class MockResponse:
    def __init__(self, status_code, json_data, headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.headers = headers or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"Error {self.status_code}")

@pytest.mark.asyncio
async def test_fetch_open_issues_success():
    client = GitHubClient()
    mock_issues_page1 = [
        {"id": 1, "title": "Issue 1"},
        {"id": 2, "title": "Issue 2", "pull_request": {}} # Should be skipped
    ]
    mock_issues_page2 = [
        {"id": 3, "title": "Issue 3"}
    ]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Setup mock responses for pagination
        # Page 1 has "next" link
        r1 = MockResponse(200, mock_issues_page1, {"link": '<url>; rel="next"'})
        # Page 2 has no "next" link
        r2 = MockResponse(200, mock_issues_page2)
        
        mock_client.get.side_effect = [r1, r2]

        issues = await client.fetch_open_issues("owner/repo")
        
        # We expect Issue 1 and Issue 3. Issue 2 is a PR.
        assert len(issues) == 2
        assert issues[0]["id"] == 1
        assert issues[1]["id"] == 3
        # Check call count - should have called get twice (once for each page)
        assert mock_client.get.call_count == 2

@pytest.mark.asyncio
async def test_fetch_open_issues_api_error():
    client = GitHubClient()
    
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Error on first page
        r1 = MockResponse(404, {"message": "Not Found"})
        mock_client.get.return_value = r1
        
        with pytest.raises(Exception):
             await client.fetch_open_issues("owner/invalid")

@pytest.mark.asyncio
async def test_fetch_open_issues_empty():
    client = GitHubClient()
    
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        r1 = MockResponse(200, [])
        mock_client.get.return_value = r1

        issues = await client.fetch_open_issues("owner/empty")
        assert len(issues) == 0

