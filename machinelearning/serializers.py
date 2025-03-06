from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from forecasting.serializers import UserSerializer
from .models import MLRun, MLGroup, MLMember, MLComment

class MLCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLComment
        fields = ('user', 'group', 'description', 'time')


class MLMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(many=False)

    class Meta:
        model = MLMember
        fields = ('user', 'group', 'admin', 'time')


class MLGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLGroup
        fields = ('id', 'name', 'location', 'description')


class MLGroupFullSerializer(serializers.ModelSerializer):
    machine_learning_members = serializers.SerializerMethodField()
    machine_learning_comments = serializers.SerializerMethodField()

    class Meta:
        model = MLGroup
        fields = ('id', 'name', 'time', 'location', 'description', 'machine_learning_members', 'machine_learning_comments')

    def get_machine_learning_comments(self, obj):
        ml_comments = MLComment.objects.filter(group=obj).order_by('-time')
        serializer = MLCommentSerializer(ml_comments, many=True)
        return serializer.data

    def get_machine_learning_members(self, obj):
        ml_members = obj.machine_learning_members.all()
        return MLMemberSerializer(ml_members, many=True).data


class MLRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLRun
        fields = (
            'id',
            'group',
            'model',
            'timeseries_file',
            'validation_file',
            'interpolate',
            'n_data_interpolate',
            'validation_required',
            'percent',
            'status',
            'start_time',
            'end_time',
            'email_send',
            'email_list',
            'results_path',
            'analysis_summary',
            'yaml_results_path',
            'error_message'
        )

    def create(self, validated_data):
        # Ensure we use the authenticated user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class MLGroupAnalysisSerializer(serializers.ModelSerializer):
    machine_learning_runs = MLRunSerializer(many=True, read_only=True)

    class Meta:
        model = MLGroup
        fields = ('id', 'name', 'location', 'description', 'machine_learning_runs')