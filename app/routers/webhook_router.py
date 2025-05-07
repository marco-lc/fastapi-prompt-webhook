# app/routers/webhook_router.py
import json
import base64
import datetime # For PR branch naming
from typing import Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Body

# Relative imports from other modules within the 'app' package
from ..models import WebhookPayload
from ..config import settings
# Import all necessary helper functions
from ..helpers import (
    commit_manifest_to_github_direct,
    get_base_branch_sha,
    create_new_branch_from_base,
    commit_file_to_branch,
    create_github_pull_request
)

# Create an APIRouter instance.
router = APIRouter(
    prefix="/webhook", # All routes in this file will be under /webhook
    tags=["GitHub Webhooks"], # Grouped under "GitHub Webhooks" in API docs
)

@router.post("/github-commit", status_code=201)
async def handle_webhook_direct_commit_endpoint(payload: WebhookPayload = Body(...)):
    """
    Webhook endpoint to receive prompt commit events and commit DIRECTLY to the configured branch.
    """
    try:
        # Call the helper for direct commits
        github_response = await commit_manifest_to_github_direct(payload)
        
        return {
            "message": "Webhook received and manifest committed directly to GitHub successfully.",
            "github_commit_details": github_response.get("commit", {}),
            "github_content_details": github_response.get("content", {})
        }
    except HTTPException:
        raise # Re-raise if it's an HTTPException from the helper
    except Exception as e:
        error_message = f"An unexpected error occurred during direct commit: {str(e)}"
        print(f"[ERROR] {error_message}")
        raise HTTPException(status_code=500, detail="An internal server error occurred during direct commit.")


@router.post("/github-pr", status_code=201) # New endpoint for creating Pull Requests
async def handle_webhook_create_pr_endpoint(payload: WebhookPayload = Body(...)):
    """
    Webhook endpoint to receive prompt commit events and create a GitHub Pull Request.
    """
    # Use a short hash and timestamp for a unique branch name
    short_commit_hash = payload.commit_hash[:12] # First 12 chars of the commit hash
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    new_branch_name = f"feature/prompt-{short_commit_hash}-{timestamp}"
    
    pr_title = f"feat: Update prompt manifest from webhook ({short_commit_hash})"
    pr_body = (
        f"Automated Pull Request from webhook event.\n\n"
        f"Associated Commit Hash (from payload): `{payload.commit_hash}`\n"
        f"Event Created At (from payload): `{payload.created_at}`\n\n"
        f"Manifest details included in this PR:\n"
        f"```json\n{json.dumps(payload.manifest, indent=2)}\n```"
    )

    # Standard headers for GitHub API calls
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Serialize manifest to Base64 for the commit
    manifest_json_string = json.dumps(payload.manifest, indent=2)
    content_base64 = base64.b64encode(manifest_json_string.encode('utf-8')).decode('utf-8')
    # Commit message for the commit on the new feature branch
    commit_message_for_pr_branch = f"feat: Update prompt manifest for PR ({short_commit_hash})"

    async with httpx.AsyncClient() as client:
        try:
            # Step 1: Get the SHA of the base branch (e.g., main, develop)
            base_sha = await get_base_branch_sha(client, headers)

            # Step 2: Create a new branch from the base branch SHA
            await create_new_branch_from_base(client, new_branch_name, base_sha, headers)

            # Step 3: Commit the manifest file to the new feature branch
            commit_details_on_new_branch = await commit_file_to_branch(
                client, new_branch_name, settings.GITHUB_FILE_PATH, 
                content_base64, commit_message_for_pr_branch, headers
            )

            # Step 4: Create the Pull Request from the new feature branch to the base branch
            pr_details = await create_github_pull_request(
                client, new_branch_name, settings.GITHUB_BRANCH, 
                pr_title, pr_body, headers
            )

            # Determine success message based on PR creation status
            response_message = "Pull Request created successfully."
            if pr_details.get("status") == "already_exists":
                response_message = pr_details.get("message", "Pull Request already exists.")


            return {
                "message": response_message,
                "pull_request_url": pr_details.get("html_url"), # URL of the created/existing PR
                "pull_request_details": pr_details, # Full PR details from GitHub API
                "new_branch_name": new_branch_name,
                "commit_on_branch_details": commit_details_on_new_branch.get("commit", {})
            }

        except HTTPException:
            # Re-raise HTTPException if it was raised by one of the helpers
            raise
        except Exception as e:
            # Catch any other unexpected errors during the PR creation process
            error_message = f"An unexpected internal server error occurred during PR creation: {str(e)}"
            print(f"[ERROR] {error_message}")
            # Clean up the created branch if PR creation fails? (More advanced error handling)
            # For now, just raise a generic 500 error.
            raise HTTPException(status_code=500, detail="An internal server error occurred during PR creation.")
