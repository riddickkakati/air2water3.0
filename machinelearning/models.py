from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.validators import MaxValueValidator, MinValueValidator

def timeseries_upload_path_handler(instance, filename):
    return "machine_learning/timeseries/{user_id}_{group_id}/timeseries.txt".format(user_id=instance.user.id, group_id=instance.group.id)

def user_validation_path_handler(instance, filename):
    return "machine_learning/timeseries/{user_id}_{group_id}/user_validation.txt".format(user_id=instance.user.id, group_id=instance.group.id)

class MLGroup(models.Model):
    name = models.CharField(max_length=32, null=False, unique=False)
    location = models.CharField(max_length=32, null=False)
    description = models.CharField(max_length=256, null=False, unique=False)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('name', 'location'))

class MLMember(models.Model):
    group = models.ForeignKey(MLGroup, related_name='machine_learning_members', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='machine_learning_members_of', on_delete=models.CASCADE)
    admin = models.BooleanField(default=False)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user', 'group'),)

class MLComment(models.Model):
    group = models.ForeignKey(MLGroup, related_name='machine_learning_comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='machine_learning_user_comments', on_delete=models.CASCADE)
    description = models.CharField(max_length=256, null=False, unique=False)
    time = models.DateTimeField(auto_now_add=True)


class MLRun(models.Model):
    MODEL_CHOICES = [
        ('W', 'Air2water'),
        ('S', 'Air2stream')
    ]

    VALIDATION_CHOICES = [
        ('F', 'False'),
        ('R', 'Random_Percentage'),
        ('U', 'Uniform_Percentage'),
        ('N', 'Uniform_Number')
    ]

    # Existing fields
    group = models.ForeignKey(MLGroup, related_name='machine_learning_group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='machine_learning_runs', on_delete=models.CASCADE)
    timeseries_file = models.FileField(
        upload_to=timeseries_upload_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])]
    )

    validation_file = models.FileField(
        upload_to=user_validation_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        null=True,
        blank=True
    )

    interpolate = models.BooleanField(default=True)
    n_data_interpolate = models.IntegerField(blank=True, null=True, default=7)
    validation_required = models.CharField(max_length=1, choices=VALIDATION_CHOICES)
    percent = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(50)], default=10)
    model = models.CharField(max_length=1, choices=MODEL_CHOICES)

    # Status and timing fields
    status = models.CharField(max_length=20, default='pending')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_send = models.BooleanField(default=False)
    email_list = models.CharField(max_length=50, blank=True)

    # Results and error handling
    results_path = models.TextField(null=True, blank=True, help_text="Stores the zip file")
    analysis_summary = models.JSONField(null=True, blank=True, help_text="Stores the complete analysis results")
    yaml_results_path = models.CharField(max_length=255, null=True, blank=True,
                                         help_text="Path to the YAML results file")
    error_message = models.TextField(null=True, blank=True)