import sqlite3
from typing import List, Dict, Any, Optional

DB_FILE = "issues.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY,
            repo TEXT NOT NULL,
            title TEXT,
            body TEXT,
            html_url TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def upsert_issue(issue: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO issues (id, repo, title, body, html_url, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            repo=excluded.repo,
            title=excluded.title,
            body=excluded.body,
            html_url=excluded.html_url,
            created_at=excluded.created_at
    """, (
        issue["id"],
        issue["repo"],
        issue["title"],
        issue.get("body", ""),
        issue["html_url"],
        issue["created_at"]
    ))
    conn.commit()
    conn.close()

def get_issues_for_repo(repo: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM issues WHERE repo = ?", (repo,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def is_repo_scanned(repo: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM issues WHERE repo = ? LIMIT 1", (repo,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_all_issue_ids(repo: str) -> List[int]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM issues WHERE repo = ?", (repo,))
    rows = cursor.fetchall()
    conn.close()
    return [row["id"] for row in rows]

def delete_issues(ids: List[int]):
    if not ids:
        return
    conn = get_connection()
    cursor = conn.cursor()
    # sqlite3 supports parameter substitution for checking membership using IN (...)
    # but the number of placeholders must match.
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(f"DELETE FROM issues WHERE id IN ({placeholders})", ids)
    conn.commit()
    conn.close()
