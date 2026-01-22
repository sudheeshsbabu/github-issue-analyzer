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
                    print("---------\n")
                    print(f"item = {item}")
                    print("---------\n")
                    if "pull_request" not in item:
                        all_issues.append(item)
                
                # Check for next page
                if "next" not in response.headers.get("link", ""):
                    break
                
                params["page"] += 1
                
        return all_issues

class LLMClient:
    def analyze(self, prompt: str, issues: List[Dict[str, Any]]) -> str:
        # Mock LLM analysis
        # Combine issues into a context string
        # Truncate if too long (simple char limit for mock)
        
        context_preview = ""
        for issue in issues[:5]: # Take top 5 for summary to keep mock simple
            context_preview += f"- {issue.get('title')} (#{issue.get('id')})\n"
        
        # Simulated analysis result
        return f"MOCK ANALYSIS RESULT:\nPrompt: {prompt}\n\nBased on {len(issues)} issues, here is the analysis:\n\nThe issues primarily concern...\n(Sample Context: \n{context_preview}\n...)"
