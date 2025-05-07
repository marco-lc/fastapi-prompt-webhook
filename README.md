# FastAPI Webhook to GitHub Service

This FastAPI application listens for webhook events and can either commit a specified part of the payload (the `manifest`) directly to a GitHub repository branch or create a Pull Request with the changes.

# Setup
You need to create a `.env` file with the corresponding environment variables values. See `.env.example` for the required variables:
* `GITHUB_TOKEN`: Your GitHub Personal Access Token with `repo` scope.
* `GITHUB_REPO_OWNER`: The owner of the target repository.
* `GITHUB_REPO_NAME`: The name of the target repository.
* `GITHUB_FILE_PATH` (optional): Path to the file within the repository (e.g., `data/manifest.json`). Defaults to `prompt_manifest.json`.
* `GITHUB_BRANCH` (optional): The base branch for direct commits and the target base branch for Pull Requests. Defaults to `main`.

# Run api (poetry)
```bash
pip install poetry
poetry install

# Install pre-commit hooks
poetry run pre-commit install

# Run api with single worker
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

# Run api (docker)

```bash
docker build -t fastapi-prompt-webhook .
docker run -p 8000:8000 --env-file .env fastapi-prompt-webhook
```

## API Documentation (Swagger UI)

Once the API is running, you can access the interactive API documentation (Swagger UI) at:
[`http://localhost:8000/docs`](http://localhost:8000/docs)

## API Endpoints

The following endpoints are available:

### 1. Health Check

* **Endpoint:** `GET /health`
* **Description:** A simple health check endpoint to verify that the service is running and operational.
* **Usage:**
    ```bash
    curl http://localhost:8000/health
    ```
* **Expected Response (200 OK):**
    ```json
    {
      "status": "ok",
      "message": "Webhook to GitHub Service is running."
    }
    ```

### 2. Webhook: Direct Commit to GitHub

* **Endpoint:** `POST /webhook/github-commit`
* **Description:** Receives a payload and directly commits the `manifest` part of it to the GitHub branch specified by the `GITHUB_BRANCH` environment variable. The file will be created or updated at the path specified by `GITHUB_FILE_PATH`.
* **Request Body:** `application/json`
    * Requires a `WebhookPayload` (see `app/models.py`):
        ```json
        {
          "manifest": {
            "lc": 1,
            "type": "constructor",
            "id": ["langchain", "schema", "runnable", "RunnableSequence"],
            "kwargs": {
              "first": {
                "lc": 1,
                // ... (rest of your manifest structure)
              },
              "last": {
                "lc": 1,
                // ... (rest of your manifest structure)
              }
            }
          },
          "commit_hash": "555d5f44caffef50eb6c1b3e1854a8848b1ae824",
          "created_at": "2025-05-06T22:30:31.762243"
        }
        ```
* **Usage (cURL Example):**
    ```bash
    curl -X POST http://localhost:8000/webhook/github-commit \
    -H "Content-Type: application/json" \
    -d '{
      "manifest": {"key": "value", "description": "Direct commit example"},
      "commit_hash": "directcommit123",
      "created_at": "2025-05-07T10:00:00Z"
    }'
    ```
* **Expected Response (201 Created):**
    ```json
    {
      "message": "Webhook received and manifest committed directly to GitHub successfully.",
      "github_commit_details": {
        "sha": "actual_commit_sha_from_github",
        "url": "url_to_the_commit_on_github",
        // ... other commit details
      },
      "github_content_details": {
        "name": "your_file.json",
        "path": "path/to/your_file.json",
        "sha": "content_sha",
        // ... other content details
      }
    }
    ```
    *(Actual commit and content details will vary based on GitHub's response.)*

### 3. Webhook: Create GitHub Pull Request

* **Endpoint:** `POST /webhook/github-pr`
* **Description:** Receives a payload, creates a new feature branch (named using the `commit_hash` and a timestamp) from the `GITHUB_BRANCH`, commits the `manifest` to this new branch, and then opens a Pull Request from the new feature branch to the `GITHUB_BRANCH`.
* **Request Body:** `application/json`
    * Requires the same `WebhookPayload` structure as the direct commit endpoint.
* **Usage (cURL Example):**
    ```bash
    curl -X POST http://localhost:8000/webhook/github-pr \
    -H "Content-Type: application/json" \
    -d '{
      "manifest": {"key": "value", "description": "PR creation example"},
      "commit_hash": "prcreation456",
      "created_at": "2025-05-07T11:00:00Z"
    }'
    ```
* **Expected Response (201 Created):**
    * If a new PR is created:
        ```json
        {
          "message": "Pull Request created successfully.",
          "pull_request_url": "[https://github.com/your-owner/your-repo/pull/123](https://github.com/your-owner/your-repo/pull/123)",
          "pull_request_details": {
            "html_url": "[https://github.com/your-owner/your-repo/pull/123](https://github.com/your-owner/your-repo/pull/123)",
            "id": 123456789,
            "number": 123,
            "title": "feat: Update prompt manifest from webhook (prcreation45)",
            // ... other PR details from GitHub
          },
          "new_branch_name": "feature/prompt-prcreation45-20250507-110000",
          "commit_on_branch_details": {
            "sha": "commit_sha_on_new_branch",
            // ... other commit details
          }
        }
        ```
    * If a PR for this branch combination already exists:
        ```json
        {
          "message": "Pull request from 'feature/prompt-prcreation45-...' to 'main' already exists.",
          "pull_request_url": "[https://github.com/your-owner/your-repo/pulls?q=is%3Apr+is%3Aopen+head%3Afeature/prompt-prcreation45-...base%3Amain](https://github.com/your-owner/your-repo/pulls?q=is%3Apr+is%3Aopen+head%3Afeature/prompt-prcreation45-...base%3Amain)",
          "pull_request_details": {
            "message": "Pull request from 'feature/prompt-prcreation45-...' to 'main' already exists.",
            "html_url": "[https://github.com/your-owner/your-repo/pulls?q=is%3Apr+is%3Aopen+head%3Afeature/prompt-prcreation45-...base%3Amain](https://github.com/your-owner/your-repo/pulls?q=is%3Apr+is%3Aopen+head%3Afeature/prompt-prcreation45-...base%3Amain)",
            "status": "already_exists"
          },
          "new_branch_name": "feature/prompt-prcreation45-20250507-110000",
          "commit_on_branch_details": { /* ... commit details ... */ }
        }
        ```
    *(Actual URLs, SHAs, and details will vary.)*
