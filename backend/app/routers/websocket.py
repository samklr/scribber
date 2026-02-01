"""
WebSocket endpoint for real-time project status updates.
"""
import asyncio
import json
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.project import Project
from app.models.user import User

router = APIRouter(tags=["WebSocket"])

# Store active connections: {user_id: {project_id: set of websockets}}
active_connections: Dict[int, Dict[int, Set[WebSocket]]] = {}


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    async def connect(self, websocket: WebSocket, user_id: int, project_id: int):
        """Accept and register a WebSocket connection."""
        await websocket.accept()

        if user_id not in active_connections:
            active_connections[user_id] = {}
        if project_id not in active_connections[user_id]:
            active_connections[user_id][project_id] = set()

        active_connections[user_id][project_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int, project_id: int):
        """Remove a WebSocket connection."""
        if user_id in active_connections:
            if project_id in active_connections[user_id]:
                active_connections[user_id][project_id].discard(websocket)
                if not active_connections[user_id][project_id]:
                    del active_connections[user_id][project_id]
            if not active_connections[user_id]:
                del active_connections[user_id]

    async def send_update(self, user_id: int, project_id: int, data: dict):
        """Send update to all connections for a specific project."""
        if user_id in active_connections:
            if project_id in active_connections[user_id]:
                dead_connections = set()
                for websocket in active_connections[user_id][project_id]:
                    try:
                        await websocket.send_json(data)
                    except Exception:
                        dead_connections.add(websocket)

                # Clean up dead connections
                for ws in dead_connections:
                    active_connections[user_id][project_id].discard(ws)

    async def broadcast_to_user(self, user_id: int, data: dict):
        """Send update to all connections for a user."""
        if user_id in active_connections:
            for project_id in active_connections[user_id]:
                await self.send_update(user_id, project_id, data)


manager = ConnectionManager()


async def get_user_from_token(token: str) -> User | None:
    """Validate token and get user."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            return None

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.email == email.lower())
            )
            return result.scalar_one_or_none()
    except JWTError:
        return None


async def verify_project_access(user_id: int, project_id: int) -> bool:
    """Verify user has access to the project."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None


@router.websocket("/ws/projects/{project_id}")
async def websocket_project_status(
    websocket: WebSocket,
    project_id: int,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time project status updates.

    Connect with: ws://localhost:8000/api/v1/ws/projects/{project_id}?token={jwt_token}

    Sends JSON messages:
    - {"type": "status", "status": "transcribing", "progress": 50}
    - {"type": "completed", "transcription": "...", "summary": "..."}
    - {"type": "error", "message": "..."}
    """
    # Authenticate user
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Verify project access
    if not await verify_project_access(user.id, project_id):
        await websocket.close(code=4003, reason="Access denied")
        return

    # Connect
    await manager.connect(websocket, user.id, project_id)

    try:
        # Send initial status
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project:
                await websocket.send_json({
                    "type": "status",
                    "status": project.status.value,
                    "transcription": project.transcription,
                    "summary": project.summary,
                    "error_message": project.error_message,
                })

        # Keep connection alive and listen for messages
        while True:
            try:
                # Wait for ping/pong or client messages
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )

                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")

                # Handle status request
                elif data == "status":
                    async with AsyncSessionLocal() as db:
                        result = await db.execute(
                            select(Project).where(Project.id == project_id)
                        )
                        project = result.scalar_one_or_none()
                        if project:
                            await websocket.send_json({
                                "type": "status",
                                "status": project.status.value,
                                "transcription": project.transcription,
                                "summary": project.summary,
                                "error_message": project.error_message,
                            })

            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, user.id, project_id)


# Helper function to notify project updates (called from tasks)
async def notify_project_update(user_id: int, project_id: int, status: str, **kwargs):
    """
    Notify connected clients about project updates.
    Call this from Celery tasks when status changes.
    """
    data = {
        "type": "status" if status not in ["completed", "failed"] else status,
        "status": status,
        **kwargs
    }
    await manager.send_update(user_id, project_id, data)
