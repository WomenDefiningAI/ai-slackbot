from fastapi import APIRouter

# Create router for health endpoints
router = APIRouter()


@router.get("/health")
async def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy"}
