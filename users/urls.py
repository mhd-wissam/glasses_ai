from django.urls import path
from .views import UserRegisterView, MyTokenObtainPairView, LogoutView, AddStoreOwnerView, UserProfileView, FavoriteToggleView, StoreOwnersListView, UserUpdateProfileView, ChangePasswordView, FavoriteListView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('login/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('add-store-owner/', AddStoreOwnerView.as_view(), name='add-store-owner'),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("favorites/toggle/", FavoriteToggleView.as_view(), name="favorite-toggle"),
    path("store-owners/", StoreOwnersListView.as_view(), name="store-owners-list"),
    path("profile/update/", UserUpdateProfileView.as_view(), name="user-update-profile"),
    path("profile/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("favorites/", FavoriteListView.as_view(), name="favorite-list"),
]
