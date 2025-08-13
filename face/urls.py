from django.urls import path
from .views import FaceAnalysisView

urlpatterns = [
    path('analyze-face/', FaceAnalysisView.as_view(), name='analyze-face'),
]
