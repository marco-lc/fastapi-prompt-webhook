# app/models.py
from typing import Dict, Any
from pydantic import BaseModel, Field

class WebhookPayload(BaseModel):
    """
    Defines the expected structure of the incoming webhook payload.
    This model is used for request body validation and serialization.
    """
    manifest: Dict[str, Any] = Field(
        ...,  # Ellipsis indicates this field is required
        description="The main content or configuration data to be committed to GitHub."
    )
    commit_hash: str = Field(
        ...,
        description="An identifier for the commit event that triggered the webhook."
    )
    created_at: str = Field(
        ...,
        description="Timestamp indicating when the event was created (ISO format preferred)."
    )

    # Example of how this model might be used in a request:
    # {
    #   "manifest": {"key": "value", "config": {"setting": True}},
    #   "commit_hash": "abc123xyz789",
    #   "created_at": "2025-05-07T10:00:00Z"
    # }

