from typing import Optional
from pydantic import BaseModel

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    userType: Optional[str] = None
