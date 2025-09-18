from pydantic import BaseModel
from typing import List, Optional


class StoreInfo(BaseModel):
    store_id: str
    team_name: str
    profile_name: str


class B2BData(BaseModel):
    profiles: List[str]
    identities: List[str]


class OnboardingState(BaseModel):
    store_id: Optional[str] = None
    team_name: Optional[str] = None
    profile_name: Optional[str] = None
    b2b_profiles: Optional[List[str]] = None
    b2b_identities: Optional[List[str]] = None
    selected_profiles: Optional[List[str]] = None
    selected_identities: Optional[List[str]] = None
    step: str = "collect_store_id"


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    state: OnboardingState
    completed: bool = False