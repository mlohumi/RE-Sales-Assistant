from typing import Optional

from properties.models import Project


def get_project_details(project_id: int) -> Optional[dict]:
    """
    Returns a structured dictionary of full project details.
    """

    try:
        p = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return None

    return {
        "id": p.id,
        "name": p.name,
        "developer_name": p.developer_name,
        "city": p.city,
        "country": p.country,
        "property_type": p.property_type,
        "unit_type": p.unit_type,
        "no_of_bedrooms": p.no_of_bedrooms,
        "bathrooms": p.bathrooms,
        "price_usd": p.price_usd,
        "area_sqm": p.area_sqm,
        "completion_status": p.completion_status,
        "completion_date": str(p.completion_date) if p.completion_date else None,
        "features": p.features,
        "facilities": p.facilities,
        "description": p.description,
    }
