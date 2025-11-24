from typing import Optional

from properties.models import Lead, Booking, Project
from agent.state import LeadInfo, BuyerProfile


def create_lead_and_booking(
    lead_info: LeadInfo,
    buyer_profile: BuyerProfile,
    project_id: int,
) -> Optional[Booking]:
    """
    Creates a Lead + Booking entry in the database.

    Returns:
        Booking instance if successful, None if project not found.
    """

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return None

    lead = Lead.objects.create(
        first_name=lead_info.first_name or "",
        last_name=lead_info.last_name or "",
        email=lead_info.email or "",
        preferences=buyer_profile.model_dump(mode="json"),
    )

    booking = Booking.objects.create(
        lead=lead,
        project=project,
        city=project.city,
    )

    return booking
