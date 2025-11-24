from typing import List
from django.db.models import Q

from properties.models import Project
from agent.state import BuyerProfile, ProjectSummary


class ProjectSqlTool:
    """
    Text-to-SQL / DB access tool for the projects database.

    NOTE:
    - In this implementation we shortcut the "text-to-SQL" part by using a
      structured BuyerProfile that is produced by the intent_classification_node.
    - The tool still acts as a distinct "SQL tool" from the agent's perspective.
    - This class can later be extended to use Vanna + ChromaDB to translate
      natural language into actual SQL queries over the same schema.
    """

    def search_projects_by_profile(self, profile: BuyerProfile) -> List[ProjectSummary]:
        """
        Softer search:
          - Hard filters: city, bedrooms, property_type
          - Soft filters: unit_size, budget_min, budget_max
          - If budget filters eliminate everything, fall back to results without budget.
        """

        # Start with everything
        qs = Project.objects.all()

        # ---------- Hard filters ----------
        if profile.city:
            qs = qs.filter(city__iexact=profile.city)

        if profile.property_type:
            qs = qs.filter(property_type__iexact=(profile.property_type or "").lower())

        if profile.bedrooms is not None:
            qs = qs.filter(no_of_bedrooms=profile.bedrooms)

        base_qs = qs  # keep a copy before soft filters

        # ---------- Soft filter: unit_size ----------
        if profile.unit_size:
            qs_unit = qs.filter(unit_type__icontains=profile.unit_size)
            if qs_unit.exists():
                qs = qs_unit

        # ---------- Soft filters: budget ----------
        qs_budget = qs

        if profile.budget_min is not None:
            tmp = qs_budget.filter(price_usd__gte=profile.budget_min)
            if tmp.exists():
                qs_budget = tmp

        if profile.budget_max is not None:
            # allow NULL prices to stay (price_on_request)
            tmp = qs_budget.filter(Q(price_usd__lte=profile.budget_max) | Q(price_usd__isnull=True))
            if tmp.exists():
                qs_budget = tmp

        # If applying budget gave us something, use that
        if qs_budget.exists():
            qs = qs_budget
        else:
            # otherwise fall back to ignoring budget
            qs = base_qs

        # Final fallback: if still nothing, just return []
        if not qs.exists():
            return []

        # Order by price if possible (NULLs last), and limit to top 10
        qs = qs.order_by("price_usd")[:10]

        results: List[ProjectSummary] = []
        for p in qs:
            results.append(
                ProjectSummary(
                    id=p.id,
                    name=p.name,
                    city=p.city,
                    country=p.country,
                    price_usd=p.price_usd or 0.0,
                    unit_type=p.unit_type,
                    no_of_bedrooms=p.no_of_bedrooms,
                    property_type=p.property_type,
                )
            )

        return results

    # Placeholder for future Vanna/Chroma-style text-to-SQL
    def text_to_sql(self, natural_language_query: str) -> str:
        """
        (Placeholder) Given a natural language query, return a SQL query string.

        In a future version, this could:
          - Use Vanna + ChromaDB to propose a SQL query
          - Be executed via Django's connection.cursor() or SQLAlchemy

        For now, this is not used by the agent.
        """
        return "-- TODO: integrate Vanna to generate SQL for: " + natural_language_query


# Single instance used by the agent
project_sql_tool = ProjectSqlTool()
