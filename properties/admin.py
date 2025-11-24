from django.contrib import admin
from .models import Project, Lead, Booking, ConversationSession


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "country", "price_usd")
    search_fields = ("name", "city", "country")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "created_at")
    search_fields = ("first_name", "last_name", "email")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "lead", "city", "status", "created_at")
    list_filter = ("status", "city")


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "created_at", "updated_at")
