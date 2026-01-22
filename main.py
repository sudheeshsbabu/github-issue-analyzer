from fastapi import FastAPI, HTTPException, BackgroundTasks
from schemas import ScanRequest, ScanResponse, AnalyzeRequest, AnalyzeResponse
from clients import GitHubClient
from llm_client import generate_analysis
import database

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
github_client = GitHubClient()
# LLM Client is now functional via generate_analysis

@app.on_event("startup")
def startup_event():
    database.init_db()



def prune_stale_issues(repo: str, fresh_issue_ids: set[int]):
    print(f"Starting prune for {repo}...")
    cached_ids = set(database.get_all_issue_ids(repo))
    stale_ids = list(cached_ids - fresh_issue_ids)
    
    if stale_ids:
        print(f"Pruning {len(stale_ids)} stale issues for {repo}")
        database.delete_issues(stale_ids)
    else:
        print(f"No stale issues to prune for {repo}")

@app.post("/scan", response_model=ScanResponse)
async def scan_repo(request: ScanRequest, background_tasks: BackgroundTasks):
    try:
        issues = await github_client.fetch_open_issues(request.repo)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error fetching issues: {str(e)}")

    count = 0
    fresh_ids = set()
    for issue in issues:
        # Extract required fields
        issue_data = {
            "id": issue["id"],
            "repo": request.repo,
            "title": issue["title"],
            "body": issue.get("body"), # body can be None
            "html_url": issue["html_url"],
            "created_at": issue["created_at"]
        }
        database.upsert_issue(issue_data)
        fresh_ids.add(issue["id"])
        count += 1
    
    background_tasks.add_task(prune_stale_issues, request.repo, fresh_ids)
    
    return ScanResponse(
        repo=request.repo,
        issues_fetched=count,
        cached_successfully=True
    )

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_repo(request: AnalyzeRequest):
    # Validate scan
    if not database.is_repo_scanned(request.repo):
        return AnalyzeResponse(analysis="Repo not scanned. Please scan first.")

    issues = database.get_issues_for_repo(request.repo)
    
    if not issues:
        return AnalyzeResponse(analysis="No issues found for this repo.")

    try:
        analysis = generate_analysis(request.prompt, issues)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")
        
    return AnalyzeResponse(analysis=analysis)
