from django.db import models
import uuid


class Project(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    developer_name = models.CharField(max_length=255, blank=True)
    no_of_bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)
    unit_type = models.CharField(max_length=100, blank=True)
    COMPLETION_STATUS_CHOICES = [
        ("off_plan", "Off plan"),
        ("available", "Available"),
        ("completed", "Completed"),
    ]
    completion_status = models.CharField(
        max_length=50,
        choices=COMPLETION_STATUS_CHOICES,
        blank=True,
    )
    price_usd = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    area_sqm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    PROPERTY_TYPE_CHOICES = [
        ("apartment", "Apartment"),
        ("villa", "Villa"),
        ("other", "Other"),
    ]
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPE_CHOICES, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    features = models.TextField(blank=True)
    facilities = models.TextField(blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.city}, {self.country})"


class Lead(models.Model):
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email


class Booking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name="bookings")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="bookings")
    city = models.CharField(max_length=255)
    preferred_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
      db_table = "visit_bookings"

    def __str__(self):
        return f"Booking #{self.id} - {self.lead} -> {self.project}"


class ConversationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lead = models.ForeignKey(Lead, null=True, blank=True, on_delete=models.SET_NULL)
    state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Conversation {self.id}"
