# app/helpers.py
import json
import base64
import datetime # Added for timestamp in branch name
from typing import Dict, Any

import httpx
from fastapi import HTTPException

# Assuming models and config are in the parent directory of 'app' if 'app' is a subdirectory
# If 'helpers.py' is inside 'app/', then these imports are correct:
from .models import WebhookPayload
from .config import settings

# --- Helper for Direct Commit ---
async def commit_manifest_to_github_direct(payload: WebhookPayload) -> Dict[str, Any]:
    """
    Helper function to commit the manifest directly to the main configured branch.
    (Renamed from _commit_manifest_to_github to avoid underscore for external use
     and to be specific about 'direct' commit)

    Args:
        payload: The webhook payload containing the manifest and commit details.

    Returns:
        A dictionary containing the response from the GitHub API upon successful commit.
    """
    github_api_base_url = "https://api.github.com"
    repo_file_url = (
        f"{github_api_base_url}/repos/{settings.GITHUB_REPO_OWNER}/"
        f"{settings.GITHUB_REPO_NAME}/contents/{settings.GITHUB_FILE_PATH}"
    )

    headers = {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    manifest_json_string = json.dumps(payload.manifest, indent=2)
    content_base64 = base64.b64encode(manifest_json_string.encode('utf-8')).decode('utf-8')
    # Using the full commit_hash in the message for direct commit
    commit_message = f"feat: Update prompt manifest via webhook - commit {payload.commit_hash}"
    
    data_to_commit = {
        "message": commit_message,
        "content": content_base64,
        "branch": settings.GITHUB_BRANCH, # Commits to the main configured branch
    }

    async with httpx.AsyncClient() as client:
        current_file_sha = None
        try:
            params_get = {"ref": settings.GITHUB_BRANCH}
            response_get = await client.get(repo_file_url, headers=headers, params=params_get)
            if response_get.status_code == 200:
                current_file_sha = response_get.json().get("sha")
            elif response_get.status_code != 404: # If not 404 (not found), it's an unexpected error
                response_get.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_detail = f"GitHub API error (GET file SHA for direct commit): {e.response.status_code} - {e.response.text}"
            print(f"[ERROR] {error_detail}")
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except httpx.RequestError as e:
            error_detail = f"Network error connecting to GitHub (GET file SHA for direct commit): {str(e)}"
            print(f"[ERROR] {error_detail}")
            raise HTTPException(status_code=503, detail=error_detail)

        if current_file_sha:
            data_to_commit["sha"] = current_file_sha

        try:
            response_put = await client.put(repo_file_url, headers=headers, json=data_to_commit)
            response_put.raise_for_status()
            return response_put.json()
        except httpx.HTTPStatusError as e:
            error_detail = f"GitHub API error (PUT content for direct commit): {e.response.status_code} - {e.response.text}"
            if e.response.status_code == 409:
                error_detail = (
                    f"GitHub API conflict (PUT content for direct commit): {e.response.text}. "
                    "This might be due to an outdated SHA or branch protection rules."
                )
            elif e.response.status_code == 422:
                error_detail = (
                    f"GitHub API Unprocessable Entity (PUT content for direct commit): {e.response.text}. "
                    f"Ensure the branch '{settings.GITHUB_BRANCH}' exists and the payload is correctly formatted."
                )
            print(f"[ERROR] {error_detail}")
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except httpx.RequestError as e:
            error_detail = f"Network error connecting to GitHub (PUT content for direct commit): {str(e)}"
            print(f"[ERROR] {error_detail}")
            raise HTTPException(status_code=503, detail=error_detail)

# --- Helpers for Pull Request Flow ---

async def get_base_branch_sha(client: httpx.AsyncClient, headers: Dict[str, str]) -> str:
    """
    Fetches the SHA of the latest commit on the configured base branch (settings.GITHUB_BRANCH).
    """
    ref_url = f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/git/refs/heads/{settings.GITHUB_BRANCH}"
    try:
        response = await client.get(ref_url, headers=headers)
        response.raise_for_status()
        return response.json()["object"]["sha"]
    except httpx.HTTPStatusError as e:
        error_detail = f"GitHub API error (getting base branch SHA for '{settings.GITHUB_BRANCH}'): {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except httpx.RequestError as e:
        error_detail = f"Network error connecting to GitHub (getting base branch SHA for '{settings.GITHUB_BRANCH}'): {str(e)}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=503, detail=error_detail)
    except (KeyError, IndexError) as e: # Catch potential issues with JSON structure
        error_detail = f"Unexpected response structure from GitHub when getting SHA for '{settings.GITHUB_BRANCH}': {str(e)}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=500, detail=error_detail)

async def create_new_branch_from_base(client: httpx.AsyncClient, new_branch_name: str, base_branch_sha: str, headers: Dict[str, str]) -> None:
    """
    Creates a new branch in the repository pointing to the base_branch_sha.
    """
    branch_url = f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/git/refs"
    payload = {
        "ref": f"refs/heads/{new_branch_name}",
        "sha": base_branch_sha
    }
    try:
        response = await client.post(branch_url, headers=headers, json=payload)
        if response.status_code == 422 and "Reference already exists" in response.text:
            print(f"[INFO] Branch '{new_branch_name}' already exists. Proceeding.")
            # Decide if this should be an error or if it's okay to proceed
            # For now, we allow proceeding, assuming the commit will update the existing branch.
            # If strict new branch creation is needed, raise HTTPException here.
            # raise HTTPException(status_code=409, detail=f"Branch '{new_branch_name}' already exists.")
            pass
        else:
            response.raise_for_status() # Raises for other 4xx/5xx errors
    except httpx.HTTPStatusError as e:
        error_detail = f"GitHub API error (creating branch '{new_branch_name}'): {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except httpx.RequestError as e:
        error_detail = f"Network error connecting to GitHub (creating branch '{new_branch_name}'): {str(e)}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=503, detail=error_detail)

async def commit_file_to_branch(client: httpx.AsyncClient, branch_name: str, file_path: str, content_base64: str, commit_message: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Commits a file to the specified branch. Creates or updates the file.
    """
    file_url = f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/contents/{file_path}"
    
    current_file_sha = None
    try:
        get_params = {"ref": branch_name} # Get file from the specific new branch
        response_get = await client.get(file_url, headers=headers, params=get_params)
        if response_get.status_code == 200:
            current_file_sha = response_get.json().get("sha")
        elif response_get.status_code != 404:
            response_get.raise_for_status()
    except httpx.HTTPStatusError as e:
        print(f"[INFO] Could not get SHA for '{file_path}' on branch '{branch_name}': {e.response.status_code}. Assuming new file or continuing.")
    except httpx.RequestError as e:
        print(f"[INFO] Network error checking for file '{file_path}' on branch '{branch_name}': {str(e)}. Assuming new file or continuing.")

    commit_payload = {
        "message": commit_message,
        "content": content_base64,
        "branch": branch_name, # Important: commit to the new feature branch
    }
    if current_file_sha:
        commit_payload["sha"] = current_file_sha

    try:
        response = await client.put(file_url, headers=headers, json=commit_payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_detail = f"GitHub API error (committing file to '{branch_name}'): {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except httpx.RequestError as e:
        error_detail = f"Network error connecting to GitHub (committing file to '{branch_name}'): {str(e)}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=503, detail=error_detail)

async def create_github_pull_request(client: httpx.AsyncClient, head_branch: str, base_branch: str, title: str, body: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """
    Creates a pull request from the head_branch to the base_branch.
    """
    pr_url = f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/pulls"
    payload = {
        "title": title,
        "body": body,
        "head": head_branch, # The branch with your new changes
        "base": base_branch,  # The branch you want to merge into (e.g., settings.GITHUB_BRANCH)
        "draft": False 
    }
    try:
        response = await client.post(pr_url, headers=headers, json=payload)
        if response.status_code == 422: # Unprocessable Entity
            response_json = response.json()
            # Check if PR already exists
            if any("A pull request already exists" in err.get("message", "") for err in response_json.get("errors", [])):
                print(f"[INFO] Pull request from '{head_branch}' to '{base_branch}' already exists.")
                # Attempt to find the existing PR URL (this is a bit more involved, might need a separate GET)
                # For simplicity, returning a generic message.
                # A more robust solution would GET /repos/{owner}/{repo}/pulls?head={owner}:{head_branch}&base={base_branch}
                # and return the html_url of the first result if it exists.
                existing_pr_url = f"https://github.com/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/pulls?q=is%3Apr+is%3Aopen+head%3A{head_branch}+base%3A{base_branch}"
                return {
                    "message": f"Pull request from '{head_branch}' to '{base_branch}' already exists.",
                    "html_url": existing_pr_url, # Provide a link to search for the PR
                    "status": "already_exists"
                }
            # Otherwise, it's some other validation error
            error_detail = f"GitHub API validation error (creating PR): {response.status_code} - {response.text}"
            print(f"[ERROR] {error_detail}")
            raise HTTPException(status_code=response.status_code, detail=error_detail)
        
        response.raise_for_status() # For other 4xx/5xx errors
        return response.json() # Contains PR details including html_url
    except httpx.HTTPStatusError as e:
        error_detail = f"GitHub API error (creating PR from '{head_branch}' to '{base_branch}'): {e.response.status_code} - {e.response.text}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except httpx.RequestError as e:
        error_detail = f"Network error connecting to GitHub (creating PR from '{head_branch}' to '{base_branch}'): {str(e)}"
        print(f"[ERROR] {error_detail}")
        raise HTTPException(status_code=503, detail=error_detail)
