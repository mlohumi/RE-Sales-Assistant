from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from uuid import UUID


class BuyerProfile(BaseModel):
    """
    Stores the property search preferences of the buyer.
    """
    city: Optional[str] = None
    budget_min: Optional[int] = None     # lower bound of budget, e.g. 500000
    budget_max: Optional[int] = None     # upper bound, e.g. 900000
    unit_size: Optional[str] = None      # e.g. "1BHK", "2BHK"
    bedrooms: Optional[int] = None       # in case user says "2 bedrooms"
    property_type: Optional[str] = None  # "apartment" / "villa" / etc.


class LeadInfo(BaseModel):
    """
    Info we collect when user agrees to book a visit.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None


class ProjectSummary(BaseModel):
    """
    Lightweight representation of a project to send back to UI / API.
    """
    id: int
    name: str
    city: str
    country: str
    price_usd: float
    unit_type: Optional[str] = None
    no_of_bedrooms: Optional[int] = None
    property_type: Optional[str] = None


class AgentState(BaseModel):
    """
    This is the core state object that LangGraph will read + update.
    It gets serialized into ConversationSession.state in the DB.
    """
    conversation_id: Optional[UUID] = None

    # full chat history: [{role: "user"/"assistant", content: "..."}]
    messages: List[Dict[str, Any]] = []

    # buyer preferences
    buyer_profile: BuyerProfile = BuyerProfile()

    # what projects we have shortlisted so far
    candidate_projects: List[ProjectSummary] = []
    selected_project_id: Optional[int] = None

    # lead details when booking
    lead_info: LeadInfo = LeadInfo()

    # simple routing fields
    intent: Optional[str] = None    # e.g. "collect_prefs", "recommend", "book_visit", "qa"
    stage: Optional[str] = None     # e.g. "greeting", "asking_prefs", "recommendations", "booking"

    class Config:
        # allow ORM-like dicts etc
        arbitrary_types_allowed = True
        json_encoders = {
        UUID: lambda v: str(v),
    }
