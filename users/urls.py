from django.urls import path
from .views import UserRegisterView, MyTokenObtainPairView, LogoutView, AddStoreOwnerView, UserProfileView, FavoriteToggleView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('add-store-owner/', AddStoreOwnerView.as_view(), name='add-store-owner'),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("favorites/toggle/", FavoriteToggleView.as_view(), name="favorite-toggle"),
]
