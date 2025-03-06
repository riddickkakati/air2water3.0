from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

def service_key_path_handler(instance, filename):
    return "monitoring/{user_id}_{group_id}/service_key.json".format(user_id=instance.user.id, group_id=instance.group.id)

class MonitoringGroup(models.Model):
    name = models.CharField(max_length=32, null=False, unique=False)
    location = models.CharField(max_length=32, null=False)
    description = models.CharField(max_length=256, null=False, unique=False)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('name', 'location'))

class MonitoringMember(models.Model):
    group = models.ForeignKey(MonitoringGroup, related_name='monitoring_members', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='monitoring_members_of', on_delete=models.CASCADE)
    admin = models.BooleanField(default=False)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user', 'group'),)

class MonitoringComment(models.Model):
    group = models.ForeignKey(MonitoringGroup, related_name='monitoring_comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='monitoring_user_comments', on_delete=models.CASCADE)
    description = models.CharField(max_length=256, null=False, unique=False)
    time = models.DateTimeField(auto_now_add=True)


class MonitoringRun(models.Model):
    SATELLITE_TILE = [
        ('L', 'Landsat'),
        ('S', 'Sentinel')
    ]

    PARAMETER = [
        ('C', 'CHLA'),
        ('T', 'TURBIDITY'),
        ('D', 'DO')
    ]

    # Existing fields
    group = models.ForeignKey(MonitoringGroup, related_name='monitoring_group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='monitoring_runs', on_delete=models.CASCADE)

    # Date fields
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)

    # Location fields
    longitude = models.FloatField(null=False, blank=False)
    latitude = models.FloatField(null=False, blank=False)

    # Analysis parameters
    satellite = models.CharField(max_length=1, choices=SATELLITE_TILE)
    parameter = models.CharField(max_length=1, choices=PARAMETER)

    # New fields for Air2water_monit
    cloud_cover = models.IntegerField(default=7)
    service_account = models.CharField(max_length=255, default="your-service-account@project.iam.gserviceaccount.com")
    service_key_file = models.FileField(
        upload_to=service_key_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['json'])],
        blank=True,
        null=True
    )

    # Status and timing fields
    status = models.CharField(max_length=20, default='pending')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Results and error handling
    results_path = models.TextField(null=True, blank=True, help_text="Stores the Folium map HTML")
    error_message = models.TextField(null=True, blank=True)