from pydantic import BaseModel
from typing import Optional

class ScanRequest(BaseModel):
    repo: str

class ScanResponse(BaseModel):
    repo: str
    issues_fetched: int
    cached_successfully: bool

class AnalyzeRequest(BaseModel):
    repo: str
    prompt: str

class AnalyzeResponse(BaseModel):
    analysis: str
