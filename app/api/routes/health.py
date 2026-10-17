from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Return the basic health status of the API."""
    return {
        "status": "ok",
        "service": "docuchat",
    }