from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.core.validators import MaxValueValidator, MinValueValidator

def profile_pic_upload_path_handler(instance, filename):
    return "avatars/{user_id}_{group_id}/profile_pic.jpg".format(id=instance.user.id)
def parameters_upload_path_handler(instance, filename):
    return "parameters/{user_id}_{group_id}/parameters_forward.yaml".format(user_id=instance.user.id, group_id=instance.group.id)
def timeseries_upload_path_handler(instance, filename):
    return "timeseries/{user_id}_{group_id}/timeseries.txt".format(user_id=instance.user.id, group_id=instance.group.id)
def parameter_ranges_upload_path_handler(instance, filename):
    return "parameters/{user_id}_{group_id}/parameter_ranges.yaml".format(user_id=instance.user.id, group_id=instance.group.id)
def user_validation_path_handler(instance, filename):
    return "timeseries/{user_id}_{group_id}/user_validation.txt".format(user_id=instance.user.id, group_id=instance.group.id)

class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=profile_pic_upload_path_handler, blank=True)
    bio = models.CharField(max_length=256, blank=True, null=True)

class ForecastingGroup(models.Model):
    name = models.CharField(max_length=32, null=False, unique=False)
    location = models.CharField(max_length=32, null=False)
    description = models.CharField(max_length=256, null=False, unique=False)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('name', 'location'))

class ForecastingMember(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='forecasting_members', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='forecasting_members_of', on_delete=models.CASCADE)
    admin = models.BooleanField(default=False)
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user', 'group'),)

class ForecastingComment(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='forecasting_comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='forecasting_user_comments', on_delete=models.CASCADE)
    description = models.CharField(max_length=256, null=False, unique=False)
    time = models.DateTimeField(auto_now_add=True)

class TimeSeriesData(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='timeseries', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='uploaded_timeseries', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=timeseries_upload_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])]
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=256, blank=True)

class ParameterFile(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='parameter_files_group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='parameter_files_user', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=parameters_upload_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['yaml'])],
        blank=True,
        null=True
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=256, blank=True)

class ForwardParameter(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='parameter_values_group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='parameter_values_user', on_delete=models.CASCADE)
    parameter1 = models.FloatField(null=True,blank=True)
    parameter2 = models.FloatField(null=True, blank=True)
    parameter3 = models.FloatField(null=True, blank=True)
    parameter4 = models.FloatField(null=True, blank=True)
    parameter5 = models.FloatField(null=True, blank=True)
    parameter6 = models.FloatField(null=True, blank=True)
    parameter7 = models.FloatField(null=True, blank=True)
    parameter8 = models.FloatField(null=True, blank=True)
    file_path = models.CharField(max_length=256, null=True, blank=True)

class ParameterRangesFile(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='parameter_ranges_group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='parameter_ranges_user', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=parameter_ranges_upload_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['yaml'])],
        blank=True,
        null=True
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=256, blank=True)

class UserValidationFile(models.Model):
    group = models.ForeignKey(ForecastingGroup, related_name='user_validation_group', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='user_validation_user', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to=user_validation_path_handler,
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        blank=True,
        null=True
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=256, blank=True)

class SimulationRun(models.Model):

    MODEL_CHOICES = [
        ('W', 'Air2water'),
        ('S', 'Air2stream')
    ]

    METHOD_CHOICES = [
        ('S', 'SPOTPY'),
        ('C', 'PYCUP')
    ]

    MODE_CHOICES = [
        ('F', 'ForwardMode'),
        ('C', 'Calibration')
    ]

    OPTIMIZER_CHOICES = [
        ('P', 'PSO'),
        ('L', 'LATINHYPERCUBE'),
        ('M', 'MONTECARLO')
    ]

    VALIDATION_CHOICES = [
        ('F', 'False'),
        ('R', 'Random_Percentage'),
        ('U', 'Uniform_Percentage'),
        ('N', 'Uniform_Number')
    ]

    ERROR_METRIC_CHOICES = [
        ('R', 'RMSE'),
        ('K', 'KGE'),
        ('N', 'NS')
    ]

    SOLVER_CHOICES = [
        ('E', 'euler'),
        ('T', 'rk2'),
        ('F', 'rk4'),
        ('C', 'cranknicolson')
    ]

    FORWARD_CHOICES = [
        ('U', 'UploadFile'),
        ('W', 'WriteParameters')
    ]

    COMPILER_CHOICES = [
        ('C', 'Cython'),
        ('F', 'Fortran')
    ]

    DB_CHOICES = [
        ('C', 'Custom'),
        ('R', 'RAM')
    ]

    group = models.ForeignKey(ForecastingGroup, related_name='simulations', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='simulation_runs', on_delete=models.CASCADE)
    timeseries = models.ForeignKey(TimeSeriesData, related_name='simulations_timeseries', on_delete=models.CASCADE)
    parameters_file = models.ForeignKey(ParameterFile, related_name='forward_simulations_file', on_delete=models.CASCADE, blank=True, null=True)
    parameters_forward = models.ForeignKey(ForwardParameter, related_name='forward_simulations_params', on_delete=models.CASCADE, blank=True, null=True)
    parameter_ranges_file = models.ForeignKey(ParameterRangesFile, related_name='parameter_ranges_file_simulation', on_delete=models.CASCADE, blank=True, null=True)
    user_validation_file = models.ForeignKey(UserValidationFile, related_name='user_validation_file_simulation', on_delete=models.CASCADE, blank=True, null=True)

    # Basic simulation parameters
    interpolate = models.BooleanField(default=True)
    n_data_interpolate = models.IntegerField(blank=True, null=True, default=7)
    validation_required = models.CharField(max_length=1, choices=VALIDATION_CHOICES)
    percent = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(50)], default=10)
    core = models.IntegerField(blank=True, null=True, default=1)
    depth = models.FloatField(blank=True, null=True, default=14.0)
    compiler = models.CharField(max_length=1, choices=COMPILER_CHOICES)
    CFL = models.FloatField(blank=True, null=True, default=0.9)
    databaseformat= models.CharField(max_length=1, choices=DB_CHOICES)
    computeparameterranges = models.BooleanField(default=True)
    computeparameters= models.BooleanField(default=False)

    model = models.CharField(max_length=1, choices=MODEL_CHOICES)
    mode = models.CharField(max_length=1, choices=MODE_CHOICES)
    method = models.CharField(max_length=1, choices=METHOD_CHOICES)
    optimizer = models.CharField(max_length=1, choices=OPTIMIZER_CHOICES, blank=True, null=True)
    forward_options = models.CharField(max_length=1, choices=FORWARD_CHOICES, default='W')
    error_metric = models.CharField(max_length=1, choices=ERROR_METRIC_CHOICES)
    solver = models.CharField(max_length=1, choices=SOLVER_CHOICES)
    log_flag = models.BooleanField(default=True)
    resampling_frequency_days = models.IntegerField(blank=True, null=True, default=1)
    resampling_frequency_weeks = models.IntegerField(blank=True, null=True, default=1)
    email_send = models.BooleanField(default=False)
    email_list = models.CharField(max_length=50, blank=True)

    # Status and results
    updated_at = models.DateTimeField(auto_now=True)
    error_message = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default='pending')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    results_path = models.CharField(max_length=512, null=True, blank=True)

class PSOParameter(models.Model):
    simulation = models.OneToOneField(
        SimulationRun,
        related_name='pso_params',
        on_delete=models.CASCADE
    )
    swarm_size = models.IntegerField(default=2000)
    phi1 = models.FloatField(default=2.0)
    phi2 = models.FloatField(default=2.0)
    omega1 = models.FloatField(default=0.5)
    omega2 = models.FloatField(default=0.5)
    max_iterations = models.IntegerField(default=2000)

class LatinParameter(models.Model):
    simulation = models.OneToOneField(
        SimulationRun,
        related_name='latin_params',
        on_delete=models.CASCADE
    )
    num_samples = models.IntegerField(default=100)


class MonteCarloParameter(models.Model):
    simulation = models.OneToOneField(
        SimulationRun,
        related_name='monte_params',
        on_delete=models.CASCADE
    )
    num_iterations = models.IntegerField(default=1000)

