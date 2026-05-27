import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.services.pubsub import get_subscriber
from app.core.auth import verify_nextauth_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

async def verify_ws_token(token: str) -> str:
    """
    Validate the NextAuth JWT token.
    """
    if not token:
        raise ValueError("No token provided")
    
    try:
        user_id = verify_nextauth_token(token)
        return user_id
    except Exception as e:
        logger.error(f"WS Token validation failed: {e}")
        raise ValueError(f"Token validation failed: {str(e)}")


@router.websocket("/progress")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        # 1. JWT Validation
        user_id = await verify_ws_token(token)
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008) # Policy Violation
        return

    await websocket.accept()
    logger.info(f"WebSocket connected for user: {user_id}")

    # 2. Subscribe to user's Redis Pub/Sub channel
    try:
        pubsub = await get_subscriber(user_id)
    except Exception as e:
        logger.error(f"Unable to subscribe to progress updates for user {user_id}: {e}")
        await websocket.close(code=1011)
        return

    try:
        # Read from Redis and send to WebSocket
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                await websocket.send_text(data)
                
                # If we detect completion, we can log it
                parsed = json.loads(data)
                if parsed.get("status") in ["completed", "failed", "cancelled"]:
                    logger.info(f"Task {parsed.get('task_id')} finished with status: {parsed.get('status')}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
