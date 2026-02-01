"""
Health check endpoints for container orchestration.

These endpoints are designed to be used by container orchestrators (Docker, Kubernetes)
and load balancers to determine service health and readiness.
"""
from fastapi import APIRouter, status

router = APIRouter()


@router.get(
    "/health/live",
    summary="Liveness Probe",
    description="Check if the application is running",
    response_description="Application liveness status",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Application is alive and running",
            "content": {
                "application/json": {
                    "example": {"status": "alive"}
                }
            },
        }
    },
    tags=["Health"],
)
async def liveness():
    """
    Liveness probe - is the application running?
    
    Used by container orchestrators to determine if the application should be restarted.
    This endpoint should return 200 as long as the application process is running.
    
    **Use case:** Kubernetes liveness probe, Docker health check
    
    **Best practice:** Keep this check simple and fast. It should only verify that
    the application is running, not that it can connect to external dependencies.
    """
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness Probe",
    description="Check if the application is ready to serve traffic",
    response_description="Application readiness status",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Application is ready to serve traffic",
            "content": {
                "application/json": {
                    "example": {"status": "ready"}
                }
            },
        },
        503: {
            "description": "Application is not ready (dependencies unavailable)",
            "content": {
                "application/json": {
                    "example": {"status": "not ready", "reason": "database unavailable"}
                }
            },
        },
    },
    tags=["Health"],
)
async def readiness():
    """
    Readiness probe - is the application ready to serve traffic?
    
    Used by load balancers to determine if traffic should be routed to this instance.
    This endpoint should verify that all critical dependencies are available.
    
    **Use case:** Kubernetes readiness probe, load balancer health checks
    
    **Current implementation:** Returns ready immediately. In production, you should add:
    - Database connectivity check
    - Cache/Redis connectivity check
    - External API availability checks
    - Any other critical dependency verification
    
    **Example enhanced check:**
    ```python
    try:
        await db.execute("SELECT 1")  # Verify database
        await redis.ping()  # Verify cache
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(503, {"status": "not ready", "reason": str(e)})
    ```
    """
    # Add database/cache connectivity checks here if needed
    return {"status": "ready"}

