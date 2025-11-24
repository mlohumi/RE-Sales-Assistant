import pytest
from decimal import Decimal

from properties.models import Project
from agent.state import BuyerProfile
from agent.tools.t2sql_tool import project_sql_tool


@pytest.mark.django_db
def test_project_sql_tool_basic_search():
    # Arrange: create some sample projects in Dubai
    p1 = Project.objects.create(
        name="Marina Heights",
        city="Dubai",
        country="UAE",
        no_of_bedrooms=2,
        property_type="apartment",
        unit_type="2BHK",
        price_usd=Decimal("280000.00"),
    )

    p2 = Project.objects.create(
        name="Palm View",
        city="Dubai",
        country="UAE",
        no_of_bedrooms=3,
        property_type="apartment",
        unit_type="3BHK",
        price_usd=Decimal("450000.00"),
    )

    # Buyer profile: 2BHK apartment in Dubai, max budget 300000
    profile = BuyerProfile(
        city="Dubai",
        budget_min=None,
        budget_max=300000,
        unit_size="2BHK",
        bedrooms=2,
        property_type="apartment",
    )

    # Act
    results = project_sql_tool.search_projects_by_profile(profile)

    # Assert
    # Should only get the 2BHK within budget (p1)
    assert len(results) == 1
    assert results[0].name == "Marina Heights"
    assert results[0].city == "Dubai"
    assert results[0].no_of_bedrooms == 2


@pytest.mark.django_db
def test_project_sql_tool_budget_fallback():
    # Arrange: single project with higher price
    Project.objects.create(
        name="Skyline Elite",
        city="Dubai",
        country="UAE",
        no_of_bedrooms=2,
        property_type="apartment",
        unit_type="2BHK",
        price_usd=Decimal("500000.00"),
    )

    # Very low budget that would exclude the project if enforced strictly
    profile = BuyerProfile(
        city="Dubai",
        budget_min=None,
        budget_max=200000,
        unit_size="2BHK",
        bedrooms=2,
        property_type="apartment",
    )

    # Act
    results = project_sql_tool.search_projects_by_profile(profile)

    # Assert
    # Our tool is "soft" on budget: it should fall back to city/bedrooms-only
    assert len(results) == 1
    assert results[0].name == "Skyline Elite"
