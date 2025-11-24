import pytest
from decimal import Decimal

from properties.models import Project, Lead, Booking
from agent.state import BuyerProfile, LeadInfo
from agent.tools.booking_tool import create_lead_and_booking


@pytest.mark.django_db
def test_create_lead_and_booking_creates_records():
    # Arrange: create a project
    project = Project.objects.create(
        name="Marina Heights",
        city="Dubai",
        country="UAE",
        no_of_bedrooms=2,
        property_type="apartment",
        unit_type="2BHK",
        price_usd=Decimal("300000.00"),
    )

    lead_info = LeadInfo(
        first_name="Mukesh",
        last_name="Lohumi",
        email="mukesh@example.com",
    )

    buyer_profile = BuyerProfile(
        city="Dubai",
        budget_min=None,
        budget_max=300000,
        unit_size="2BHK",
        bedrooms=2,
        property_type="apartment",
    )

    # Act
    booking = create_lead_and_booking(
        lead_info=lead_info,
        buyer_profile=buyer_profile,
        project_id=project.id,
    )

    # Assert: Lead & Booking are created and linked
    assert booking is not None
    assert isinstance(booking, Booking)
    assert booking.project == project
    assert booking.city == "Dubai"

    lead = booking.lead
    assert lead.first_name == "Mukesh"
    assert lead.email == "mukesh@example.com"

    # Lead.preferences should contain the serialized BuyerProfile
    assert isinstance(lead.preferences, dict)
    assert lead.preferences.get("city") == "Dubai"
    assert lead.preferences.get("bedrooms") == 2

    # There should be one lead and one booking in DB
    assert Lead.objects.count() == 1
    assert Booking.objects.count() == 1
