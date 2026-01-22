# GitHub Issue Analyzer Service

A FastAPI-based backend service that fetches GitHub issues, caches them locally, and performs AI-powered analysis using an LLM (Mock, OpenAI, Anthropic, or Gemini).

## Features
- **Fetch & Cache**: Retrieves open issues from any public GitHub repository and caches them in a local SQLite database (`POST /scan`).
- **Smart Pruning**: Automatically detects and ignores stale/closed issues during scans.
- **AI Analysis**: Analyzes cached issues using natural language prompts (`POST /analyze`).
- **Flexible LLM Support**:
  - **Mock LLM**: Default (no API keys required).
  - **Real Providers**: Automatically switches to OpenAI, Anthropic, or Gemini if their respective API keys are detected in the environment.
- **Map-Reduce Chunking**: Handles large repositories by splitting issues into chunks for analysis before synthesizing a final result.
- **Dockerized**: specific `Dockerfile` for easy deployment.

## Configuration

To use real LLM providers (instead of the default Mock), create a `.env` file in the root directory:

```bash
touch .env
```

Add your API keys to the file:
```ini
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```
The application will automatically detect these keys.


## Quick Start

### Option 1: Docker Compose (Easiest)
1. **Run the helper script**:
    ```bash
    chmod +x run_docker.sh
    ./run_docker.sh
    ```
    This will stop any running containers and build/start the service on port 8000.

### Option 2: Docker Build (Manual)


### Option 2: Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```bash
   uvicorn main:app --reload
   ```

## Usage

**1. Scan a Repository**
```bash
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"repo": "fastapi/fastapi"}'
```

**2. Analyze Issues**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "fastapi/fastapi",
    "prompt": "What are the most common feature requests?"
  }'
```

## Design Decisions

### Local Storage: SQLite
- **Why?** The requirements called for a simple local cache, and introducing an additional hot-cache layer would be unnecessary overengineering for this use case. A lightweight SQL database provides sufficient performance while keeping the architecture simple and maintainable.

- **Benefit**: Zero configuration, single-file durability (issues.db), and predictable behavior without added complexity.

### LLM Integration
- **Strategy**: The `LLMClient` uses a Factory pattern to check environment variables (`OPENAI_API_KEY`, etc.) at runtime.
- **Mock by Default**: Ensures the application is testable and runnable by anyone, even without incurring API costs.
- **Chunking**: Implemented a basic Map-Reduce approach to handle context limits when analyzing repositories with hundreds of issues.

## Documentation Links
- [Testing & Coverage](docs/testing.md): Details on the test suite (99% coverage).
- [Prompt History](docs/prompts.md): Transparency log of AI prompts used to build this project.
- [Chat Export](docs/chatexport.md): Chat export of AI prompts used to build this project.

## Future Improvements
- **Rate Limiting**: Add handling for GitHub API rate limits.
- **Async Processing**: Offload the `/analyze` step to a background queue for very large datasets.
- **Vector Search**: Use embeddings to retrieve only semantically relevant issues for the analysis prompt instead of map-reduce.
