import pytest
from decimal import Decimal

from properties.models import Project
from agent.tools.project_info_tool import get_project_details


@pytest.mark.django_db
def test_get_project_details_returns_expected_fields():
    # Arrange
    project = Project.objects.create(
        name="Marina Heights",
        city="Dubai",
        country="UAE",
        developer_name="SilverLand Dev",
        no_of_bedrooms=2,
        bathrooms=2,
        unit_type="2BHK",
        completion_status="available",
        price_usd=Decimal("300000.00"),
        area_sqm=Decimal("110.5"),
        property_type="apartment",
        features="Sea view, Balcony",
        facilities="Pool, Gym",
        description="A premium waterfront apartment.",
    )

    # Act
    details = get_project_details(project.id)

    # Assert
    assert details is not None
    assert details["name"] == "Marina Heights"
    assert details["city"] == "Dubai"
    assert details["country"] == "UAE"
    assert details["developer_name"] == "SilverLand Dev"
    assert details["no_of_bedrooms"] == 2
    assert details["bathrooms"] == 2
    assert details["property_type"] == "apartment"
    assert float(details["price_usd"]) == 300000.0
    assert float(details["area_sqm"]) == 110.5
    assert "Sea view" in (details["features"] or "")
    assert "Pool" in (details["facilities"] or "")
    assert "waterfront" in (details["description"] or "")
