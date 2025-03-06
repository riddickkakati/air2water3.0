from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.authtoken.views import ObtainAuthToken
from django.utils import timezone
import multiprocessing as mp
import json
import time
from .models import (
    MLRun,
)

from forecasting.models import (
    UserProfile
)

from .models import (
    MLGroup, MLMember, MLComment
)

from forecasting.serializers import (
    UserSerializer, UserProfileSerializer, ChangePasswordSerializer
)

from .serializers import MLRunSerializer, MLGroupSerializer, MLGroupFullSerializer, MLMemberSerializer, \
    MLCommentSerializer, MLGroupAnalysisSerializer
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from .Air2waterML.Air2water import ML_Model
from django.conf import settings
import os
from sklearn.metrics import r2_score
import yaml


# Existing ViewSets remain unchanged
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)

    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.all()

    def update(self, request, *args, **kwargs):
        if kwargs['pk'] != str(request.user.id):
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if kwargs['pk'] != str(request.user.id):
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(methods=['PUT'], detail=True, serializer_class=ChangePasswordSerializer,
            permission_classes=[IsAuthenticated])
    def change_pass(self, request, pk):
        user = User.objects.get(pk=pk)
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            if not user.check_password(serializer.data.get('old_password')):
                return Response({'message': 'Wrong old password'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.data.get('new_password'))
            user.save()
            return Response({'message': 'Password Updated'}, status=status.HTTP_200_OK)


class MLCommentViewset(viewsets.ModelViewSet):
    queryset = MLComment.objects.all()
    serializer_class = MLCommentSerializer


class UserProfileViewset(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class MLGroupViewset(viewsets.ModelViewSet):
    queryset = MLGroup.objects.all()
    serializer_class = MLGroupSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.query_params.get('analysis_data', False):
            serializer = MLGroupAnalysisSerializer(instance, many=False, context={'request': request})
        else:
            serializer = MLGroupFullSerializer(instance, many=False, context={'request': request})
        return Response(serializer.data)


class MLMemberViewset(viewsets.ModelViewSet):
    queryset = MLMember.objects.all()
    serializer_class = MLMemberSerializer

    @action(methods=['post'], detail=False)
    def join(self, request):
        if 'group' in request.data and 'user' in request.data:
            try:
                group = MLGroup.objects.get(id=request.data['group'])
                user = User.objects.get(id=request.data['user'])

                member = MLMember.objects.create(group=group, user=user, admin=request.data.get('admin', False))
                serializer = MLMemberSerializer(member, many=False)
                response = {'message': 'Joined group', 'results': serializer.data}
                return Response(response, status=status.HTTP_200_OK)
            except:
                response = {'message': 'Cannot join'}
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        else:
            response = {'message': 'Wrong params'}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'], detail=False)
    def leave(self, request):
        if 'group' in request.data and 'user' in request.data:
            try:
                group = MLGroup.objects.get(id=request.data['group'])
                user = User.objects.get(id=request.data['user'])

                member = MLMember.objects.get(group=group, user=user)
                member.delete()
                response = {'message': 'Left group'}
                return Response(response, status=status.HTTP_200_OK)
            except:
                response = {'message': 'Group, user or member not found'}
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
        else:
            response = {'message': 'Wrong params'}
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(CustomObtainAuthToken, self).post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data['token'])
        user = User.objects.get(id=token.user_id)
        userSerilizer = UserSerializer(user, many=False)
        return Response({'token': token.key, 'user': userSerilizer.data})


class MLRunViewSet(viewsets.ModelViewSet):
    queryset = MLRun.objects.all()
    serializer_class = MLRunSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            return MLRun.objects.filter(user=self.request.user.id)
        return MLRun.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @staticmethod
    def run_ml_process(ml_run_id):
        """
        Static method to run the ML process in a separate process
        """

        def convert_to_serializable(obj):
            """Helper function to convert numpy types to Python native types"""
            import numpy as np
            if isinstance(obj, np.generic):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_to_serializable(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj

        ml_run = None
        try:
            # Get the ML run instance
            ml_run = MLRun.objects.get(pk=ml_run_id)
            start_time = time.time()

            # Create results directory
            results_dir = f"{settings.MEDIA_ROOT}/ml_results/{ml_run.user.id}_{ml_run.group.id}/"
            os.makedirs(results_dir, exist_ok=True)

            # Initialize model with parameters from MLRun instance
            model = ML_Model(
                user_id=ml_run.user_id,
                group_id=ml_run.group_id,
                model="air2water" if ml_run.model == "W" else "air2stream",
                interpolate=ml_run.interpolate,
                n_data_interpolate=ml_run.n_data_interpolate,
                validation_required=False if ml_run.validation_required == "F" else "Uniform Percentage" if ml_run.validation_required == "U" else "Random Percentage" if ml_run.validation_required == "R" else "Uniform Number",
                percent=ml_run.percent,
                air2waterusercalibrationpath=ml_run.timeseries_file.path if ml_run.model == "W" else None,
                air2streamusercalibrationpath=ml_run.timeseries_file.path if ml_run.model == "S" else None,
                air2wateruservalidationpath=ml_run.validation_file.path if ml_run.model == "W" and ml_run.validation_file else None,
                air2streamuservalidationpath=ml_run.validation_file.path if ml_run.model == "S" and ml_run.validation_file else None,
                results_file_name=f"results_{ml_run.id}.zip",
                email_send=ml_run.email_send,
                sim_id=ml_run.id,
                email_list=ml_run.email_list.split(',') if ml_run.email_list else []
            )

            # Run the analysis
            results = model.run()

            # Find best performing model
            best_val_r2 = -float('inf')
            best_model = None
            best_type = None

            # Compare original and PCA results to find best model
            for data_type in ['original', 'pca']:
                for model_name, model_data in results[data_type].items():
                    val_r2 = float(r2_score(  # Convert to float
                        model_data['val']['Evaluation_(Water_temperature_data)'],
                        model_data['val']['Best_simulation']
                    ))
                    if val_r2 > best_val_r2:
                        best_val_r2 = val_r2
                        best_model = model_name
                        best_type = data_type

            # Calculate total execution time
            total_time = float(time.time() - start_time)  # Convert to float

            # Structure the complete analysis results
            analysis_summary = {
                # Store results for each transformation type
                'original_data': {},
                'pca_data': {},
                'kpca_data': {},
                'lda_data': {},

                # Store PCA explanation ratio - convert numpy array to list
                'explained_variance_ratio': convert_to_serializable(results['explained_variance_ratio']),

                # Store best model information
                'best_model': {
                    'name': str(best_model).upper(),  # Ensure string
                    'type': 'Original' if best_type == 'original' else 'PCA',
                    'validation_r2': float(best_val_r2),  # Convert to float
                    'training_r2_mean': float(results[best_type][best_model]['cv_mean']),  # Convert to float
                    'training_r2_std': float(results[best_type][best_model]['cv_std'])  # Convert to float
                },

                # Store execution time
                'total_time': total_time,

                # Store grid search results
                'grid_search_results': convert_to_serializable(results.get('grid_search', {}))
            }

            # Calculate and store results for each transformation type
            for transform_type in ['original', 'pca', 'kpca', 'lda']:
                transform_data = {}
                if transform_type in results:
                    for model_name, model_data in results[transform_type].items():
                        # Calculate validation R² score
                        val_r2 = float(r2_score(  # Convert to float
                            model_data['val']['Evaluation_(Water_temperature_data)'],
                            model_data['val']['Best_simulation']
                        ))

                        # Store model results
                        transform_data[model_name] = {
                            'training_r2_mean': float(model_data['cv_mean']),  # Convert to float
                            'training_r2_std': float(model_data['cv_std']),  # Convert to float
                            'validation_r2': float(val_r2)  # Convert to float
                        }

                    # Store results for this transformation type
                    analysis_summary[f'{transform_type}_data'] = transform_data

            # Convert any remaining numpy types in the entire structure
            analysis_summary = convert_to_serializable(analysis_summary)

            # Create results directory if it doesn't exist
            results_dir = f"{settings.MEDIA_ROOT}/ml_results/{ml_run.user_id}_{ml_run.group_id}/"
            os.makedirs(results_dir, exist_ok=True)

            # Save results to YAML file
            yaml_path = os.path.join(results_dir, f"analysis_results_{ml_run.user.id}_{ml_run.group.id}_{ml_run.id}.yaml")
            with open(yaml_path, 'w') as f:
                yaml.dump(analysis_summary, f, default_flow_style=False)

            # Update ml_run with results
            ml_run.status = "completed"
            ml_run.results_path = f"{settings.MEDIA_ROOT}/ml_results/{ml_run.user_id}_{ml_run.group_id}/results_{ml_run.user_id}_{ml_run.group_id}_{ml_run.id}.zip"  # Store the zip file path
            ml_run.yaml_results_path = yaml_path  # Store YAML file path
            ml_run.end_time = timezone.now()
            ml_run.analysis_summary = analysis_summary
            ml_run.save()

        except MLRun.DoesNotExist:
            print(f"ML run with id {ml_run_id} not found")
            return

        except Exception as e:
            error_message = str(e)
            print(f"Error in ML run {ml_run_id}: {error_message}")

            if ml_run:
                current_time = timezone.now()
                ml_run.status = "failed"
                ml_run.error_message = error_message[:500]  # Truncate long error messages
                ml_run.end_time = current_time

                # Store error information in analysis summary
                error_summary = {
                    'status': 'failed',
                    'error': error_message[:500],
                    'end_time': current_time.isoformat()
                }
                ml_run.analysis_summary = error_summary  # Direct assignment
                ml_run.save()

        except MLRun.DoesNotExist:
            print(f"ML run with id {ml_run_id} not found")
            return

        except Exception as e:
            error_message = str(e)
            print(f"Error in ML run {ml_run_id}: {error_message}")

            if ml_run:
                current_time = timezone.now()
                ml_run.status = "failed"
                ml_run.error_message = error_message[:500]  # Truncate long error messages
                ml_run.end_time = current_time

                # Store error information in analysis summary
                error_summary = {
                    'status': 'failed',
                    'error': error_message[:500],
                    'end_time': current_time.isoformat()
                }
                ml_run.analysis_summary = json.dumps(error_summary)
                ml_run.save()

        except MLRun.DoesNotExist:
            print(f"ML run with id {ml_run_id} not found")
            return

        except Exception as e:
            error_message = str(e)
            print(f"Error in ML run {ml_run_id}: {error_message}")

            if ml_run:
                current_time = timezone.now()
                ml_run.status = "failed"
                ml_run.error_message = error_message[:500]  # Truncate long error messages
                ml_run.end_time = current_time

                # Create a minimal results JSON with error information
                results_dir = f"{settings.MEDIA_ROOT}/ml_results/{ml_run.user_id}_{ml_run.group_id}/"
                results_json_path = os.path.join(results_dir, f"results_{ml_run.id}.json")
                error_results = {
                    'status': 'failed',
                    'error': error_message[:500],
                    'end_time': current_time.isoformat()
                }

                try:
                    with open(results_json_path, 'w') as f:
                        json.dumps(error_results, f)
                except Exception as e:
                    print(f"Error saving error results JSON: {str(e)}")

                ml_run.save()

    @action(methods=['post'], detail=True)
    def run_analysis(self, request, pk=None):
        """
        Initiate the ML analysis process.
        """
        ml_run = self.get_object()

        # Check if run belongs to user
        if ml_run.user.id != request.user.id:
            return Response({"detail": "You cannot run other users' analyses."},
                            status=status.HTTP_403_FORBIDDEN)

        # Check if analysis is already running
        if ml_run.status == "running":
            # Check for timeout (5 minutes)
            time_threshold = timezone.now() - timezone.timedelta(minutes=5)
            if ml_run.updated_at < time_threshold:
                ml_run.status = "failed"
                ml_run.error_message = "Analysis timed out"
                ml_run.save()
            else:
                return Response({
                    'message': 'Analysis is already running',
                    'start_time': ml_run.start_time
                }, status=status.HTTP_400_BAD_REQUEST)

        # Validate required files
        if not ml_run.timeseries_file:
            return Response({
                'message': 'Timeseries file is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # If validation is required but not using percentage split, check validation file
        if (ml_run.validation_required == 'F' and
                not ml_run.validation_file):
            return Response({
                'message': 'Validation file is required when not using percentage split'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Update run status and timing
        ml_run.status = "running"
        ml_run.error_message = None
        ml_run.start_time = timezone.now()
        ml_run.updated_at = timezone.now()
        ml_run.end_time = None
        ml_run.analysis_summary = None  # Clear any previous results
        ml_run.save()

        # Start the analysis in a separate process
        p = mp.Process(
            target=MLRunViewSet.run_ml_process,
            args=(ml_run.id,)
        )
        p.daemon = True  # Process will be terminated if parent process ends
        p.start()

        return Response({
            'message': 'Analysis submitted successfully',
            'run_id': ml_run.id,
            'status': 'running',
            'start_time': ml_run.start_time
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def check_status(self, request, pk=None):
        ml_run = self.get_object()

        if ml_run.user.id != request.user.id:
            return Response({"detail": "You cannot access other users' data."},
                            status=status.HTTP_403_FORBIDDEN)

        response_data = {
            'status': ml_run.status,
            'start_time': ml_run.start_time,
            'end_time': ml_run.end_time,
        }

        if ml_run.status == "completed":
            # Base URL for media files
            base_url = f"{request.scheme}://{request.get_host()}/mediafiles/ml_results/{ml_run.user_id}_{ml_run.group_id}/"

            response_data.update({
                'results_zip': f"{base_url}{os.path.basename(ml_run.results_path)}",
                'results_yaml': f"{base_url}{os.path.basename(ml_run.yaml_results_path)}",
                # Include only key summary statistics
                'best_model': ml_run.analysis_summary['best_model'],
                'total_time': ml_run.analysis_summary['total_time']
            })

        elif ml_run.status == "failed" and ml_run.error_message:
            response_data['error_message'] = ml_run.error_message

        return Response(response_data)