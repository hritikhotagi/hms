from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Doctor, Patient, PatientRecord, Department

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    is_doctor = serializers.BooleanField(write_only=True, required=True)  # Specify if the user is a doctor
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'is_doctor', 'department')

    def create(self, validated_data):
        is_doctor = validated_data.pop('is_doctor', False)
        department = validated_data.pop('department', None)

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

        if is_doctor and department:
            # Create doctor profile
            Doctor.objects.create(user=user, department=department)
        else:
            # Create patient profile without department
            Patient.objects.create(user=user)

        return user
    
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'diagnostics', 'location', 'specialization']

class PatientRecordSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all())

    class Meta:
        model = PatientRecord
        fields = ['id', 'patient', 'created_date', 'diagnostics', 'observations', 'treatments', 'department', 'misc']

class DoctorSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    department = DepartmentSerializer(read_only=True)
    patients = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all(), many=True)

    class Meta:
        model = Doctor
        fields = ['id', 'user', 'department', 'patients']

class PatientSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    department = DepartmentSerializer(read_only=True)
    doctors = serializers.PrimaryKeyRelatedField(queryset=Doctor.objects.all(), many=True)

    class Meta:
        model = Patient
        fields = ['id', 'user', 'department', 'doctors']
