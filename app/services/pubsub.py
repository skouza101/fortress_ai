import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import redis as sync_redis
import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None
_sync_redis_client: Optional[sync_redis.Redis] = None


def _validate_redis_url() -> str:
    redis_url = settings.REDIS_URL
    scheme = urlparse(redis_url).scheme
    if scheme not in {"redis", "rediss", "unix"}:
        raise RuntimeError(
            "REDIS_URL must start with redis://, rediss://, or unix://. "
            f"Current value starts with {scheme or 'no scheme'}."
        )
    return redis_url


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(_validate_redis_url(), decode_responses=True)
    return _redis_client


def get_sync_redis_client() -> sync_redis.Redis:
    global _sync_redis_client
    if _sync_redis_client is None:
        _sync_redis_client = sync_redis.from_url(_validate_redis_url(), decode_responses=True)
    return _sync_redis_client


async def publish_progress(task_id: str, user_id: str, payload: Dict[str, Any]):
    """
    Publish a progress update to a user-specific Redis channel.
    Channel format: `user_{user_id}_progress`
    """
    try:
        channel = f"user_{user_id}_progress"
        message = json.dumps({
            "task_id": task_id,
            **payload
        })
        await get_redis_client().publish(channel, message)
        logger.debug(f"Published to {channel}: {message}")
    except Exception as e:
        logger.error(f"Failed to publish progress to Redis: {e}")


async def get_subscriber(user_id: str):
    """
    Get a Redis PubSub object subscribed to the user's progress channel.
    """
    channel = f"user_{user_id}_progress"
    pubsub = get_redis_client().pubsub()
    await pubsub.subscribe(channel)
    logger.info(f"Subscribed to {channel}")
    return pubsub


def sync_publish_progress(task_id: str, user_id: str, payload: Dict[str, Any]):
    """
    Publish a progress update synchronously (for use in Celery tasks).
    """
    try:
        channel = f"user_{user_id}_progress"
        message = json.dumps({
            "task_id": task_id,
            **payload
        })
        get_sync_redis_client().publish(channel, message)
        logger.debug(f"Sync published to {channel}: {message}")
    except Exception as e:
        logger.error(f"Failed to sync publish progress to Redis: {e}")
