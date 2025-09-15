from django.db import models
from core.models import UserProfile


class HealthConnectData(models.Model):
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='health_data')
    method = models.CharField(max_length=50)  # e.g., 'steps', 'heartRate'
    record_id = models.CharField(max_length=255, db_index=True)  # from _id in API response
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    data = models.JSONField()  # Raw data object from Health Connect
    app_source = models.CharField(max_length=255)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profile', 'method', 'record_id')
        ordering = ['-start_time']
        verbose_name = "Health Connect Data"
        verbose_name_plural = "Health Connect Data"

    def __str__(self):
        return f"{self.method} - {self.start_time} ({self.profile.username})"