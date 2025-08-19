# glasses/urls.py
from django.urls import path
from .views import Upload3DModelView, AddGlassesView, UploadGlassesImagesView, AddGlassesWithImagesView, ListGlassesView, RetrieveGlassesView, GlassesByMaterialFormDataView,GlassesSmartFilterView
from .views import GlassesDetailView
urlpatterns = [
    path('upload-model/', Upload3DModelView.as_view(), name='upload-model'),
    path('add/', AddGlassesView.as_view(), name='add-glasses'),
    path('upload-images/', UploadGlassesImagesView.as_view(), name='upload-glasses-images'),
    path('add-with-images/', AddGlassesWithImagesView.as_view(), name='add-with-images'),
    path('list/', ListGlassesView.as_view(), name='list-glasses'),
    path('<int:id>/', RetrieveGlassesView.as_view(), name='get-glasses-by-id'),  
    path('by-material-formdata/', GlassesByMaterialFormDataView.as_view(), name='glasses-by-material-formdata'),
    path('filter/', GlassesSmartFilterView.as_view(), name='glasses-filter'),
    path("detail/<int:glasses_id>/", GlassesDetailView.as_view(), name="glasses-detail"),
]
