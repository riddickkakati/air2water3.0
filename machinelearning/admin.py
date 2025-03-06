from django.contrib import admin
from .models import MLRun, MLGroup, MLMember, MLComment


@admin.register(MLGroup)
class MLGroupAdmin(admin.ModelAdmin):
    fields = ('name', 'location', 'description')
    list_display = ('id', 'name', 'time', 'location', 'description')
    search_fields = ('name', 'location')
    list_filter = ('time',)


@admin.register(MLMember)
class MLMemberAdmin(admin.ModelAdmin):
    fields = ('user', 'group', 'admin')
    list_display = ('user', 'group', 'admin', 'time')
    search_fields = ('user__username', 'group__name')
    list_filter = ('admin', 'time')


@admin.register(MLComment)
class MLCommentAdmin(admin.ModelAdmin):
    fields = ('user', 'group', 'description')
    list_display = ('user', 'group', 'description', 'time')
    search_fields = ('user__username', 'group__name', 'description')
    list_filter = ('time',)


@admin.register(MLRun)
class MLRunAdmin(admin.ModelAdmin):
    fields = (
        'user',
        'group',
        'model',
        'timeseries_file',
        'validation_file',
        'interpolate',
        'n_data_interpolate',
        'validation_required',
        'percent',
        'status',
        'end_time',
        'email_send',
        'email_list',
        'results_path',
        'analysis_summary',
        'yaml_results_path',
        'error_message'
    )

    list_display = (
        'id',
        'user',
        'group',
        'model',
        'validation_required',
        'status',
        'start_time',
        'end_time'
    )

