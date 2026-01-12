from dataclasses import dataclass
from typing import Optional, List

@dataclass
class UserProfile:
    uid: str
    email: str
    display_name: str
    faculty: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[List[str]] = None
    is_tutor: bool = False
