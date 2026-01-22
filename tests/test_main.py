
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from main import app, prune_stale_issues
import database

client = TestClient(app)

# --- Prune Task Tests ---

@patch("database.get_all_issue_ids")
@patch("database.delete_issues")
def test_prune_stale_issues_logic(mock_delete, mock_get_ids):
    mock_get_ids.return_value = [1, 2, 3] # DB has 1, 2, 3
    fresh_ids = {2, 3, 4} # Scan found 2, 3, 4
    
    # 1 is stale (in DB but not fresh)
    # 4 is new (will be upserted elsewhere, pruning only cares about what to delete)
    
    prune_stale_issues("repo", fresh_ids)
    
    mock_delete.assert_called_once_with([1])

@patch("database.get_all_issue_ids")
@patch("database.delete_issues")
def test_prune_stale_issues_no_stale(mock_delete, mock_get_ids):
    mock_get_ids.return_value = [1, 2]
    fresh_ids = {1, 2, 3}
    
    prune_stale_issues("repo", fresh_ids)
    
    mock_delete.assert_not_called()


# --- API Endpoint Tests ---

@patch("main.github_client.fetch_open_issues")
@patch("database.upsert_issue")
# We patch BackgroundTasks to ensure it's added but not necessarily executing the function in unit test unless we want to
def test_scan_repo_success(mock_upsert, mock_fetch):
    mock_fetch.return_value = [
        {"id": 1, "title": "T1", "body": "B1", "html_url": "u1", "created_at": "d1"},
        {"id": 2, "title": "T2", "body": None, "html_url": "u2", "created_at": "d2"}
    ]
    
    response = client.post("/scan", json={"repo": "owner/repo"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["repo"] == "owner/repo"
    assert data["issues_fetched"] == 2
    assert mock_upsert.call_count == 2
    
@patch("main.github_client.fetch_open_issues")
def test_scan_repo_error(mock_fetch):
    mock_fetch.side_effect = Exception("GitHub API Down")
    
    response = client.post("/scan", json={"repo": "owner/repo"})
    
    assert response.status_code == 404
    assert "GitHub API Down" in response.json()["detail"]


@patch("database.is_repo_scanned")
@patch("database.get_issues_for_repo")
@patch("main.generate_analysis")
def test_analyze_repo_success(mock_generate, mock_get_issues, mock_is_scanned):
    mock_is_scanned.return_value = True
    mock_get_issues.return_value = [{"id": 1}]
    mock_generate.return_value = "Analysis Result"
    
    response = client.post("/analyze", json={"repo": "owner/repo", "prompt": "Analyze this"})
    
    assert response.status_code == 200
    assert response.json()["analysis"] == "Analysis Result"

def test_analyze_repo_not_scanned():
    with patch("database.is_repo_scanned", return_value=False):
        response = client.post("/analyze", json={"repo": "unscanned", "prompt": "Analyze"})
        assert "not scanned" in response.json()["analysis"]

def test_analyze_repo_no_issues():
    with patch("database.is_repo_scanned", return_value=True):
        with patch("database.get_issues_for_repo", return_value=[]):
            response = client.post("/analyze", json={"repo": "empty", "prompt": "Analyze"})
            assert "No issues" in response.json()["analysis"]

@patch("database.is_repo_scanned", return_value=True)
@patch("database.get_issues_for_repo", return_value=[{"id": 1}])
@patch("main.generate_analysis")
def test_analyze_repo_llm_error(mock_generate, mock_get, mock_scan):
    mock_generate.side_effect = Exception("LLM connection failed")
    
    response = client.post("/analyze", json={"repo": "repo", "prompt": "Analyze"})
    
    assert response.status_code == 500
    assert "LLM connection failed" in response.json()["detail"]
