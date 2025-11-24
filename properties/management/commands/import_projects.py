import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from properties.models import Project


class Command(BaseCommand):
    help = "Import property projects from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to the CSV file containing project data",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]

        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                row_count = 0
                created_count = 0
                updated_count = 0

                for row in reader:
                    row_count += 1

                    name = row.get("Project name") or row.get("project_name")
                    if not name:
                        self.stderr.write(f"Row {row_count}: missing Project name, skipping")
                        continue

                    # Basic fields – adapt keys if your headers differ slightly
                    city = row.get("city") or row.get("City")
                    country = row.get("country") or row.get("Country")
                    developer_name = row.get("developer name") or row.get("Developer Name")

                    no_of_bedrooms = row.get("No of bedrooms") or row.get("Bedrooms")
                    bathrooms = row.get("bathrooms") or row.get("Bathrooms")
                    unit_type = row.get("unit type") or row.get("Unit Type")
                    completion_status = row.get("Completion status (off plan/available)") or row.get("completion_status")

                    price_usd = row.get("Price (USD)") or row.get("price_usd")
                    area_sqm = row.get("Area (sq mtrs)") or row.get("area_sqm")
                    property_type = row.get("Property type (apartment/villa)") or row.get("property_type")

                    completion_date_raw = row.get("completion_date") or row.get("Completion Date")
                    features = row.get("features") or ""
                    facilities = row.get("facilities") or ""
                    description = row.get("Project description") or row.get("description") or ""

                    # Convert numeric fields safely
                    def to_int(val):
                        try:
                            return int(val)
                        except (TypeError, ValueError):
                            return None

                    def to_float(val):
                        try:
                            return float(val)
                        except (TypeError, ValueError):
                            return None

                    no_of_bedrooms = to_int(no_of_bedrooms)
                    bathrooms = to_int(bathrooms)
                    price_usd = to_float(price_usd)
                    area_sqm = to_float(area_sqm)

                    # Convert completion_status into our choices
                    status_normalized = None
                    if completion_status:
                        cs = completion_status.strip().lower()
                        if "off" in cs:
                            status_normalized = "off_plan"
                        elif "avail" in cs or "available" in cs:
                            status_normalized = "available"
                        elif "complete" in cs:
                            status_normalized = "completed"

                    # Parse completion date if present
                    parsed_date = None
                    if completion_date_raw:
                        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                            try:
                                parsed_date = datetime.strptime(completion_date_raw.strip(), fmt).date()
                                break
                            except ValueError:
                                continue

                    # Either create or update based on (name, city, country)
                    obj, created = Project.objects.update_or_create(
                        name=name,
                        city=city or "",
                        country=country or "",
                        defaults={
                            "developer_name": developer_name or "",
                            "no_of_bedrooms": no_of_bedrooms,
                            "bathrooms": bathrooms,
                            "unit_type": unit_type or "",
                            "completion_status": status_normalized or "",
                            "price_usd": price_usd,
                            "area_sqm": area_sqm,
                            "property_type": (property_type or "").lower() or "",
                            "completion_date": parsed_date,
                            "features": features or "",
                            "facilities": facilities or "",
                            "description": description or "",
                        },
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Processed {row_count} rows: {created_count} created, {updated_count} updated."
                    )
                )
        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_path}")
        except Exception as e:
            raise CommandError(f"Error while importing: {e}")
