from fastapi import APIRouter, Depends, HTTPException
import logging
from app.core.auth import get_current_user
from app.db.store import store
from app.schemas.user import ProfileUpdate

router = APIRouter(prefix="/api/users", tags=["Users"])
logger = logging.getLogger(__name__)

@router.post("/complete-profile")
async def complete_profile(
    update: ProfileUpdate,
    user_id: str = Depends(get_current_user)
):
    """
    Update the user's profile with their name and/or user type.
    This is called during the onboarding flow.
    """
    try:
        success = await store.update_user(
            user_id=user_id,
            name=update.name,
            user_type=update.userType
        )
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update profile")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error while completing user profile")
        raise HTTPException(status_code=500, detail="Internal server error")
