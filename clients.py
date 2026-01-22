import httpx
from typing import List, Dict, Any

class GitHubClient:
    async def fetch_open_issues(self, repo: str) -> List[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {
            "state": "open",
            "per_page": 100,
            "page": 1
        }
        all_issues = []
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            while True:
                response = await client.get(url, params=params)
                if response.status_code != 200:
                    # If repo not found or other error, decided to raise or return empty.
                    # Prompt says "Exclude pull requests"
                    # For simplicity, if error, we stop and return what we have or raise.
                    # Let's log/print and break for robustness, or raise if it's the first page (repo likely invalid).
                    if params["page"] == 1:
                        response.raise_for_status() 
                    break

                data = response.json()
                if not data:
                    break
                
                for item in data:
                    if "pull_request" not in item:
                        all_issues.append(item)
                
                # Check for next page
                if "next" not in response.headers.get("link", ""):
                    break
                
                params["page"] += 1
                
        return all_issues

