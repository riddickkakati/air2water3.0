from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from forecasting.serializers import UserSerializer
from .models import MonitoringRun, MonitoringGroup, MonitoringMember, MonitoringComment

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringComment
        fields = ('user', 'group', 'description', 'time')


class MemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)

    class Meta:
        model = MonitoringMember
        fields = ('user', 'group', 'admin', 'time')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringGroup
        fields = ('id', 'name', 'location', 'description',)


class GroupFullSerializer(serializers.ModelSerializer):
    monitoring_members = serializers.SerializerMethodField()
    monitoring_comments = serializers.SerializerMethodField()

    class Meta:
        model = MonitoringGroup
        fields = ('id', 'name', 'time', 'location', 'description', 'monitoring_members', 'monitoring_comments')

    def get_monitoring_comments(self, obj):
        monitoring_comments = MonitoringComment.objects.filter(group=obj).order_by('-time')
        serializer = CommentSerializer(monitoring_comments, many=True)
        return serializer.data

    def get_monitoring_members(self, obj):  # Changed name to match your field
        monitoring_members = obj.monitoring_members.all()
        return MemberSerializer(monitoring_members, many=True).data


class MonitoringRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringRun
        fields = (
            'id',
            'group',
            'start_date',
            'end_date',
            'longitude',
            'latitude',
            'satellite',
            'parameter',
            'cloud_cover',
            'service_account',
            'service_key_file'
        )

    def create(self, validated_data):
        # Ensure we use the authenticated user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class GroupMonitorSerializer(serializers.ModelSerializer):
    simulations = MonitoringRunSerializer(many=True, read_only=True)

    class Meta:
        model = MonitoringGroup
        fields = ('id', 'name', 'location', 'description', 'simulations')