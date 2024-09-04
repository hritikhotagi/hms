from django.db import models
from django.contrib.auth.models import User
# import uuid

class Department(models.Model):
    name = models.CharField(max_length=255)
    diagnostics = models.TextField()
    location = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    patients = models.ManyToManyField('Patient', related_name='doctors')

    def __str__(self):
        return self.user.username

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def __str__(self):
        return self.user.username

class PatientRecord(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    diagnostics = models.TextField()
    observations = models.TextField()
    treatments = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.CASCADE)  # Keeping department here for context in records
    misc = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.created_date}"
