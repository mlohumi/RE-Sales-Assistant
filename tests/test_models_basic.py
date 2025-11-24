import pytest
from properties.models import Project, Lead, Booking


@pytest.mark.django_db
def test_project_str():
    p = Project.objects.create(
        name="Marina Heights",
        city="Dubai",
        country="UAE",
    )
    s = str(p)
    assert "Marina Heights" in s
    assert "Dubai" in s


@pytest.mark.django_db
def test_booking_table_name():
    # Just ensures Django sees Booking and db_table is correct
    assert Booking._meta.db_table == "visit_bookings"
