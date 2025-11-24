from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional, Any


class ConversationCreateResponse(BaseModel):
    conversation_id: UUID
    message: str


class ChatRequest(BaseModel):
    conversation_id: UUID
    message: str


class ProjectItem(BaseModel):
    id: int
    name: str
    city: str
    country: str
    price_usd: float
    unit_type: Optional[str]
    no_of_bedrooms: Optional[int]
    property_type: Optional[str]


class ChatResponse(BaseModel):
    conversation_id: UUID
    reply: str
    shortlisted_projects: List[ProjectItem] = []
    agent_state: Any
