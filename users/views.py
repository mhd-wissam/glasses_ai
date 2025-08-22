from rest_framework.response import Response
from rest_framework import status, generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .models import CustomUser
from .serializers import UserRegisterSerializer, MyTokenObtainPairSerializer, StoreOwnerCreateSerializer
from .serializers import UserUpdateSerializer, ChangePasswordSerializer
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer   # لازم تكون عامل Serializer لليوزر

class UserRegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserRegisterSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class AddStoreOwnerView(generics.CreateAPIView):
    queryset = CustomUser.objects.filter(role='store_owner')
    serializer_class = StoreOwnerCreateSerializer
    permission_classes = [permissions.IsAdminUser]


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful."}, status=status.HTTP_205_RESET_CONTENT)
        except KeyError:
            return Response({"detail": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        except TokenError:
            return Response({"detail": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # اليوزر المستخرج من الـ Token
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
# users/views.py
from rest_framework import generics, permissions
from .models import Favorite
from .serializers import FavoriteSerializer

class FavoriteToggleView(generics.CreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        glasses = self.request.data.get("glasses")

        favorite, created = Favorite.objects.get_or_create(
            user=user,
            glasses_id=glasses,
            defaults={"is_favorite": True}
        )

        if not created:  # موجودة مسبقًا
            favorite.is_favorite = not favorite.is_favorite
            favorite.save()

        serializer.instance = favorite

class StoreOwnersListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(role='store_owner')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  # يفضل تخليها للـ admin فقط

class UserUpdateProfileView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # المستخدم يعدل حسابه الشخصي فقط
        return self.request.user  

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"detail": "Password changed successfully."},
            status=status.HTTP_200_OK
        )
    
from rest_framework import generics, permissions
from glasses.models import Glasses
from glasses.serializers import GlassesSerializer

class FavoriteListView(generics.ListAPIView):
    serializer_class = GlassesSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Glasses.objects.filter(
            favorites__user=self.request.user,
            favorites__is_favorite=True
        ).prefetch_related("images", "purposes").select_related("store")