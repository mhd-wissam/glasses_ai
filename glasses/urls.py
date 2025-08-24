# glasses/urls.py
from django.urls import path
from .views import *
# (
#     Upload3DModelView, AddGlassesView, UploadGlassesImagesView, AddGlassesWithImagesView, 
#     ListGlassesView, RetrieveGlassesView, GlassesByMaterialFormDataView,GlassesSmartFilterView,
#     GlassesByStoreView, MyStoreGlassesView
#     )
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
    path("by/stores/<int:store_id>/", GlassesByStoreView.as_view(), name="glasses-by-store"),
    path("my-store/", MyStoreGlassesView.as_view(), name="my-store-glasses"),
    path("recommend/face-shape/", RecommendGlassesByFaceShapeView.as_view(), name="recommend-by-face-shape"),
    path("<int:glasses_id>/update/", UpdateGlassesView.as_view(), name="update-glasses"),
    path("<int:glasses_id>/delete/", DeleteGlassesView.as_view(), name="delete-glasses"),
]
