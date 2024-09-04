from django.shortcuts import redirect, render
from django.conf import settings
from django.views import View
import requests
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from .models import Doctor, Patient, PatientRecord, Department
from .serializers import UserSerializer, DoctorSerializer, PatientSerializer, PatientRecordSerializer, DepartmentSerializer
# from .permissions import IsDoctor, IsPatient, IsDoctorOrReadOnly, IsOwnerOrReadOnly
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout, login
from django.http import HttpResponseRedirect, HttpResponse
import urllib.parse
from decouple import config
from rest_framework.views import APIView

# Home view
def home_view(request):
    access_token = request.session.get('access_token')
    return render(request, 'home.html', {'access_token': access_token})


# Auth0 Login View
class Auth0LoginView(View):
    def get(self, request):
        auth_url = f"https://{settings.AUTH0_DOMAIN}/authorize?client_id={settings.AUTH0_CLIENT_ID}&redirect_uri={settings.AUTH0_CALLBACK_URL}&scope={settings.AUTH0_SCOPE}&response_type=code"
        return redirect(auth_url)

# Auth0 Callback View
class Auth0CallbackView(View):
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return HttpResponse('Authorization code was not returned', status=400)

        token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'authorization_code',
            'client_id': settings.AUTH0_CLIENT_ID,
            'client_secret': settings.AUTH0_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.AUTH0_CALLBACK_URL,
        }
        response = requests.post(token_url, headers=headers, data=data)
        token_info = response.json()

        if 'access_token' not in token_info:
            return HttpResponse('Failed to retrieve access token', status=400)

        # Store the access token in the session
        request.session['access_token'] = token_info['access_token']
        request.session.save()

        # print("session access token \n\n",request.session.get('access_token', None))
        # Use the access token to get user info from Auth0
        user_info_url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
        headers = {'Authorization': f"Bearer {token_info['access_token']}"}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()

        # Check if user exists in Django; if not, create one
        email = user_info['email']
        username = user_info.get('nickname', email.split('@')[0])

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, email=email)
            user.save()
        # print("!!!!!!!!!!!!!!!!!!!!!!!!\n\n",user)
        login(request, user)
        return redirect('home')

# Logout View auth0 button
def logout_view(request):
    access_token = request.session.get('access_token')
    if access_token:
        revoke_url = f"https://{settings.AUTH0_DOMAIN}/oauth/revoke"
        headers = {
            'content-type': 'application/json'
        }
        data = {
            'client_id': settings.AUTH0_CLIENT_ID,
            'client_secret': settings.AUTH0_CLIENT_SECRET,
            'token': access_token
        }
        response = requests.post(revoke_url, json=data, headers=headers)
        if response.status_code != 200:
            print('Failed to revoke token:', response.json())
    logout(request)
    return_to = urllib.parse.quote(config('Home_URL'))
    auth0_logout_url = f"https://{settings.AUTH0_DOMAIN}/v2/logout?client_id={settings.AUTH0_CLIENT_ID}&returnTo={return_to}"
    return HttpResponseRedirect(auth0_logout_url)

# Register view
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
        })
    
class DetermineRoleView(APIView):    
    def post(self, request):
        # import pdb
        # pdb.set_trace()
        auth0_user = request.auth0_user
        email = auth0_user['email']
        auth0_name = auth0_user.get('name', None)
        name_from_body = request.data.get('email', None)

        print(name_from_body, auth0_name)
        if not name_from_body:
            return Response({'detail': 'Name must be provided in the request body.'}, status=status.HTTP_400_BAD_REQUEST)

        if auth0_name != name_from_body:
            return Response({'detail': 'Name in token does not match the name provided in the body.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user exists or create a new user
        user, created = User.objects.get_or_create(
            email=email, 
            defaults={'username': email.split('@')[0], 'first_name': auth0_name}
        )

        # Determine if the user is registering as a doctor or patient
        is_doctor = request.data.get('is_doctor', None)
        department_id = request.data.get('department', None)

        if is_doctor is None:
            return Response({'detail': 'Specify whether the user is a doctor or a patient.'}, status=status.HTTP_400_BAD_REQUEST)
        if is_doctor:
            if department_id is None:
                return Response({'detail': 'Specify the department for the doctor.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                department = Department.objects.get(id=department_id)
            except Department.DoesNotExist:
                return Response({'detail': 'Department not found.'}, status=status.HTTP_404_NOT_FOUND)

            doctor, created = Doctor.objects.get_or_create(user=user, department=department)
            return Response({'message': 'User registered as a doctor', 'doctor': DoctorSerializer(doctor).data})
        else:
            patient, created = Patient.objects.get_or_create(user=user)
            return Response({'message': 'User registered as a patient', 'patient': PatientSerializer(patient).data})


# Doctors views
class DoctorListCreateView(generics.ListCreateAPIView):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = (permissions.AllowAny,)


@api_view(['GET', 'PUT', 'DELETE'])
# @permission_classes([IsDoctor, IsOwnerOrReadOnly])
def doctor_detail_view(request, pk):
    try:
        doctor = Doctor.objects.get(pk=pk)
    except Doctor.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = DoctorSerializer(doctor)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = DoctorSerializer(doctor, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        doctor.delete()
        return Response(message="Deleted",status=status.HTTP_204_NO_CONTENT)


# Patients views
class PatientListCreateView(generics.ListCreateAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = (permissions.AllowAny,)


@api_view(['GET', 'PUT', 'DELETE'])
# @permission_classes([IsPatient, IsDoctorOrReadOnly, IsOwnerOrReadOnly])
def patient_detail_view(request, pk):
    try:
        patient = Patient.objects.get(pk=pk)
    except Patient.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PatientSerializer(patient)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PatientSerializer(patient, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        patient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Add PatientRecordCreateView
class PatientRecordCreateView(generics.CreateAPIView):
    queryset = PatientRecord.objects.all()
    serializer_class = PatientRecordSerializer

    def post(self, request, *args, **kwargs):
        # Ensure the patient exists
        patient_id = request.data.get('patient')
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({'detail': 'Patient not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Handle the patient record creation
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient_record = serializer.save()

        return Response({
            "message": "Patient record created successfully.",
            "patient_record": PatientRecordSerializer(patient_record).data
        }, status=status.HTTP_201_CREATED)

# PatientRecords views
class PatientRecordListCreateView(generics.ListCreateAPIView):
    queryset = PatientRecord.objects.all()
    serializer_class = PatientRecordSerializer
    permission_classes = (permissions.AllowAny,)


@api_view(['GET', 'PUT', 'DELETE'])
# @permission_classes([IsPatient, IsDoctorOrReadOnly, IsOwnerOrReadOnly])
def patient_record_detail_view(request, pk):
    try:
        patient_record = PatientRecord.objects.get(pk=pk)
    except PatientRecord.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PatientRecordSerializer(patient_record)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PatientRecordSerializer(patient_record, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        patient_record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Departments views
class DepartmentListCreateView(generics.ListCreateAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = (permissions.AllowAny,)

@api_view(['GET', 'PUT'])
# @permission_classes([IsDoctor])
def department_doctors_view(request, pk):
    try:
        department = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        doctors = Doctor.objects.filter(department=department)
        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Update department doctors logic here
        pass


@api_view(['GET', 'PUT'])
# @permission_classes([IsDoctor])
def department_patients_view(request, pk):
    try:
        department = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        patients = Patient.objects.filter(department=department)
        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # Update department patients logic here
        pass


# View to list patients under a doctor
class DoctorPatientsView(generics.ListAPIView):
    serializer_class = PatientSerializer
    permission_classes = (permissions.AllowAny,)

    def get_queryset(self):
        # Get the authenticated user
        user = self.request.user

        # Get the doctor object associated with the user
        doctor = Doctor.objects.get(user=user)

        # Return the patients associated with this doctor
        return doctor.patients.all()


# View to add a patient to a doctor
class AddPatientToDoctorView(generics.GenericAPIView):
    serializer_class = PatientSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        try:
            # Get the doctor object for the authenticated user
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return Response({"detail": "Doctor not found for this user."}, status=status.HTTP_404_NOT_FOUND)

        # Get the patient ID from the request data
        patient_id = request.data.get('patient_id')

        try:
            # Retrieve the patient object
            patient = Patient.objects.get(id=patient_id)
            
            # Add the patient to the doctor's patient list
            doctor.patients.add(patient)
            
            # Return success response with doctor and patient details
            return Response({
                "detail": f"Patient {patient.user.username} added to Doctor {doctor.user.username} successfully.",
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.user.username,
                    "department": doctor.department.name
                },
                "patient": {
                    "id": patient.id,
                    "name": patient.user.username
                }
            }, status=status.HTTP_200_OK)

        except Patient.DoesNotExist:
            return Response({"detail": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

