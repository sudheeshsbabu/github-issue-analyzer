# Project Prompts

This document records the key prompts used during the development of this project, ensuring transparency in the AI-assisted workflow.

## Phase 1: Initial Implementation (User)

**Prompt:**
> Build a small FastAPI service that implements a local caching and analysis system for GitHub issues.
> Requirements:
> 1. Implement POST /scan (Fetch open issues, Cache in SQLite)
> 2. Implement POST /analyze (Load cached issues, Call LLM)
> ...

**Follow-up Prompt (Refinement):**
> Calling the /scan endpoint will perform upsert for new and existing open issues but it doesn’t delete the old open ticket now in closed status in the database. So include that as well.
> Optional: you can do it as a background job or a thread

**Follow-up Prompt (LLM Integration):**
> Implement a flexible LLM calling mechanism that:
> - Uses a mock response by default
> - Automatically selects a real LLM provider if API keys are present (OpenAI, Anthropic)
> - Falls back safely
> - Implements Chunking (Map-Reduce)

**Follow-up Prompt (Gemini Support):**
> Create a gemini llm model class in addition to OpenAI and Anthropic

## Phase 2: Testing & QA (Agentic Workflow)

**Prompt (Test Planning):**
> Create comprehensive test cases for this project with the goal of achieving maximum code coverage(90+%)
> Tasks for each unit test:
> - Test basic functionality
> - Test negative result
> - Test an edge case

**Prompt (Import Error Debugging):**
> I am getting the following import error while testing on a seperate cli. What could be the issue?
> `ModuleNotFoundError: No module named 'clients'`

**Action Taken:**
Created `pytest.ini` with `pythonpath = .` to resolve module discovery issues.

## Phase 3: Refactoring (Production Prep)

**Prompt (Deprecation Fix):**
> Fix the following deprecated warning issue in main.py
> `on_event is deprecated, use lifespan event handlers instead.`

**Action Taken:**
Refactored `main.py` to use `contextlib.asynccontextmanager` for database initialization.

## Phase 4: Final Documentation

**Prompt:**
> Prepare this project for public GitHub submission with Docker support and clear documentation...
> Output: Dockerfile, Folder structure, README.md, docs/testing.md, docs/prompts.md...

**Action Taken:**
Generated this documentation suite and Docker configuration.


