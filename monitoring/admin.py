from django.contrib import admin
from .models import MonitoringRun, MonitoringGroup, MonitoringMember, MonitoringComment


@admin.register(MonitoringGroup)
class GroupAdmin(admin.ModelAdmin):
    fields = ('name', 'location', 'description')
    list_display = ('id','name', 'time', 'location', 'description')


@admin.register(MonitoringMember)
class MemberAdmin(admin.ModelAdmin):
    fields = ('user', 'group', 'admin')
    list_display = ('user', 'group', 'admin', 'time')

@admin.register(MonitoringComment)
class CommentAdmin(admin.ModelAdmin):
    fields = ('user', 'group', 'description')
    list_display = ('user', 'group', 'description', 'time')


@admin.register(MonitoringRun)
class SimulationRunAdmin(admin.ModelAdmin):
    fields = (
        'user',
        'group',
        'start_date',
        'end_date',
        'longitude',
        'latitude',
        'satellite',
        'parameter',
        'cloud_cover',
        'service_account',
        'service_key_file',
        'status'
    )

    list_display = (
            'user',
            'group',
            'start_date',
            'end_date',
            'longitude',
            'latitude',
            'satellite',
            'parameter',
            'cloud_cover',
            'service_account',
            'service_key_file',
            'status'
        )
