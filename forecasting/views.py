from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.parsers import MultiPartParser, FormParser
from .air2water.Air2water import Air2water_OOP
from django.conf import settings
from django.utils import timezone
import multiprocessing as mp
from datetime import datetime
from .models import (
    ForecastingGroup, UserProfile, ForecastingMember, ForecastingComment,
    TimeSeriesData, ParameterFile, ForwardParameter, ParameterRangesFile, SimulationRun, UserValidationFile,
    PSOParameter, LatinParameter, MonteCarloParameter
)
from .serializers import (
    GroupSerializer, GroupFullSerializer, GroupForecastSerializer, ForwardParametersSerializer, ParameterRangesFileSerializer, UserValidationFileSerializer,
    UserSerializer, UserProfileSerializer, ChangePasswordSerializer,
    MemberSerializer, CommentSerializer, TimeSeriesDataSerializer,
    ParameterFileSerializer, SimulationRunSerializer, PSOParametersSerializer, LatinParametersSerializer, MonteCarloParametersSerializer
)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
import os
import yaml
from django.conf import settings


# Existing ViewSets remain unchanged
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    authentication_classes = (TokenAuthentication,)

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.all()

    def update(self, request, *args, **kwargs):
        # Restrict updates to the current user only
        if kwargs['pk'] != str(request.user.id):
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        if kwargs['pk'] != str(request.user.id):
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)

    def get_permissions(self):
        # Ensure all actions require authentication
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


class CommentViewset(viewsets.ModelViewSet):
    queryset = ForecastingComment.objects.all()
    serializer_class = CommentSerializer


class UserProfileViewset(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class GroupViewset(viewsets.ModelViewSet):
    queryset = ForecastingGroup.objects.all()
    serializer_class = GroupSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticatedOrReadOnly,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.query_params.get('forecast_data', False):
            serializer = GroupForecastSerializer(instance, many=False, context={'request': request})
        else:
            serializer = GroupFullSerializer(instance, many=False, context={'request': request})
        return Response(serializer.data)


class MemberViewset(viewsets.ModelViewSet):
    queryset = ForecastingMember.objects.all()
    serializer_class = MemberSerializer

    @action(methods=['post'], detail=False)
    def join(self, request):
        if 'group' in request.data and 'user' in request.data:
            try:
                group = ForecastingGroup.objects.get(id=request.data['group'])
                user = User.objects.get(id=request.data['user'])

                member = ForecastingMember.objects.create(group=group, user=user, admin=request.data.get('admin', False))
                serializer = MemberSerializer(member, many=False)
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
                group = ForecastingGroup.objects.get(id=request.data['group'])
                user = User.objects.get(id=request.data['user'])

                member = ForecastingMember.objects.get(group=group, user=user)
                member.delete()
                response = {'message': 'Left group'}
                return Response(response, status=status.HTTP_200_OK)
            except:
                response = {'message': 'ForecastingGroup, user or member not found'}
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


# New ViewSets for forecasting functionality
class TimeSeriesDataViewSet(viewsets.ModelViewSet):
    queryset = TimeSeriesData.objects.all()
    serializer_class = TimeSeriesDataSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return TimeSeriesData.objects.filter(user=self.request.user.id)
        return TimeSeriesData.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)


class ParameterFileViewSet(viewsets.ModelViewSet):
    queryset = ParameterFile.objects.all()
    serializer_class = ParameterFileSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return ParameterFile.objects.filter(user=self.request.user.id)
        return ParameterFile.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)


class ParameterForwardViewSet(viewsets.ModelViewSet):
    queryset = ForwardParameter.objects.all()
    serializer_class = ForwardParametersSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        # First save the ForwardParameter object
        forward_param = serializer.save(user=self.request.user)

        # Create the parameters dictionary in the required format
        parameters_dict = {
            'Optimized': {
                'model': 'Air2water',
                'parameters': {
                    'a1': float(forward_param.parameter1) if forward_param.parameter1 is not None else 0.0,
                    'a2': float(forward_param.parameter2) if forward_param.parameter2 is not None else 0.0,
                    'a3': float(forward_param.parameter3) if forward_param.parameter3 is not None else 0.0,
                    'a4': float(forward_param.parameter4) if forward_param.parameter4 is not None else 0.0,
                    'a5': float(forward_param.parameter5) if forward_param.parameter5 is not None else 0.0,
                    'a6': float(forward_param.parameter6) if forward_param.parameter6 is not None else 0.0,
                    'a7': float(forward_param.parameter7) if forward_param.parameter7 is not None else 0.0,
                    'a8': float(forward_param.parameter8) if forward_param.parameter8 is not None else 0.0
                }
            }
        }

        # Create the directory if it doesn't exist
        yaml_dir = os.path.join(settings.MEDIA_ROOT, 'parameters', f'{forward_param.user.id}_{forward_param.group.id}')
        os.makedirs(yaml_dir, exist_ok=True)

        # Define the YAML file path
        yaml_file_path = os.path.join(yaml_dir, 'parameters_forward.yaml')

        # Write the parameters to the YAML file
        with open(yaml_file_path, 'w') as f:
            yaml.dump(parameters_dict, f, default_flow_style=False)

        # Update the ForwardParameter object with the file path
        forward_param.file_path = yaml_file_path
        forward_param.save()

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return ForwardParameter.objects.filter(user=self.request.user.id)
        return ForwardParameter.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)

class ParameterRangesViewSet(viewsets.ModelViewSet):
    queryset = ParameterRangesFile.objects.all()
    serializer_class = ParameterRangesFileSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return ParameterRangesFile.objects.filter(user=self.request.user.id)
        return ParameterRangesFile.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)

class UserValidationViewSet(viewsets.ModelViewSet):
    queryset = UserValidationFile.objects.all()
    serializer_class = UserValidationFileSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return UserValidationFile.objects.filter(user=self.request.user.id)
        return UserValidationFile.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)


class SimulationRunViewSet(viewsets.ModelViewSet):
    queryset = SimulationRun.objects.all()
    serializer_class = SimulationRunSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        # Modify the incoming data
        data = request.data.copy()

        # Handle user data - could be either an object or ID
        user_data = request.data.get('user')
        if isinstance(user_data, dict):
            data['user'] = user_data['id']

        # Handle group data - could be either an object or ID
        group_data = request.data.get('group')
        if isinstance(group_data, dict):
            data['group'] = group_data['id']

        # Handle timeseries data - could be either an object or ID
        timeseries_data = request.data.get('timeseries')
        if isinstance(timeseries_data, dict):
            data['timeseries'] = timeseries_data['id']

        # Create serializer with modified data
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            return SimulationRun.objects.filter(user=self.request.user.id)
        return SimulationRun.objects.all()

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
    def run_simulation_process(simulation_id):
        """
        Static method to run the simulation in a separate process
        """
        simulation = None
        try:
            simulation = SimulationRun.objects.get(pk=simulation_id)

            # Build paths for required files
            results_dir = f"{settings.MEDIA_ROOT}/results/{simulation.user.id}_{simulation.group.id}/"
            os.makedirs(results_dir, exist_ok=True)

            # Get forward parameters path - either from uploaded file or from generated YAML
            forward_parameters_path = None
            if simulation.parameters_file:
                forward_parameters_path = simulation.parameters_file.file.path
            elif simulation.parameters_forward:
                forward_parameters_path = simulation.parameters_forward.file_path

            # Initialize model with correct parameters

            swarm_size = simulation.pso_params.swarm_size if hasattr(simulation,
                                                                     'pso_params') and simulation.pso_params else None
            phi1 = simulation.pso_params.phi1 if hasattr(simulation, 'pso_params') and simulation.pso_params else None
            phi2 = simulation.pso_params.phi2 if hasattr(simulation, 'pso_params') and simulation.pso_params else None
            omega1 = simulation.pso_params.omega1 if hasattr(simulation, 'pso_params') and simulation.pso_params else None
            omega2 = simulation.pso_params.omega2 if hasattr(simulation,
                                                             'pso_params') and simulation.pso_params else None
            max_iterations = simulation.pso_params.max_iterations if hasattr(simulation,
                                                                             'pso_params') and simulation.pso_params else None
            if hasattr(simulation, 'latin_params') and simulation.latin_params:
                numbersim = simulation.latin_params.num_samples
            elif hasattr(simulation, 'monte_params') and simulation.monte_params:
                numbersim = simulation.monte_params.num_iterations
            else:
                numbersim = None

            try:
                model = Air2water_OOP(
                    user_id=simulation.user.id,
                    group_id=simulation.group.id,
                    interpolate=simulation.interpolate,
                    n_data_interpolate=simulation.n_data_interpolate,
                    validation_required=False if simulation.validation_required == "F" else "Uniform Percentage" if simulation.validation_required == "U" else "Random Percentage" if simulation.validation_required == "R" else "Uniform Number",
                    percent=simulation.percent,
                    model="air2water" if simulation.model == "W" else "air2stream",
                    core=simulation.core,
                    depth=simulation.depth,
                    db_file=f"{results_dir}{simulation.method}_calibration_{simulation.id}.db",
                    results_file_name=f"{results_dir}results_{simulation_id}.db",
                    swarmsize=swarm_size,
                    phi1=phi1,
                    phi2=phi2,
                    omega1=omega1,
                    omega2=omega2,
                    maxiter=max_iterations,
                    numbersim=numbersim,
                    method="SpotPY" if simulation.method == "S" else "PYCUP",
                    mode="calibration" if simulation.mode == "C" else "forward",
                    error="RMSE" if simulation.error_metric == "R" else "KGE" if simulation.error_metric == "K" else "NS",
                    optimizer="PSO" if simulation.optimizer == "P" else "LHS" if simulation.optimizer == "L" else "MC",
                    solver="cranknicolson" if simulation.solver == "C" else "rk2" if simulation.solver == "T" else "rk4" if simulation.solver == "F" else "euler",
                    compiler="fortran" if simulation.compiler == "F" else "C",
                    CFL=simulation.CFL,
                    databaseformat="custom" if simulation.databaseformat == "C" else "ram",
                    computeparametersranges="Yes" if simulation.computeparameterranges else "No",
                    computeparameters="Yes" if simulation.computeparameters else "No",
                    forward_parameters=forward_parameters_path,
                    parameter_ranges=simulation.parameter_ranges_file.file.path if simulation.parameter_ranges_file else None,
                    air2waterusercalibrationpath=simulation.timeseries.file.path if simulation.timeseries else None,
                    air2streamusercalibrationpath=simulation.timeseries.file.path if simulation.timeseries else None,
                    air2wateruservalidationpath=simulation.user_validation_file.file.path if simulation.user_validation_file else None,
                    air2streamuservalidationpath=simulation.user_validation_file.file.path if simulation.user_validation_file else None,
                    log_flag=1 if simulation.log_flag else 0,
                    resampling_frequency_days=simulation.resampling_frequency_days,
                    resampling_frequency_weeks=simulation.resampling_frequency_weeks,
                    email_send=1 if simulation.email_send else 0,
                    sim_id=simulation.id,
                    email_list=simulation.email_list.split(',') if simulation.email_list else []
                )

                # Run the simulation
                num_missing_col3 = model.run()

                # Update simulation with results
                simulation.status = "completed"
                simulation.results_path = results_dir
                simulation.save()

                if num_missing_col3 == None:
                    simulation.status = "failed"
                    simulation.error_message = str(
                        "Validation file or flags not found for \"Validation Required\"= False. Either put \"Validation Required\"=True, or add flag, or add validation file.")
                    simulation.save()

            except TypeError as e:
                if "unsupported operand type(s) for /: 'list' and 'float'" in str(e):
                    simulation.status = "failed"
                    simulation.error_message = "Please provide proper input parameters (check parameter values a1-a8)"
                    simulation.save()
                elif "Execution failed on sql 'SELECT * FROM RESULTS': no such table: RESULTS" in str(e):
                    simulation.status = "failed"
                    simulation.error_message = "Please provide proper hyperparameters (settings) for the model calibration"
                    simulation.save()
                else:
                    raise

        except SimulationRun.DoesNotExist:
            # Handle case where simulation object doesn't exist
            print(f"Simulation with id {simulation_id} not found")
            return

        except Exception as e:
            error_message = str(e)
            print(f"Error in simulation {simulation_id}: {error_message}")

            if simulation:
                simulation.status = "failed"
                simulation.error_message = error_message[:500]  # Truncate if too long
                simulation.save()

    @action(methods=['post'], detail=True)
    def run_simulation(self, request, pk=None):
        simulation = self.get_object()

        # Check if simulation belongs to user
        if simulation.user.id != request.user.id:
            return Response({"detail": "You cannot run other users' simulations."},
                            status=status.HTTP_403_FORBIDDEN)

        # Check if simulation is already running
        if simulation.status == "running":
            # Double check if it's been running for too long (e.g., 24 hours)
            # This helps recover from failed runs that didn't update status
            time_threshold = timezone.now() - timezone.timedelta(minutes=5)
            if simulation.updated_at < time_threshold:
                simulation.status = "failed"
                simulation.error_message = "Simulation timed out"
                simulation.save()
            else:
                return Response({
                    'message': 'Simulation is already running'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Update simulation status to running
        simulation.status = "running"
        simulation.error_message = None  # Clear any previous error message
        simulation.updated_at = timezone.now()
        simulation.save()

        # Start the simulation in a separate process
        p = mp.Process(
            target=SimulationRunViewSet.run_simulation_process,
            args=(simulation.id,)
        )
        p.daemon = True  # Make process exit when main program exits
        p.start()

        return Response({
            'message': 'Simulation submitted successfully',
            'simulation_id': simulation.id
        }, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True)
    def check_status(self, request, pk=None):
        simulation = self.get_object()

        if simulation.user.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        results_path = f"{request.scheme}://{request.get_host()}/mediafiles/results/{simulation.user.id}_{simulation.group.id}/"
        response_data = {
            'status': simulation.status,
            'calibration_plot_path': f"{results_path}calibration_best_modelrun_{simulation.id}.png" if simulation.status == "completed" else None,
            'validation_plot_path': f"{results_path}validation_best_modelrun_{simulation.id}.png" if simulation.status == "completed" else None,
            'dotty_plots': f"{results_path}dottyplots_{simulation.id}.png" if (
                        simulation.status == "completed" and simulation.mode != "forward") else None,
            'obj_function_path': f"{results_path}objectivefunctiontrace_{simulation.id}.png" if (simulation.status == "completed" and simulation.mode != "forward") else None,
            'parameter_convergence': f"{results_path}{simulation.method}_calibration_{simulation.id}.csv" if simulation.status == "completed" else None,
            'calibration_timeseries_path': f"{results_path}results_{simulation.id}_calibration.csv" if simulation.status == "completed" else None,
            'validation_timeseries_path': f"{results_path}results_{simulation.id}_validation.csv" if simulation.status == "completed" else None
        }

        # Include error message if simulation failed
        if simulation.status == "failed" and hasattr(simulation, 'error_message'):
            response_data['error_message'] = simulation.error_message

        return Response(response_data)

class PSOParametersViewSet(viewsets.ModelViewSet):
    queryset = PSOParameter.objects.all()
    serializer_class = PSOParametersSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        # Remove the user=self.request.user part
        serializer.save()  # Just save without adding user

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return PSOParameter.objects.filter(user=self.request.user.id)
        return PSOParameter.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)

class LatinParameterViewSet(viewsets.ModelViewSet):
    queryset = LatinParameter.objects.all()
    serializer_class = LatinParametersSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save()

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return LatinParameter.objects.filter(user=self.request.user.id)
        return LatinParameter.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)

class MonteCarloParameterViewSet(viewsets.ModelViewSet):
    queryset = MonteCarloParameter.objects.all()
    serializer_class = MonteCarloParametersSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        serializer.save()

    def get_queryset(self):
        # Ensure `get_queryset` always returns a valid queryset
        if self.action in ['list', 'retrieve']:
            return MonteCarloParameter.objects.filter(user=self.request.user.id)
        return MonteCarloParameter.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # Restrict partial updates to the current user only
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot update other users' data."}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Retrieve the object to be deleted
        instance = self.get_object()

        # Check if the instance belongs to the authenticated user
        if instance.id != request.user.id:
            return Response({"detail": "You cannot delete other users' data."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to delete the instance
        return super().destroy(request, *args, **kwargs)