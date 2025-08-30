from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Store
from .serializers import StoreSerializer
from users.models import CustomUser

from rest_framework.parsers import MultiPartParser, FormParser

class StoreInfoView(APIView):
    permission_classes = [permissions.AllowAny]  # لأنه ما عنده توكن لسا
    parser_classes = [MultiPartParser, FormParser]

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

        # تجهيز بيانات المتجر (مع الصورة)
        store_data = {
            "store_name": request.data.get("store_name"),
            "phone": request.data.get("phone"),
            "location_lat": request.data.get("location_lat"),
            "location_lng": request.data.get("location_lng"),
            "image": request.FILES.get("image"),   # 👈 إضافة الصورة هنا
        }

        serializer = StoreSerializer(data=store_data)
        serializer.is_valid(raise_exception=True)
        store = serializer.save(owner=user)

        # تفعيل الحساب
        user.is_active = True
        user.save()

        # توليد التوكين
        refresh = RefreshToken.for_user(user)

        return Response({
            "detail": "Store info added, account activated, and token generated.",
            "store": StoreSerializer(store, context={"request": request}).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class ListStoresView(APIView):
    permission_classes = [permissions.AllowAny]  # أي شخص يقدر يشوف المتاجر

    def get(self, request, *args, **kwargs):
        stores = Store.objects.all()
        serializer = StoreSerializer(stores, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class MyStoreInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # ✅ جلب متجر المستخدم الحالي
        user = request.user
        if not hasattr(user, "store"):
            return Response({"detail": "You do not own a store."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StoreSerializer(user.store, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        # ✅ تعديل بيانات المتجر (كاملة)
        user = request.user
        if not hasattr(user, "store"):
            return Response({"detail": "You do not own a store."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StoreSerializer(user.store, data=request.data, partial=False, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        # ✅ تعديل بيانات المتجر (جزئية)
        user = request.user
        if not hasattr(user, "store"):
            return Response({"detail": "You do not own a store."}, status=status.HTTP_404_NOT_FOUND)

        serializer = StoreSerializer(user.store, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)