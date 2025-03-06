from django.contrib import admin
from .models import ForecastingGroup, UserProfile, ForecastingMember, ForecastingComment, SimulationRun, TimeSeriesData, ParameterFile, PSOParameter, LatinParameter, MonteCarloParameter, ForwardParameter, ParameterRangesFile, UserValidationFile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    fields = ('user', 'image', 'bio')
    list_display = ('id', 'user', 'image')

@admin.register(ForecastingGroup)
class GroupAdmin(admin.ModelAdmin):
    fields = ('name', 'location', 'description')
    list_display = ('id','name', 'time', 'location', 'description')


@admin.register(ForecastingMember)
class MemberAdmin(admin.ModelAdmin):
    fields = ('user', 'group', 'admin')
    list_display = ('user', 'group', 'admin', 'time')

@admin.register(ForecastingComment)
class CommentAdmin(admin.ModelAdmin):
    fields = ('user', 'group', 'description')
    list_display = ('user', 'group', 'description', 'time')

@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    fields = (
        'group', 'user', 'timeseries', 'parameter_ranges_file', 'parameters_file', 'user_validation_file', 'parameters_forward', 'model', 'mode', 'method',
        'optimizer', 'forward_options', 'error_metric', 'solver', 'interpolate', 'n_data_interpolate',
        'validation_required', 'percent', 'core', 'depth', 'compiler', 'CFL', 'databaseformat', 'computeparameterranges',
        'computeparameters', 'log_flag', 'resampling_frequency_days', 'resampling_frequency_weeks',
        'email_send', 'email_list', 'error_message', 'status', 'results_path'
    )

    list_display = (
        'id', 'group', 'user', 'timeseries', 'parameters_file', 'parameters_forward', 'model', 'mode', 'method',
        'optimizer', 'forward_options', 'error_metric', 'solver', 'interpolate', 'validation_required', 'percent',
        'compiler', 'databaseformat', 'status', 'start_time', 'end_time'
    )

@admin.register(TimeSeriesData)
class TimeSeriesDataAdmin(admin.ModelAdmin):
    fields = ('group', 'user', 'file', 'description')
    list_display = ('id', 'group', 'user', 'file', 'upload_date', 'description')

@admin.register(ParameterFile)
class ParameterFileAdmin(admin.ModelAdmin):
    fields = ('group', 'user', 'file', 'description')
    list_display = ('id', 'group', 'user', 'file', 'upload_date', 'description')

@admin.register(ForwardParameter)
class ForwardParametersAdmin(admin.ModelAdmin):
    fields = ('group', 'user', 'parameter1', 'parameter2', 'parameter3',
                    'parameter4', 'parameter5', 'parameter6', 'parameter7', 'parameter8', 'file_path')
    list_display =  ('id', 'group', 'user', 'parameter1', 'parameter2', 'parameter3',
                    'parameter4', 'parameter5', 'parameter6', 'parameter7', 'parameter8', 'file_path')

@admin.register(PSOParameter)
class PSOParametersAdmin(admin.ModelAdmin):
    fields = ('simulation','swarm_size', 'phi1', 'phi2', 'omega1', 'omega2','max_iterations')
    list_display = ('simulation','swarm_size', 'phi1', 'phi2', 'omega1', 'omega2', 'max_iterations')
@admin.register(LatinParameter)
class LatinParametersAdmin(admin.ModelAdmin):
    fields = ('simulation','num_samples',)
    list_display = ('simulation','num_samples',)

@admin.register(MonteCarloParameter)
class MonteCarloParametersAdmin(admin.ModelAdmin):
    fields = ('simulation','num_iterations',)
    list_display = ('simulation','num_iterations',)

@admin.register(ParameterRangesFile)
class ParameterRangesFileAdmin(admin.ModelAdmin):
    fields = ('group', 'user', 'file', 'description')
    list_display = ('id', 'group', 'user', 'file', 'upload_date', 'description')

@admin.register(UserValidationFile)
class UserValidationFileAdmin(admin.ModelAdmin):
    fields = ('group', 'user', 'file', 'description')
    list_display = ('id', 'group', 'user', 'file', 'upload_date', 'description')
