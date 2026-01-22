
import pytest
import database
import os
import sqlite3

TEST_DB = "test_issues.db"

@pytest.fixture(autouse=True)
def setup_teardown_db():
    # Setup: Use a test DB file
    original_db_file = database.DB_FILE
    database.DB_FILE = TEST_DB
    
    # Clean previous run
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Initialize DB
    database.init_db()
    
    yield
    
    # Teardown
    database.DB_FILE = original_db_file
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_init_db():
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")
    assert cursor.fetchone() is not None
    conn.close()

def test_upsert_issue_insert():
    issue = {
        "id": 101,
        "repo": "owner/repo",
        "title": "Test Issue",
        "body": "Body",
        "html_url": "http://url",
        "created_at": "2023-01-01"
    }
    database.upsert_issue(issue)
    
    issues = database.get_issues_for_repo("owner/repo")
    assert len(issues) == 1
    assert issues[0]["title"] == "Test Issue"

def test_upsert_issue_update():
    # Insert first
    issue = {
        "id": 101,
        "repo": "owner/repo",
        "title": "Original Title",
        "body": "Body",
        "html_url": "http://url",
        "created_at": "2023-01-01"
    }
    database.upsert_issue(issue)
    
    # Update same ID
    issue["title"] = "Updated Title"
    database.upsert_issue(issue)
    
    issues = database.get_issues_for_repo("owner/repo")
    assert len(issues) == 1
    assert issues[0]["title"] == "Updated Title"

def test_get_issues_for_repo_filtering():
    database.upsert_issue({"id": 1, "repo": "r1", "title": "t1", "html_url": "u", "created_at": "d"})
    database.upsert_issue({"id": 2, "repo": "r2", "title": "t2", "html_url": "u", "created_at": "d"})
    
    issues_r1 = database.get_issues_for_repo("r1")
    assert len(issues_r1) == 1
    assert issues_r1[0]["id"] == 1

def test_is_repo_scanned():
    assert not database.is_repo_scanned("r1")
    database.upsert_issue({"id": 1, "repo": "r1", "title": "t1", "html_url": "u", "created_at": "d"})
    assert database.is_repo_scanned("r1")

def test_get_all_issue_ids():
    database.upsert_issue({"id": 1, "repo": "r1", "title": "t1", "html_url": "u", "created_at": "d"})
    database.upsert_issue({"id": 2, "repo": "r1", "title": "t2", "html_url": "u", "created_at": "d"})
    
    ids = database.get_all_issue_ids("r1")
    assert set(ids) == {1, 2}

def test_delete_issues():
    database.upsert_issue({"id": 1, "repo": "r1", "title": "t1", "html_url": "u", "created_at": "d"})
    database.upsert_issue({"id": 2, "repo": "r1", "title": "t2", "html_url": "u", "created_at": "d"})
    database.upsert_issue({"id": 3, "repo": "r1", "title": "t3", "html_url": "u", "created_at": "d"})
    
    database.delete_issues([1, 3])
    
    ids = database.get_all_issue_ids("r1")
    assert ids == [2]

def test_delete_issues_empty():
    database.delete_issues([])
    # Should not error
