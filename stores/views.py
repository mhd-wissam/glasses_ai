from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Store
from .serializers import StoreSerializer
from users.models import CustomUser


class StoreInfoView(APIView):
    permission_classes = [permissions.AllowAny]  # لأنه ما عنده توكن لسا

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        # ✅ بدل authenticate()
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            return Response({"detail": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

        if user.role != "store_owner":
            return Response({"detail": "Only store owners can complete this step."}, status=status.HTTP_403_FORBIDDEN)


        # تجهيز بيانات المتجر
        store_data = {
            "store_name": request.data.get("store_name"),
            "phone": request.data.get("phone"),
            "location_lat": request.data.get("location_lat"),
            "location_lng": request.data.get("location_lng"),
        }

        serializer = StoreSerializer(data=store_data)
        serializer.is_valid(raise_exception=True)
        store = serializer.save(owner=user)

        user.is_active = True
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "detail": "Store info added, account activated, and token generated.",
            "store": StoreSerializer(store).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class ListStoresView(APIView):
    permission_classes = [permissions.AllowAny]  # أي شخص يقدر يشوف المتاجر

    def get(self, request, *args, **kwargs):
        stores = Store.objects.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)