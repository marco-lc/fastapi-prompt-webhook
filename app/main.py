# app/main.py
from fastapi import FastAPI

# Relative imports for modules within the 'app' package
from .routers import webhook_router
from .config import settings # Import settings to ensure they are loaded/validated at startup

# Initialize FastAPI app
app = FastAPI(
    title="Webhook to GitHub Commit Service",
    description=(
        "Receives a webhook payload and commits its 'manifest' part "
        "to a GitHub repository. Refactored structure."
    ),
    version="1.0.1", # Updated version for the refactor
)

# Include the webhook router
# All routes defined in webhook_router will be available under its defined prefix (e.g., /webhook)
app.include_router(webhook_router.router)

# Health check endpoint
@app.get("/health", status_code=200, tags=["Health"])
async def health_check():
    """
    A simple health check endpoint to confirm the service is operational.
    """
    return {"status": "ok", "message": "Webhook to GitHub Commit Service is running."}

