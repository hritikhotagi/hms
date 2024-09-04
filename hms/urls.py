from django.urls import path
from .views import AddPatientToDoctorView, PatientRecordCreateView, RegisterView, DoctorListCreateView, PatientListCreateView, PatientRecordListCreateView, DepartmentListCreateView, doctor_detail_view, patient_detail_view, patient_record_detail_view, department_doctors_view, department_patients_view, DetermineRoleView

urlpatterns = [
    # Authentication endpoints
    path('register/', RegisterView.as_view(), name='register'),
    # path('logout/', LogoutView.as_view(), name='logout'),
    path('determine_role/', DetermineRoleView.as_view(), name='determine_role'),

    # Doctor endpoints
    path('doctors/', DoctorListCreateView.as_view(), name='doctor-list'),
    path('doctors/<int:pk>/', doctor_detail_view, name='doctor-detail'),
    path('doctor/add-patient/', AddPatientToDoctorView.as_view(), name='add-patient-to-doctor'),

    # Patient endpoints
    path('patients/', PatientListCreateView.as_view(), name='patient-list'),
    path('patients/<int:pk>/', patient_detail_view, name='patient-detail'),

    # PatientRecord endpoints
    path('patient_records/add/', PatientRecordCreateView.as_view(), name='patient-record-add'),
    path('patient_records/', PatientRecordListCreateView.as_view(), name='patient-record-list'),
    path('patient_records/<int:pk>/', patient_record_detail_view, name='patient-record-detail'),

    # Department endpoints
    path('departments/', DepartmentListCreateView.as_view(), name='department-list'),
    path('department/<int:pk>/doctors/', department_doctors_view, name='department-doctors'),
    path('department/<int:pk>/patients/', department_patients_view, name='department-patients'),
]
